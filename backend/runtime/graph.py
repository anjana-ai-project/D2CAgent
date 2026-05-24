"""LangGraph graph builder for D2CAgent workflow orchestration."""

from datetime import datetime
from typing import Any, Dict, Optional
import json
import uuid

from langgraph.graph import StateGraph, END

from backend.agents.compensation_agent import CompensationAgent
from backend.agents.response_agent import ResponseAgent
from backend.agents.shipping_agent import ShippingAgent
from backend.agents.support_agent import SupportAgent
from backend.config import settings
from backend.database.database import get_db
from backend.database.models import Agent, Workflow, WorkflowRun
from backend.logger import setup_logger
from backend.runtime.state import AgentState, create_initial_state

logger = setup_logger(__name__)


def load_agent_configs(brand_id: str) -> Dict[str, Dict]:
    """Load all agent configs from SQLite for a brand.
    
    Returns dict keyed by role:
    support, shipping, compensation, response
    """
    db = next(get_db())
    try:
        agents = db.query(Agent).filter_by(brand_id=brand_id).all()
        configs = {}
        for agent in agents:
            configs[agent.role] = {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "role": agent.role,
                "system_prompt": agent.system_prompt,
                "model": agent.model,
                "tools": agent.tools,
                "guardrails": agent.guardrails,
                "interaction_rules": agent.interaction_rules,
                "memory_enabled": agent.memory_enabled
            }
        return configs
    finally:
        db.close()


def load_workflow(workflow_id: str) -> Optional[Dict]:
    """Load workflow config from SQLite by workflow_id."""
    db = next(get_db())
    try:
        workflow = db.query(Workflow).filter_by(
            workflow_id=workflow_id).first()
        if not workflow:
            return None
        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "agent_sequence": workflow.agent_sequence,
            "conditional_edges": workflow.conditional_edges,
            "loop_config": workflow.loop_config
        }
    finally:
        db.close()


def create_run_record(
    workflow_id: str,
    brand_id: str,
    telegram_chat_id: str,
    trigger_message: str
) -> str:
    """Create a WorkflowRun record in SQLite.
    
    Returns run_id string.
    Called at the start of every workflow execution.
    """
    run_id = str(uuid.uuid4())
    db = next(get_db())
    try:
        run = WorkflowRun(
            run_id=run_id,
            workflow_id=workflow_id,
            brand_id=brand_id,
            telegram_chat_id=telegram_chat_id,
            trigger_message=trigger_message,
            status="running",
            started_at=datetime.utcnow()
        )
        db.add(run)
        db.commit()
        return run_id
    finally:
        db.close()


def complete_run_record(
    run_id: str,
    state: AgentState,
    status: str = "completed"
) -> None:
    """Update WorkflowRun record when workflow completes.
    
    Saves total tokens, cost and completion time.
    """
    db = next(get_db())
    try:
        run = db.query(WorkflowRun).filter_by(
            run_id=run_id).first()
        if run:
            run.status = status
            run.completed_at = datetime.utcnow()
            run.total_tokens = state["total_tokens"]
            run.total_cost_usd = state["total_cost_usd"]
            db.commit()
    finally:
        db.close()


def route_from_support(state: AgentState) -> str:
    """Conditional routing from Support Agent.
    
    Reads intent from state and returns next agent name.
    Safety alerts always go directly to response.
    """
    intent = state.get("intent", "simple_faq")
    is_safety = state.get("is_safety_alert", False)

    if is_safety:
        logger.info("Safety alert — routing direct to response")
        return "response"

    routing = {
        "order_status": "shipping",
        "order_modification": "shipping",
        "complaint": "compensation",
        "return_request": "compensation",
        "cancellation": "compensation",
        "simple_faq": "response",
        "product_query": "response",
        "positive_feedback": "response",
        "safety_alert": "response"
    }

    result = routing.get(intent, "response")
    logger.info(f"Support routing: {intent} -> {result}")
    return result


def route_from_shipping(state: AgentState) -> str:
    """Conditional routing from Shipping Agent.
    
    Returns compensation if issue found, else response directly.
    """
    decision = state.get("shipping_decision", "resolved")
    result = "compensation" if decision == "issue_found" else "response"
    logger.info(f"Shipping routing: {decision} -> {result}")
    return result


def route_from_response(state: AgentState) -> str:
    """Conditional routing from Response Agent.
    
    Implements feedback loop — routes back to compensation
    if response insufficient and loop limit not reached.
    Forces END after max_loop_iterations.
    """
    sufficient = state.get("response_sufficient", True)
    loop_count = state.get("loop_count", 0)
    max_loops = state.get("max_loop_iterations", 2)

    if not sufficient and loop_count < max_loops:
        logger.info(
            f"Feedback loop triggered: attempt {loop_count}")
        return "compensation"

    logger.info("Response sufficient — ending workflow")
    return END


def build_graph(agent_configs: Dict[str, Dict]) -> Any:
    """Build LangGraph StateGraph from agent configs.
    
    Creates nodes for all 4 agents and wires
    conditional edges for routing and feedback loop.
    """
    # Initialize agents from configs
    support = SupportAgent(agent_configs["support"])
    shipping = ShippingAgent(agent_configs["shipping"])
    compensation = CompensationAgent(agent_configs["compensation"])
    response = ResponseAgent(agent_configs["response"])

    # Create graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("support", support.run)
    graph.add_node("shipping", shipping.run)
    graph.add_node("compensation", compensation.run)
    graph.add_node("response", response.run)

    # Set entry point
    graph.set_entry_point("support")

    # Conditional edges from support
    graph.add_conditional_edges(
        "support",
        route_from_support,
        {
            "shipping": "shipping",
            "compensation": "compensation",
            "response": "response"
        }
    )

    # Conditional edges from shipping
    graph.add_conditional_edges(
        "shipping",
        route_from_shipping,
        {
            "compensation": "compensation",
            "response": "response"
        }
    )

    # Fixed edge — compensation always goes to response
    graph.add_edge("compensation", "response")

    # Conditional edges from response — feedback loop
    graph.add_conditional_edges(
        "response",
        route_from_response,
        {
            "compensation": "compensation",
            END: END
        }
    )

    # Compile
    compiled = graph.compile()
    logger.info("LangGraph compiled successfully")
    return compiled


async def run_workflow(
    telegram_chat_id: str,
    customer_message: str,
    workflow_id: str = "wf_order_support",
    brand_id: Optional[str] = None,
    customer_name: Optional[str] = None
) -> AgentState:
    """Main entry point to run a complete workflow.
    
    Called by FastAPI webhook when Telegram message arrives.
    Loads configs, builds graph, runs workflow, saves results.
    Returns final state after all agents complete.
    """
    use_brand_id = brand_id or settings.brand_id
    session_id = str(uuid.uuid4())

    # Step 1 — Create run record
    run_id = create_run_record(
        workflow_id=workflow_id,
        brand_id=use_brand_id,
        telegram_chat_id=telegram_chat_id,
        trigger_message=customer_message
    )

    # Step 2 — Load agent configs
    agent_configs = load_agent_configs(use_brand_id)
    if not agent_configs:
        logger.error("No agent configs found")
        raise ValueError("No agents configured for brand")

    # Step 3 — Load workflow for loop config
    workflow = load_workflow(workflow_id)
    max_loop_iterations = 2
    if workflow and workflow.get("loop_config"):
        loop_config = workflow["loop_config"]
        if isinstance(loop_config, str):
            loop_config = json.loads(loop_config)
        max_loop_iterations = loop_config.get("max_iterations", 2)

    # Step 4 — Create initial state
    state = create_initial_state(
        brand_id=use_brand_id,
        telegram_chat_id=telegram_chat_id,
        customer_message=customer_message,
        workflow_id=workflow_id,
        session_id=session_id,
        run_id=run_id,
        customer_name=customer_name,
        max_loop_iterations=max_loop_iterations
    )

    # Step 5 — Build and run graph
    try:
        compiled_graph = build_graph(agent_configs)
        logger.info(
            f"Running workflow {workflow_id} "
            f"for {telegram_chat_id}")
        final_state = await compiled_graph.ainvoke(state)
        complete_run_record(run_id, final_state, "completed")
        logger.info(
            f"Workflow complete. "
            f"Tokens: {final_state['total_tokens']}")
        return final_state
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        complete_run_record(run_id, state, "failed")
        raise