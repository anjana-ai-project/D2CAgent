"""Response Agent — crafts and delivers final customer response."""

from typing import Any, Dict
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from backend.agents.base_agent import BaseAgent
from backend.config import settings
from backend.logger import setup_logger
from backend.runtime.state import AgentState


class ResponseAgent(BaseAgent):
    """Response Agent — crafts and delivers final customer response.
    
    Reads full state context from all previous agents.
    Crafts warm professional response using LLM.
    Evaluates response quality for feedback loop.
    Sends via Telegram. Saves to ChromaDB memory.
    """

    def __init__(self, agent_config: Dict[str, Any]):
        """Initialize Response Agent with config from database."""
        super().__init__("agent_response", agent_config)
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.llm_model,
            temperature=0.7
        )
        self.logger = setup_logger(__name__)

    async def run(self, state: AgentState) -> AgentState:
        """Craft and deliver final response to customer."""
        state["current_agent"] = "response"
        self.logger.info("Response Agent crafting response")

        # Step 1 — Build context string
        context_parts = []
        context_parts.append(
            f"Customer Message: {state['customer_message']}")
        context_parts.append(
            f"Intent: {state.get('intent', 'unknown')}")
        context_parts.append(
            f"Customer Name: {state.get('customer_name', 'Valued Customer')}")

        if state.get("order_data"):
            order = state["order_data"]
            context_parts.append("Order Information:")
            context_parts.append(
                f"- Order ID: {order.get('order_id', 'N/A')}")
            context_parts.append(
                f"- Product: {order.get('product_name', 'N/A')}")
            context_parts.append(
                f"- Status: {order.get('status', 'N/A')}")
            context_parts.append(
                f"- Delivery: {order.get('delivery_message', 'N/A')}")
            context_parts.append(
                f"- Delayed: {order.get('is_delayed', False)}")

        if state.get("compensation_decision"):
            comp = state["compensation_decision"]
            context_parts.append("Resolution Decision:")
            context_parts.append(
                f"- Action: {comp.get('action', 'none')}")
            context_parts.append(
                f"- Reason: {comp.get('reason', '')}")
            if comp.get("coupon_code"):
                context_parts.append(
                    f"- Coupon Code: {comp['coupon_code']}")
                context_parts.append(
                    f"- Discount: {comp.get('discount_percent', 0)}% off")
                context_parts.append(
                    "IMPORTANT: Use ONLY this exact coupon code. Do NOT generate or invent any other code.")

        if state["escalate_to_human"]:
            context_parts.append(
                "Note: Case flagged for human review.")

        if state["loop_count"] > 0:
            context_parts.append(
                f"Note: Retry attempt {state['loop_count']}. "
                "Please be more helpful.")

        context = "\n".join(context_parts)

        # Step 2 — Build prompt
        system_prompt = self.build_system_prompt(state)
        response_instructions = """
Craft a warm professional response based on context.
Rules:
- Address customer by name
- Be empathetic and solution-focused
- If coupon provided include code clearly
- If escalated say owner follows up within 24 hours
- Keep under 200 words
- End with: Is there anything else I can help you with?
- CRITICAL: If a coupon code is provided in context use ONLY that exact code. Never invent coupon codes.
- CRITICAL: If no Coupon Code appears in the context above do NOT mention any discount or coupon. Never invent compensation.
Respond with ONLY valid JSON no markdown:
{
  "response": "the full customer message here",
  "is_sufficient": true,
  "summary": "one sentence summary of this interaction"
}
"""
        full_prompt = system_prompt + response_instructions

        # Step 3 — Call LLM
        tokens_used = 0
        try:
            messages = [
                SystemMessage(content=full_prompt),
                HumanMessage(content=context)
            ]
            llm_response = await self.llm.ainvoke(messages)
            parsed = self._parse_json_response(llm_response.content)
            if not parsed or "response" not in parsed:
                parsed = {
                    "response": llm_response.content,
                    "is_sufficient": True,
                    "summary": f"Customer asked about {state.get('intent')}"
                }
            if hasattr(llm_response, "usage_metadata") and \
                    llm_response.usage_metadata:
                tokens_used = llm_response.usage_metadata.get(
                    "total_tokens", 0)
        except Exception as e:
            self.logger.error(f"LLM response failed: {e}")
            parsed = {
                "response": (
                    "I apologize for the inconvenience. "
                    "Please contact our support team directly. "
                    "Is there anything else I can help you with?"
                ),
                "is_sufficient": True,
                "summary": "System error — manual follow up needed"
            }

         # Step 4 — Set state
        state["final_response"] = parsed["response"]
        
        # Never loop for these intents
        no_loop_intents = [
            "order_status", "order_modification",
            "simple_faq", "product_query",
            "positive_feedback", "safety_alert"
        ]
        
        if state.get("intent") in no_loop_intents:
            state["response_sufficient"] = True
        elif state["loop_count"] >= state["max_loop_iterations"]:
            state["response_sufficient"] = True
        else:
            state["response_sufficient"] = parsed.get(
                "is_sufficient", True)
                
        # Step 5 — Send via Telegram
        await self.execute_tool(
            "send_telegram_message", state,
            chat_id=state["telegram_chat_id"],
            message=state["final_response"]
        )

        # Step 6 — Save outbound message
        await self.save_message(
            state, state["final_response"], "outbound")

        # Step 7 — Save to ChromaDB
        summary = parsed.get(
            "summary",
            f"Customer asked about {state.get('intent', 'unknown')}")
        resolution = "none"
        if state.get("compensation_decision"):
            resolution = state["compensation_decision"].get(
                "action", "none")
        await self.execute_tool(
            "save_conversation", state,
            chat_id=state["telegram_chat_id"],
            summary=summary,
            intent=state.get("intent", "unknown"),
            resolution=resolution
        )

        # Step 8 — Increment loop count
        state["loop_count"] += 1

        # Step 9 — Log
        state = await self.log_action(
            state,
            "response_sent",
            tokens_used=tokens_used
        )

        return state