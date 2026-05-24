"""Abstract base class for all D2CAgent agents."""
import json
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional  # noqa: F401  (List kept for downstream typing)

from backend.config import settings  # noqa: F401  (kept available to subclasses)
from backend.database.database import get_db
from backend.database.models import AgentLog, Conversation
from backend.logger import setup_logger
from backend.runtime.state import AgentState
from backend.tools.base_tool import BaseTool  # noqa: F401  (kept available to subclasses)
from backend.tools.registry import get_tools_for_agent


class BaseAgent(ABC):
    """Abstract base class for all D2CAgent agents.

    All agents must extend this class and implement run().
    Handles tool execution, logging, and state updates.
    All agents are async.
    """

    def __init__(self, agent_id: str, agent_config: Dict[str, Any]) -> None:
        """Initialize the agent from its configuration record.

        Args:
            agent_id: The stable identifier of this agent (e.g. "agent_support").
            agent_config: The agent's configuration dict, typically loaded
                from the Agent ORM record. May contain JSON-encoded string
                values for tools, guardrails and interaction_rules.
        """
        self.agent_id = agent_id
        self.agent_config = agent_config
        self.agent_name = agent_config["name"]
        self.role = agent_config["role"]
        self.system_prompt = agent_config["system_prompt"]

        tools_list = agent_config.get("tools", [])
        if isinstance(tools_list, str):
            try:
                tools_list = json.loads(tools_list)
            except (TypeError, ValueError):
                tools_list = []
        self.tools = get_tools_for_agent(tools_list)

        guardrails = agent_config.get("guardrails", {})
        if isinstance(guardrails, str):
            try:
                guardrails = json.loads(guardrails)
            except (TypeError, ValueError):
                guardrails = {}
        self.guardrails = guardrails if guardrails else {}

        rules = agent_config.get("interaction_rules", [])
        if isinstance(rules, str):
            try:
                rules = json.loads(rules)
            except (TypeError, ValueError):
                rules = []
        self.interaction_rules = rules if rules else []

        self.memory_enabled = agent_config.get("memory_enabled", False)
        self.logger = setup_logger(__name__)

    @abstractmethod
    async def run(self, state: AgentState) -> AgentState:
        """Execute the agent's logic against the current shared state.

        Args:
            state: The shared AgentState dict for the current run.

        Returns:
            The updated AgentState dict after the agent's logic completes.
        """
        raise NotImplementedError

    def build_system_prompt(self, state: AgentState) -> str:
        """Assemble the agent's system prompt with rules and recent history.

        Args:
            state: The current AgentState dict.

        Returns:
            The fully composed system prompt string for the LLM.
        """
        prompt = self.system_prompt
        if self.interaction_rules:
            prompt += "\n\nInteraction Rules — follow these strictly:\n"
            for rule in self.interaction_rules:
                prompt += f"- {rule}\n"

        history = state.get("conversation_history") or []
        if history:
            prompt += "\n\nCustomer conversation history:\n"
            for entry in history[-3:]:
                if isinstance(entry, dict) and "document" in entry:
                    content = entry.get("document", str(entry))
                    role = "agent"
                elif isinstance(entry, dict):
                    role = entry.get("role", "agent")
                    content = entry.get("content", "")
                else:
                    role = "agent"
                    content = str(entry)
                prompt += f"{role}: {content}\n"
        return prompt

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Best-effort parse of a JSON object from an LLM response string.

        Args:
            content: The raw LLM response content, possibly wrapped in
                markdown code fences.

        Returns:
            The parsed dict, or an empty dict on parse failure.
        """
        if "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1]
                if content.startswith("json"):
                    content = content[4:]
        content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            self.logger.warning("Failed to parse LLM JSON response: %s", exc)
            return {}

    async def execute_tool(
        self,
        tool_name: str,
        state: AgentState,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Look up a tool by name on this agent and invoke it safely.

        Args:
            tool_name: The registered tool name to invoke.
            state: The current AgentState (not mutated here, but available
                for future routing or guardrails).
            **kwargs: Keyword arguments to pass to the tool's execute().

        Returns:
            The tool's result dict, or an error envelope if not found.
        """
        tool = next((t for t in self.tools if t.name == tool_name), None)
        if tool is None:
            self.logger.warning(
                "Tool %s not found for %s", tool_name, self.agent_name
            )
            return {
                "success": False,
                "error": f"Tool {tool_name} not found",
            }
        start_time = time.time()
        result = await tool.safe_execute(**kwargs)
        latency_ms = int((time.time() - start_time) * 1000)
        self.logger.info(
            "%s executed %s in %dms", self.agent_name, tool_name, latency_ms
        )
        return result

    async def log_action(
        self,
        state: AgentState,
        action: str,
        tool_called: Optional[str] = None,
        tool_input: Optional[Dict[str, Any]] = None,
        tool_output: Optional[Dict[str, Any]] = None,
        tokens_used: int = 0,
        status: str = "success",
    ) -> AgentState:
        """Append an agent log entry to state and persist it to SQLite.

        Args:
            state: The current AgentState dict.
            action: A short identifier for the action being logged.
            tool_called: Optional tool name that was invoked.
            tool_input: Optional input payload for the tool call.
            tool_output: Optional output payload from the tool call.
            tokens_used: Number of LLM tokens consumed for this action.
            status: Outcome status ("success", "failed", "timeout").

        Returns:
            The updated AgentState dict with the log appended and totals
            incremented.
        """
        cost_usd = tokens_used * 0.0000003
        log_entry = {
            "agent_name": self.agent_name,
            "action": action,
            "tool_called": tool_called,
            "tool_input": tool_input,
            "tool_output": tool_output,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
            "latency_ms": 0,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
        state["agent_logs"].append(log_entry)
        state["total_tokens"] += tokens_used
        state["total_cost_usd"] += cost_usd

        db = next(get_db())
        try:
            log = AgentLog(
                log_id=str(uuid.uuid4()),
                brand_id=state["brand_id"],
                workflow_id=state["workflow_id"],
                run_id=state["run_id"],
                conversation_id=None,
                agent_name=self.agent_name,
                action=action,
                tool_called=tool_called,
                tool_input=json.dumps(tool_input) if tool_input else None,
                tool_output=json.dumps(tool_output) if tool_output else None,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                latency_ms=0,
                status=status,
            )
            db.add(log)
            db.commit()
        except Exception as exc:
            self.logger.error("Failed to persist log: %s", exc)
        finally:
            db.close()
        return state

    async def save_message(
        self,
        state: AgentState,
        message: str,
        direction: str,
    ) -> None:
        """Persist a single conversation message row to SQLite.

        Args:
            state: The current AgentState dict.
            message: The message body to persist.
            direction: Either "inbound" (from customer) or "outbound" (from
                the platform).
        """
        db = next(get_db())
        try:
            conv = Conversation(
                conversation_id=str(uuid.uuid4()),
                brand_id=state["brand_id"],
                workflow_id=state["workflow_id"],
                session_id=state["session_id"],
                telegram_chat_id=state["telegram_chat_id"],
                agent_name=self.agent_name,
                message=message,
                direction=direction,
                intent=state.get("intent"),
            )
            db.add(conv)
            db.commit()
        except Exception as exc:
            self.logger.error("Failed to save message: %s", exc)
        finally:
            db.close()
