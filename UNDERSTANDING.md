# My Understanding — AI Agent Orchestration Platform

## The Problem I Set Out To Solve

While buying wooden toys for my child from small independent vendors, 
I noticed a recurring pattern — talented makers with great products but 
no way to handle customer support at scale. Messages go unanswered, 
order updates are manual, complaints get lost. These businesses cannot 
afford a support team and have no tech team to build automation.

D2CAgent is my answer to that problem.

## What I Built

An AI Agent Orchestration Platform where D2C brand operators — not 
developers — can create AI agents, configure how they behave, connect 
them into workflows, and deploy them to Telegram. No code required.

The demo brand is Kreactive Toys — a handcrafted wooden toy brand 
selling to parents across India.

## How I Thought About Agents

The first question I asked was: does this actually need agents, or 
can a normal API do this?

A normal API handles known inputs with predetermined outputs. It works 
for "where is order ORD001" — query database, return status.

But real customer messages are not that clean:
- "My kid's birthday is tomorrow and the toy hasn't come"
- "I received something damaged"  
- "My child swallowed a piece"

These require intent classification, emotional reasoning, policy 
judgment, and safety detection. That is where agents add genuine value 
— not in the happy path, but in the edge cases.

## The Four Agents and Why

I designed four specialized agents — each with a distinct responsibility:

**Support Agent** — The entry point. Classifies customer intent into 
9 categories, detects safety keywords before LLM call, extracts order 
IDs mentioned in messages, and routes to the right specialist. Memory 
enabled — reads ChromaDB conversation history.

**Shipping Agent** — The data specialist. Queries SQLite for real order 
data. Uses mentioned order ID if the customer specified one, otherwise 
looks up by Telegram ID. Decides if the situation needs compensation 
review or can be resolved directly.

**Compensation Agent** — The decision maker. Evaluates policy based on 
intent, delay, and safety. Checks guardrails before taking action — 
auto-approves below ₹200, requires human review above ₹500. Generates 
real coupons stored in the database or raises flags for human review.

**Response Agent** — The communicator. Reads full context from all 
previous agents. Crafts empathetic, brand-appropriate responses. 
Evaluates response quality for the feedback loop. Saves conversation 
summary to ChromaDB for future sessions.

## The Workflow Design

The workflow is data-driven — stored as JSON in SQLite, not hardcoded. 
LangGraph reads it at runtime and builds the graph dynamically. This 
means any tenant can have a different agent sequence without code changes.

Conditional routing from Support Agent:
- order_status → Shipping → Compensation (if issue) → Response
- complaint/return → Compensation → Response  
- faq/product → Response directly
- safety_alert → Response immediately + critical flag

One feedback loop: Response → Compensation, maximum 2 iterations, 
only for complaint and return_request intents.

## Key Technical Decisions

**LangGraph over CrewAI/AutoGen** — Explicit state machines give full 
visibility into every agent transition. Shared state passing is clean. 
Conditional edges and feedback loops are first-class features. The graph 
is auditable — every routing decision is logged.

**SQLite over PostgreSQL** — The brief requires single-command local 
setup. PostgreSQL needs a running server. SQLAlchemy abstraction means 
one config line switches to PostgreSQL for production. Right tool for 
the right scope.

**Telegram over WhatsApp** — Free Bot API, no business account, no Meta 
approval, instant setup. Architecturally identical to WhatsApp — swapping 
channels means implementing one interface in one file.

**Groq free tier (Llama 3.3 70B)** — Open source model, no cost, fast 
inference. No vendor lock-in. The LLM choice is a config value — 
switching models requires changing one line in .env.

**ChromaDB for memory** — Local vector store, no cloud dependency. 
Conversation summaries embedded and retrieved semantically. Each agent 
decides independently whether to use memory based on its configuration.

## What I Deliberately Did Not Build

**Schedules** — The field is in the database and UI. Execution would use 
APScheduler with cron expressions. Deprioritised for the 2-day scope — 
the architecture supports it.

**Workflow canvas persistence** — React Flow shows the workflow visually. 
Saving canvas changes back to the database is the next feature. The 
graph builder is fully data-driven so it will work once the Save 
endpoint is added.

**Multi-tenant auth** — The data model has brand_id on every table. 
Adding proper authentication is straightforward — the isolation is 
already built in.

## What I Learned

The hardest part was not the code — it was deciding what agents actually 
need to reason about versus what should be deterministic logic.

Safety detection is deterministic — keyword matching before LLM call. 
Faster, more reliable, no hallucination risk.

Compensation decisions are reasoning — the LLM evaluates multiple 
factors. But guardrails are deterministic — the code enforces limits 
regardless of what the LLM decides.

That boundary — where to use reasoning and where to use rules — is the 
core design judgment in any agent system.

## Impact Metrics

- 9 configurable dimensions per agent
- Single setup.bat command from zero to working platform
- 4 customer scenarios tested end to end
- 24 automated tests — all passing
- $0.0044 total LLM cost for all test runs