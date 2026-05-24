"""Telegram channel implementation and message-sending tool."""
from typing import Any, Dict

import telegram

from backend.config import settings
from backend.interfaces.channel_interface import ChannelInterface
from backend.logger import setup_logger
from backend.tools.base_tool import BaseTool


class TelegramChannel(ChannelInterface):
    """Telegram implementation of ChannelInterface.

    Uses python-telegram-bot 21.3.
    send() is async — must be awaited.
    """

    def __init__(self) -> None:
        """Initialize the Telegram bot client with the configured token."""
        self.logger = setup_logger(__name__)
        self.bot = telegram.Bot(token=settings.telegram_bot_token)

    def receive(self, request: dict) -> dict:
        """Parse an inbound Telegram webhook payload into a normalized dict.

        Args:
            request: The raw webhook JSON payload from Telegram.

        Returns:
            A dict with chat_id, text, first_name and username keys. All
            fields default to empty strings on parse failure.
        """
        try:
            message = request.get("message", {})
            chat = message.get("chat", {})
            return {
                "chat_id": str(chat.get("id", "")),
                "text": message.get("text", ""),
                "first_name": chat.get("first_name", ""),
                "username": chat.get("username", ""),
            }
        except Exception as exc:
            self.logger.error("Failed to parse Telegram request: %s", exc)
            return {
                "chat_id": "",
                "text": "",
                "first_name": "",
                "username": "",
            }

    async def send(self, recipient_id: str, message: str) -> None:
        """Send an HTML-formatted Telegram message to the given chat ID.

        Args:
            recipient_id: The Telegram chat ID of the recipient.
            message: The HTML-formatted message body to send.
        """
        async with self.bot:
            await self.bot.send_message(
                chat_id=recipient_id,
                text=message,
                parse_mode="HTML",
            )
        self.logger.info("Message sent to %s", recipient_id)


class SendTelegramMessage(BaseTool):
    """Send the final response message to a customer on Telegram."""

    name = "send_telegram_message"
    description = "Send final response message to customer on Telegram"

    def __init__(self) -> None:
        """Initialize the tool with a shared TelegramChannel instance."""
        super().__init__()
        self.channel = TelegramChannel()

    async def execute(self, chat_id: str, message: str) -> Dict[str, Any]:
        """Dispatch the message via the underlying Telegram channel.

        Args:
            chat_id: The Telegram chat ID of the recipient.
            message: The message body to send.

        Returns:
            A dict confirming success with chat_id.
        """
        self.logger.info("send_telegram_message: chat_id=%s", chat_id)
        await self.channel.send(chat_id, message)
        return {"success": True, "chat_id": chat_id}
