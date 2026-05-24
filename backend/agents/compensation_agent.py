"""Compensation Agent — resolution decision and guardrail enforcement."""
from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.config import settings  # noqa: F401  (kept for downstream access)
from backend.logger import setup_logger
from backend.runtime.state import AgentState


class CompensationAgent(BaseAgent):
    """Compensation Agent — evaluates and decides customer resolution.

    Checks guardrails before any compensation action.
    Raises flags for human review when needed.
    Generates coupons within configured limits.
    Sets compensation_decision in state.
    """

    def __init__(self, agent_config: Dict[str, Any]) -> None:
        """Initialize the Compensation Agent.

        Args:
            agent_config: The agent configuration dict loaded from SQLite.
        """
        super().__init__("agent_compensation", agent_config)
        self.logger = setup_logger(__name__)

    async def run(self, state: AgentState) -> AgentState:
        """Evaluate the situation and choose apology / coupon / escalate.

        Args:
            state: The shared AgentState dict for the current run.

        Returns:
            The updated AgentState dict with compensation_decision and any
            escalation flags populated.
        """
        state["current_agent"] = "compensation"
        self.logger.info("Compensation Agent evaluating")

        # Step 1 — Handle safety alert
        if state["is_safety_alert"]:
            order_id = (
                state["order_data"]["order_id"]
                if state.get("order_data")
                and state["order_data"].get("order_id")
                else None
            )
            await self.execute_tool(
                "raise_flag",
                state,
                reason="Safety alert — customer mentioned injury or safety concern",
                urgency="critical",
                raised_by_agent=self.agent_name,
                order_id=order_id,
            )
            state["compensation_decision"] = {
                "action": "escalate",
                "reason": "Safety concern escalated to human review",
                "coupon_code": None,
                "discount_percent": 0,
                "flag_id": None,
            }
            state["escalate_to_human"] = True
            state = await self.log_action(
                state, "safety_escalation", status="success"
            )
            return state

        # Step 2 — Evaluate compensation
        order_data = state.get("order_data") or {}
        days_delayed = order_data.get("days_delayed", 0) or 0
        eval_result = await self.execute_tool(
            "evaluate_compensation",
            state,
            intent=state.get("intent", "complaint"),
            is_safety_alert=state["is_safety_alert"],
            days_delayed=days_delayed,
            order_data=order_data,
        )
        recommended_action = eval_result.get("recommended_action", "apology")
        suggested_discount = eval_result.get("suggested_discount", 0)

        # Step 3 — Check guardrail if coupon
        if recommended_action == "coupon" and suggested_discount > 0:
            order_value = order_data.get("order_value", 0) or 0
            if order_value == 0:
                order_value = 500
            compensation_amount = order_value * (suggested_discount / 100)
            guardrail = await self.execute_tool(
                "check_guardrail",
                state,
                amount_inr=compensation_amount,
            )
            if not guardrail.get("within_limit", True):
                recommended_action = "escalate"
                eval_result["reason"] = (
                    eval_result.get("reason", "")
                    + " — exceeds guardrail limit requires human approval"
                )

        # Step 4 — Execute decision
        if recommended_action == "coupon":
            coupon = await self.execute_tool(
                "generate_coupon",
                state,
                order_id=order_data.get("order_id", "unknown"),
                discount_percent=suggested_discount,
            )
            state["compensation_decision"] = {
                "action": "coupon",
                "reason": eval_result.get("reason", ""),
                "coupon_code": coupon.get("coupon_code"),
                "discount_percent": suggested_discount,
                "expires_at": coupon.get("expires_at"),
                "flag_id": None,
            }
        elif recommended_action == "escalate":
            flag = await self.execute_tool(
                "raise_flag",
                state,
                reason=eval_result.get("reason", "Requires human review"),
                urgency=eval_result.get("urgency", "medium"),
                raised_by_agent=self.agent_name,
                order_id=order_data.get("order_id"),
            )
            state["compensation_decision"] = {
                "action": "escalate",
                "reason": eval_result.get("reason", ""),
                "coupon_code": None,
                "discount_percent": 0,
                "flag_id": flag.get("flag_id"),
            }
            state["escalate_to_human"] = True
        else:
            state["compensation_decision"] = {
                "action": "apology",
                "reason": eval_result.get("reason", "Standard resolution"),
                "coupon_code": None,
                "discount_percent": 0,
                "flag_id": None,
            }

        # Step 5 — Log
        state = await self.log_action(
            state,
            f"compensation_{recommended_action}",
            tool_output=state["compensation_decision"],
        )
        return state
