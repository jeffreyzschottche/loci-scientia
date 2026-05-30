# Kioskmodus (Bosgame M5 appliance)

Kioskmodus maakt van een AITJE-kastje een single-purpose appliance: bij het
opstarten verschijnt **alleen** de PySide6-frontend, zonder Ubuntu-/GNOME-bureaublad
en zonder Ubuntu-logo tijdens het booten. Er is geen manier om uit de app naar een
desktop te ontsnappen.

```
Stroom aan → zwart scherm (geen logo) → cage → ./lociscientia.sh → Qt-frontend (enig venster)
```

## Hoe het werkt

| Onderdeel | Rol |
| --- | --- |
| `systemd/aitje-kiosk.service` | Systemd-service die op tty1 **`cage`** start (de Wayland-kioskcompositor). `Restart=always` met start-limiet (max 5 starts/60s) en `WantedBy=multi-user.target`. |
| `scripts/kiosk-session.sh` | Het enige commando dat cage draait. Exec't `lociscientia.sh` met `AITJE_KIOSK=1`. De frontend wordt zo het enige venster. |
| `scripts/aitje-kiosk-apply.sh` | Zet kiosk **aan/uit** (service + GDM + sudo + GRUB). Idempotent. |
| `sudoers/aitje-kiosk.template` | `NOPASSWD: ALL` voor de device-gebruiker, zodat `lociscientia.sh` onbeheerd boot (apt, hostnamectl, systemctl, setcap, Caddy op :80/:443). |
| GRUB | `splash` wordt verwijderd + `bgrt_disable` toegevoegd → zwarte boot zonder logo. Originele `/etc/default/grub` wordt geback-upt naar `/etc/default/grub.aitje-backup`. |
| GDM | Wordt uitgeschakeld zolang kiosk aanstaat (GNOME laadt niet). Bij uitzetten weer ingeschakeld. |

### Dependencies

De enige extra systeemdependency is **`cage`** (apt-pakket). Die wordt
automatisch geïnstalleerd door:

- `scripts/aitje-kiosk-apply.sh enable` (kritisch pad — cage moet aanwezig zijn
  vóór de eerste kioskboot), én
- `lociscientia.sh` (via `ensure_kiosk_dependencies`) zodra `SHOW_KIOSK_TOGGLE=1`
  of `AITJE_KIOSK=1`.

Er zijn **geen extra Python-dependencies**: de toggle gebruikt alleen de
standaardbibliotheek plus de al aanwezige PySide6/qasync uit `app/requirements.txt`.
`enable` voegt de device-gebruiker ook toe aan `video`/`input`/`render` (terugval
naast logind-seat-ACL's) en maskeert `getty@tty1`. `cage`/Qt verwachten
`XDG_RUNTIME_DIR`; de unit zet dit via `PAMName=login` (pam_systemd), met een
terugval in `kiosk-session.sh`.

In kioskmodus (`AITJE_KIOSK=1`):

- de frontend draait fullscreen en de afsluit/herstart-knop voert een **device**-`poweroff`/`reboot` uit i.p.v. de app te sluiten (anders blijf je op een zwart scherm hangen);
- stopt of crasht de frontend, dan stopt `lociscientia.sh` ook en herstart systemd de hele stack.

## Eenmalige bootstrap (op het device)

De allereerste keer is er nog geen passwordless sudo, dus draai dit één keer in een
terminal op het kastje:

```bash
cd /pad/naar/loci-scientia
sudo scripts/aitje-kiosk-apply.sh enable
sudo reboot
```

Daarna staat NOPASSWD geïnstalleerd en kun je kiosk aan/uit zetten **zonder
wachtwoord** — ook vanuit de Qt-UI (zie hieronder).

## De dev-toggle in de Qt-UI

Voor ontwikkel-/onderhoudskastjes is er een schakelaar in **Instellingen → Systeem →
Kioskmodus**. Die is standaard **verborgen**; zet hem aan met een vlag in `.env`:

```bash
SHOW_KIOSK_TOGGLE=1
```

De schakelaar roept `scripts/aitje-kiosk-apply.sh enable|disable` aan via
`sudo -n` en biedt daarna aan om te herstarten. Lukt `sudo -n` niet (de bootstrap
hierboven is nog niet gedaan), dan toont de UI welke commando je eenmalig moet
draaien.

- **Aan** → kiosk-service + sudo + GDM-uit + zwarte boot. Herstart om toe te passen.
- **Uit** → GNOME-desktop terug, GRUB hersteld, kiosk-service uit. Herstart om toe te passen.

## Handmatig terug naar een normale desktop

```bash
sudo scripts/aitje-kiosk-apply.sh disable
sudo reboot
```

Lukt de UI niet meer (kiosk hangt): schakel naar een andere VT met
`Ctrl+Alt+F3`, log in en draai bovenstaande `disable`.

## Status opvragen

```bash
scripts/aitje-kiosk-apply.sh status
# kiosk_service=enabled|disabled|absent
# display_manager=enabled|disabled|absent
# grub_splash=present|absent
# sudoers=present|absent
# kiosk=on|off
```

> **Let op:** dit alles is bedoeld voor het echte device. Op een ontwikkel-/werkmachine
> hoef je `enable` nooit te draaien — dan schakel je per ongeluk je eigen GNOME uit.
