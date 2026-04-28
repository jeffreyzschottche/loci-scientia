# WiFi-fix: wifi verbindt niet automatisch bij boot (Ubuntu)

## Symptoom

Na het opstarten van Ubuntu verbindt de wifi niet vanzelf. Pas nadat je
handmatig wifi uit en weer aan zet (of opnieuw inlogt op je netwerk) komt
de verbinding tot stand.

## Oorzaak

**Niet** een driver- of timing-probleem van de wifi-adapter. De echte oorzaak
zie je terug in de NetworkManager-logs:

```
poging 1  →  state change: config -> failed (reason 'no-secrets')
poging 2  →  Activation: ... successful. Connected to 'Weltevree'.
```

Het wifi-wachtwoord stond opgeslagen in de **gnome-keyring** (per-user).
NetworkManager probeert al te verbinden vóórdat de keyring unlocked is
(dat gebeurt pas bij login), krijgt `no-secrets` terug en geeft op. Wanneer
je daarna handmatig de wifi toggelt, is de keyring inmiddels open en lukt
het wel.

Bijkomend: er stonden twee verbindingsprofielen voor hetzelfde SSID
(`Weltevree` en `Weltevree 1`), wat extra ruis kan geven bij autoconnect.

## Diagnose

```bash
# adapter & connecties
lspci | grep -i net
nmcli connection show
nmcli device status

# logs van laatste boot
journalctl -b0 -u NetworkManager --no-pager \
  | grep -iE "wlan0|wifi|dhcp|associat|fail|secrets"
```

Zie je `reason 'no-secrets'` op de eerste poging en daarna een geslaagde
tweede poging? Dan is dit het geval.

## Fix

Het wifi-wachtwoord op **systeem-niveau** opslaan in plaats van in de
user-keyring. Daarmee staat het op disk in
`/etc/NetworkManager/system-connections/` (mode 600, alleen root) en is
het beschikbaar vóór een user inlogt.

```bash
# 1. PSK uit huidige (per-user) opslag halen
PSK=$(sudo nmcli -s -g 802-11-wireless-security.psk connection show "Weltevree 1")

# 2. Connectie omzetten naar system-wide opslag
sudo nmcli connection modify "Weltevree 1" \
  802-11-wireless-security.psk-flags 0 \
  802-11-wireless-security.psk "$PSK" \
  connection.permissions "" \
  connection.autoconnect yes \
  connection.autoconnect-priority 10

# 3. Duplicate profiel opruimen
sudo nmcli connection delete "Weltevree"

unset PSK
```

Vervang `"Weltevree 1"` door de naam van jouw verbinding (zie `nmcli connection show`).

### Wat de waarden betekenen

| Setting                                  | Waarde | Effect                                                    |
| ---------------------------------------- | ------ | --------------------------------------------------------- |
| `802-11-wireless-security.psk-flags`     | `0`    | `none` — wachtwoord op disk, geen agent/keyring nodig     |
| `connection.permissions`                 | `""`   | system-wide, niet gebonden aan één user                   |
| `connection.autoconnect`                 | `yes`  | automatisch verbinden bij beschikbaarheid                 |
| `connection.autoconnect-priority`        | `10`   | hogere prioriteit dan default (0)                         |

`psk-flags` waarden voor de volledigheid:

- `0` = none (system-stored, plaintext op disk in `/etc/NetworkManager/system-connections/`)
- `1` = agent-owned (per-user, gnome-keyring) ← was dit
- `2` = not-saved (elke keer vragen)
- `4` = not-required

## Verificatie

```bash
nmcli -f connection.permissions,802-11-wireless-security.psk-flags,connection.autoconnect \
  connection show "Weltevree 1"
```

Verwacht:
```
connection.permissions:               --
802-11-wireless-security.psk-flags:   0 (none)
connection.autoconnect:               yes
```

En het bestand bestaat:
```bash
sudo ls -la /etc/NetworkManager/system-connections/
```

Reboot en check of de wifi vanzelf verbindt zonder handmatige toggle.

## Trade-off

Het wachtwoord staat nu in plaintext in
`/etc/NetworkManager/system-connections/Weltevree 1.nmconnection` (mode
`600`, alleen leesbaar voor root). Dat is hetzelfde model dat de meeste
servers en kiosks gebruiken. Wie root op de machine heeft, kan het
wachtwoord lezen — maar wie root heeft, kan sowieso alles. Voor een
laptop die je dagelijks gebruikt is dit een acceptabele trade-off voor
een werkende boot-flow.

Wil je dit terugdraaien:
```bash
sudo nmcli connection modify "Weltevree 1" 802-11-wireless-security.psk-flags 1
```
