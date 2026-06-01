# SHS/SSH Support Tunnel Handleiding

Deze handleiding beschrijft hoe je via de Hetzner VPS een tijdelijke SSH-verbinding naar een AITJE hardware device opent.

De tunnel werkt zo:

- Het AITJE device maakt zelf een reverse SSH-tunnel naar de Hetzner VPS.
- De VPS luistert daarna lokaal op de gekozen `TUNNEL_PORT` uit de `.env`, bijvoorbeeld `10001` of `10002`.
- Vanaf de VPS kun je dan via `ssh -p <poort> aitje@localhost` inloggen op het hardware device.

## Benodigd

- SSH toegang tot de Hetzner VPS:

```bash
ssh root@78.47.164.114
```

- Het root-wachtwoord van de VPS.
- De public key van het AITJE device.
- De gekozen tunnelpoort uit `/home/aitje/loci-scientia/.env` op het device, bijvoorbeeld:

```env
TUNNEL_PORT=10002
```

- Het wachtwoord van de gebruiker `aitje` op het hardware device. Dat heb je nodig wanneer je via de tunnel op het device inlogt.

## 1. Public key van het AITJE device ophalen

Log lokaal in op het AITJE device en toon de public key:

```bash
cat /home/aitje/.ssh/tunnel_key.pub
```

Als de key nog niet bestaat, maak je hem aan vanuit de projectmap:

```bash
cd /home/aitje/loci-scientia
./scripts/setup-tunnel-key.sh
```

Kopieer de volledige regel die begint met `ssh-ed25519`.

## 2. Inloggen op de Hetzner VPS

Log vanaf je eigen machine in op de VPS:

```bash
ssh root@78.47.164.114
```

Voer daarna het root-wachtwoord van de VPS in.

## 3. Public key opslaan op de VPS

Open op de VPS het `authorized_keys` bestand van de tunnelgebruiker:

```bash
sudo nano /home/support-tunnel/.ssh/authorized_keys
```

Voeg de public key van het AITJE device toe. Gebruik bij voorkeur een restrictie per devicepoort:

```text
restrict,port-forwarding,permitlisten="10002" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... aitje-support-tunnel
```

Vervang `10002` door de `TUNNEL_PORT` van dit device. Vervang de rest van de regel door de echte public key van het device.

Opslaan in nano:

- `Ctrl+O`
- `Enter`
- `Ctrl+X`

Controleer daarna de rechten:

```bash
sudo chown support-tunnel:support-tunnel /home/support-tunnel/.ssh/authorized_keys
sudo chmod 600 /home/support-tunnel/.ssh/authorized_keys
```

## 4. Tunnel starten op het AITJE device

Start remote support via de AITJE admin UI. De backend start dan de `aitje-tunnel` service en opent de reverse SSH-tunnel naar de VPS.

Handmatig kan dit op het device met:

```bash
sudo systemctl start aitje-tunnel
```

Controleer eventueel de status:

```bash
sudo systemctl status aitje-tunnel
```

## 5. Vanaf de VPS inloggen op het device

Zodra de tunnel actief is, blijf je ingelogd op de VPS en verbind je naar de lokale tunnelpoort:

```bash
ssh -p 10002 aitje@localhost
```

Gebruik hier dezelfde poort als `TUNNEL_PORT` in de `.env` van het device.

Voorbeelden:

```bash
ssh -p 10001 aitje@localhost
ssh -p 10002 aitje@localhost
```

Voer daarna het wachtwoord van de gebruiker `aitje` op het hardware device in.

Je zit nu via SSH op het AITJE device. Vanaf hier kun je supportwerk doen, zoals services controleren, logs bekijken of SUNO-gerelateerde commands draaien.

## Handige commands op het device

Projectmap openen:

```bash
cd /home/aitje/loci-scientia
```

Backend logs volgen:

```bash
tail -f backend.log
```

Tunnelstatus bekijken:

```bash
sudo systemctl status aitje-tunnel
```

Tunnel stoppen:

```bash
sudo systemctl stop aitje-tunnel
```

## Let op

- Geef elk AITJE device een eigen `TUNNEL_PORT`, bijvoorbeeld `10001`, `10002`, enzovoort.
- Zet in `/home/support-tunnel/.ssh/authorized_keys` alleen public keys van devices die support mogen openen.
- Deel het wachtwoord van het hardware device alleen met iemand die daadwerkelijk support moet uitvoeren.
- Sluit de tunnel na supportwerk als hij niet automatisch verloopt.
