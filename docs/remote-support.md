# Remote Support

AITJE remote support gebruikt een on-demand reverse SSH-tunnel naar een Hetzner jump server. De tunnel staat standaard uit en wordt alleen via de UI geopend voor 30, 60 of 120 minuten.

Voor de praktische supportprocedure op de Hetzner VPS, zie ook [`shs-tunnel-handleiding.md`](shs-tunnel-handleiding.md).

## Device-side dependencies

Installeer op het kastje:

```bash
sudo apt install autossh openssh-client
```

`./lociscientia.sh` probeert deze pakketten op Debian automatisch te installeren wanneer `sudo` beschikbaar is.

## `.env` configuratie

Zet in de projectroot (`/home/aitje/loci-scientia/.env`) minimaal:

```env
JUMP_SERVER_IP=your.jump.server
TUNNEL_PORT=10001
TUNNEL_USER=support-tunnel
TUNNEL_KEY_PATH=/home/aitje/.ssh/tunnel_key
```

Elke AITJE-box krijgt een eigen `TUNNEL_PORT`.

## SSH key provisioning

Genereer op een nieuw kastje de tunnel-key:

```bash
cd /home/aitje/loci-scientia
./scripts/setup-tunnel-key.sh
```

Het script:

- maakt een `ed25519` keypair zonder passphrase
- schrijft standaard naar `/home/aitje/.ssh/tunnel_key`
- vraagt bevestiging voordat een bestaande key wordt overschreven
- print de public key direct naar stdout

## Jump server setup

Maak op de VPS een aparte gebruiker aan, bijvoorbeeld:

```bash
sudo adduser --disabled-password --gecos "" support-tunnel
sudo install -d -m 700 -o support-tunnel -g support-tunnel /home/support-tunnel/.ssh
sudo touch /home/support-tunnel/.ssh/authorized_keys
sudo chown support-tunnel:support-tunnel /home/support-tunnel/.ssh/authorized_keys
sudo chmod 600 /home/support-tunnel/.ssh/authorized_keys
```

Voeg in `/etc/ssh/sshd_config` een beperkte match toe:

```text
Match User support-tunnel
    PasswordAuthentication no
    PubkeyAuthentication yes
    AllowTcpForwarding remote
    PermitTTY no
    X11Forwarding no
```

Herlaad daarna SSH:

```bash
sudo systemctl reload ssh
```

## `authorized_keys` restricties

Voeg de public key van het kastje toe aan `/home/support-tunnel/.ssh/authorized_keys`. Gebruik per device een `permitlisten` restrictie voor de eigen poort:

```text
restrict,port-forwarding,permitlisten="10001" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... aitje-support-tunnel
```

Als je meerdere kastjes hebt, krijgt elk kastje zijn eigen regel met zijn eigen `permitlisten` poort.

## Systemd unit en sudoers installeren

Installeer de meegeleverde bestanden op het kastje:

```bash
sudo cp systemd/aitje-tunnel.service /etc/systemd/system/aitje-tunnel.service
sudo cp sudoers/aitje-tunnel /etc/sudoers.d/aitje-tunnel
sudo chmod 440 /etc/sudoers.d/aitje-tunnel
sudo systemctl daemon-reload
```

De unit is bewust niet enabled. Laat hem uit bij boot; de FastAPI backend start en stopt hem alleen on-demand.

## Gebruik

- De UI opent de tunnel via `POST /api/support/tunnel` met `action=open`.
- De backend start `aitje-tunnel` en plant via `systemd-run` automatisch een stop-moment.
- Handmatig sluiten of automatisch verlopen stopt dezelfde service weer.
- De huidige status is zichtbaar via `GET /api/support/tunnel`.
