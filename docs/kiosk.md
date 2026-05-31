# Kioskmodus (Bosgame M5 appliance)

Kioskmodus maakt van een AITJE-kastje een single-purpose appliance: bij het
opstarten verschijnt **alleen** de PySide6-frontend, zonder Ubuntu-/GNOME-bureaublad
en zonder Ubuntu-logo tijdens het booten. Er is geen manier om uit de app naar een
desktop te ontsnappen.

```
Stroom aan → zwart scherm (geen logo) → weston (kiosk-shell) → ./lociscientia.sh → Qt-frontend (enig venster)
```

## Hoe het werkt

| Onderdeel | Rol |
| --- | --- |
| `systemd/aitje-kiosk.service` | Systemd-service die op tty1 **`weston --shell=kiosk-shell.so`** start (de Wayland-kioskcompositor). `Restart=always` met start-limiet (max 5 starts/60s) en `WantedBy=multi-user.target`. |
| `scripts/kiosk-session.sh` | De sessie-client die weston via `--` draait. Start `lociscientia.sh` met `AITJE_KIOSK=1`; de frontend verbindt als Wayland-client en wordt zo het enige venster. **Vangt boot-fouten af**: faalt de stack, dan toont het een leesbaar fullscreen-scherm (met de laatste regels uit `kiosk-session.log`) i.p.v. de sessie te laten crashen → geen knipperende cursor. |
| `scripts/aitje-kiosk-apply.sh` | Zet kiosk **aan/uit** (service + GDM + sudo + GRUB). Idempotent. `enable` weigert op een niet-device tenzij `/etc/aitje-device` bestaat of je `--force` geeft. |
| `scripts/kiosk-test.sh` | **Veilige** test: draait weston GENEST als venster in je huidige desktop (raakt GDM/GRUB/systemd niet aan). `sanity` = minimaal Qt-venster, `frontend` = de echte UI. Ctrl+C of sluit het venster om te stoppen. |
| `sudoers/aitje-kiosk.template` | `NOPASSWD: ALL` voor de device-gebruiker, zodat `lociscientia.sh` onbeheerd boot (apt, hostnamectl, systemctl, setcap, Caddy op :80/:443). |
| GRUB | `splash` wordt verwijderd + stille-boot-vlaggen toegevoegd (`bgrt_disable`, `systemd.show_status=0`, `udev.log_level=3`, `console=tty12`, …) → zwarte boot zonder logo én zonder `[ OK ]/[FAILED]`-bootregels of warnings op tty1. Originele `/etc/default/grub` wordt geback-upt naar `/etc/default/grub.aitje-backup`. |
| GDM | Wordt uitgeschakeld zolang kiosk aanstaat (GNOME laadt niet). Bij uitzetten weer ingeschakeld. |

### Dependencies

De extra systeemdependency is **`weston`** (apt-pakket; bevat `kiosk-shell.so`). Die
wordt automatisch geïnstalleerd door:

- `scripts/aitje-kiosk-apply.sh enable` (kritisch pad — weston moet aanwezig zijn
  vóór de eerste kioskboot), én
- `lociscientia.sh` (via `ensure_kiosk_dependencies`) zodra `SHOW_KIOSK_TOGGLE=1`
  of `AITJE_KIOSK=1`.

> **Waarom weston en niet cage?** cage 0.2.1 (de enige versie in Ubuntu) is gelinkt
> tegen wlroots 0.19 en crasht zodra een Qt-client een surface aanmaakt: native
> Wayland geeft `assert 'surface->initialized'` (`wlr_xdg_surface`), en via XWayland
> `assert ... associate.listener_list` (`xwm.c`). Omdat cage zélf afgaat — niet alleen
> de client — herstart systemd in een lus → de "knipperende cursor" flikker-loop.
> weston is een volwassen, compatibele compositor; `kiosk-shell` maakt de frontend
> fullscreen en de frontend draait gewoon als **native Wayland**-client
> (`QT_QPA_PLATFORM=wayland`).

Er zijn **geen extra Python-dependencies**: de toggle gebruikt alleen de
standaardbibliotheek plus de al aanwezige PySide6/qasync uit `app/requirements.txt`.
`enable` voegt de device-gebruiker ook toe aan `video`/`input`/`render` (terugval
naast logind-seat-ACL's) en maskeert `getty@tty1`. `weston`/Qt verwachten
`XDG_RUNTIME_DIR`; de unit zet dit via `PAMName=login` (pam_systemd), met een
terugval in `kiosk-session.sh`.

In kioskmodus (`AITJE_KIOSK=1`):

- de frontend draait fullscreen en de afsluit/herstart-knop voert een **device**-`poweroff`/`reboot` uit i.p.v. de app te sluiten (anders blijf je op een zwart scherm hangen);
- stopt of crasht de frontend, dan stopt `lociscientia.sh` ook en herstart systemd de hele stack.

## Veilig testen (op élke machine, ook je dev-laptop)

Wil je zien of weston + de frontend renderen zónder iets aan de boot te veranderen,
draai dan de geneste test binnen je normale desktop:

```bash
scripts/kiosk-test.sh sanity     # minimaal Qt-venster onder weston (bewijst render + GPU)
scripts/kiosk-test.sh frontend   # de echte PySide6-frontend onder weston
```

weston opent dan een gewoon **venster** (het grijpt de tty niet over). Sluit het
venster om te stoppen — geen herstel nodig. Werkt `sanity`, dan ligt een eventueel
kiosk-probleem in de boot-stack (`lociscientia.sh`), niet in de compositor.

> ⚠️  Draai `aitje-kiosk-apply.sh enable` **nooit** op een dev-/werkmachine — dat
> schakelt je GDM uit en herschrijft GRUB. De `enable` weigert daarom standaard
> tenzij `/etc/aitje-device` bestaat of je expliciet `--force` geeft.

## Eenmalige bootstrap (op het echte device)

De allereerste keer is er nog geen passwordless sudo en nog geen device-markering.
NOPASSWD kan zichzelf niet zonder wachtwoord installeren, dus draai dit één keer met
sudo in een terminal op het kastje. Twee smaken:

**A. Alles ineens aanzetten via de terminal** (`--force` markeert + zet kiosk aan):

```bash
cd /pad/naar/loci-scientia
sudo scripts/aitje-kiosk-apply.sh enable --force
sudo reboot
```

**B. Alleen voorbereiden en daarna vanuit de Qt-UI aan/uit zetten** (aanrader als je
de toggle wilt gebruiken). `bootstrap` zet enkel NOPASSWD + de device-marker neer,
zónder GDM/GRUB/service aan te raken:

```bash
cd /pad/naar/loci-scientia
sudo scripts/aitje-kiosk-apply.sh bootstrap
```

Na beide bestaat `/etc/aitje-device` en staat NOPASSWD geïnstalleerd, dus kun je
kiosk **zonder wachtwoord en zonder `--force`** aan/uit zetten — ook vanuit de
Qt-UI (zie hieronder).

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
# device_marker=present|absent
# kiosk=on|off
```

> **Let op:** dit alles is bedoeld voor het echte device. Op een ontwikkel-/werkmachine
> hoef je `enable` nooit te draaien — dan schakel je per ongeluk je eigen GNOME uit.
