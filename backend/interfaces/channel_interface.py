"""Abstract interface for messaging channels."""
from abc import ABC, abstractmethod


class ChannelInterface(ABC):
    """Abstract base class defining the contract for any messaging channel."""

    @abstractmethod
    def receive(self, request: dict) -> dict:
        """Process an inbound message payload from the channel.

        Args:
            request: The raw inbound request payload from the channel.

        Returns:
            A normalized dictionary representing the parsed inbound message.
        """
        raise NotImplementedError

    @abstractmethod
    def send(self, recipient_id: str, message: str) -> None:
        """Send a message to a recipient on the channel.

        Args:
            recipient_id: The identifier of the message recipient.
            message: The textual message to send.
        """
        raise NotImplementedError
