# 🧠 Loci Scientia OS

Een lokale “AITJE”-console die een **FastAPI backend**, **PySide6 desktop UI**, vector search (Qdrant), kaarten en chat combineert. Deze README beschrijft hoe je de omgeving klaarzet, hoe je devices exposeert op je LAN, en hoe clients het `/api/v1/ask`-endpoint kunnen aanroepen.

---

## 🚀 Snelstart

```bash
# 1. Zorg dat je in de projectroot zit
cd loci-scientia

# 2. Eenmalig dependencies + services starten
./lociscientia.sh
```

Dat script:

1. Leest `.env` (bijv. `DEVICE_NUMBER=2`) en kiest een hostname zoals `aitje-2`.
2. Op macOS/Linux: zet automatisch HostName/LocalHostName (en schakelt Avahi in op Linux/Jetson).
3. Installeert de virtuele omgeving (`.venv`) en `pip install -r app/requirements.txt`.
4. Start de backend (`uvicorn`) en wacht tot `/health` reageert.
5. Start daarna de Qt-frontend (`python -m app.frontend.main`).
6. Logfiles: `backend.log`, `pmtiles.log`, `ollama.log`.

Stop met `Ctrl+C`; het script sluit frontend/backend af en **zet je originele hostname terug**.

---

## ⚙️ Handmatige installatie (indien nodig)

### 1) Virtuele omgeving

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
```

### 2) Packages

```bash
python -m pip install --upgrade pip
python -m pip install -r app/requirements.txt
```

### 3) Backend starten

```bash
uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Wil je dat de webclient op `http://aitje-2.local:8000` bereikbaar blijft zonder de desktop-UI open te houden, installeer dan de user-service:

```bash
./scripts/install-user-backend-service.sh
```

Controle:

```bash
systemctl --user status aitje-backend.service
curl http://aitje-2.local:8000/health
```

### 4) Frontend starten (nieuw venster)

```bash
python -m app.frontend.main
```

Let op: de frontend gebruikt `BACKEND_HTTP` uit `.env`. Laat `BACKEND_HOST/BACKEND_HTTP` leeg om automatisch `http://aitje-<DEVICE_NUMBER>.local:8000` te gebruiken.

---

## 🌐 LAN-discovery & `.env`

Voor mDNS-advertising en consistente URLs:

```env
DEVICE_NUMBER=2
DEVICE_NAME_PREFIX=aitje
# BACKEND_HOST, BACKEND_HTTP, PUBLIC_BASE_URL leeg laten
```

`./lociscientia.sh` detecteert het platform:

- **macOS**: gebruikt `scutil` om HostName/LocalHostName/ComputerName te zetten naar `aitje-2`.
- **Linux/Jetson**: gebruikt `hostnamectl` en installeert `avahi-daemon` (via `apt`) zodat `aitje-2.local` broadcast. Luistert op `0.0.0.0:8000`.
- **Windows**: toont instructies om de machine handmatig te hernoemen en Bonjour te installeren (automatiseren kan niet zonder adminrechten).

Tijdens shutdown reset het script de hostname automatisch naar de oude waarde.  
Clients op hetzelfde netwerk kunnen dan altijd `http://aitje-2.local:8000/...` bereiken.

---

## 🧩 Remote support

Remote support loopt nu on-demand via een reverse SSH-tunnel met `autossh` naar een Hetzner jump server.
De tunnel staat standaard uit en wordt alleen tijdelijk geopend vanuit de UI.

De volledige setup staat in [docs/remote-support.md](/home/kees/Documents/loci-scientia/docs/remote-support.md).

---

## 📡 API testen

Elke client (bijv. telefoon/laptop) doet nu twee stappen:

```bash
# 1) Token ophalen (90 dagen geldig)
curl -X POST "http://aitje-2.local:8000/api/v1/signon" \
  -H "Content-Type: application/json" \
  -d '{"user_name":"<naam>","password":"<wachtwoord>"}'

# 2) Vraag stellen met Authorization header
curl -X POST "http://aitje-2.local:8000/api/v1/ask" \
  -H "Authorization: Bearer <token-uit-stap-1>" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"biggest city of germany"}'
```

**Verwacht antwoord:** het **zelfde** als in de desktop chat, omdat `/api/v1/ask` nu dezelfde augmented prompt en LLM gebruikt als de streaming-UI.

### Streaming variant

```bash
curl -N "http://aitje-2.local:8000/api/v1/ask/stream" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"vertel een grap"}'
```

Stuurt SSE events (`data: {"status":"queued"...}` gevolgd door token-by-token output).

---

## 📁 Belangrijkste paden

```
app/
  backend/
    main.py          # FastAPI entry
    apiAsk.py        # prompt + Ollama-logica
    devices_repo.py
    schemas.py
    settings.py
  frontend/
    main.py
    widgets/
      api_page.py    # API management UI (Toon API URL-knop)
      devices_page.py# Connected devices (Toon client URL)
  requirements.txt
qdrant_storage/
  devices_db/
.env.example
lociscientia.sh
```

---

## 🧠 Embeddings & Qdrant

- Devices worden in `qdrant_storage/...` opgeslagen via `qdrant-client[fastembed]`.
- `FASTEMBED_MODEL` default naar `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- Wil je volledig offline zijn? Zet de ONNX-modelbestanden in `fastembed_models/<modelnaam>` en stel `FASTEMBED_ALLOW_DOWNLOAD=0`.

---

## 🛠 Troubleshooting

| Probleem | Oplossing |
|----------|-----------|
| `curl` naar `aitje-2.local` faalt | Controleer of `./lociscientia.sh` draaide, `ping aitje-2.local`, of gebruik tijdelijk het IP (`http://192.168.x.x:8000`). |
| Desktop UI zegt “Backend niet bereikbaar” | Kijk in `backend.log` (root van project) of `uvicorn` errors los op. |
| Hostname blijft `aitje-2` na afsluiten | Zorg dat je script met Ctrl+C afsluit (cleanup draait). Bij crash kun je handmatig `sudo scutil --set HostName <oude naam>` doen. |
| Qdrant data onzichtbaar | Controleer of `qdrant_storage/...` schrijfbaar is en dat `QDRANT_*` env niet naar een onbereikbare server wijst. |

---

## ✅ Samenvatting workflow

1. `.env` instellen (minimaal `DEVICE_NUMBER`).
2. `./lociscientia.sh` starten → applicatie én mDNS host up.
3. Lokale UI gebruikt `PUBLIC_BASE_URL` om endpoints te tonen (pop-ups via “Toon API URL”).
4. Externe clients roepen `http://aitje-<nr>.local:8000/api/v1/ask` aan met JSON payload.
5. Afsluiten → hostname + services netjes teruggezet.

Veel succes met AITJE! Mocht je iets missen in de setup, pas `.env.example` aan en run het script opnieuw. 💛
