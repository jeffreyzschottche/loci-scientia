# End-to-End Test: Embedding Flow

Testplan voor de volledige kennisbank-flow na verwijdering van alle relatie-logica.

## Architectuur

Twee losse stacks die via een git-repo aan elkaar hangen:

| Stack | Locatie | Poort (default) | Rol |
|---|---|---|---|
| Laravel API | `Embedding-Application/backend` | 8000 | Upload, parse, chunk, JSON-LD generatie, git-push |
| Nuxt frontend | `Embedding-Application/frontend` | 3000 | UI voor upload/library/priorities/insights |
| FastAPI | `app/backend` | `$BACKEND_PORT` (default 8000) | Trekt git-repo, bouwt SQLite-cache, serveert RAG |
| PySide6 UI | `app/frontend` | — | Desktop UI voor sync + library view |
| Git repo | `kennisbank_repo/` | — | Overdrachtspunt: Laravel pusht, FastAPI pullt |

> ⚠️ Laravel en FastAPI draaien beide standaard op 8000. Zet `BACKEND_PORT=8001` voor `./lociscientia.sh` of draai ze na elkaar.

## Login credentials (Nuxt)

- **Email:** `user1234@aitje.nl`
- **Wachtwoord:** `pwuser1234`

Deze credentials komen uit `KENNISBANK_USER` / `KENNISBANK_PW` in de root `.env` en worden bij elke Laravel-boot gesynct door `app/Services/KennisbankUserSynchronizer.php`.

## Stappenplan

### 1. Database migreren

Draait de drop-migratie voor `document_relations`, `section_relations`, en `documents.parent_id`.

```bash
cd Embedding-Application/backend
php artisan migrate --force
```

Verwacht: `2026_04_15_000001_drop_relation_tables ... DONE`. MariaDB moet up zijn op `127.0.0.1:3307` per `.env`.

### 2. Laravel API starten

```bash
# in Embedding-Application/backend
php artisan serve --host=127.0.0.1 --port=8000
```

Sanity: `curl http://127.0.0.1:8000/up` moet 200 geven. Op eerste request wordt `KennisbankUserSynchronizer` aangeroepen — dat mag niet meer falen.

### 3. Nuxt frontend starten (nieuw terminal)

```bash
cd Embedding-Application/frontend
npm run dev
```

Open http://localhost:3000, log in met bovenstaande credentials.

### 4. UI smoke test

Controleer dat de relatie-cleanup niks gebroken heeft:

- **Kennisbank → Uploaden**: upload een kleine PDF of MD, doorloop mapping + processing tot `status = formatted`.
- **Kennisbank → Bibliotheek**: tree laadt, document + secties openen zonder console errors.
- **Nav bar**: de tab **"Relaties"** moet weg zijn. Zichtbaar: Uploaden · Bibliotheek · Prioriteiten · Inzicht.
- **Kennisbank → Prioriteiten** en **Inzicht**: beide pagina's laden zonder errors.

### 5. Git config checken

Onder **Mijn Account**: git-config moet staan. Als leeg, vul in:

- Repo URL: `https://github.com/KeesvanRuler/Kees_test_kennisbank.git`
- Branch: `main`
- Access token: uit `KENNISBANK_GIT_TOKEN` in root `.env`

### 6. Push naar GitHub

Klik **"Sync naar GitHub"** rechtsboven in de Kennisbank nav.

Verwacht resultaat in `kennisbank_repo/knowledge_base/`:

```bash
ls kennisbank_repo/knowledge_base/
# manifest.json, model.json, statistics.json,
# categories/, documents/, sections/, chunks/
# GEEN relations/ directory
```

Extra check:

```bash
grep -l documentRelations kennisbank_repo/knowledge_base/manifest.json
# moet niks returnen
```

### 7. Laravel stoppen, FastAPI + PySide6 starten

Stop `php artisan serve` (Ctrl-C) om poort 8000 vrij te maken. Dan:

```bash
cd /home/kees/Documents/loci-scientia
./lociscientia.sh
```

Wat er gebeurt:

- `.venv` wordt gemaakt/geactiveerd, requirements geïnstalleerd
- `uvicorn app.backend.main:app` start op `$BACKEND_PORT`
- Healthcheck op `/health` slaagt
- `python -m app.frontend.main` start de PySide6 UI

### 8. PySide6 sync triggeren

In de PySide6 **Kennisbank** pagina:

1. Klik **🔄 Sync** — progress dialog verschijnt
2. FastAPI hit `/api/v1/kennisbank/sync/stream`, trekt `kennisbank_repo`, herbouwt `kennisbank_cache.db`
3. Progress loopt naar 100% zonder errors
4. Documents table vult zich
5. Vector-DB kaart toont **2 rijen**: Storage, Embeddings — de "Relations" rij is weg
6. Klik op een rij → preview rendert

### 9. Sanity checks

```bash
# SQLite cache moet gevuld zijn
sqlite3 kennisbank_cache.db '.tables'
# documents, chunks, sync_state — geen relations tabel nodig

sqlite3 kennisbank_cache.db 'SELECT COUNT(*) FROM documents;'
# > 0 als de sync werkte
```

Logs bij problemen:

- Laravel: `Embedding-Application/backend/storage/logs/laravel.log`
- FastAPI: `backend.log` in project root
- PySide6: stderr van `./lociscientia.sh`

## Troubleshooting

| Probleem | Oorzaak | Fix |
|---|---|---|
| Login werkt niet | `KennisbankUserSynchronizer` bug (dubbel-gehashed wachtwoord) | Zou opgelost moeten zijn; anders `php artisan tinker --execute="app(\App\Services\KennisbankUserSynchronizer::class)->sync();"` |
| Migratie faalt op index | FK `documents_user_id_foreign` leunt op composite index | Migratie voegt losse `documents_user_id_index` toe vóór drop; zou automatisch moeten gaan |
| PySide6 toont "Relaties" labels | Stale `.pyc` cache | `find app -name __pycache__ -exec rm -rf {} +` en opnieuw starten |
| `KeyError: 'relations'` in PySide6 | Oude `kennisbank_cache.db` met relations-schema | `rm kennisbank_cache.db` en sync opnieuw draaien |
| Port 8000 in gebruik | Laravel + FastAPI botsen | `export BACKEND_PORT=8001` vóór `./lociscientia.sh` |
| Git push faalt | Token verlopen of geen write access | Check `KENNISBANK_GIT_TOKEN` in root `.env` |
| PySide6 sync faalt met `Your local changes to the following files would be overwritten by merge` | Lokale wijzigingen in `kennisbank_repo/` (bijv. handmatige edits of achtergebleven cleanup) botsen met de Laravel-push | Gooi lokale changes weg en pull fast-forward:<br>`cd kennisbank_repo`<br>`git checkout -- .`<br>`git pull`<br>Dit is veilig: de bron van waarheid is de Laravel-export; alles wat lokaal is aangepast wordt bij de volgende push toch overschreven. |

## Wat is verwijderd (ter info)

- Backend: `DocumentRelation`, `SectionRelation` models; `RelationController`; relation-routes; hiërarchie (`parent_id`, `children()`, `ancestors()`, etc.)
- Frontend: `pages/kennisbank/relations.vue`, `RelationModal.vue`, `DocumentNode.vue`; relation store actions; `DocumentRelation`/`SectionRelation`/`Graph*` types; "Relaties" nav tab
- Python: `_load_document_relations()` in `knowledge_library.py`; "Relations" progress row in PySide6 kennisbank page; relatie-translations
- Data: `kennisbank_repo/knowledge_base/relations/` directory; `documentRelations` key in manifest
