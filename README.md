# 🧠 Loci Scientia Desktop

Een moderne **desktopapplicatie** met:

- **PySide6 UI** (frontend)
- **FastAPI backend** (API + WebSocket)
- **Chat-interface, API-routebeheer en SSD-monitoring**

---

## 📁 Projectstructuur

```
app/
  backend/
    main.py
    schemas.py
    settings.py
    store.py
  frontend/
    main.py
    theme.py
    net/ws_client.py
    widgets/
      sidebar.py
      headerbar.py
      chat_page.py
      api_page.py
      ssd_monitor.py
  requirements.txt
```

---

## ⚙️ Installatie & Setup

> Deze instructies werken voor zowel **macOS/Linux** als **Windows**.

### 🧩 1. Controleer of Python is geïnstalleerd

#### macOS (zsh)

```bash
command -v python3 && python3 --version
```

Als je géén versie ziet of iets van _“command not found”_, installeer Python via Homebrew:

```bash
# Installeer Homebrew (als je dat nog niet hebt)
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python@3.11
echo 'export PATH="/usr/local/opt/python@3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### Windows (PowerShell)

Download en installeer Python via  
👉 https://www.python.org/downloads/  
Zorg dat je **“Add Python to PATH”** aanvinkt tijdens installatie.

Controleer daarna:

```powershell
py --version
```

---

### 🧱 2. Virtuele omgeving maken

#### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Je terminalprompt verandert nu (bijv. `(venv)`).

---

### 🧰 3. Dependencies installeren

Werk eerst pip bij en installeer daarna alle vereisten:

```bash
python -m pip install -U pip
python -m pip install -r app/requirements.txt
```

#### Veelvoorkomende fout

> `zsh: command not found: python`  
> Gebruik dan `python3` in plaats van `python`.

> `zsh: command not found: pip`  
> Gebruik `python -m pip ...`.

---

## 🚀 Applicatie starten

### ⚡ Eén commando

Als je alles tegelijk wilt starten en alleen verder wil zodra de backend klaar is, draai je vanaf de projectroot:

```bash
./lociscientia.sh
```

Het script zorgt ervoor dat:

1. De virtuele omgeving bestaat en afhankelijkheden worden geïnstalleerd (éénmalig).
2. De backend (`uvicorn ...`) in de achtergrond draait en wacht tot `/health` reageert.
3. Pas als de backend klaar is, wordt de frontend gestart.
4. `backend.log` alle backend-output verzamelt zodat je fouten kunt teruglezen.

Stoppen doe je met Ctrl+C; het script sluit eerst de frontend en daarna de backend netjes af.

### 🖥️ Backend (API + WebSocket)

Laat dit venster open:

```bash
uvicorn app.backend.main:app --reload --host "${BACKEND_HOST:-127.0.0.1}" --port "${BACKEND_PORT:-8000}"
```

Gebruik dezelfde waarden als in `.env` (standaard `127.0.0.1:8000`). Als alles goed is zie je:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

### 🪟 Frontend (PySide6 Desktop UI)

Open een **nieuw terminalvenster**, activeer opnieuw de venv en start:

```bash
source .venv/bin/activate  # (of .\.venv\Scripts\Activate.ps1 op Windows)
python -m app.frontend.main
```

De **Loci Scientia Desktop UI** opent automatisch en verbindt met  
➡️ de `BACKEND_HTTP` uit `.env` (standaard `http://127.0.0.1:8000`)

---

## 🧩 Extra Tools (optioneel)

Maak het makkelijker met `Makefile`-commando’s:

```makefile
# Makefile
setup:
	python -m venv .venv && source .venv/bin/activate && python -m pip install -U pip && python -m pip install -r app/requirements.txt

backend:
	source .venv/bin/activate && uvicorn app.backend.main:app --reload --host "${BACKEND_HOST:-127.0.0.1}" --port "${BACKEND_PORT:-8000}"

frontend:
	source .venv/bin/activate && python -m app.frontend.main
```

Gebruik dan:

```bash
make setup
make backend
make frontend
```

---

## 💡 Troubleshooting

| Probleem                                         | Oplossing                                                                         |
| ------------------------------------------------ | --------------------------------------------------------------------------------- |
| `ModuleNotFoundError: No module named 'fastapi'` | Virtuele omgeving niet actief → `source .venv/bin/activate` en installeer opnieuw |
| `zsh: command not found: python`                 | Gebruik `python3` of installeer via Homebrew                                      |
| `zsh: command not found: pip`                    | Gebruik `python -m pip install ...`                                               |
| Backend start niet                               | Controleer of `uvicorn` geïnstalleerd is (`python -m pip show uvicorn`)           |

---

## 🧬 Credits

**Loci Scientia OS**  
Cognitionis Scientia • Chat, API Management, Knowledge & Monitoring
