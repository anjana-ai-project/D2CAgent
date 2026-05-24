"""SQLAlchemy ORM models for the D2CAgent platform."""
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)

from backend.config import settings  # noqa: F401  (kept for downstream access)
from backend.database.database import Base
from backend.logger import setup_logger

logger = setup_logger(__name__)


class Brand(Base):
    """A D2C brand tenant whose agents and data live within the platform."""

    __tablename__ = "brands"

    brand_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    telegram_bot_token = Column(String, nullable=False)
    webhook_secret = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        """Return a developer-facing string representation."""
        return f"<Brand(brand_id={self.brand_id!r}, name={self.name!r})>"


class Agent(Base):
    """An AI agent definition belonging to a brand."""

    __tablename__ = "agents"

    agent_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id = Column(String, ForeignKey("brands.brand_id"), nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=False)
    model = Column(String, nullable=False)
    _tools = Column("tools", Text, nullable=True)
    _skills = Column("skills", Text, nullable=True)
    schedule = Column(String, nullable=True)
    channel = Column(String, default="telegram")
    _guardrails = Column("guardrails", Text, nullable=True)
    _interaction_rules = Column("interaction_rules", Text, nullable=True)
    memory_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def tools(self) -> list:
        """Return the tool name list, decoded from JSON.

        Returns:
            A list of tool name strings, or an empty list if unset.
        """
        if not self._tools:
            return []
        try:
            return json.loads(self._tools)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to decode Agent.tools JSON: %s", exc)
            return []

    @tools.setter
    def tools(self, value: list) -> None:
        """Persist the tool name list as JSON text.

        Args:
            value: The tool name list to serialize and persist.
        """
        self._tools = json.dumps(value or [])

    @property
    def skills(self) -> list:
        """Return the skill name list, decoded from JSON.

        Returns:
            A list of skill name strings, or an empty list if unset.
        """
        if not self._skills:
            return []
        try:
            return json.loads(self._skills)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to decode Agent.skills JSON: %s", exc)
            return []

    @skills.setter
    def skills(self, value: list) -> None:
        """Persist the skill name list as JSON text.

        Args:
            value: The skill name list to serialize and persist.
        """
        self._skills = json.dumps(value or [])

    @property
    def guardrails(self) -> dict:
        """Return the guardrails object, decoded from JSON.

        Returns:
            A dictionary of guardrail rules, or an empty dict if unset.
        """
        if not self._guardrails:
            return {}
        try:
            return json.loads(self._guardrails)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to decode Agent.guardrails JSON: %s", exc)
            return {}

    @guardrails.setter
    def guardrails(self, value: dict) -> None:
        """Persist the guardrails object as JSON text.

        Args:
            value: The guardrail dictionary to serialize and persist.
        """
        self._guardrails = json.dumps(value or {})

    @property
    def interaction_rules(self) -> list:
        """Return the interaction rule list, decoded from JSON.

        Returns:
            A list of rule strings, or an empty list if unset.
        """
        if not self._interaction_rules:
            return []
        try:
            return json.loads(self._interaction_rules)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to decode Agent.interaction_rules JSON: %s", exc)
            return []

    @interaction_rules.setter
    def interaction_rules(self, value: list) -> None:
        """Persist the interaction rule list as JSON text.

        Args:
            value: The rule list to serialize and persist.
        """
        self._interaction_rules = json.dumps(value or [])

    def __repr__(self) -> str:
        """Return a developer-facing string representation."""
        return (
            f"<Agent(agent_id={self.agent_id!r}, name={self.name!r}, "
            f"role={self.role!r}, brand_id={self.brand_id!r})>"
        )


class Workflow(Base):
    """A multi-agent workflow definition for a brand."""

    __tablename__ = "workflows"

    workflow_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id = Column(String, ForeignKey("brands.brand_id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    _agent_sequence = Column("agent_sequence", Text, nullable=True)
    _conditional_edges = Column("conditional_edges", Text, nullable=True)
    _loop_config = Column("loop_config", Text, nullable=True)
    is_template = Column(Boolean, default=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def agent_sequence(self) -> list:
        """Return the ordered list of agent roles in the workflow.

        Returns:
            A list of agent role strings, or an empty list if unset.
        """
        if not self._agent_sequence:
            return []
        try:
            return json.loads(self._agent_sequence)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to decode Workflow.agent_sequence JSON: %s", exc)
            return []

    @agent_sequence.setter
    def agent_sequence(self, value: list) -> None:
        """Persist the agent sequence as JSON text.

        Args:
            value: The ordered list of agent role strings.
        """
        self._agent_sequence = json.dumps(value or [])

    @property
    def conditional_edges(self) -> dict:
        """Return the conditional edge routing rules, decoded from JSON.

        Returns:
            A dictionary mapping agent roles to routing rules, or an empty dict.
        """
        if not self._conditional_edges:
            return {}
        try:
            return json.loads(self._conditional_edges)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Failed to decode Workflow.conditional_edges JSON: %s", exc
            )
            return {}

    @conditional_edges.setter
    def conditional_edges(self, value: dict) -> None:
        """Persist the conditional edge routing rules as JSON text.

        Args:
            value: The dictionary of routing rules to persist.
        """
        self._conditional_edges = json.dumps(value or {})

    @property
    def loop_config(self) -> dict:
        """Return the loop configuration, decoded from JSON.

        Returns:
            A dict like {"max_iterations": int, "loop_agents": list}, or empty.
        """
        if not self._loop_config:
            return {}
        try:
            return json.loads(self._loop_config)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to decode Workflow.loop_config JSON: %s", exc)
            return {}

    @loop_config.setter
    def loop_config(self, value: dict) -> None:
        """Persist the loop configuration as JSON text.

        Args:
            value: The loop configuration dictionary to persist.
        """
        self._loop_config = json.dumps(value or {})

    def __repr__(self) -> str:
        """Return a developer-facing string representation."""
        return (
            f"<Workflow(workflow_id={self.workflow_id!r}, name={self.name!r}, "
            f"status={self.status!r})>"
        )


class WorkflowRun(Base):
    """A single execution instance of a workflow."""

    __tablename__ = "workflow_runs"

    run_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.workflow_id"), nullable=False)
    brand_id = Column(String, ForeignKey("brands.brand_id"), nullable=False)
    telegram_chat_id = Column(String, nullable=False)
    trigger_message = Column(Text, nullable=False)
    status = Column(String, default="running")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)

    def __repr__(self) -> str:
        """Return a developer-facing string representation."""
        return (
            f"<WorkflowRun(run_id={self.run_id!r}, "
            f"workflow_id={self.workflow_id!r}, status={self.status!r})>"
        )


class Order(Base):
    """A customer order placed with a brand."""

    __tablename__ = "orders"

    order_id = Column(String, primary_key=True)
    brand_id = Column(String, ForeignKey("brands.brand_id"), nullable=False)
    customer_name = Column(String, nullable=False)
    customer_telegram_id = Column(String, nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    status = Column(String, nullable=False)
    tracking_number = Column(String, nullable=True)
    expected_delivery = Column(DateTime, nullable=True)
    order_value = Column(Float, nullable=False)
    shipping_address = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        """Return a developer-facing string representation."""
        return (
            f"<Order(order_id={self.order_id!r}, status={self.status!r}, "
            f"customer_name={self.customer_name!r})>"
        )


class Product(Base):
    """A product offered by a brand."""

    __tablename__ = "products"

    product_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id = Column(String, ForeignKey("brands.brand_id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    age_group = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        """Return a developer-facing string representation."""
        return (
            f"<Product(product_id={self.product_id!r}, name={self.name!r}, "
            f"price={self.price!r})>"
        )


class Conversation(Base):
    """A single message exchanged between a customer and an agent."""

    __tablename__ = "conversations"

    conversation_id = Column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    brand_id = Column(String, ForeignKey("brands.brand_id"), nullable=False)
    workflow_id = Column(String, nullable=True)
    session_id = Column(String, nullable=False)
    telegram_chat_id = Column(String, nullable=False)
    agent_name = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    direction = Column(String, nullable=False)
    intent = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        """Return a developer-facing string representation."""
        return (
            f"<Conversation(conversation_id={self.conversation_id!r}, "
            f"agent_name={self.agent_name!r}, direction={self.direction!r})>"
        )


class AgentLog(Base):
    """A structured log entry capturing a single agent action."""

    __tablename__ = "agent_logs"

    log_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id = Column(String, ForeignKey("brands.brand_id"), nullable=False)
    workflow_id = Column(String, nullable=True)
    run_id = Column(String, nullable=True)
    conversation_id = Column(String, nullable=True)
    agent_name = Column(String, nullable=False)
    action = Column(String, nullable=False)
    tool_called = Column(String, nullable=True)
    _tool_input = Column("tool_input", Text, nullable=True)
    _tool_output = Column("tool_output", Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    status = Column(String, default="success")
    timestamp = Column(DateTime, default=datetime.utcnow)

    @property
    def tool_input(self) -> dict:
        """Return the tool input payload, decoded from JSON.

        Returns:
            A dictionary of tool input arguments, or an empty dict if unset.
        """
        if not self._tool_input:
            return {}
        try:
            return json.loads(self._tool_input)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to decode AgentLog.tool_input JSON: %s", exc)
            return {}

    @tool_input.setter
    def tool_input(self, value: Any) -> None:
        """Persist the tool input payload as JSON text.

        Args:
            value: The tool input value to serialize and persist.
        """
        self._tool_input = json.dumps(value if value is not None else {})

    @property
    def tool_output(self) -> dict:
        """Return the tool output payload, decoded from JSON.

        Returns:
            A dictionary representing the tool output, or an empty dict if unset.
        """
        if not self._tool_output:
            return {}
        try:
            return json.loads(self._tool_output)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to decode AgentLog.tool_output JSON: %s", exc)
            return {}

    @tool_output.setter
    def tool_output(self, value: Any) -> None:
        """Persist the tool output payload as JSON text.

        Args:
            value: The tool output value to serialize and persist.
        """
        self._tool_output = json.dumps(value if value is not None else {})

    def __repr__(self) -> str:
        """Return a developer-facing string representation."""
        return (
            f"<AgentLog(log_id={self.log_id!r}, agent_name={self.agent_name!r}, "
            f"action={self.action!r}, status={self.status!r})>"
        )


class Flag(Base):
    """A flagged escalation raised by an agent for human review."""

    __tablename__ = "flags"

    flag_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id = Column(String, ForeignKey("brands.brand_id"), nullable=False)
    order_id = Column(String, nullable=True)
    conversation_id = Column(String, nullable=True)
    reason = Column(Text, nullable=False)
    urgency = Column(String, nullable=False)
    raised_by_agent = Column(String, nullable=False)
    status = Column(String, default="open")
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        """Return a developer-facing string representation."""
        return (
            f"<Flag(flag_id={self.flag_id!r}, urgency={self.urgency!r}, "
            f"status={self.status!r}, raised_by_agent={self.raised_by_agent!r})>"
        )


class Coupon(Base):
    """A discount coupon issued by an agent as compensation."""

    __tablename__ = "coupons"

    coupon_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id = Column(String, ForeignKey("brands.brand_id"), nullable=False)
    order_id = Column(String, nullable=True)
    code = Column(String, nullable=False, unique=True)
    discount_percent = Column(Integer, nullable=False)
    created_by_agent = Column(String, nullable=False)
    used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        """Return a developer-facing string representation."""
        return (
            f"<Coupon(coupon_id={self.coupon_id!r}, code={self.code!r}, "
            f"discount_percent={self.discount_percent!r}, used={self.used!r})>"
        )
