"""Shared LangGraph state schema for the D2CAgent workflow."""
from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict):
    """Single shared state object passed between all LangGraph nodes.

    Each agent reads the full state and writes only its own section.
    Never mutate state directly — always return a new dict. The state
    is passed sequentially from Support → Shipping → Compensation →
    Response, with conditional edges and bounded loops as defined in
    the workflow configuration.
    """

    # Customer context
    brand_id: str
    telegram_chat_id: str
    customer_name: Optional[str]
    customer_message: str
    session_id: str
    run_id: str

    # Workflow context
    workflow_id: str
    current_agent: str
    intent: Optional[str]
    # Intent values: order_status, order_modification, complaint,
    # return_request, cancellation, simple_faq, product_query,
    # safety_alert, positive_feedback

    # Memory context
    conversation_history: List[Dict[str, Any]]
    # Each entry: {role, content, timestamp, agent_name}

    # Order context — populated by Shipping Agent
    order_data: Optional[Dict[str, Any]]
    # Structure: {
    #   order_id, customer_name, product_name,
    #   status, tracking_number, expected_delivery,
    #   order_value, shipping_address, notes,
    #   is_delayed, days_delayed
    # }

    # Shipping decision — written by Shipping Agent
    shipping_decision: Optional[str]
    # Values: "resolved" or "issue_found"

    # Compensation context — populated by Compensation Agent
    compensation_decision: Optional[Dict[str, Any]]
    # Structure: {
    #   action: "apology"/"coupon"/"escalate",
    #   coupon_code: Optional[str],
    #   discount_percent: Optional[int],
    #   flag_id: Optional[str],
    #   reason: str
    # }

    # Response context — populated by Response Agent
    final_response: Optional[str]
    response_sufficient: bool
    loop_count: int
    max_loop_iterations: int

    # Safety and escalation flags
    is_safety_alert: bool
    escalate_to_human: bool

    # Monitoring context — appended by every agent
    agent_logs: List[Dict[str, Any]]
    # Each log entry: {
    #   agent_name: str,
    #   action: str,
    #   tool_called: Optional[str],
    #   tool_input: Optional[dict],
    #   tool_output: Optional[dict],
    #   tokens_used: int,
    #   cost_usd: float,
    #   latency_ms: int,
    #   status: str,  # success/failed/timeout
    #   timestamp: str  # ISO format
    # }

    flags: List[Dict[str, Any]]
    # Each flag entry: {
    #   reason: str,
    #   urgency: str,  # low/medium/high/critical
    #   raised_by_agent: str
    # }

    total_tokens: int
    total_cost_usd: float


def create_initial_state(
    brand_id: str,
    telegram_chat_id: str,
    customer_message: str,
    workflow_id: str,
    session_id: str,
    run_id: str,
    customer_name: Optional[str] = None,
    max_loop_iterations: int = 2,
) -> AgentState:
    """Build a fresh AgentState for a new workflow run.

    Args:
        brand_id: Identifier of the brand this run belongs to.
        telegram_chat_id: Telegram chat ID for the customer conversation.
        customer_message: The inbound customer message that triggered the run.
        workflow_id: Identifier of the workflow being executed.
        session_id: Identifier of the customer session.
        run_id: Unique identifier of this specific workflow run.
        customer_name: Optional known customer first name; None if unknown.
        max_loop_iterations: Maximum allowed iterations of the compensation
            and response loop before forced exit. Defaults to 2.

    Returns:
        An AgentState dict with all fields initialized to their starting
        values, with current_agent set to "support".
    """
    return AgentState(
        brand_id=brand_id,
        telegram_chat_id=telegram_chat_id,
        customer_name=customer_name,
        customer_message=customer_message,
        session_id=session_id,
        run_id=run_id,
        workflow_id=workflow_id,
        current_agent="support",
        intent=None,
        conversation_history=[],
        order_data=None,
        shipping_decision=None,
        compensation_decision=None,
        final_response=None,
        response_sufficient=False,
        loop_count=0,
        max_loop_iterations=max_loop_iterations,
        is_safety_alert=False,
        escalate_to_human=False,
        agent_logs=[],
        flags=[],
        total_tokens=0,
        total_cost_usd=0.0,
    )
