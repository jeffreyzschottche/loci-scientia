from __future__ import annotations

import os
from pathlib import Path

ENV_FILE_PATH = Path(
    os.environ.get(
        "AITJE_ENV_PATH",
        Path(__file__).resolve().parents[3] / ".env",
    )
).expanduser().resolve()


def persist_env_var(key: str, value: str) -> None:
    """Write or update ``KEY=value`` in the project .env file.

    Raises ``FileNotFoundError`` if .env is missing so callers can surface it.
    """
    if not ENV_FILE_PATH.exists():
        raise FileNotFoundError(f".env niet gevonden: {ENV_FILE_PATH}")

    content = ENV_FILE_PATH.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    prefix = f"{key}="
    updated = False
    for idx, line in enumerate(lines):
        if line.startswith(prefix):
            lines[idx] = f"{prefix}{value}\n"
            updated = True
            break
    if not updated:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"
        lines.append(f"{prefix}{value}\n")

    ENV_FILE_PATH.write_text("".join(lines), encoding="utf-8")
