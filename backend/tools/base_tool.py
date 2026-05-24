"""Abstract base class for all D2CAgent tools."""
from abc import ABC, abstractmethod
from typing import Any, Dict

from backend.logger import setup_logger


class BaseTool(ABC):
    """Abstract base class for all D2CAgent tools.

    All tools must extend this class.
    execute() is async — never use asyncio.run() inside tools.
    safe_execute() wraps execute() with error handling.
    """

    name: str = ""
    description: str = ""

    def __init__(self) -> None:
        """Initialize the tool's logger."""
        self.logger = setup_logger(__name__)

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Run the tool's primary action.

        Args:
            **kwargs: Tool-specific keyword arguments.

        Returns:
            A dictionary describing the tool's result. Must always be a dict.
        """
        raise NotImplementedError

    async def safe_execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Invoke execute() with structured exception handling.

        Args:
            **kwargs: Tool-specific keyword arguments forwarded to execute().

        Returns:
            The successful result of execute(), or an error envelope of the
            form {"success": False, "error": str, "tool": str} on failure.
        """
        try:
            return await self.execute(**kwargs)
        except Exception as exc:
            self.logger.error(
                "Tool %s failed with kwargs=%s: %s",
                self.name,
                kwargs,
                exc,
                exc_info=True,
            )
            return {"success": False, "error": str(exc), "tool": self.name}
