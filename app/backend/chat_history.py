from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional

from .schemas import ChatMessage, HistoryDocument


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class HistoryRecord:
    messages: List[ChatMessage] = field(default_factory=list)
    updated_at: datetime = field(default_factory=_utcnow)
    summary: Optional[str] = None
    summarized_at: Optional[datetime] = None


@dataclass(frozen=True)
class HistorySnapshot:
    key: str
    messages: List[ChatMessage]
    summary: Optional[str]
    updated_at: datetime
    summarized_at: Optional[datetime]


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
            messages: List[ChatMessage] = []
            if record.summary:
                messages.append(
                    ChatMessage(
                        role="system",
                        content=f"Samenvatting tot nu toe: {record.summary}",
                    )
                )
            messages.extend(record.messages)
            return list(messages)

    def append(
        self,
        key: str,
        role: str,
        content: str,
        images: Optional[List[str]] = None,
        documents: Optional[List[HistoryDocument]] = None,
    ) -> None:
        clean = (content or "").strip()
        image_list = [item for item in (images or []) if item]
        document_list = [item for item in (documents or []) if item]
        if not key or (not clean and not image_list and not document_list):
            return
        with self._lock:
            record = self._data.get(key)
            if record is None:
                record = HistoryRecord()
                self._data[key] = record
            record.messages.append(
                ChatMessage(
                    role=role,
                    content=clean,
                    images=list(image_list),
                    documents=list(document_list),
                )
            )
            if len(record.messages) > self._max_items:
                record.messages = record.messages[-self._max_items :]
            record.updated_at = _utcnow()

    def clear(self, key: str) -> None:
        if not key:
            return
        with self._lock:
            self._data.pop(key, None)

    def snapshot_idle(self, idle_before: datetime) -> List[HistorySnapshot]:
        snapshots: List[HistorySnapshot] = []
        with self._lock:
            for key, record in self._data.items():
                if record.updated_at > idle_before:
                    continue
                if not record.messages:
                    continue
                if record.summarized_at and record.summarized_at >= record.updated_at:
                    continue
                snapshots.append(
                    HistorySnapshot(
                        key=key,
                        messages=list(record.messages),
                        summary=record.summary,
                        updated_at=record.updated_at,
                        summarized_at=record.summarized_at,
                    )
                )
        return snapshots

    def snapshot_pending(self) -> List[HistorySnapshot]:
        snapshots: List[HistorySnapshot] = []
        with self._lock:
            for key, record in self._data.items():
                if not record.messages:
                    continue
                if record.summarized_at and record.summarized_at >= record.updated_at:
                    continue
                snapshots.append(
                    HistorySnapshot(
                        key=key,
                        messages=list(record.messages),
                        summary=record.summary,
                        updated_at=record.updated_at,
                        summarized_at=record.summarized_at,
                    )
                )
        return snapshots

    def apply_summary(
        self,
        key: str,
        summary: str,
        expected_updated_at: datetime,
        expected_summarized_at: Optional[datetime],
    ) -> bool:
        clean = (summary or "").strip()
        if not key or not clean:
            return False
        with self._lock:
            record = self._data.get(key)
            if not record:
                return False
            if record.updated_at != expected_updated_at:
                return False
            if record.summarized_at != expected_summarized_at:
                return False
            record.summary = clean
            record.messages = [
                msg
                for msg in record.messages
                if getattr(msg, "images", None) or getattr(msg, "documents", None)
            ]
            record.summarized_at = _utcnow()
            return True
