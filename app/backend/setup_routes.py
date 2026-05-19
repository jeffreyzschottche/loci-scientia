"""Bootstrap-flow routes for first-time client onboarding.

External clients (phone, laptop, tablet) reach the device over plain HTTP
on port 80 and land on ``/connect``. The page detects the user-agent,
hands the right CA download (Apple .mobileconfig for iOS/macOS, raw .crt
for Android/desktop), and once the device cert is trusted it forwards the
client to the HTTPS chat- or embedder-app.

Reachable over plain HTTP because the whole purpose is to install the cert
that makes HTTPS work in the first place.
"""

from __future__ import annotations

import base64
import os
import plistlib
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

router = APIRouter()


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CA_PATH = _PROJECT_ROOT / "devices_db" / "tls" / "ca.crt"
_PROFILE_NAMESPACE = uuid.UUID("8e1f3c5a-7d2b-4f60-9a3e-1c1a73aa17e5")


def _ca_path() -> Path:
    override = os.environ.get("AITJE_CA_CERT_PATH")
    if override:
        return Path(override)
    return _DEFAULT_CA_PATH


def _device_hostname() -> str:
    explicit = os.environ.get("DEVICE_MDNS")
    if explicit:
        return explicit.strip()
    prefix = (os.environ.get("DEVICE_NAME_PREFIX") or "aitje").strip() or "aitje"
    number = (os.environ.get("DEVICE_NUMBER") or "1").strip() or "1"
    base = os.environ.get("DEVICE_HOSTNAME") or f"{prefix}-{number}"
    return f"{base}.local"


def _https_base(host: str) -> str:
    port = os.environ.get("CADDY_HTTPS_PORT", "443").strip() or "443"
    if port == "443":
        return f"https://{host}"
    return f"https://{host}:{port}"


def _detect_platform(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if "ipad" in ua or "iphone" in ua or "ipod" in ua:
        return "ios"
    if "android" in ua:
        return "android"
    if "macintosh" in ua or "mac os x" in ua:
        return "macos"
    if "windows" in ua:
        return "windows"
    if "linux" in ua:
        return "linux"
    return "other"


def _load_ca_pem() -> Optional[bytes]:
    path = _ca_path()
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _pem_to_der(pem: bytes) -> Optional[bytes]:
    marker_begin = b"-----BEGIN CERTIFICATE-----"
    marker_end = b"-----END CERTIFICATE-----"
    if marker_begin not in pem or marker_end not in pem:
        return None
    inner = pem.split(marker_begin, 1)[1].split(marker_end, 1)[0]
    b64 = b"".join(inner.split())
    try:
        return base64.b64decode(b64, validate=False)
    except Exception:
        return None


@router.get("/ca.crt")
def download_ca_cert() -> Response:
    pem = _load_ca_pem()
    if pem is None:
        raise HTTPException(
            status_code=503,
            detail="CA-certificaat nog niet beschikbaar; herstart lociscientia.sh.",
        )
    return Response(
        content=pem,
        media_type="application/x-x509-ca-cert",
        headers={
            "Content-Disposition": 'attachment; filename="aitje-ca.crt"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/aitje-ca.mobileconfig")
def download_mobileconfig() -> Response:
    pem = _load_ca_pem()
    if pem is None:
        raise HTTPException(
            status_code=503,
            detail="CA-certificaat nog niet beschikbaar; herstart lociscientia.sh.",
        )
    der = _pem_to_der(pem)
    if der is None:
        raise HTTPException(status_code=500, detail="CA-cert kon niet worden gedecodeerd.")

    host = _device_hostname()
    https_base = _https_base(host)
    chat_url = f"{https_base}/"
    embedder_url = f"{https_base}/embedder/"

    ca_uuid = uuid.uuid5(_PROFILE_NAMESPACE, f"ca:{host}")
    chat_uuid = uuid.uuid5(_PROFILE_NAMESPACE, f"chat:{host}")
    embedder_uuid = uuid.uuid5(_PROFILE_NAMESPACE, f"embedder:{host}")
    top_uuid = uuid.uuid5(_PROFILE_NAMESPACE, f"top:{host}")

    payload = {
        "PayloadDisplayName": f"AITJE ({host})",
        "PayloadDescription": (
            "Installeert het AITJE-apparaatcertificaat en plaatst snelkoppelingen "
            "naar de chat en embedder op het beginscherm."
        ),
        "PayloadIdentifier": f"nl.lociscientia.aitje.{host}.profile",
        "PayloadOrganization": "Loci Scientia",
        "PayloadRemovalDisallowed": False,
        "PayloadType": "Configuration",
        "PayloadUUID": str(top_uuid).upper(),
        "PayloadVersion": 1,
        "PayloadContent": [
            {
                "PayloadType": "com.apple.security.root",
                "PayloadVersion": 1,
                "PayloadIdentifier": f"nl.lociscientia.aitje.{host}.ca",
                "PayloadUUID": str(ca_uuid).upper(),
                "PayloadDisplayName": f"AITJE root CA ({host})",
                "PayloadDescription": (
                    "Vertrouwt het lokale TLS-certificaat van dit AITJE-apparaat."
                ),
                "PayloadCertificateFileName": "aitje-ca.crt",
                "PayloadContent": der,
            },
            {
                "PayloadType": "com.apple.webClip.managed",
                "PayloadVersion": 1,
                "PayloadIdentifier": f"nl.lociscientia.aitje.{host}.chat",
                "PayloadUUID": str(chat_uuid).upper(),
                "PayloadDisplayName": "AITJE Chat",
                "URL": chat_url,
                "Label": "AITJE Chat",
                "IsRemovable": True,
                "FullScreen": False,
            },
            {
                "PayloadType": "com.apple.webClip.managed",
                "PayloadVersion": 1,
                "PayloadIdentifier": f"nl.lociscientia.aitje.{host}.embedder",
                "PayloadUUID": str(embedder_uuid).upper(),
                "PayloadDisplayName": "AITJE Embedder",
                "URL": embedder_url,
                "Label": "AITJE Embedder",
                "IsRemovable": True,
                "FullScreen": False,
            },
        ],
    }

    body = plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=False)
    return Response(
        content=body,
        media_type="application/x-apple-aspen-config",
        headers={
            "Content-Disposition": 'attachment; filename="aitje.mobileconfig"',
            "Cache-Control": "no-store",
        },
    )


def _render_connect_page(host: str, platform: str, app: str) -> str:
    https_base = _https_base(host)
    chat_url = f"{https_base}/"
    embedder_url = f"{https_base}/embedder/"
    target_url = embedder_url if app == "embedder" else chat_url
    target_label = "AITJE Embedder" if app == "embedder" else "AITJE Chat"

    if platform in ("ios", "macos"):
        install_label = "Profiel installeren"
        install_href = "/aitje-ca.mobileconfig"
        install_kind = "ios"
    elif platform == "android":
        install_label = "Certificaat downloaden"
        install_href = "/ca.crt"
        install_kind = "android"
    else:
        install_label = "Certificaat downloaden"
        install_href = "/ca.crt"
        install_kind = "desktop"

    instructions = _instructions_html(install_kind)

    page = f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>AITJE verbinden — {host}</title>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0; padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, sans-serif;
      background: #fffdf8;
      color: #0f172a;
      -webkit-font-smoothing: antialiased;
    }}
    main {{
      max-width: 520px;
      margin: 0 auto;
      padding: 32px 20px 64px;
    }}
    .logo {{
      text-align: center;
      font-size: 14px; letter-spacing: 0.32em;
      color: #6b7280; text-transform: uppercase; font-weight: 700;
      margin-bottom: 8px;
    }}
    h1 {{
      font-size: 28px; font-weight: 800; margin: 0 0 8px;
      text-align: center; letter-spacing: -0.01em;
    }}
    .subtitle {{
      text-align: center; color: #4b5563; font-size: 15px; line-height: 1.5;
      margin: 0 0 28px;
    }}
    .host {{
      display: inline-block;
      background: #fff4cf; border: 1px solid #e7dcc0;
      color: #0f172a; font-weight: 700;
      border-radius: 999px; padding: 2px 12px; font-size: 13px;
    }}
    .card {{
      background: #ffffff;
      border: 1px solid #e7dcc0;
      border-radius: 24px;
      padding: 28px 24px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
      margin-bottom: 16px;
    }}
    .step {{
      display: flex; align-items: flex-start; gap: 14px;
      margin-bottom: 14px;
    }}
    .step:last-child {{ margin-bottom: 0; }}
    .step-num {{
      flex: 0 0 28px; height: 28px;
      background: #facc15; color: #050505;
      border-radius: 999px; font-weight: 800; font-size: 14px;
      display: inline-flex; align-items: center; justify-content: center;
    }}
    .step-body {{ flex: 1; }}
    .step-body strong {{ display: block; font-weight: 700; margin-bottom: 2px; }}
    .step-body span {{ color: #4b5563; font-size: 14px; line-height: 1.5; }}
    .btn {{
      display: block;
      text-align: center;
      width: 100%;
      padding: 14px 18px;
      border-radius: 14px;
      font-weight: 800;
      font-size: 16px;
      text-decoration: none;
      letter-spacing: 0.01em;
      transition: transform 0.06s ease;
    }}
    .btn:active {{ transform: translateY(1px); }}
    .btn-primary {{
      background: #facc15; color: #050505;
      border: 1px solid #facc15;
    }}
    .btn-primary:hover {{ background: #fde047; }}
    .btn-secondary {{
      background: #ffffff; color: #0f172a;
      border: 1px solid #e7dcc0;
      margin-top: 10px;
    }}
    .btn-secondary:hover {{ background: #f8f6ef; }}
    .open-row {{ margin-top: 18px; }}
    .open-row .btn + .btn {{ margin-top: 10px; }}
    .hint {{
      font-size: 12px; color: #6b7280;
      text-align: center; margin-top: 18px; line-height: 1.5;
    }}
    .live-status {{
      font-size: 13px; color: #6b7280;
      text-align: center; margin-top: 10px;
      min-height: 18px;
    }}
    .live-status.ok {{ color: #15803d; font-weight: 700; }}
    code {{
      background: #f3f4f6; border-radius: 6px; padding: 1px 6px;
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <main>
    <div class="logo">AITJE · Loci Scientia</div>
    <h1>Verbinden met je apparaat</h1>
    <p class="subtitle">
      Eénmalig: installeer het apparaatcertificaat van
      <span class="host">{host}</span>, daarna werken chat en embedder over een
      beveiligde verbinding (HTTPS).
    </p>

    <div class="card">
      <div class="step">
        <div class="step-num">1</div>
        <div class="step-body">
          <strong>Certificaat installeren</strong>
          <span>Tik op de knop hieronder en volg de stappen voor je apparaat.</span>
        </div>
      </div>

      <a class="btn btn-primary" href="{install_href}" download>{install_label}</a>

      <div style="margin-top:18px">
        {instructions}
      </div>
    </div>

    <div class="card">
      <div class="step">
        <div class="step-num">2</div>
        <div class="step-body">
          <strong>App openen</strong>
          <span>Zodra het certificaat vertrouwd is, opent {target_label} automatisch — of tik hieronder.</span>
        </div>
      </div>

      <div class="open-row">
        <a class="btn btn-primary" id="open-target" href="{target_url}">Open {target_label}</a>
        <a class="btn btn-secondary" href="{chat_url}">Open AITJE Chat</a>
        <a class="btn btn-secondary" href="{embedder_url}">Open AITJE Embedder</a>
      </div>

      <div class="live-status" id="live-status">Controleert verbinding…</div>
    </div>

    <p class="hint">
      Andere apparaat? Open op je laptop of telefoon dezelfde QR-code of ga
      naar <code>http://{host}/connect</code>.
    </p>
  </main>

  <script>
    (function () {{
      var target = {target_url!r};
      var status = document.getElementById('live-status');
      var attempts = 0;
      function poll() {{
        attempts += 1;
        fetch({https_base!r} + '/health', {{ mode: 'cors', cache: 'no-store' }})
          .then(function (r) {{
            if (!r.ok) throw new Error('not ok');
            status.textContent = '✓ Verbonden — doorgaan…';
            status.classList.add('ok');
            setTimeout(function () {{ window.location = target; }}, 600);
          }})
          .catch(function () {{
            if (attempts < 60) {{
              status.textContent = 'Wachten op vertrouwd certificaat…';
              setTimeout(poll, 2000);
            }} else {{
              status.textContent = 'Nog niet vertrouwd. Tik handmatig op "Open" hierboven zodra het profiel geïnstalleerd is.';
            }}
          }});
      }}
      setTimeout(poll, 1500);
    }})();
  </script>
</body>
</html>
"""
    return page


def _instructions_html(kind: str) -> str:
    if kind == "ios":
        return (
            '<span style="font-size:13px;color:#4b5563;line-height:1.55;">'
            "Tik op <strong>Toestaan</strong>, open daarna "
            "<strong>Instellingen → Profiel gedownload → Installeer</strong>. "
            "Ga vervolgens naar <strong>Instellingen → Algemeen → Info → "
            "Certificaatvertrouwensinstellingen</strong> en zet de schakelaar bij "
            "<em>AITJE root CA</em> aan."
            "</span>"
        )
    if kind == "android":
        return (
            '<span style="font-size:13px;color:#4b5563;line-height:1.55;">'
            "Open het gedownloade bestand en kies bij <em>Type</em> "
            "<strong>CA-certificaat</strong>. Bevestig met je toegangscode. "
            "Browsers (Chrome, Firefox) vertrouwen daarna dit apparaat; sommige "
            "apps gebruiken een eigen vertrouwensstore."
            "</span>"
        )
    return (
        '<span style="font-size:13px;color:#4b5563;line-height:1.55;">'
        "Dubbelklik het gedownloade <code>aitje-ca.crt</code> bestand en zet "
        "het in de <strong>Trusted Root</strong>-store. Op macOS: open Sleutelhanger, "
        "sleep het certificaat naar <em>Systeem</em> en zet bij <em>Vertrouwen</em> "
        "de optie op <em>Altijd vertrouwen</em>."
        "</span>"
    )


@router.get("/connect", response_class=HTMLResponse)
def connect_page(request: Request, app: str = "chat") -> HTMLResponse:
    host = _device_hostname()
    platform = _detect_platform(request.headers.get("user-agent", ""))
    app_kind = "embedder" if app == "embedder" else "chat"
    html = _render_connect_page(host=host, platform=platform, app=app_kind)
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})
