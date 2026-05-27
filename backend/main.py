"""FastAPI main application for D2CAgent."""

import asyncio
import json
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import settings
from backend.database.database import get_db, init_db
from backend.database.models import (
    Agent, Brand, Conversation, Flag,
    Product, Workflow, WorkflowRun, AgentLog
)
from backend.logger import setup_logger
from backend.runtime.graph import run_workflow

# Windows asyncio fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

logger = setup_logger(__name__)

# FastAPI app
app = FastAPI(
    title="D2CAgent — AI Agent Orchestration Platform",
    description="Multi-agent platform for D2C brands",
    version="1.0.0"
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# WebSocket connection manager
class ConnectionManager:
    """Manages active WebSocket connections for live monitoring."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()


# ─── Startup ───────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()
    logger.info("D2CAgent started successfully")


# ─── Health Check ──────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "brand": settings.brand_name,
        "timestamp": datetime.utcnow().isoformat()
    }


# ─── Telegram Webhook ──────────────────────────────────────

@app.post("/telegram/webhook")
async def telegram_webhook(request: Dict[str, Any]):
    """Receive messages from Telegram and trigger workflow.
    
    Telegram sends POST requests here when customer messages the bot.
    Extracts chat_id and message text, runs the workflow.
    """
    try:
        # Extract message data
        message = request.get("message", {})
        if not message:
            return {"ok": True}

        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        text = message.get("text", "").strip()
        first_name = chat.get("first_name", "")

        if not chat_id or not text:
            return {"ok": True}

        # Skip bot commands except /start
        if text.startswith("/") and text != "/start":
            return {"ok": True}

        # Handle /start command
        if text == "/start":
            text = "Hello, I need help with my order"

        logger.info(
            f"Telegram message from {chat_id}: {text[:50]}")

        # Broadcast to monitoring dashboard
        await manager.broadcast({
            "type": "message_received",
            "chat_id": chat_id,
            "message": text,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Run workflow asynchronously
        asyncio.create_task(
            run_workflow_and_broadcast(
                telegram_chat_id=chat_id,
                customer_message=text,
                customer_name=first_name
            )
        )

        return {"ok": True}

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": True}


async def run_workflow_and_broadcast(
    telegram_chat_id: str,
    customer_message: str,
    customer_name: Optional[str] = None
):
    """Run workflow and broadcast events to dashboard."""
    try:
        final_state = await run_workflow(
            telegram_chat_id=telegram_chat_id,
            customer_message=customer_message,
            customer_name=customer_name
        )

        # Broadcast completion event
        await manager.broadcast({
            "type": "workflow_complete",
            "chat_id": telegram_chat_id,
            "intent": final_state.get("intent"),
            "agents_used": [
                log["agent_name"]
                for log in final_state.get("agent_logs", [])
            ],
            "total_tokens": final_state.get("total_tokens", 0),
            "total_cost_usd": final_state.get("total_cost_usd", 0.0),
            "timestamp": datetime.utcnow().isoformat()
        })

        # Broadcast each agent log
        for log in final_state.get("agent_logs", []):
            await manager.broadcast({
                "type": "agent_log",
                **log
            })

    except Exception as e:
        logger.error(f"Workflow broadcast error: {e}")
        await manager.broadcast({
            "type": "workflow_error",
            "chat_id": telegram_chat_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })


# ─── WebSocket Monitoring ──────────────────────────────────

@app.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    """WebSocket endpoint for live monitoring dashboard."""
    await manager.connect(websocket)
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ─── Agent CRUD ────────────────────────────────────────────

class AgentCreate(BaseModel):
    """Request model for creating an agent."""
    name: str
    role: str
    system_prompt: str
    model: str = "llama-3.1-70b-versatile"
    tools: List[str] = []
    skills: List[str] = []
    guardrails: Dict[str, Any] = {}
    interaction_rules: List[str] = []
    memory_enabled: bool = False
    channel: str = "telegram"
    schedule: Optional[str] = None


class AgentUpdate(BaseModel):
    """Request model for updating an agent."""
    name: Optional[str] = None
    role: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    guardrails: Optional[Dict[str, Any]] = None
    interaction_rules: Optional[List[str]] = None
    memory_enabled: Optional[bool] = None
    channel: Optional[str] = None
    schedule: Optional[str] = None


@app.get("/agents")
async def get_agents():
    """Get all agents for the brand."""
    db = next(get_db())
    try:
        agents = db.query(Agent).filter_by(
            brand_id=settings.brand_id).all()
        return [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "role": a.role,
                "system_prompt": a.system_prompt,
                "model": a.model,
                "tools": a.tools,
                "skills": a.skills,
                "guardrails": a.guardrails,
                "interaction_rules": a.interaction_rules,
                "memory_enabled": a.memory_enabled,
                "channel": a.channel,
                "schedule": a.schedule,
                "created_at": a.created_at.isoformat()
            }
            for a in agents
        ]
    finally:
        db.close()


@app.post("/agents")
async def create_agent(agent: AgentCreate):
    """Create a new agent."""
    db = next(get_db())
    try:
        new_agent = Agent(
            agent_id=str(uuid.uuid4()),
            brand_id=settings.brand_id,
            name=agent.name,
            role=agent.role,
            system_prompt=agent.system_prompt,
            model=agent.model,
            tools=json.dumps(agent.tools),
            skills=json.dumps(agent.skills),
            guardrails=json.dumps(agent.guardrails),
            interaction_rules=json.dumps(agent.interaction_rules),
            memory_enabled=agent.memory_enabled,
            channel=agent.channel,
            schedule=agent.schedule
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        logger.info(f"Agent created: {agent.name}")
        return {"agent_id": new_agent.agent_id, "name": new_agent.name}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get a single agent by ID."""
    db = next(get_db())
    try:
        agent = db.query(Agent).filter_by(
            agent_id=agent_id,
            brand_id=settings.brand_id
        ).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "role": agent.role,
            "system_prompt": agent.system_prompt,
            "model": agent.model,
            "tools": agent.tools,
            "skills": agent.skills,
            "guardrails": agent.guardrails,
            "interaction_rules": agent.interaction_rules,
            "memory_enabled": agent.memory_enabled,
            "channel": agent.channel,
            "schedule": agent.schedule,
            "created_at": agent.created_at.isoformat()
        }
    finally:
        db.close()


@app.put("/agents/{agent_id}")
async def update_agent(agent_id: str, update: AgentUpdate):
    """Update an existing agent."""
    db = next(get_db())
    try:
        agent = db.query(Agent).filter_by(
            agent_id=agent_id,
            brand_id=settings.brand_id
        ).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        if update.name is not None:
            agent.name = update.name
        if update.role is not None:
            agent.role = update.role
        if update.system_prompt is not None:
            agent.system_prompt = update.system_prompt
        if update.model is not None:
            agent.model = update.model
        if update.tools is not None:
            agent.tools = json.dumps(update.tools)
        if update.skills is not None:
            agent.skills = json.dumps(update.skills)
        if update.guardrails is not None:
            agent.guardrails = json.dumps(update.guardrails)
        if update.interaction_rules is not None:
            agent.interaction_rules = json.dumps(update.interaction_rules)
        if update.memory_enabled is not None:
            agent.memory_enabled = update.memory_enabled
        if update.channel is not None:
            agent.channel = update.channel
        if update.schedule is not None:
            agent.schedule = update.schedule
        db.commit()
        logger.info(f"Agent updated: {agent_id}")
        return {"agent_id": agent_id, "updated": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent."""
    db = next(get_db())
    try:
        agent = db.query(Agent).filter_by(
            agent_id=agent_id,
            brand_id=settings.brand_id
        ).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        db.delete(agent)
        db.commit()
        logger.info(f"Agent deleted: {agent_id}")
        return {"agent_id": agent_id, "deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ─── Workflow CRUD ─────────────────────────────────────────

@app.get("/workflows")
async def get_workflows():
    """Get all workflows for the brand."""
    db = next(get_db())
    try:
        workflows = db.query(Workflow).filter_by(
            brand_id=settings.brand_id).all()
        return [
            {
                "workflow_id": w.workflow_id,
                "name": w.name,
                "description": w.description,
                "agent_sequence": w.agent_sequence,
                "conditional_edges": w.conditional_edges,
                "loop_config": w.loop_config,
                "is_template": w.is_template,
                "status": w.status,
                "created_at": w.created_at.isoformat()
            }
            for w in workflows
        ]
    finally:
        db.close()


# ─── Monitoring ────────────────────────────────────────────

@app.get("/monitoring/logs")
async def get_logs(limit: int = 50):
    """Get recent agent logs for monitoring dashboard."""
    db = next(get_db())
    try:
        logs = db.query(AgentLog).filter_by(
            brand_id=settings.brand_id
        ).order_by(
            AgentLog.timestamp.desc()
        ).limit(limit).all()
        return [
            {
                "log_id": l.log_id,
                "agent_name": l.agent_name,
                "action": l.action,
                "tool_called": l.tool_called,
                "tokens_used": l.tokens_used,
                "cost_usd": l.cost_usd,
                "status": l.status,
                "timestamp": l.timestamp.isoformat()
            }
            for l in logs
        ]
    finally:
        db.close()


@app.get("/monitoring/conversations")
async def get_conversations(limit: int = 50):
    """Get recent conversations for monitoring dashboard."""
    db = next(get_db())
    try:
        convs = db.query(Conversation).filter_by(
            brand_id=settings.brand_id
        ).order_by(
            Conversation.timestamp.desc()
        ).limit(limit).all()
        return [
            {
                "conversation_id": c.conversation_id,
                "telegram_chat_id": c.telegram_chat_id,
                "agent_name": c.agent_name,
                "message": c.message,
                "direction": c.direction,
                "intent": c.intent,
                "timestamp": c.timestamp.isoformat()
            }
            for c in convs
        ]
    finally:
        db.close()


@app.get("/monitoring/flags")
async def get_flags():
    """Get all open flags for human review."""
    db = next(get_db())
    try:
        flags = db.query(Flag).filter_by(
            brand_id=settings.brand_id,
            status="open"
        ).order_by(Flag.created_at.desc()).all()
        return [
            {
                "flag_id": f.flag_id,
                "reason": f.reason,
                "urgency": f.urgency,
                "raised_by_agent": f.raised_by_agent,
                "order_id": f.order_id,
                "status": f.status,
                "created_at": f.created_at.isoformat()
            }
            for f in flags
        ]
    finally:
        db.close()


@app.put("/monitoring/flags/{flag_id}/resolve")
async def resolve_flag(flag_id: str):
    """Mark a flag as resolved."""
    db = next(get_db())
    try:
        flag = db.query(Flag).filter_by(flag_id=flag_id).first()
        if not flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        flag.status = "resolved"
        flag.resolved_at = datetime.utcnow()
        flag.resolved_by = "human"
        db.commit()
        return {"flag_id": flag_id, "resolved": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.get("/monitoring/runs")
async def get_workflow_runs(limit: int = 20):
    """Get recent workflow runs."""
    db = next(get_db())
    try:
        runs = db.query(WorkflowRun).filter_by(
            brand_id=settings.brand_id
        ).order_by(
            WorkflowRun.started_at.desc()
        ).limit(limit).all()
        return [
            {
                "run_id": r.run_id,
                "workflow_id": r.workflow_id,
                "telegram_chat_id": r.telegram_chat_id,
                "trigger_message": r.trigger_message,
                "status": r.status,
                "total_tokens": r.total_tokens,
                "total_cost_usd": r.total_cost_usd,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat()
                    if r.completed_at else None
            }
            for r in runs
        ]
    finally:
        db.close()


# ─── Products ──────────────────────────────────────────────

@app.get("/products")
async def get_products():
    """Get all active products."""
    db = next(get_db())
    try:
        products = db.query(Product).filter_by(
            brand_id=settings.brand_id,
            is_active=True
        ).all()
        return [
            {
                "product_id": p.product_id,
                "name": p.name,
                "category": p.category,
                "price": p.price,
                "stock_quantity": p.stock_quantity,
                "description": p.description,
                "age_group": p.age_group
            }
            for p in products
        ]
    finally:
        db.close()


# ─── Telegram Webhook Setup ────────────────────────────────

@app.post("/setup/webhook")
async def setup_webhook(ngrok_url: str):
    """Set Telegram webhook URL.
    
    Call this after starting ngrok with the ngrok URL.
    Example: POST /setup/webhook?ngrok_url=https://abc.ngrok-free.app
    """
    import telegram
    try:
        bot = telegram.Bot(token=settings.telegram_bot_token)
        webhook_url = f"{ngrok_url}/telegram/webhook"
        async with bot:
            await bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set: {webhook_url}")
        return {
            "success": True,
            "webhook_url": webhook_url
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )