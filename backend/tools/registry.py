"""Central registry mapping tool names to BaseTool instances."""
from typing import Dict, List, Optional

from backend.logger import setup_logger
from backend.tools.base_tool import BaseTool
from backend.tools.compensation_tools import (
    CheckGuardrail,
    EvaluateCompensation,
    GenerateCoupon,
    RaiseFlag,
)
from backend.tools.memory_tools import ReadHistory, SaveConversation
from backend.tools.order_tools import (
    GetDeliveryEstimate,
    GetOrderByCustomer,
    GetOrderStatus,
    GetProductStock,
)
from backend.tools.telegram_tools import SendTelegramMessage

logger = setup_logger(__name__)

TOOL_REGISTRY: Dict[str, BaseTool] = {
    "get_order_by_customer": GetOrderByCustomer(),
    "get_order_status": GetOrderStatus(),
    "get_delivery_estimate": GetDeliveryEstimate(),
    "get_product_stock": GetProductStock(),
    "check_guardrail": CheckGuardrail(),
    "evaluate_compensation": EvaluateCompensation(),
    "generate_coupon": GenerateCoupon(),
    "raise_flag": RaiseFlag(),
    "read_history": ReadHistory(),
    "save_conversation": SaveConversation(),
    "send_telegram_message": SendTelegramMessage(),
}


def get_tools_for_agent(tool_names: List[str]) -> List[BaseTool]:
    """Filter the registry by tool names for a specific agent.

    Args:
        tool_names: The list of tool name strings to resolve.

    Returns:
        A list of BaseTool instances matching the requested names.
        Unknown names are skipped and logged as warnings.
    """
    tools: List[BaseTool] = []
    for name in tool_names:
        if name in TOOL_REGISTRY:
            tools.append(TOOL_REGISTRY[name])
        else:
            logger.warning("Tool not found in registry: %s", name)
    return tools


def get_tool(tool_name: str) -> Optional[BaseTool]:
    """Look up a single tool by name in the registry.

    Args:
        tool_name: The name of the tool to fetch.

    Returns:
        The matching BaseTool instance, or None if not found.
    """
    tool = TOOL_REGISTRY.get(tool_name)
    if tool is None:
        logger.warning("Tool not found: %s", tool_name)
    return tool
