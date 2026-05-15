# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

"Loci Scientia OS" / "AITJE" — a local-first device that bundles a FastAPI backend, a PySide6 desktop UI, a Nuxt SPA webclient, Ollama for LLM inference, Qdrant for vector storage, SearXNG for web search, and the Aitje Embedding Application (Laravel + Nuxt SPA) under `/embedder`. Each physical device runs the whole stack and advertises itself on the LAN as `aitje-<DEVICE_NUMBER>.local` so phones/laptops can hit `http://aitje-2.local:8000/api/v1/ask` or open `http://aitje-2.local:8000/embedder/` in a browser. README is in Dutch.

## Bootstrap & run

`./lociscientia.sh` is the entry point — it sources `.env`, sets hostname/mDNS, installs `.venv` (`app/requirements.txt`), starts/pulls Ollama, optionally starts a SearXNG Docker container, builds the Nuxt webclient (incremental: rebuilds when `app/webclient/{app,public,*.json,*.ts}` is newer than the build stamp), composer-installs + migrates the embedder Laravel app (SQLite, incremental on `composer.lock`), builds the embedder Nuxt SPA (same stamp pattern), starts `php artisan serve` on `127.0.0.1:${EMBEDDER_PORT:-8001}`, starts uvicorn, waits for `/health`, and finally launches the PySide6 frontend. `Ctrl+C` triggers the cleanup trap that restores the original hostname and kills the embedder PHP process.

Manual run (after `source .venv/bin/activate`):
- Backend: `python -m uvicorn app.backend.main:app --reload --host 0.0.0.0 --port 8000`
- Frontend: `python -m app.frontend.main`
- Webclient dev: `cd app/webclient && npm run dev` (Nuxt dev on :3000, served from FastAPI `/` in prod via `npm run generate` → `.output/public`)
- Tests: `python -m pytest app/tests` — single test: `python -m pytest app/tests/test_prompt_building.py::TestName::test_x`. Tests stub `qdrant_client` and `fastembed` so they run without those models installed (see `_install_dependency_stubs` in `test_prompt_building.py`).

Logs land in the repo root: `backend.log`, `ollama.log`, `promptlog.log` (full augmented prompts), `apiprompt.log` (API-only prompts).

## Architecture

### Backend (`app/backend/`, FastAPI)

- `main.py` — all routes live here (`/api/v1/ask`, `/api/v1/ask/stream` SSE, `/api/v1/signon`, `/api/v1/kennisbank/import` + `/import/stream` SSE for receiving pushes from the embedder, `/api/v1/kennisbank/sync-state`, `/devices`, support tunnel, Ollama model switch, WebSocket at `settings.ws_path`). Holds module-level singletons: `devices_repo`, `token_store`, `chat_history`, `support_tunnel`, `admin_tokens`, `ApiStats`, `DevicePresenceTracker`, `active_generations` (for cancellation).
- `apiAsk.py` — the prompt-building heart. Loads `prompt.txt` plus mode templates from `prompt_templates/`, normalizes images/documents (PDFs via pypdf, docx/xlsx), pulls top-k RAG context from Qdrant, fuses web-search results, calls Ollama. `/api/v1/ask` (REST) and the WebSocket/SSE streaming path go through the **same** `build_augmented_prompt_with_details` so responses match across clients — preserve this invariant.
- `settings.py` — single `Settings` pydantic model populated from env via `get_settings()` at import. `OLLAMA_MAX_CONTEXT` is a comma list aligned by index with `OLLAMA_MODELS`. The module-level `settings` is evaluated once at import; don't mutate it, re-export it.
- `auth_tokens.py` (`BearerTokenStore`, 90-day TTL, JSON-backed) + `admin_access.py` (`AdminTokenManager` writes `devices_db/admin_token.json` for the local UI). Most admin routes use `Depends(require_admin_token)`; user-facing `/api/v1/ask` uses `Depends(require_token)`.
- `devices_repo.py` / `kennisbank_sync.py` / `knowledge_repository.py` — Qdrant collections (`devices`, `kennisbank`) accessed through `qdrant_utils.get_qdrant_client()`, which returns either an embedded client context manager (default, file-backed in `qdrant_storage/`) or a cached remote client when `QDRANT_HOST` is set. The embedded client is guarded by a process-wide lock — only one block can be open at a time.
- `rag/embedder.py` — `fastembed` wrapper. Default model `paraphrase-multilingual-mpnet-base-v2`; offline mode requires the unpacked ONNX in `fastembed_models/<model>/` and `FASTEMBED_ALLOW_DOWNLOAD=0`. Cached via `lru_cache`.
- `kennisbank_sync.py` — receives a `knowledge_base/` JSON-LD export bundle (POSTed as a ZIP to `/api/v1/kennisbank/import` by the embedder app, no Git involved), chunks JSON-LD documents, hashes chunks (`.kennisbank_chunk_hashes.json`) so only changed chunks re-embed. SQLite cache at `kennisbank_cache.db`, sync-state at `devices_db/kennisbank_sync_state.json`. Public entry point: `import_kennisbank_from_dir(export_base, progress_callback=...)`.
- `support_tunnel.py` — wraps the `aitje-tunnel` systemd unit (see `systemd/`, `sudoers/`, `docs/remote-support.md`). Opens reverse-SSH via `systemd-run` with an auto-stop timer.
- `web_search.py` — SearXNG client. Toggled per request from the UI; results are folded into the prompt by `apiAsk.py`.

### Frontend (`app/frontend/`, PySide6 + qasync)

- `main.py` — `QMainWindow` with a `QStackedLayout` of pages (`chat_page`, `devices_page`, `knowledge_page`, `network_page`, `settings_page`). Uses `qasync.QEventLoop` to run asyncio inside Qt. Optional boot video via `QtMultimedia` (gated by `LOCI_BOOT_VIDEO`).
- `config.py` — derives `BACKEND_HTTP`, `BACKEND_WS`, `PUBLIC_BASE_URL` from `.env` with the rule: if `BACKEND_HOST` is empty or `0.0.0.0/127.0.0.1`, fall back to `aitje-<DEVICE_NUMBER>.local`. Loads the local-admin bearer token from `devices_db/admin_token.json` so the UI can call admin endpoints without sign-in.
- `net/ws_client.py` — WebSocket to the backend's `/ws` path.
- `translations.py` — large in-repo i18n dictionary (Dutch primary). Frontend `t()` and backend `translations.t()` are **separate** modules with separate keys.

### Webclient (`app/webclient/`, Nuxt 4 SPA)

Built statically (`npm run generate`) and mounted by FastAPI at `/`. `ssr: false`. Pinia for state, Tailwind, `marked` for message rendering. The `.output/public` directory is symlinked from `dist/`. Default backend is the same origin (relies on FastAPI hosting both).

### Embedder (`app/embedder/{backend,frontend}/`, Laravel 12 + Nuxt 4 SPA)

**LAN push (no Git):** the embedder pushes a knowledge-base export directly to the device's FastAPI via `POST /embedder/api/v1/kennisbank/push` → `KennisbankController::pushToDevice` → `Services\DeviceSyncService::syncUser`, which calls `JsonLdGenerator::generateStructuredFileMap`, zips the result with `knowledge_base/...` paths, and POSTs it as `bundle` (multipart) to `${AITJE_DEVICE_BASE_URL}/api/v1/kennisbank/import` with the device's admin bearer (read lazily from `devices_db/admin_token.json`). The old `GitConfiguration` model, `GitSyncService`, and `git-config` admin routes are deleted (migration `2026_05_15_000001_drop_git_configurations_table.php` drops the table).

Geïnternaliseerde Aitje Embedding Application. The Laravel backend uses SQLite (`database/database.sqlite`), Sanctum personal-access tokens (Bearer only — no cookie/session domain config), and binds to `127.0.0.1:${EMBEDDER_PORT:-8001}`. Routes are mounted by Laravel under `/embedder/api/*` via `apiPrefix` in `bootstrap/app.php` — same path the SPA hits, so signed URLs (email verification) survive the proxy hop. The Nuxt frontend is forced to `ssr: false` with `app.baseURL='/embedder/'` and `apiBaseUrl='/embedder/api/v1'` (same-origin). FastAPI reverse-proxies `/embedder/api/*` to the Laravel loopback port (`_embedder_proxy` in `main.py`, preserving the full path) and mounts the generated SPA at `/embedder/`. `bootstrap/app.php` trusts `*` proxies; `AppServiceProvider::boot()` calls `URL::forceRootUrl(config('app.url'))`. `lociscientia.sh` seeds `APP_URL` (scheme+host only — no `/embedder` suffix), `FRONTEND_URL` (with `/embedder` suffix), `ADMIN_EMAIL`, `ADMIN_PASSWORD_HASH` into `app/embedder/backend/.env` on each boot. Several upstream migrations used MySQL-only SQL (`SHOW INDEX`, `MODIFY ENUM`, `information_schema.KEY_COLUMN_USAGE`, `ALTER TABLE ... DROP FOREIGN KEY`) — they are guarded with driver checks or replaced with `Schema::getIndexes()` / `->change()` so SQLite passes.

### Cross-cutting

- **Three clients, one prompt:** desktop Qt UI (WebSocket), Nuxt SPA (REST + SSE), external REST callers all hit `apiAsk.build_augmented_prompt_with_details`. When changing prompt assembly, RAG retrieval, or model output normalization, verify all three paths.
- **Cancellation:** generations are tracked in `active_generations[token]`; `/api/v1/ask/cancel` closes the in-flight `httpx` response.
- **Idle summarization:** if `CHAT_SUMMARY_IDLE_MINUTES > 0`, a background task summarizes chat history after global prompt-idle. Polling cadence is `SUMMARY_POLL_SECONDS = 60`.

## Conventions worth knowing

- The repo root is computed by walking up from `__file__` (`Path(__file__).resolve().parents[2]`) in many modules — don't move files between directory depths without updating those.
- Code comments, error messages, and user-facing strings are mostly in Dutch. Keep that voice when editing them.
- Logs (`*.log`, `kennisbank_cache.db`, `qdrant_storage/*` except `.gitkeep`, `.env`, `fastembed_models/`) are git-ignored — don't commit them. The old `kennisbank_repo/` Git submodule is no longer used (LAN push replaces it).
- `.env` is required and not in git; copy from `.env.example`. The minimum is `DEVICE_NUMBER`.
