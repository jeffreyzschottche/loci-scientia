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
from fastapi.responses import FileResponse, HTMLResponse, Response

router = APIRouter()


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CA_PATH = _PROJECT_ROOT / "devices_db" / "tls" / "ca.crt"
_CONNECT_LOGO_PATH = _PROJECT_ROOT / "app" / "embedder" / "frontend" / "public" / "aitje.png"
_CONNECT_FAVICON_PATH = _PROJECT_ROOT / "app" / "webclient" / "public" / "favicon.ico"
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
    if app == "embedder":
        target_url = embedder_url
        target_label = "AITJE Embedder"
        target_short = "Embedder"
        other_url = chat_url
        other_label = "AITJE Chat"
    else:
        target_url = chat_url
        target_label = "AITJE Chat"
        target_short = "Chat"
        other_url = embedder_url
        other_label = "AITJE Embedder"

    if platform in ("ios", "macos"):
        install_label = "Profiel installeren"
        install_label_en = "Install profile"
        install_href = "/aitje-ca.mobileconfig"
        install_kind = "ios"
        settings_href = "App-prefs:General"
        settings_label = "Open Instellingen"
        settings_label_en = "Open Settings"
    elif platform == "android":
        install_label = "Certificaat downloaden"
        install_label_en = "Download certificate"
        install_href = "/ca.crt"
        install_kind = "android"
        settings_href = "intent:#Intent;action=android.settings.SECURITY_SETTINGS;end"
        settings_label = "Open instellingen"
        settings_label_en = "Open settings"
    else:
        install_label = "Certificaat downloaden"
        install_label_en = "Download certificate"
        install_href = "/ca.crt"
        install_kind = "desktop"
        settings_href = ""
        settings_label = ""
        settings_label_en = ""

    instructions = _all_instructions_html(install_kind)
    settings_button = (
        f'<a class="btn btn-secondary" id="settings-action" href="{settings_href or "#"}" '
        f'{"hidden " if not settings_href else ""}'
        f'data-label-nl="{settings_label}" data-label-en="{settings_label_en}">'
        f"{settings_label}</a>"
    )

    page = f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>AITJE</title>
  <link rel="icon" type="image/x-icon" href="/connect/favicon.ico">
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0; padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, sans-serif;
      background: #fffdf8;
      color: #0f172a;
      -webkit-font-smoothing: antialiased;
    }}
    .topbar {{
      background: #ffffff;
      border-bottom: 1px solid #e5e7eb;
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    .nav-inner {{
      max-width: 1200px;
      margin: 0 auto;
      min-height: 64px;
      padding: 0 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
    }}
    .brand {{
      display: inline-flex;
      align-items: center;
      min-width: 0;
      text-decoration: none;
      color: #111827;
      font-weight: 900;
      letter-spacing: 0;
    }}
    .brand img {{
      display: block;
      height: 40px;
      width: auto;
      object-fit: contain;
    }}
    .brand span {{
      font-size: 18px;
      margin-left: 8px;
    }}
    .brand img[src] + span {{ display: none; }}
    .nav-actions {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }}
    .language-switch {{
      display: inline-flex;
      align-items: center;
      gap: 2px;
      border: 1px solid #e5e7eb;
      background: #ffffff;
      border-radius: 999px;
      padding: 3px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
    }}
    .lang-option {{
      border: 0;
      border-radius: 999px;
      background: transparent;
      color: #4b5563;
      cursor: pointer;
      font-size: 11px;
      font-weight: 800;
      min-width: 34px;
      padding: 6px 8px;
    }}
    .lang-option.active {{
      background: #facc15;
      color: #111827;
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
    .step-toggle {{
      width: 100%;
      border: 0;
      background: transparent;
      padding: 0;
      text-align: left;
      cursor: pointer;
    }}
    .step-toggle:disabled {{ cursor: default; }}
    .step-toggle .step {{ margin-bottom: 0; }}
    .step-num {{
      flex: 0 0 28px; height: 28px;
      background: #facc15; color: #050505;
      border-radius: 999px; font-weight: 800; font-size: 14px;
      display: inline-flex; align-items: center; justify-content: center;
    }}
    .step-body {{ flex: 1; }}
    .step-body strong {{ display: block; font-weight: 700; margin-bottom: 2px; }}
    .step-body span {{ color: #4b5563; font-size: 14px; line-height: 1.5; }}
    .chevron {{
      display: none;
      flex: 0 0 auto;
      width: 28px;
      height: 28px;
      align-items: center;
      justify-content: center;
      color: #4b5563;
      transition: transform 0.16s ease;
    }}
    .cert-trusted .chevron {{ display: inline-flex; }}
    .cert-trusted .step-toggle[aria-expanded="true"] .chevron {{ transform: rotate(180deg); }}
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
    .install-actions .btn + .btn {{ margin-top: 10px; }}
    .instructions {{
      background: #fffdf8;
      border: 1px solid #eee2c4;
      border-radius: 16px;
      padding: 16px;
      margin-top: 18px;
    }}
    .install-panel.collapsed {{ display: none; }}
    .instructions-title {{
      font-size: 14px;
      font-weight: 800;
      margin: 0 0 10px;
      color: #111827;
    }}
    .instructions ol {{
      margin: 0;
      padding-left: 20px;
      color: #374151;
      font-size: 14px;
      line-height: 1.55;
    }}
    .instructions li + li {{ margin-top: 8px; }}
    .small-note {{
      margin: 12px 0 0;
      color: #6b7280;
      font-size: 12px;
      line-height: 1.5;
    }}
    [hidden] {{ display: none !important; }}
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
  <header class="topbar">
    <div class="nav-inner">
      <a class="brand" href="{https_base}/" aria-label="AITJE">
        <img src="/connect/aitje.png" alt="AITJE" />
        <span>AITJE</span>
      </a>
      <div class="nav-actions">
        <div class="language-switch" aria-label="Taal kiezen">
          <button type="button" class="lang-option active" data-lang-button="nl">NL</button>
          <button type="button" class="lang-option" data-lang-button="en">EN</button>
        </div>
      </div>
    </div>
  </header>
  <main>
    <h1 data-i18n="hero.title">Verbinden met je apparaat</h1>
    <p class="subtitle" data-i18n-html="hero.subtitle">
      Eenmalig: installeer het apparaatcertificaat van
      <span class="host">{host}</span>. Daarna werken Chat en Embedder via een
      beveiligde verbinding.
    </p>

    <div class="card">
      <button class="step-toggle" id="install-toggle" type="button" aria-expanded="true" disabled>
        <div class="step">
          <div class="step-num">1</div>
          <div class="step-body">
            <strong data-i18n="install.title">Certificaat installeren</strong>
            <span data-i18n="install.copy">Tik eerst op downloaden. Volg daarna rustig de stappen hieronder.</span>
          </div>
          <span class="chevron" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
              <path d="M5 8l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
        </div>
      </button>

      <div class="install-panel" id="install-panel">
        <div class="install-actions">
          <a class="btn btn-primary" id="install-action" href="{install_href}" download data-label-nl="{install_label}" data-label-en="{install_label_en}">{install_label}</a>
          {settings_button}
        </div>

        <div class="instructions">
          {instructions}
        </div>
      </div>
    </div>

    <div class="card">
      <div class="step">
        <div class="step-num">2</div>
        <div class="step-body">
          <strong data-i18n="open.title">App openen</strong>
          <span data-i18n="open.copy">Zodra het certificaat vertrouwd is, opent de app automatisch. Je kunt ook zelf op openen tikken.</span>
        </div>
      </div>

      <div class="open-row">
        <a class="btn btn-primary" id="open-target" href="{target_url}" data-open-target="true">Open {target_label}</a>
        <a class="btn btn-secondary" href="{other_url}" data-open-other="true">Open {other_label}</a>
      </div>

      <div class="live-status" id="live-status" data-i18n="status.checking">Controleert verbinding...</div>
    </div>

    <p class="hint" data-i18n-html="hint">
      Ander apparaat? Scan dezelfde QR-code of ga naar
      <code>http://{host}/connect</code>.
    </p>
  </main>

  <script>
    (function () {{
      var currentLang = localStorage.getItem('aitje-connect-language') || localStorage.getItem('language') || 'nl';
      currentLang = currentLang.indexOf('en') === 0 ? 'en' : 'nl';
      var target = {target_url!r};
      var healthUrl = {https_base!r} + '/health';
      var host = {host!r};
      var targetLabel = {target_label!r};
      var targetShort = {target_short!r};
      var otherLabel = {other_label!r};
      var status = document.getElementById('live-status');
      var body = document.body;
      var installToggle = document.getElementById('install-toggle');
      var installPanel = document.getElementById('install-panel');
      var attempts = 0;
      var maxAttempts = 120;
      var settled = false;
      var inFlight = false;
      var nextDelay = 500;
      var nextTimer = null;
      var platform = detectPlatform();
      var platformConfig = {{
        android: {{
          installHref: '/ca.crt',
          installNl: 'Certificaat downloaden',
          installEn: 'Download certificate',
          settingsHref: 'intent:#Intent;action=android.settings.SECURITY_SETTINGS;end',
          settingsNl: 'Open CA-certificaten',
          settingsEn: 'Open CA certificates'
        }},
        ios: {{
          installHref: '/aitje-ca.mobileconfig',
          installNl: 'Profiel installeren',
          installEn: 'Install profile',
          settingsHref: 'App-prefs:General',
          settingsNl: 'Open Instellingen',
          settingsEn: 'Open Settings'
        }},
        desktop: {{
          installHref: '/ca.crt',
          installNl: 'Certificaat downloaden',
          installEn: 'Download certificate',
          settingsHref: '',
          settingsNl: '',
          settingsEn: ''
        }}
      }};
      var translations = {{
        nl: {{
          'hero.title': 'Verbinden met je apparaat',
          'hero.subtitle': 'Eenmalig: installeer het apparaatcertificaat van <span class="host">' + host + '</span>. Daarna werken Chat en Embedder via een beveiligde verbinding.',
          'install.title': 'Certificaat installeren',
          'install.copy': 'Tik eerst op downloaden. Volg daarna rustig de stappen hieronder.',
          'open.title': 'App openen',
          'open.copy': 'Zodra het certificaat vertrouwd is, opent de app automatisch. Je kunt ook zelf op openen tikken.',
          'status.checking': 'Controleert verbinding...',
          'status.connected': 'Certificaat vertrouwd. Kies hieronder Chat of Embedder.',
          'status.waiting': 'Wachten op vertrouwd certificaat...',
          'status.manual': 'Nog niet vertrouwd. Tik handmatig op "Open" zodra het certificaat geinstalleerd is.',
          'hint': 'Ander apparaat? Scan dezelfde QR-code of ga naar <code>http://' + host + '/connect</code>.',
          'open.target': 'Open ' + targetLabel,
          'open.other': 'Open ' + otherLabel
        }},
        en: {{
          'hero.title': 'Connect your device',
          'hero.subtitle': 'Install the device certificate for <span class="host">' + host + '</span> once. After that, Chat and Embedder use a secure connection.',
          'install.title': 'Install certificate',
          'install.copy': 'First tap download. Then follow the steps below at your own pace.',
          'open.title': 'Open app',
          'open.copy': 'Once the certificate is trusted, the app opens automatically. You can also tap open yourself.',
          'status.checking': 'Checking connection...',
          'status.connected': 'Certificate trusted. Choose Chat or Embedder below.',
          'status.waiting': 'Waiting for trusted certificate...',
          'status.manual': 'Not trusted yet. Tap "Open" manually after the certificate has been installed.',
          'hint': 'Another device? Scan the same QR code or go to <code>http://' + host + '/connect</code>.',
          'open.target': 'Open ' + targetLabel,
          'open.other': 'Open ' + otherLabel
        }}
      }};

      function translate(key) {{
        return (translations[currentLang] && translations[currentLang][key]) || translations.nl[key] || key;
      }}

      function detectPlatform() {{
        var ua = (navigator.userAgent || '').toLowerCase();
        var platformName = (navigator.platform || '').toLowerCase();
        var isiPadOS = platformName === 'macintel' && navigator.maxTouchPoints > 1;
        if (ua.indexOf('android') !== -1) return 'android';
        if (ua.indexOf('iphone') !== -1 || ua.indexOf('ipad') !== -1 || ua.indexOf('ipod') !== -1 || isiPadOS) return 'ios';
        return 'desktop';
      }}

      function applyPlatform() {{
        var config = platformConfig[platform] || platformConfig.desktop;
        var installAction = document.getElementById('install-action');
        var settingsAction = document.getElementById('settings-action');
        if (installAction) {{
          installAction.href = config.installHref;
          installAction.setAttribute('data-label-nl', config.installNl);
          installAction.setAttribute('data-label-en', config.installEn);
          if (platform === 'ios') installAction.removeAttribute('download');
          else installAction.setAttribute('download', '');
        }}
        if (settingsAction) {{
          if (config.settingsHref) {{
            settingsAction.hidden = false;
            settingsAction.href = config.settingsHref;
            settingsAction.setAttribute('data-label-nl', config.settingsNl);
            settingsAction.setAttribute('data-label-en', config.settingsEn);
          }} else {{
            settingsAction.hidden = true;
          }}
        }}
        document.querySelectorAll('[data-platform]').forEach(function (block) {{
          block.hidden = block.getAttribute('data-platform') !== platform;
        }});
      }}

      function applyLanguage(lang) {{
        currentLang = lang === 'en' ? 'en' : 'nl';
        localStorage.setItem('aitje-connect-language', currentLang);
        localStorage.setItem('language', currentLang === 'en' ? 'en-US' : 'nl-NL');
        document.documentElement.lang = currentLang;
        document.querySelectorAll('[data-i18n]').forEach(function (el) {{
          el.textContent = translate(el.getAttribute('data-i18n'));
        }});
        document.querySelectorAll('[data-i18n-html]').forEach(function (el) {{
          el.innerHTML = translate(el.getAttribute('data-i18n-html'));
        }});
        document.querySelectorAll('[data-lang-button]').forEach(function (button) {{
          button.classList.toggle('active', button.getAttribute('data-lang-button') === currentLang);
        }});
        document.querySelectorAll('[data-locale]').forEach(function (block) {{
          block.hidden = block.getAttribute('data-locale') !== currentLang;
        }});
        document.querySelectorAll('[data-label-nl][data-label-en]').forEach(function (el) {{
          el.textContent = el.getAttribute(currentLang === 'en' ? 'data-label-en' : 'data-label-nl');
        }});
        var openTarget = document.querySelector('[data-open-target]');
        var openOther = document.querySelector('[data-open-other]');
        if (openTarget) openTarget.textContent = translate('open.target');
        if (openOther) openOther.textContent = translate('open.other');
      }}

      function redirect() {{
        if (settled) return;
        settled = true;
        body.classList.add('cert-trusted');
        if (installToggle && installPanel) {{
          installToggle.disabled = false;
          installToggle.setAttribute('aria-expanded', 'false');
          installPanel.classList.add('collapsed');
        }}
        status.textContent = translate('status.connected');
        status.classList.add('ok');
      }}

      function schedule(delay) {{
        if (settled) return;
        if (nextTimer) clearTimeout(nextTimer);
        nextTimer = setTimeout(poll, delay);
      }}

      function poll() {{
        nextTimer = null;
        if (settled || inFlight) return;
        inFlight = true;
        attempts += 1;
        fetch(healthUrl, {{ mode: 'cors', cache: 'no-store' }})
          .then(function (r) {{
            inFlight = false;
            if (!r.ok) throw new Error('not ok');
            redirect();
          }})
          .catch(function () {{
            inFlight = false;
            if (settled) return;
            if (attempts >= maxAttempts) {{
              status.textContent = translate('status.manual');
              return;
            }}
            status.textContent = translate('status.waiting');
            // Gentle backoff: 500ms → cap at 2s. Visibilitychange resets it,
            // so a returning user always gets a fast first poll.
            nextDelay = Math.min(nextDelay + 250, 2000);
            schedule(nextDelay);
          }});
      }}

      function nudge() {{
        // Fired when the user comes back to the page (e.g. after installing
        // the profile in Settings on iOS). Reset the cadence and poll now.
        if (settled) return;
        nextDelay = 500;
        if (nextTimer) {{ clearTimeout(nextTimer); nextTimer = null; }}
        poll();
      }}

      document.addEventListener('visibilitychange', function () {{
        if (document.visibilityState === 'visible') nudge();
      }});
      window.addEventListener('pageshow', nudge);
      window.addEventListener('focus', nudge);
      document.querySelectorAll('[data-lang-button]').forEach(function (button) {{
        button.addEventListener('click', function () {{
          applyLanguage(button.getAttribute('data-lang-button'));
        }});
      }});
      if (installToggle && installPanel) {{
        installToggle.addEventListener('click', function () {{
          if (!body.classList.contains('cert-trusted')) return;
          var expanded = installToggle.getAttribute('aria-expanded') === 'true';
          installToggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
          installPanel.classList.toggle('collapsed', expanded);
        }});
      }}

      applyPlatform();
      applyLanguage(currentLang);
      // First poll: immediate, no initial delay.
      poll();
    }})();
  </script>
</body>
</html>
"""
    return page


def _all_instructions_html(active_kind: str) -> str:
    return "".join(
        _instructions_html(kind, active=(kind == active_kind))
        for kind in ("android", "ios", "desktop")
    )


def _instructions_html(kind: str, active: bool = True) -> str:
    hidden = "" if active else " hidden"
    platform_open = f'<div data-platform="{kind}"{hidden}>'
    platform_close = "</div>"
    if kind == "ios":
        return platform_open + (
            '<div data-locale="nl">'
            '<p class="instructions-title">Op iPhone of iPad</p>'
            "<ol>"
            "<li>Tik op <strong>Profiel installeren</strong> en kies "
            "<strong>Sta toe</strong>.</li>"
            "<li>Open <strong>Instellingen</strong>. Bovenaan staat meestal "
            "<strong>Profiel gedownload</strong>. Tik daarop en kies "
            "<strong>Installeer</strong>.</li>"
            "<li>Ga daarna naar <strong>Instellingen → Algemeen → Info → "
            "Certificaatvertrouwensinstellingen</strong>.</li>"
            "<li>Zet <strong>AITJE root CA</strong> aan en bevestig dat je het "
            "certificaat vertrouwt.</li>"
            "<li>Kom terug naar deze pagina. AITJE opent daarna vanzelf, of tik "
            "op <strong>Open AITJE</strong>.</li>"
            "</ol>"
            '<p class="small-note">Op iOS moet dit handmatig. Apple laat een '
            "website een CA-certificaat niet automatisch vertrouwen.</p>"
            "</div>"
            '<div data-locale="en" hidden>'
            '<p class="instructions-title">On iPhone or iPad</p>'
            "<ol>"
            "<li>Tap <strong>Install profile</strong> and choose "
            "<strong>Allow</strong>.</li>"
            "<li>Open <strong>Settings</strong>. Near the top you should see "
            "<strong>Profile Downloaded</strong>. Tap it and choose "
            "<strong>Install</strong>.</li>"
            "<li>Then go to <strong>Settings → General → About → Certificate "
            "Trust Settings</strong>.</li>"
            "<li>Turn on <strong>AITJE root CA</strong> and confirm that you "
            "trust the certificate.</li>"
            "<li>Return to this page. AITJE will open automatically, or tap "
            "<strong>Open AITJE</strong>.</li>"
            "</ol>"
            '<p class="small-note">On iOS this must be done manually. Apple does '
            "not allow a website to trust a CA certificate automatically.</p>"
            "</div>"
        ) + platform_close
    if kind == "android":
        return platform_open + (
            '<div data-locale="nl">'
            '<p class="instructions-title">Op Android</p>'
            "<ol>"
            "<li>Tik eerst op <strong>Certificaat downloaden</strong>. Het bestand "
            "heet <strong>aitje-ca.crt</strong>.</li>"
            "<li>Tik daarna op <strong>Open CA-certificaten</strong>. Werkt die knop "
            "niet, open zelf de app <strong>Instellingen</strong>.</li>"
            "<li>Zoek in Instellingen naar <strong>certificaat</strong> of ga naar "
            "<strong>Beveiliging → Encryptie en referenties → Certificaat "
            "installeren</strong>. De naam verschilt per Android-telefoon.</li>"
            "<li>Kies <strong>CA-certificaat</strong>, selecteer "
            "<strong>aitje-ca.crt</strong> bij Downloads en geef het certificaat "
            "de naam <strong>AITJE</strong>.</li>"
            "<li>Bevestig met je pincode, patroon of vingerafdruk. Kom daarna "
            "terug naar deze pagina en tik op <strong>Open AITJE</strong>.</li>"
            "</ol>"
            '<p class="small-note">Android toont hierbij een waarschuwing. Dat is '
            "normaal: je geeft alleen jouw AITJE-apparaat toestemming voor HTTPS "
            "op je eigen netwerk.</p>"
            "</div>"
            '<div data-locale="en" hidden>'
            '<p class="instructions-title">On Android</p>'
            "<ol>"
            "<li>First tap <strong>Download certificate</strong>. The file is "
            "called <strong>aitje-ca.crt</strong>.</li>"
            "<li>Then tap <strong>Open CA certificates</strong>. If that button does "
            "not work, open the <strong>Settings</strong> app yourself.</li>"
            "<li>Search Settings for <strong>certificate</strong>, or go to "
            "<strong>Security → Encryption and credentials → Install a "
            "certificate</strong>. The name differs per Android phone.</li>"
            "<li>Choose <strong>CA certificate</strong>, select "
            "<strong>aitje-ca.crt</strong> from Downloads and name it "
            "<strong>AITJE</strong>.</li>"
            "<li>Confirm with your PIN, pattern or fingerprint. Return to this "
            "page and tap <strong>Open AITJE</strong>.</li>"
            "</ol>"
            '<p class="small-note">Android shows a warning here. That is normal: '
            "you only allow your own AITJE device to use HTTPS on your local "
            "network.</p>"
            "</div>"
        ) + platform_close
    return platform_open + (
        '<div data-locale="nl">'
        '<p class="instructions-title">Op laptop of desktop</p>'
        "<ol>"
        "<li>Download <strong>aitje-ca.crt</strong>.</li>"
        "<li>Installeer het certificaat als vertrouwde root-CA.</li>"
        "<li>Op macOS: open Sleutelhanger, sleep het certificaat naar "
        "<strong>Systeem</strong> en zet <strong>Vertrouwen</strong> op "
        "<strong>Altijd vertrouwen</strong>.</li>"
        "<li>Op Windows: kies de store <strong>Trusted Root Certification "
        "Authorities</strong>.</li>"
        "</ol>"
        "</div>"
        '<div data-locale="en" hidden>'
        '<p class="instructions-title">On laptop or desktop</p>'
        "<ol>"
        "<li>Download <strong>aitje-ca.crt</strong>.</li>"
        "<li>Install the certificate as a trusted root CA.</li>"
        "<li>On macOS: open Keychain Access, drag the certificate to "
        "<strong>System</strong> and set <strong>Trust</strong> to "
        "<strong>Always Trust</strong>.</li>"
        "<li>On Windows: choose the <strong>Trusted Root Certification "
        "Authorities</strong> store.</li>"
        "</ol>"
        "</div>"
    ) + platform_close


def _connect_response(request: Request, app: str) -> HTMLResponse:
    host = _device_hostname()
    platform = _detect_platform(request.headers.get("user-agent", ""))
    app_kind = "embedder" if app == "embedder" else "chat"
    html = _render_connect_page(host=host, platform=platform, app=app_kind)
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


@router.get("/connect", response_class=HTMLResponse)
def connect_page_default(request: Request) -> HTMLResponse:
    # Bare /connect — default to chat. Kept so a hand-typed bare URL still works.
    return _connect_response(request, "chat")


@router.get("/connect/aitje.png")
def connect_logo() -> FileResponse:
    if not _CONNECT_LOGO_PATH.is_file():
        raise HTTPException(status_code=404, detail="Logo niet gevonden.")
    return FileResponse(
        _CONNECT_LOGO_PATH,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/connect/favicon.ico")
def connect_favicon() -> FileResponse:
    if not _CONNECT_FAVICON_PATH.is_file():
        raise HTTPException(status_code=404, detail="Favicon niet gevonden.")
    return FileResponse(
        _CONNECT_FAVICON_PATH,
        media_type="image/x-icon",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/connect/{app}", response_class=HTMLResponse)
def connect_page_app(request: Request, app: str) -> HTMLResponse:
    # /connect/chat or /connect/embedder — the QR codes encode these.
    return _connect_response(request, app)
