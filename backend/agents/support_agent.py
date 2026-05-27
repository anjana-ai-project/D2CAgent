"""Support Agent — entry point and intent classifier."""
import json  # noqa: F401  (available for downstream JSON work)
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from backend.agents.base_agent import BaseAgent
from backend.config import settings
from backend.logger import setup_logger
from backend.runtime.state import AgentState


class SupportAgent(BaseAgent):
    """Support Agent — entry point for all customer interactions.

    Reads conversation history from ChromaDB memory.
    Classifies customer intent using LLM.
    Detects safety keywords before LLM call.
    Routes to correct next agent via state intent.
    """

    VALID_INTENTS = [
        "order_status",
        "order_modification",
        "complaint",
        "return_request",
        "cancellation",
        "simple_faq",
        "product_query",
        "safety_alert",
        "positive_feedback",
    ]

    def __init__(self, agent_config: Dict[str, Any]) -> None:
        """Initialize the Support Agent and its Groq LLM client.

        Args:
            agent_config: The agent configuration dict loaded from SQLite.
        """
        super().__init__("agent_support", agent_config)
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.llm_model,
            temperature=0.1,
        )
        self.logger = setup_logger(__name__)

    async def run(self, state: AgentState) -> AgentState:
        """Classify customer intent and route to the next agent.

        Args:
            state: The shared AgentState dict for the current run.

        Returns:
            The updated AgentState dict with intent, history and safety
            fields populated.
        """
        state["current_agent"] = "support"
        self.logger.info("Support Agent: %s", state["telegram_chat_id"])

        # Step 1 — Read conversation history if memory enabled
        if self.memory_enabled:
            result = await self.execute_tool(
                "read_history",
                state,
                chat_id=state["telegram_chat_id"],
            )
            if result.get("success") and result.get("count", 0) > 0:
                state["conversation_history"] = result["history"]

        # Step 2 — Check safety keywords
        safety_keywords = self.guardrails.get(
            "escalate_on_keywords",
            ["injury", "safety", "swallowed", "hurt", "emergency"],
        )
        message_lower = state["customer_message"].lower()
        if any(kw in message_lower for kw in safety_keywords):
            state["is_safety_alert"] = True
            state["intent"] = "safety_alert"
            state = await self.log_action(
                state, "safety_alert_detected", status="success"
            )
            self.logger.warning(
                "Safety alert: %s", state["telegram_chat_id"]
            )
            await self.save_message(
                state, state["customer_message"], "inbound"
            )
            return state

        # Step 3 — Build classification prompt
        system_prompt = self.build_system_prompt(state)
        classification_instructions = """
        Classify the customer message into exactly one intent.
        Valid intents: order_status, order_modification, complaint,
        return_request, cancellation, simple_faq, product_query,
        safety_alert, positive_feedback

        Also extract the order ID if mentioned.
        Order IDs follow the pattern: ORD followed by numbers.
        Examples: ORD001, ORD016, ORD1234

        Respond with ONLY a valid JSON object, no markdown:
        {
            "intent": "one_of_the_valid_intents",
            "confidence": 0.95,
            "reasoning": "brief explanation",
            "customer_name_mentioned": null,
            "order_id_mentioned": null
        }
        """
        full_prompt = system_prompt + classification_instructions

        # Step 4 — Call LLM
        tokens_used = 0
        try:
            messages = [
                SystemMessage(content=full_prompt),
                HumanMessage(content=state["customer_message"]),
            ]
            response = await self.llm.ainvoke(messages)
            parsed = self._parse_json_response(response.content)
            intent = parsed.get("intent", "simple_faq")
            if intent not in self.VALID_INTENTS:
                intent = "simple_faq"
            state["intent"] = intent
            customer_name = parsed.get("customer_name_mentioned")
            if customer_name and customer_name != "null":
                state["customer_name"] = customer_name
            order_id = parsed.get("order_id_mentioned")
            if order_id and order_id != "null" and order_id is not None:
                state["mentioned_order_id"] = str(order_id).upper()
                self.logger.info(f"Order ID extracted: {state['mentioned_order_id']}")
            if (
                hasattr(response, "usage_metadata")
                and response.usage_metadata
            ):
                tokens_used = response.usage_metadata.get("total_tokens", 0)
        except Exception as exc:
            self.logger.error("LLM classification failed: %s", exc)
            state["intent"] = "simple_faq"
            tokens_used = 0

        # Step 5 — Save inbound message
        await self.save_message(state, state["customer_message"], "inbound")

        # Step 6 — Log action
        state = await self.log_action(
            state,
            f"classified_intent_{state['intent']}",
            tokens_used=tokens_used,
        )

        return state
