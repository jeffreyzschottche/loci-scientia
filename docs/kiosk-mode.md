# Kiosk-modus

Kiosk-modus laat een AITJE edge-device direct opstarten in de AITJE-interface zonder dat de eindgebruiker het GRUB-menu, een Ubuntu loginscherm of de GNOME shell ziet. Tijdens ontwikkeling kun je vanuit dezelfde UI weer terugschakelen naar de normale Ubuntu-desktop.

De modus is bedoeld voor klant-deployments: één doel, één scherm, geen rondklikken in het OS. Dat past bij de appliance-positionering en voorkomt dat een eindgebruiker per ongeluk in lokale data of accounts terechtkomt — wat voor onze GDPR / data-sovereignty propositie belangrijk is.

## Wat het doet

- GRUB stilgezet (`GRUB_TIMEOUT=0`, `GRUB_TIMEOUT_STYLE=hidden`, `quiet splash`).
- Plymouth toont een AITJE-branded splash (logo + gele dot-spinner op donkere achtergrond).
- Auto-login voor de `aitje` user via GDM3.
- Op `tty1` start systemd `aitje-kiosk.service`: een `cage` Wayland-compositor die `lociscientia.sh` opstart — backend + Qt-frontend in één sessie.
- De toggle is bedienbaar vanuit de AITJE UI én vanuit de CLI.

## Installatie

Run het installer-script eenmalig op een fresh device:

```bash
sudo bash scripts/kiosk/install.sh
```

Het script is idempotent: re-runnen op een al ingerichte device is veilig en herhaalt geen werk.

Standaard staat kiosk-modus **uit** na de installatie — `gdm3` blijft actief en je houdt je gewone Ubuntu-desktop tot je expliciet toggled. Dit voorkomt dat een dev-machine ineens in kiosk-modus opstart.

Configureerbare paden (env vars vóór het commando zetten):

| Variabele | Default |
|-----------|---------|
| `AITJE_PROJECT_ROOT` | de map waar het script vandaan draait (de repo-checkout) |
| `AITJE_USER` | `aitje` |
| `AITJE_STATE_FILE` | `/etc/aitje/kiosk-mode` |
| `AITJE_LOG_FILE` | `/var/log/aitje-kiosk-toggle.log` |
| `AITJE_TOGGLE_BIN` | `/usr/local/bin/aitje-kiosk-toggle` |

## Toggle vanuit de UI

1. Open de AITJE-interface.
2. Ga naar **Instellingen → Systeem**.
3. In de kaart **Kiosk-modus**:
   - bekijk de huidige status,
   - vink optioneel **Direct herstarten na wijziging** aan,
   - klik **Activeer kiosk-modus** of **Schakel kiosk-modus uit**,
   - bevestig in de dialog.

> _(Screenshot placeholder — voeg een UI-screenshot toe wanneer beschikbaar.)_

De UI bevestigt elke wijziging en toont een recovery-hint voor het geval de kiosk-sessie ooit niet opstart.

## Toggle vanuit de CLI

```bash
sudo aitje-kiosk-toggle status
sudo aitje-kiosk-toggle enable --reboot
sudo aitje-kiosk-toggle disable --reboot
```

`--reboot` is optioneel — laat 'm weg om alleen de modus te switchen zonder direct te herstarten (de wijziging wordt dan pas zichtbaar bij de volgende boot).

Logregels per actie staan in `/var/log/aitje-kiosk-toggle.log`.

## API endpoints

Beide endpoints vereisen een admin-bearer token (zelfde mechanisme als `/api/support/tunnel`):

| Methode | Pad | Doel |
|---------|-----|------|
| `GET` | `/api/kiosk/mode` | Huidige modus opvragen (`enabled` of `disabled`). |
| `POST` | `/api/kiosk/mode` | Body `{"mode": "enabled"\|"disabled", "reboot": bool}` — switcht en geeft de nieuwe state + log terug. |

## Recovery procedure

Als de kiosk-sessie ooit vastloopt of de UI onbruikbaar is, kun je altijd terug naar een tty:

1. Druk **Ctrl+Alt+F2** (of een andere tty: F3 t/m F6).
2. Login als `aitje`.
3. Run:
   ```bash
   sudo aitje-kiosk-toggle disable --reboot
   ```
4. Het apparaat herstart en boot in de gewone Ubuntu-desktop met `gdm3`.

Remote access via de bestaande SSH-jumpserver-tunnel blijft beschikbaar — kiosk-modus raakt het netwerk niet.

## Bekende issues / caveats

- **GPU-drivers**: cage onder Wayland werkt niet altijd direct met out-of-tree NVIDIA-drivers. Als de kiosk-sessie zwart blijft, controleer `journalctl -u aitje-kiosk.service` en overweeg de open-source nouveau-driver of de officiële NVIDIA Wayland-build.
- **Qt + Wayland**: PySide6 vereist `qt6-wayland`; `install.sh` regelt dit, maar als je de installer overslaat moet je dit pakket handmatig installeren.
- **GDM3-wisseling**: bij toggle wordt `gdm3` `disable --now` gezet en `aitje-kiosk.service` `enable --now`. Als je een display manager anders dan GDM3 gebruikt (LightDM, SDDM), pas `DM_UNIT` in `/usr/local/bin/aitje-kiosk-toggle` of in de install-config aan.
- **Eerste boot na install**: de installer raakt de huidige sessie niet — kiosk-modus wordt pas actief vanaf de eerstvolgende toggle naar `enabled` (en eventuele reboot).
