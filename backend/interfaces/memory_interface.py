"""Abstract interface for conversation memory backends."""
from abc import ABC, abstractmethod


class MemoryInterface(ABC):
    """Abstract base class defining the contract for any memory backend."""

    @abstractmethod
    def save(self, chat_id: str, summary: str, metadata: dict) -> None:
        """Persist a summary entry for the given chat.

        Args:
            chat_id: The identifier for the conversation.
            summary: The textual summary to persist.
            metadata: Additional metadata to store alongside the summary.
        """
        raise NotImplementedError

    @abstractmethod
    def retrieve(self, chat_id: str, n_results: int) -> list:
        """Retrieve the most relevant memory entries for the given chat.

        Args:
            chat_id: The identifier for the conversation.
            n_results: The maximum number of entries to return.

        Returns:
            A list of memory entries retrieved from the backend.
        """
        raise NotImplementedError
