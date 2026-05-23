from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .auth_tokens import BearerTokenStore, TokenRecord
from .user_roles import ALL_ROLES

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AdminTokenPayload:
    token: str
    user_name: str
    expires_at: str


class AdminTokenManager:
    def __init__(
        self,
        *,
        token_store: BearerTokenStore,
        admin_usernames: list[str],
        token_path: Optional[Path] = None,
        admin_device_id: Optional[str] = None,
        ttl_days: int = 3650,
    ) -> None:
        base_dir = Path(__file__).resolve().parents[2] / "devices_db"
        self.token_store = token_store
        self.token_path = token_path or (base_dir / "admin_token.json")
        self.admin_device_id = admin_device_id or os.environ.get("ADMIN_DEVICE_ID", "local-admin")
        self.admin_usernames = [name for name in admin_usernames if name] or ["ADMIN"]
        self._issuer = BearerTokenStore(
            tokens_path=token_store.tokens_path,
            ttl_days=ttl_days,
        )
        self.token_path.parent.mkdir(parents=True, exist_ok=True)

    def ensure(self) -> Optional[TokenRecord]:
        user_name = self.admin_usernames[0]
        record = self.token_store.get_valid_for_device(
            self.admin_device_id,
            user_name=user_name,
        )
        if record is None:
            record = self._issuer.issue_token(self.admin_device_id, user_name, roles=ALL_ROLES)
        try:
            self._persist_local_token(record)
        except OSError:
            logger.warning("Kon admin token file niet schrijven", exc_info=True)
        return record

    def _persist_local_token(self, record: TokenRecord) -> None:
        payload = AdminTokenPayload(
            token=record.token,
            user_name=record.user_name,
            expires_at=record.expires_at.isoformat(),
        )
        tmp_path = self.token_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload.__dict__, indent=2), encoding="utf-8")
        tmp_path.replace(self.token_path)
        try:
            os.chmod(self.token_path, 0o600)
        except OSError:
            logger.warning("Kon admin token permissies niet instellen", exc_info=True)
