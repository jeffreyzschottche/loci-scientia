from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List

from .schemas import ChatMessage


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class HistoryRecord:
    messages: List[ChatMessage] = field(default_factory=list)
    updated_at: datetime = field(default_factory=_utcnow)


class ChatHistoryStore:
    """In-memory, per-token chat history. Not persisted to disk."""

    def __init__(self, max_items: int = 20) -> None:
        self._max_items = max(1, max_items)
        self._lock = Lock()
        self._data: Dict[str, HistoryRecord] = {}

    def get(self, key: str) -> List[ChatMessage]:
        if not key:
            return []
        with self._lock:
            record = self._data.get(key)
            if not record:
                return []
            return list(record.messages)

    def append(self, key: str, role: str, content: str) -> None:
        clean = (content or "").strip()
        if not key or not clean:
            return
        with self._lock:
            record = self._data.get(key)
            if record is None:
                record = HistoryRecord()
                self._data[key] = record
            record.messages.append(ChatMessage(role=role, content=clean))
            if len(record.messages) > self._max_items:
                record.messages = record.messages[-self._max_items :]
            record.updated_at = _utcnow()

    def clear(self, key: str) -> None:
        if not key:
            return
        with self._lock:
            self._data.pop(key, None)
