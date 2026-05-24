"""ChromaDB-backed long-term memory implementation and exposed tools."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import chromadb

from backend.config import settings
from backend.interfaces.memory_interface import MemoryInterface
from backend.logger import setup_logger
from backend.tools.base_tool import BaseTool


class ChromaMemory(MemoryInterface):
    """ChromaDB implementation of MemoryInterface.

    Stores and retrieves conversation summaries as vector embeddings.
    Keyed by telegram_chat_id for customer-specific memory.
    """

    def __init__(self):
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        """Initialize the persistent Chroma client and conversations collection."""
        self.logger = setup_logger(__name__)
        chroma_path = Path(settings.chroma_path)
        chroma_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(chroma_path))
        self.collection = self.client.get_or_create_collection(
            name="conversations",
            metadata={"hnsw:space": "cosine"},
        )
        self.logger.info("ChromaDB initialized")

    def save(
        self,
        chat_id: str,
        summary: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Save a conversation summary keyed by chat_id with metadata.

        Args:
            chat_id: The Telegram chat ID associated with the summary.
            summary: The textual summary to persist.
            metadata: Additional metadata fields to store alongside the
                summary. All values will be coerced to strings as required
                by ChromaDB.
        """
        doc_id = f"{chat_id}_{datetime.utcnow().timestamp()}"
        full_metadata: Dict[str, Any] = {
            "chat_id": chat_id,
            "timestamp": datetime.utcnow().isoformat(),
            **metadata,
        }
        full_metadata = {k: str(v) for k, v in full_metadata.items()}
        self.collection.add(
            documents=[summary],
            ids=[doc_id],
            metadatas=[full_metadata],
        )
        self.logger.info("Saved conversation memory for %s", chat_id)

    def retrieve(
        self,
        chat_id: str,
        n_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve the most relevant past summaries for the given chat.

        Args:
            chat_id: The Telegram chat ID whose memory to retrieve.
            n_results: Maximum number of memory entries to return.

        Returns:
            A list of {document, metadata} dicts, or an empty list on
            error or when no entries exist.
        """
        try:
            count = self.collection.count()
            if count == 0:
                return []
            results = self.collection.query(
                query_texts=[f"customer conversation {chat_id}"],
                where={"chat_id": chat_id},
                n_results=min(n_results, count),
            )
            if not results["documents"] or not results["documents"][0]:
                return []
            return [
                {"document": doc, "metadata": meta}
                for doc, meta in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                )
            ]
        except Exception as exc:
            self.logger.warning("Memory retrieve failed: %s", exc)
            return []


class ReadHistory(BaseTool):
    """Read prior conversation summaries for a customer from ChromaDB."""

    name = "read_history"
    description = "Read conversation history for a customer from ChromaDB"

    def __init__(self) -> None:
        """Initialize the tool with a shared ChromaMemory instance."""
        super().__init__()
        self.memory = ChromaMemory()

    async def execute(
        self,
        chat_id: str,
        n_results: int = 5,
    ) -> Dict[str, Any]:
        """Return recent memory entries for the given chat.

        Args:
            chat_id: The Telegram chat ID to query.
            n_results: Maximum number of entries to return.

        Returns:
            A dict with chat_id, history list and count.
        """
        self.logger.info(
            "read_history: chat_id=%s n_results=%s", chat_id, n_results
        )
        results = self.memory.retrieve(chat_id, n_results)
        return {
            "success": True,
            "chat_id": chat_id,
            "history": results,
            "count": len(results),
        }


class SaveConversation(BaseTool):
    """Persist a conversation summary to ChromaDB long-term memory."""

    name = "save_conversation"
    description = "Save conversation summary to ChromaDB long-term memory"

    def __init__(self) -> None:
        """Initialize the tool with a shared ChromaMemory instance."""
        super().__init__()
        self.memory = ChromaMemory()

    async def execute(
        self,
        chat_id: str,
        summary: str,
        intent: Optional[str] = None,
        resolution: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save a summary entry tagged with intent and resolution metadata.

        Args:
            chat_id: The Telegram chat ID the summary belongs to.
            summary: The textual conversation summary.
            intent: Optional classified intent label.
            resolution: Optional resolution outcome label.

        Returns:
            A dict confirming the save with chat_id.
        """
        self.logger.info(
            "save_conversation: chat_id=%s intent=%s resolution=%s",
            chat_id,
            intent,
            resolution,
        )
        self.memory.save(
            chat_id=chat_id,
            summary=summary,
            metadata={
                "intent": intent or "unknown",
                "resolution": resolution or "unknown",
            },
        )
        return {"success": True, "chat_id": chat_id}
