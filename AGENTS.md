# AGENTS.md

Guidance for coding agents (Codex, etc.) working in this repository.

## What this is

"Loci Scientia OS" / "AITJE" — a local-first device (current target hardware: **Bosgame M5** mini-PC running Linux) that bundles a FastAPI backend, a PySide6 desktop UI, a Nuxt SPA webclient, Ollama for LLM inference, Qdrant for vector storage, SearXNG for web search, and the Aitje Embedding Application (in-process FastAPI + Nuxt SPA) under `/embedder`. Two distinct surfaces:

- **On-device admin UI (PySide6):** opens only on the Bosgame M5 itself. Manages devices, knowledge base, settings; not meant to be exposed to the LAN.
- **LAN web apps:** the Nuxt chat client at `/` and the embedder SPA at `/embedder/`. These are what external phones/laptops on the same network consume — Caddy fronts the device on `https://aitje-<DEVICE_NUMBER>.local/` with TLS terminated by a per-device internal CA. First-time visitors hit `http://aitje-<DEVICE_NUMBER>.local/connect` (plain-HTTP bootstrap) to install the CA, after which everything runs over HTTPS.

README is in Dutch.

## Bootstrap & run

`./lociscientia.sh` is the entry point — it sources `.env`, sets hostname/mDNS, installs `.venv` (`app/requirements.txt`), starts/pulls Ollama, optionally starts a SearXNG Docker container, **apt-installs + foreground-starts Caddy** as the HTTPS reverse proxy (internal CA, listens on `:80` for `/connect`/`/ca.crt`/`/aitje-ca.mobileconfig` and redirects everything else to `:443`), builds the Nuxt webclient (incremental: rebuilds when `app/webclient/{app,public,*.json,*.ts}` is newer than the build stamp), builds the embedder Nuxt SPA (same stamp pattern), starts uvicorn (bound to `127.0.0.1:8000` when Caddy is up; falls back to `0.0.0.0:8000` plain-HTTP if Caddy refused to start), waits for `/health`, and finally launches the PySide6 frontend. `Ctrl+C` triggers the cleanup trap that stops Caddy, kills uvicorn, and restores the original hostname.

Manual run (after `source .venv/bin/activate`):
- Backend: `python -m uvicorn app.backend.main:app --reload --host 127.0.0.1 --port 8000` (loopback because Caddy is what exposes the LAN; bind `0.0.0.0` only when running without Caddy)
- Frontend: `python -m app.frontend.main`
- Webclient dev: `cd app/webclient && npm run dev` (Nuxt dev on :3000, served from FastAPI `/` in prod via `npm run generate` → `.output/public`)
- Tests: `python -m pytest app/tests` — single test: `python -m pytest app/tests/test_prompt_building.py::TestName::test_x`. Tests stub `qdrant_client` and `fastembed` so they run without those models installed (see `_install_dependency_stubs` in `test_prompt_building.py`).

Logs land in the repo root: `backend.log`, `caddy.log`, `ollama.log`, `promptlog.log` (full augmented prompts), `apiprompt.log` (API-only prompts).

## Architecture

### Backend (`app/backend/`, FastAPI)

- `main.py` — all routes live here (`/api/v1/ask`, `/api/v1/ask/stream` SSE, `/api/v1/signon`, `/api/v1/kennisbank/sync-state`, `/api/v1/kennisbank/library`, `/devices`, support tunnel, Ollama model switch). Holds module-level singletons: `devices_repo`, `token_store`, `chat_history`, `support_tunnel`, `admin_tokens`, `ApiStats`, `DevicePresenceTracker`, `active_generations` (for cancellation).
- `apiAsk.py` — the prompt-building heart. Loads `prompt.txt` plus mode templates from `prompt_templates/`, normalizes images/documents (PDFs via pypdf, docx/xlsx), pulls top-k RAG context from Qdrant, fuses web-search results, calls Ollama. `/api/v1/ask` (REST) and the `/api/v1/ask/stream` SSE path go through the **same** `build_augmented_prompt_with_details` so responses match across clients — preserve this invariant. Both routes build the prompt (and thus run RAG retrieval) exactly once per request; the SSE generator only rebuilds when web search adds results mid-stream.
- `settings.py` — single `Settings` pydantic model populated from env via `get_settings()` at import. `OLLAMA_MAX_CONTEXT` is a comma list aligned by index with `OLLAMA_MODELS`. The module-level `settings` is evaluated once at import; don't mutate it, re-export it.
- `auth_tokens.py` (`BearerTokenStore`, 90-day TTL, JSON-backed) + `admin_access.py` (`AdminTokenManager` writes `devices_db/admin_token.json` for the local UI). Most admin routes use `Depends(require_admin_token)`; user-facing `/api/v1/ask` uses `Depends(require_token)`.
- `devices_repo.py` / `kennisbank_sync.py` / `knowledge_repository.py` — Qdrant collections (`devices`, `kennisbank`) accessed through `qdrant_utils.get_qdrant_client()`, which returns either an embedded client context manager (default, file-backed in `qdrant_storage/`) or a cached remote client when `QDRANT_HOST` is set. The embedded client is guarded by a process-wide lock — only one block can be open at a time. `kennisbank_sync.py` is nowadays just shared constants + the sync-state JSON file; the actual import logic lives in `app/backend/embedder/sync.py`.
- `rag/embedder.py` — `fastembed` wrapper. Default model `paraphrase-multilingual-mpnet-base-v2`; offline mode requires the unpacked ONNX in `app/fastembed_models/<model>/` (note: **under `app/`**, not the repo root — the module's `_PROJECT_ROOT` resolves to `app/`) and `FASTEMBED_ALLOW_DOWNLOAD=0`. Cached via `lru_cache`.
- `kennisbank_sync.py` — slimmed down to shared kennisbank constants/helpers: the Qdrant collection name, the chunk-id → UUID mapping, and the sync-state file at `devices_db/kennisbank_sync_state.json`. The old ZIP-import endpoints (`/api/v1/kennisbank/import*`) and `import_kennisbank_from_dir` are gone; the embedder syncs in-process via `app/backend/embedder/sync.py::sync_changed_chunks_to_qdrant()`.
- `support_tunnel.py` — wraps the `aitje-tunnel` systemd unit (see `systemd/`, `sudoers/`, `docs/remote-support.md`). Opens reverse-SSH via `systemd-run` with an auto-stop timer.
- `web_search.py` — SearXNG client. Toggled per request from the UI; results are folded into the prompt by `apiAsk.py`.
- `setup_routes.py` — LAN onboarding flow served over plain HTTP for first-time clients: `/connect` (UA-sniffing HTML page in the AITJE cream/yellow palette; offers a platform-specific install button, then JS-polls `https://<host>/health` and auto-redirects once the cert is trusted), `/ca.crt` (raw CA cert), `/aitje-ca.mobileconfig` (Apple Configuration Profile carrying the CA + two Web Clips so iOS gets "AITJE Chat" and "AITJE Embedder" icons on the home screen). Reads the CA from `devices_db/tls/ca.crt`; `lociscientia.sh` copies it there from `devices_db/caddy/pki/authorities/local/root.crt` after Caddy finishes provisioning. Caddy's plain-HTTP vhost reverse-proxies exactly these three paths and redirects everything else to HTTPS, so the router stays accessible during the bootstrap.

### Frontend (`app/frontend/`, PySide6 + qasync)

- `main.py` — `QMainWindow` with a `QStackedLayout` of pages (`chat_page`, `devices_page`, `knowledge_page`, `network_page`, `settings_page`). Uses `qasync.QEventLoop` to run asyncio inside Qt. Optional boot video via `QtMultimedia` (gated by `LOCI_BOOT_VIDEO`).
- `config.py` — derives `BACKEND_HTTP` (loopback to uvicorn — the desktop UI never goes through Caddy), the LAN-facing `PUBLIC_BASE_URL` (defaults to `https://aitje-<n>.local` when Caddy's HTTPS port is 443; this is what gets displayed in the devices/embedder pages), and `SETUP_URL` (`http://aitje-<n>.local/connect` — what the QR codes actually encode). Loads the local-admin bearer token from `devices_db/admin_token.json` so the UI can call admin endpoints without sign-in.
- `translations.py` — large in-repo i18n dictionary (Dutch primary). Frontend `t()` and backend `translations.t()` are **separate** modules with separate keys.

### Webclient (`app/webclient/`, Nuxt 4 SPA)

Built statically (`npm run generate`) and mounted by FastAPI at `/`. `ssr: false`. Pinia for state, Tailwind, `marked` for message rendering. The `.output/public` directory is symlinked from `dist/`. Default backend is the same origin (relies on FastAPI hosting both).

### Embedder (`app/backend/embedder/` + `app/embedder/frontend/`, in-process FastAPI + Nuxt 4 SPA)

The embedding application no longer runs as a separate Laravel process — it's an `APIRouter` (`app/backend/embedder/`) mounted on the same uvicorn at `/embedder/api/v1/*` and a Nuxt 4 SPA generated to `app/embedder/frontend/.output/public` and mounted by FastAPI at `/embedder/`. The SPA is forced to `ssr: false` with `app.baseURL='/embedder/'` and `apiBaseUrl='/embedder/api/v1'` (same-origin). `app/backend/main.py` installs custom exception handlers that wrap embedder API errors into the `{"message": ...}` shape the SPA expects, but only for requests under `/embedder/api/`. Persistence is SQLite at `devices_db/embedder.db`; uploads at `devices_db/embedder_uploads/`; the single admin account is seeded from `EMBEDDER_USER_EMAIL`/`EMBEDDER_USER_PASSWORD`/`EMBEDDER_USER_NAME` on each boot.

**In-process sync (no Git, no ZIP):** `POST /embedder/api/v1/kennisbank/push` (and the automatic sync after `/documents/{id}/process`) calls `app/backend/embedder/sync.py::sync_changed_chunks_to_qdrant()` directly: it embeds chunks whose `content_hash` differs from `last_synced_hash`, upserts them into the `kennisbank` Qdrant collection, deletes chunks that no longer exist in the embedder DB, and writes the sync-state file.

Older docs mention a Laravel backend on `127.0.0.1:8001`, a `_embedder_proxy` in `main.py`, and `app/embedder/backend/` — that all went away when the embedder was internalized; treat any surviving reference as historical.

### Cross-cutting

- **Three clients, one prompt:** desktop Qt UI (REST + SSE), Nuxt SPA (REST + SSE), external REST callers all hit `apiAsk.build_augmented_prompt_with_details`. When changing prompt assembly, RAG retrieval, or model output normalization, verify all three paths.
- **HTTPS for the LAN, plain HTTP for loopback only:** external phones/laptops only ever talk to `https://aitje-<n>.local/` (chat) and `https://aitje-<n>.local/embedder/` (embedder), terminated by Caddy on :443 with a per-device internal CA. Uvicorn itself binds `127.0.0.1:8000`, so anything that needs to hit FastAPI directly (the PySide6 UI, the in-process embedder→device push, tests) uses `http://127.0.0.1:8000`. The bootstrap paths (`/connect`, `/ca.crt`, `/aitje-ca.mobileconfig`) are exempt from the HTTPS redirect on :80 — that's how a phone with no trusted cert reaches the install flow. Caddy data lives under `devices_db/caddy/`; the root CA is mirrored to `devices_db/tls/ca.crt` for `setup_routes.py` to serve.
- **Two QR codes, one onboarding flow:** the devices page and the embedder page each render a QR that encodes `SETUP_URL?app=chat` / `?app=embedder`. Both land on `/connect`; the `app=` hint just picks which app the page nudges the user toward after cert install.
- **Cancellation:** generations are tracked in `active_generations[token]`; `/api/v1/ask/cancel` closes the in-flight `httpx` response.
- **Idle summarization:** if `CHAT_SUMMARY_IDLE_MINUTES > 0`, a background task summarizes chat history after global prompt-idle. Polling cadence is `SUMMARY_POLL_SECONDS = 60`.

## Conventions worth knowing

- The repo root is computed by walking up from `__file__` (`Path(__file__).resolve().parents[2]`) in many modules — don't move files between directory depths without updating those.
- Code comments, error messages, and user-facing strings are mostly in Dutch. Keep that voice when editing them.
- Logs (`*.log`, `kennisbank_cache.db`, `qdrant_storage/*` except `.gitkeep`, `.env`, `fastembed_models/`) are git-ignored — don't commit them. The old `kennisbank_repo/` Git submodule is no longer used (LAN push replaces it).
- `.env` is required and not in git; copy from `.env.example`. The minimum is `DEVICE_NUMBER`.
