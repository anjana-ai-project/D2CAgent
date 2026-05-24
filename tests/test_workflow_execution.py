"""Tests for workflow execution — critical paths."""

import asyncio
import json
import pytest


def test_guardrail_within_limit():
    """Test guardrail allows compensation within limit."""
    import sys
    sys.path.insert(0, '.')
    from backend.tools.compensation_tools import CheckGuardrail
    tool = CheckGuardrail()
    result = asyncio.run(tool.safe_execute(amount_inr=300))
    assert result["within_limit"] is True
    assert result["requires_human_approval"] is False


def test_guardrail_exceeds_limit():
    """Test guardrail blocks compensation above limit."""
    from backend.tools.compensation_tools import CheckGuardrail
    tool = CheckGuardrail()
    result = asyncio.run(tool.safe_execute(amount_inr=600))
    assert result["within_limit"] is False
    assert result["requires_human_approval"] is True


def test_evaluate_compensation_damaged_product():
    """Test compensation evaluation for damaged product."""
    from backend.tools.compensation_tools import EvaluateCompensation
    tool = EvaluateCompensation()
    result = asyncio.run(tool.safe_execute(
        intent="complaint",
        days_delayed=0
    ))
    assert result["recommended_action"] == "coupon"
    assert result["suggested_discount"] == 5


def test_evaluate_compensation_long_delay():
    """Test compensation evaluation for significant delay."""
    from backend.tools.compensation_tools import EvaluateCompensation
    tool = EvaluateCompensation()
    result = asyncio.run(tool.safe_execute(
        intent="complaint",
        days_delayed=6
    ))
    assert result["recommended_action"] == "coupon"
    assert result["suggested_discount"] == 10


def test_evaluate_compensation_safety_alert():
    """Test compensation evaluation escalates safety alerts."""
    from backend.tools.compensation_tools import EvaluateCompensation
    tool = EvaluateCompensation()
    result = asyncio.run(tool.safe_execute(
        intent="complaint",
        is_safety_alert=True
    ))
    assert result["recommended_action"] == "escalate"
    assert result["urgency"] == "critical"


def test_routing_order_status():
    """Test Support Agent routes order_status to shipping."""
    from backend.runtime.graph import route_from_support
    from backend.runtime.state import create_initial_state
    import uuid
    state = create_initial_state(
        brand_id="kreactive_toys",
        telegram_chat_id="111001",
        customer_message="Where is my order?",
        workflow_id="wf_order_support",
        session_id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4())
    )
    state["intent"] = "order_status"
    result = route_from_support(state)
    assert result == "shipping"


def test_routing_complaint_skips_shipping():
    """Test complaint routes directly to compensation."""
    from backend.runtime.graph import route_from_support
    from backend.runtime.state import create_initial_state
    import uuid
    state = create_initial_state(
        brand_id="kreactive_toys",
        telegram_chat_id="111001",
        customer_message="I received a damaged product",
        workflow_id="wf_order_support",
        session_id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4())
    )
    state["intent"] = "complaint"
    result = route_from_support(state)
    assert result == "compensation"


def test_routing_faq_direct_to_response():
    """Test FAQ routes directly to response agent."""
    from backend.runtime.graph import route_from_support
    from backend.runtime.state import create_initial_state
    import uuid
    state = create_initial_state(
        brand_id="kreactive_toys",
        telegram_chat_id="111001",
        customer_message="What is your return policy?",
        workflow_id="wf_order_support",
        session_id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4())
    )
    state["intent"] = "simple_faq"
    result = route_from_support(state)
    assert result == "response"


def test_routing_safety_alert_direct():
    """Test safety alert routes directly to response."""
    from backend.runtime.graph import route_from_support
    from backend.runtime.state import create_initial_state
    import uuid
    state = create_initial_state(
        brand_id="kreactive_toys",
        telegram_chat_id="111001",
        customer_message="My child swallowed a piece",
        workflow_id="wf_order_support",
        session_id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4())
    )
    state["intent"] = "safety_alert"
    state["is_safety_alert"] = True
    result = route_from_support(state)
    assert result == "response"


def test_feedback_loop_exits_at_max():
    """Test feedback loop forces exit after max iterations."""
    from backend.runtime.graph import route_from_response
    from backend.runtime.state import create_initial_state
    from langgraph.graph import END
    import uuid
    state = create_initial_state(
        brand_id="kreactive_toys",
        telegram_chat_id="111001",
        customer_message="test",
        workflow_id="wf_order_support",
        session_id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4()),
        max_loop_iterations=2
    )
    state["response_sufficient"] = False
    state["loop_count"] = 2
    result = route_from_response(state)
    assert result == END