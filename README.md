# D2CAgent — AI Agent Orchestration Platform

> Build AI Employees. They talk, think, and work together to get real things done.

A multi-agent AI platform that enables D2C brands to deploy intelligent customer support agents — powered by LangGraph, connected via Telegram, managed through a visual web dashboard.

**Demo Brand:** Kreactive Toys — handcrafted wooden toys for kids in India.

---

## Demo Video
https://www.loom.com/share/0114bdc4ee3a4c60896a178645ed2f21
---

## Architecture
┌─────────────────────────────────────────────────┐
│              EXTERNAL CHANNEL                    │
│                  Telegram                        │
└─────────────────┬───────────────────────────────┘
│ webhook
┌─────────────────▼───────────────────────────────┐
│         CHANNEL GATEWAY — FastAPI                │
│     Receives messages, triggers workflows        │
└─────────────────┬───────────────────────────────┘
│
┌─────────────────▼───────────────────────────────┐
│         ORCHESTRATOR — LangGraph                 │
│   Builds agent graph dynamically from JSON       │
│   Manages shared state across all agents         │
└──────┬──────────┬──────────┬────────────────────┘
│          │          │
┌──────▼──┐ ┌────▼────┐ ┌───▼──────────────────┐
│ Support │ │Shipping │ │Compensation  Response  │
│  Agent  │ │  Agent  │ │   Agent       Agent   │
└──────┬──┘ └────┬────┘ └───┬──────────────────┘
│          │          │
┌──────▼──────────▼──────────▼────────────────────┐
│              TOOL EXECUTOR                       │
│  SQLite          ChromaDB        Groq API        │
│  orders/products memory/vectors  Llama 3.3 70B   │
└─────────────────────────────────────────────────┘
│
┌─────────────────▼───────────────────────────────┐
│              WEB UI — React                      │
│  Agent Builder  Workflow Canvas  Live Monitor    │
└─────────────────────────────────────────────────┘
---

## Multi-Agent Workflow
Customer message on Telegram
↓
Support Agent — classifies intent, routes conditionally
↓
├── order_status/order_modification → Shipping Agent
│         ↓
│    issue found → Compensation Agent
│    resolved   → Response Agent
│
├── complaint/return/cancellation → Compensation Agent
│         ↓
│    Resolution ready → Response Agent
│
├── faq/product_query → Response Agent (direct)
│
└── safety_alert → Response Agent + Critical Flag
↓
Response Agent — crafts reply, sends to Telegram
If insufficient → loops back to Compensation (max 2x)

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| AI Runtime | LangGraph 1.2.1 | Stateful agent graphs, conditional routing, feedback loops |
| LLM | Groq — Llama 3.3 70B | Free tier, fast inference, open source model |
| Backend | FastAPI 0.111 | Async-native, WebSocket support, automatic API docs |
| Memory | ChromaDB 0.5.3 | Local vector store, no cloud dependency |
| Database | SQLite + SQLAlchemy | Zero setup, single file, swap-ready for PostgreSQL |
| Channel | Telegram Bot API | Free, instant setup, no business account needed |
| Frontend | React + Vite + Tailwind | Fast, modern, component-based |
| Workflow Canvas | React Flow | Purpose-built node graph, drag-drop, conditional edges |
| Testing | pytest + pytest-asyncio | 24 tests, critical paths covered |

---

## Runtime Choice — LangGraph

LangGraph was chosen over CrewAI, AutoGen, and custom runtime because:

1. **Explicit state machines** — every agent transition is auditable and visible in monitoring
2. **Native async** — all nodes run as async coroutines on FastAPI's event loop
3. **Conditional edges** — intent-based routing is a first-class feature
4. **Feedback loops** — Response → Compensation loop with cycle detection built in
5. **Dynamic graph building** — workflow JSON from database builds the graph at runtime, enabling per-tenant agent sequences without code changes

---

## Language Choice — Python

Python was chosen because:

1. LangGraph, LangChain, ChromaDB are Python-native
2. FastAPI provides async WebSocket support out of the box
3. SQLAlchemy ORM works seamlessly with SQLite and PostgreSQL
4. The entire AI/ML ecosystem is Python-first

---

## Database Choice — SQLite

SQLite was chosen over PostgreSQL because:

1. **Single setup command requirement** — PostgreSQL requires a running server process
2. **Zero configuration** — SQLite is built into Python
3. **Swap-ready** — changing one line in `.env` switches to PostgreSQL via SQLAlchemy abstraction
4. For production multi-tenant deployment, PostgreSQL is the recommended upgrade path

---

## Features

### Agent Management
- Full CRUD — name, role, system prompt, model, tools, skills, channel
- Per-agent memory toggle
- Configurable guardrails and interaction rules
- Skills checklist — controls which tools each agent can use

### Workflow Canvas
- Visual node-based workflow builder (React Flow)
- Conditional routing with labeled edges
- Feedback loop visualization
- 2 pre-built templates — Order Support Flow, Product Discovery Flow
- Drag nodes, delete edges, connect agents visually

### Multi-Agent Runtime
- 4 specialized agents — Support, Shipping, Compensation, Response
- Conditional routing based on intent classification
- Shared state passing between all agents
- Feedback loop — Response → Compensation (max 2 iterations)
- Safety alert detection with immediate escalation

### External Channel
- Telegram Bot integration
- Webhook-based message receiving
- Async response delivery

### Live Monitoring
- Real-time WebSocket event feed
- Per-agent action logs
- Token and cost tracking
- Conversation history
- Flag management with resolve action
- Workflow run history

### Knowledge Base
- ChromaDB vector store for product catalog
- Semantic product search for recommendations
- Upload Documents UI (coming soon)

### Guardrails
- Per-agent configurable limits
- Max compensation ₹500 enforced at runtime
- Auto-approve below ₹200
- Safety keyword detection
- Interaction rules injected into agent prompts

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- ngrok account (free) — https://ngrok.com
- Groq API key (free) — https://console.groq.com
- Telegram Bot Token — create via @BotFather

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/D2CAgent.git
cd D2CAgent
```

### 2. Configure environment

```bash
copy .env.example .env
```

Edit `.env` and fill in:
GROQ_API_KEY=your_groq_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
### 3. Run setup

```bash
setup.bat
```

This will:
- Create Python virtual environment
- Install all dependencies
- Seed database with Kreactive Toys demo data
- Seed ChromaDB with product catalog
- Run all 24 tests

### 4. Start ngrok

```bash
ngrok http 8000
```

Copy the `https://` URL.

### 5. Start the backend

```bash
venv\Scripts\activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 6. Start the frontend

```bash
cd frontend
npm run dev
```

### 7. Set Telegram webhook

Open http://localhost:8000/docs

Find `POST /setup/webhook` → Try it out → Enter your ngrok URL → Execute

### 8. Open the dashboard
http://localhost:5173
### 9. Test the system

Message your Telegram bot:
Where is my order?
Watch the Monitor dashboard update in real time.

---

## Running Tests

```bash
pytest tests/ -v
```

Expected output: 24 passed, 0 failed

### Test Coverage

| File | Tests | What It Covers |
|---|---|---|
| test_agent_crud.py | 6 | Agent create, read, update, delete via API |
| test_message_delivery.py | 8 | Order lookup, coupon generation, flag creation, endpoints |
| test_workflow_execution.py | 10 | Routing logic, compensation evaluation, feedback loop |

---

## Demo Scenarios

### Order Status Query
Message: "Where is my order?"
Flow: Support → Shipping → Response
Result: Delivery status with tracking info

### Damaged Product Complaint
Message: "My order arrived damaged"
Flow: Support → Compensation → Response
Result: Empathetic reply with coupon code KREACTXXXXXX

### Safety Alert
Message: "My child swallowed a piece from the toy"
Flow: Support → Response (immediate)
Result: Escalation message + Critical flag in dashboard

### Product Discovery
Message: "What toys do you have for a 4 year old?"
Flow: Support → Response (ChromaDB search)
Result: Product recommendations from catalog

---

## Adding New Workflow Templates

1. Define agent sequence in `backend/database/seed.py`
2. Add conditional edges JSON to the workflow record
3. Seed with `python -m backend.database.seed`
4. Template appears in Workflow Canvas UI automatically

## Adding New Messaging Channels

1. Create `backend/channels/your_channel.py`
2. Implement `ChannelInterface`:
   - `receive(request)` — extract chat_id and message
   - `send(recipient_id, message)` — deliver response
3. Add webhook endpoint in `backend/main.py`
4. Add channel option in Agent Builder UI

## Project Structure
D2CAgent/
├── backend/
│   ├── main.py                 # FastAPI app + webhook
│   ├── config.py               # Settings from .env
│   ├── logger.py               # Centralized logging
│   ├── interfaces/             # Abstract base classes
│   ├── agents/                 # 4 agent implementations
│   ├── runtime/                # LangGraph graph builder
│   ├── tools/                  # 11 tool implementations
│   ├── channels/               # Telegram channel
│   └── database/               # Models, seed data
├── frontend/
│   └── src/
│       ├── pages/              # 5 UI pages
│       └── api/                # API client
├── tests/                      # 24 pytest tests
├── .env.example
├── requirements.txt
├── setup.bat
└── README.md

---

## Architecture Decisions

### Why SQLite over PostgreSQL
Single-command local setup requirement. SQLAlchemy abstraction means one line change to switch to PostgreSQL for production.

### Why Telegram over WhatsApp
Telegram Bot API is free with no business account or approval process. Identical demo experience.

### Why Groq over OpenAI
Free tier with open source Llama 3.3 70B model. No credit card required. Fast inference.

### Why React Flow over n8n/Langflow
n8n and Langflow are full platforms — embedding them would make LangGraph redundant. React Flow gives us a purpose-built canvas we fully control, directly integrated with our workflow JSON data model.

### Agent Communication — Async via Shared State
Agents communicate through LangGraph's shared state object running on FastAPI's asyncio event loop. Each agent is an async coroutine — no blocking, no queue needed for this scale.

### Schedules — Implementation Approach
The schedule field is persisted per agent as a cron expression in SQLite. 
The execution engine would use APScheduler:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()
scheduler.add_job(
    run_workflow,
    CronTrigger.from_crontab(agent.schedule),
    args=[brand_id, workflow_id]
)
scheduler.start()
```

Deprioritised for the 2-day MVP scope. Data model and UI configuration are ready.
---

## Tradeoffs

| Decision | What We Gained | What We Traded |
|---|---|---|
| SQLite | Zero setup, single command | Not production-scale |
| Telegram | Free, instant | Not WhatsApp |
| Groq free tier | No cost | Rate limits at scale |
| Shared state async | Simple, fast | No distributed agents |
| 4 fixed agents | Clear demo | Less flexible than n-agent |

---

*Built for Yuno AI Engineer Hiring Challenge*
*Stack: Python 3.11 · LangGraph · FastAPI · ChromaDB · React · Telegram*