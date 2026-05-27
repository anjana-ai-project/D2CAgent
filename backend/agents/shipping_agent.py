"""Shipping Agent — order and inventory data specialist."""
from typing import Any, Dict

from backend.agents.base_agent import BaseAgent
from backend.config import settings  # noqa: F401
from backend.logger import setup_logger
from backend.runtime.state import AgentState


class ShippingAgent(BaseAgent):
    """Shipping Agent — handles all order and inventory queries.

    Queries SQLite for real order data.
    Uses mentioned order ID if customer specified one.
    Falls back to telegram_id lookup otherwise.
    Determines shipping_decision: resolved or issue_found.
    Sets order_data in state for downstream agents.
    """

    def __init__(self, agent_config: Dict[str, Any]) -> None:
        """Initialize the Shipping Agent."""
        super().__init__("agent_shipping", agent_config)
        self.logger = setup_logger(__name__)

    async def run(self, state: AgentState) -> AgentState:
        """Look up customer orders and decide if escalation is needed."""
        state["current_agent"] = "shipping"
        self.logger.info(
            "Shipping Agent: %s", state["telegram_chat_id"]
        )

        # Step 1 — Get customer orders
        # Use mentioned order ID if customer specified one
        mentioned_order_id = state.get("mentioned_order_id")

        if mentioned_order_id:
            self.logger.info(
                f"Using mentioned order ID: {mentioned_order_id}")
            result = await self.execute_tool(
                "get_order_status", state,
                order_id=mentioned_order_id
            )
            if result.get("success") and result.get("found"):
                state["order_data"] = result
                estimate = await self.execute_tool(
                    "get_delivery_estimate", state,
                    order_id=mentioned_order_id
                )
                if estimate.get("success"):
                    state["order_data"]["delivery_message"] = \
                        estimate.get("message", "")
                if state["order_data"].get("is_delayed") or \
                        state["order_data"].get("status") == "cancelled":
                    state["shipping_decision"] = "issue_found"
                else:
                    state["shipping_decision"] = "resolved"
                state = await self.log_action(
                    state,
                    f"shipping_decision_{state['shipping_decision']}",
                    tool_called="get_order_status",
                    tool_output={
                        "decision": state["shipping_decision"],
                        "order_id": mentioned_order_id
                    }
                )
                return state
            else:
                self.logger.warning(
                    f"Order {mentioned_order_id} not found "
                    "— falling back to telegram_id lookup")

        # Fall back to telegram ID lookup
        result = await self.execute_tool(
            "get_order_by_customer",
            state,
            telegram_id=state["telegram_chat_id"],
        )
        if not result.get("success") or result.get("count", 0) == 0:
            state["order_data"] = {
                "found": False,
                "message": "No orders found for this customer",
            }
            state["shipping_decision"] = "resolved"
            state = await self.log_action(
                state, "no_orders_found", status="success"
            )
            return state

        # Step 2 — Use most recent order
        most_recent = result["orders"][0]
        state["order_data"] = most_recent

        # Step 3 — Get detailed status
        status_result = await self.execute_tool(
            "get_order_status",
            state,
            order_id=most_recent["order_id"],
        )
        if status_result.get("success") and status_result.get("found"):
            state["order_data"].update(status_result)

        # Step 4 — Get delivery estimate
        estimate_result = await self.execute_tool(
            "get_delivery_estimate",
            state,
            order_id=most_recent["order_id"],
        )
        if estimate_result.get("success"):
            state["order_data"]["delivery_message"] = estimate_result.get(
                "message", ""
            )

        # Step 5 — Determine shipping decision
        if (
            state["order_data"].get("is_delayed")
            or state["order_data"].get("status") == "cancelled"
        ):
            state["shipping_decision"] = "issue_found"
        else:
            state["shipping_decision"] = "resolved"

        # Step 6 — Log
        state = await self.log_action(
            state,
            f"shipping_decision_{state['shipping_decision']}",
            tool_called="get_order_status",
            tool_output={
                "decision": state["shipping_decision"],
                "order_id": most_recent["order_id"],
            },
        )
        return state