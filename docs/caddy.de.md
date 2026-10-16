# Caddy mit postquantenfestem TLS

[English](caddy.md) · [Русский](caddy.ru.md) · [Deutsch](caddy.de.md)

Caddy ab 2.10 (mit Go 1.24+ gebaut) bietet den hybriden TLS-1.3-Schlüsselaustausch `X25519MLKEM768` standardmäßig neben klassischem X25519 an. Das eigene `caddy`-Paket von Ubuntu 24.04 ist Version 2.6.2 und bietet dies nicht; das Kit verwendet daher das offizielle Caddy-Repository auf Cloudsmith.

Keine `curves`-Direktive hinzufügen: Die Voreinstellung bevorzugt bereits den hybriden Austausch; eine explizite Liste kann ältere Clients versehentlich ausschließen.

<a id="new-server"></a>
## Neuer Server

Aus dem Stammverzeichnis dieses geprüften Repositorys ausführen. Der vollständige Fingerabdruck des Primärschlüssels ist in `scripts/verify-caddy-key.py` festgelegt:
`65760C51EDEA2017CEA2CA15155B6D79CA56EA34`.
Er wurde mit den [offiziellen Repository-Metadaten von Caddy](https://cloudsmith.io/~caddy/repos/stable/packages/) abgeglichen. Ein anderer, abgelaufener, widerrufener, fehlerhafter oder zusätzlicher Primärschlüssel stoppt die Installation vor Einrichtung des Vertrauens. Bei Schlüsselwechsel den neuen Schlüssel unabhängig prüfen und das Kit kontrolliert aktualisieren; die Prüfung nie umgehen und den erwarteten Fingerabdruck nicht aus demselben Download ableiten.

```sh
(
  set -eu
  apt-get install -y python3 debian-keyring debian-archive-keyring apt-transport-https curl gnupg
  KEY_WORK=$(mktemp -d)
  trap 'rm -rf "$KEY_WORK"' EXIT HUP INT TERM
  curl --proto '=https' --proto-redir '=https' --tlsv1.2 -fLsS --max-time 60 \
    'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' -o "$KEY_WORK/caddy.key"
  python3 scripts/verify-caddy-key.py "$KEY_WORK/caddy.key"
  gpg --batch --yes --dearmor --output "$KEY_WORK/caddy.gpg" "$KEY_WORK/caddy.key"
  install -m 644 "$KEY_WORK/caddy.gpg" /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  printf '%s\n' 'deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main' \
    > /etc/apt/sources.list.d/caddy-stable.list
  chmod 644 /etc/apt/sources.list.d/caddy-stable.list
  apt-get update
  apt-cache policy caddy
)
```

`Candidate` muss von `dl.cloudsmith.io` stammen und mindestens 2.10 sein. Genau diese Version installieren und festhalten, damit Updates bewusst erfolgen:

```sh
V=2.11.7                      # replace with the exact Candidate version if it is newer
apt-get install -y "caddy=$V"
apt-mark hold caddy
caddy version
sh bin/require-pq-caddy       # from this kit
```

Danach die Site gemäß `config/Caddyfile.example` einrichten (README, Schritt 4).

<a id="upgrading"></a>
## Aktualisierung

Für einen Server mit älterem Caddy vor dem Relay. Etwa 15–20 Minuten einplanen. Offene WebSockets werden beim Caddy-Neustart kurz getrennt; Clients verbinden sich erneut, gespeicherte Ereignisse bleiben erhalten (strfry läuft weiter). Mehrere Relays einzeln aktualisieren.

Shell-Variablen gelten nur in der aktuellen SSH-Sitzung; nach erneutem Verbinden wieder setzen. Jeden Block erst nach Erfolg des vorherigen ausführen. Bei Fehlern stoppen, nicht mit einem Neustart fortfahren.

### 1. Sicherung auf dem Server

```sh
BK=/root/caddy-before-upgrade-$(date -u +%Y%m%dT%H%M%SZ); mkdir -m 700 "$BK"
caddy version | tee "$BK/version.txt"; dpkg -l caddy | tail -1 | tee -a "$BK/version.txt"
cp -a "$(command -v caddy)" "$BK/caddy"
cp -a /etc/caddy "$BK/etc-caddy"
OLD_VERSION=$(dpkg-query -W -f='${Version}' caddy)
printf '%s\n' "$OLD_VERSION" > "$BK/package-version"
mkdir -m 700 "$BK/package"
(
    set -eu
    cd "$BK/package"
    apt-get download "caddy=$OLD_VERSION"
    set -- ./caddy_*.deb
    [ "$#" -eq 1 ] && [ -f "$1" ]
    [ "$(dpkg-deb -f "$1" Package)" = caddy ]
    [ "$(dpkg-deb -f "$1" Version)" = "$OLD_VERSION" ]
    sha256sum "$1" > SHA256SUMS
)
ls -la /var/lib/caddy/.local/share/caddy/certificates/*/ | tee "$BK/certs.txt"
/usr/local/libexec/strfry-health
```

Nur aktualisieren, wenn die exakt installierte `.deb` gespeichert und geprüft wurde. Ist sie nicht mehr herunterladbar, genau dieses Paket aus vertrauenswürdigem Cache/Archiv beschaffen und dieselben Paket-/Versions-/Prüfsummenprüfungen durchführen; nicht den aktuellen Kandidaten einsetzen. Die gesicherte ausführbare Datei allein ist eine Notlösung, kein vollständiges Paket-Rollback.

Bedient dasselbe Caddy auch eine Website, einen Seiten-Fingerabdruck für den späteren Vergleich speichern:
`curl -fsS https://your.domain/ | sha256sum | tee "$BK/site.sha256"`.

### 2. Repository hinzufügen

Wie unter [Neuer Server](#new-server) bis `apt-cache policy caddy`; dann `V` auf die genaue `Candidate`-Version (2.10+) setzen.

### 3. Aktuelles Caddyfile vor Installation mit der neuen Binärdatei prüfen

Die Paketinstallation startet Caddy neu. Deshalb die Konfiguration vorher mit einer entpackten Kopie prüfen; Zertifikate und aktive Daten bleiben unberührt:

```sh
(
    set -eu
    T=$(mktemp -d)
    trap 'rm -rf "$T"' 0
    cd "$T"
    apt-get download "caddy=$V"
    dpkg-deb -x caddy_*.deb x
    ./x/usr/bin/caddy version
    XDG_DATA_HOME="$T/data" XDG_CONFIG_HOME="$T/config" \
      ./x/usr/bin/caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
)
```

Erwartet wird `Valid configuration`. Warnungen wie „input is not formatted“ betreffen die Formatierung; `caddy fmt --overwrite` würde die Datei umschreiben und soll hier nicht ausgeführt werden. Bei jedem Fehler stoppen.

### 4. Installieren

`--force-confold` erhält `/etc/caddy/Caddyfile` statt der Paketvorgabe.

```sh
(
    set -eu
    # Reapply this kit's hold policy on success AND if apt fails.
    trap 'apt-mark hold caddy' 0
    apt-mark unhold caddy
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
      -o Dpkg::Options::=--force-confold -o Dpkg::Options::=--force-confdef "caddy=$V"
    cmp /etc/caddy/Caddyfile "$BK/etc-caddy/Caddyfile"
    echo "Caddyfile unchanged"
    systemctl restart caddy
    sleep 3
    systemctl is-active caddy
    journalctl -u caddy --since '2 min ago' --no-pager | grep -E '"level":"(error|warn)"|obtaining' | tail -20
)
```

Bei unerwarteter Zertifikatsanforderung für eine Domain mit gültigem Zertifikat zunächst Speicherpfade und Rechte prüfen; die Logzeile allein beweist keinen Speicherverlust.

### 5. Prüfen

Auf dem Server: `/usr/local/libexec/strfry-health`, NIP-11-`curl`, `/metrics` → 404 sowie gegebenenfalls Website-Fingerabdruck. Von einem Rechner mit OpenSSL 3.5+:

```sh
sh scripts/check-pq-tls.sh your.domain
```

### Rollback auf das exakt gesicherte Paket

`BK` auf das Sicherungsverzeichnis aus Schritt 1 setzen. Cloudsmith-Repository eingerichtet lassen. Dieser Ablauf stellt die gesicherte Version wieder her, nicht den Distributionskandidaten, und setzt den Hold auch bei Installationsfehlern erneut. Da die Paketverwaltung Caddy neu starten kann, zuerst die gesicherte Konfiguration wiederherstellen und prüfen. Vorhandener Zertifikatsspeicher wird nicht ersetzt.

```sh
(
    set -eu
    cd "$BK/package"
    sha256sum -c SHA256SUMS
    set -- ./caddy_*.deb
    [ "$#" -eq 1 ] && [ -f "$1" ]
    [ "$(dpkg-deb -f "$1" Package)" = caddy ]
    [ "$(dpkg-deb -f "$1" Version)" = "$(cat "$BK/package-version")" ]
    CHECK_DIR=$(mktemp -d)
    trap 'rm -rf "$CHECK_DIR"' 0
    cp -a "$BK/etc-caddy/." /etc/caddy/
    XDG_DATA_HOME="$CHECK_DIR/data" XDG_CONFIG_HOME="$CHECK_DIR/config" \
      "$BK/caddy" validate --config /etc/caddy/Caddyfile --adapter caddyfile
    trap 'apt-mark hold caddy; rm -rf "$CHECK_DIR"' 0
    apt-mark unhold caddy
    DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades \
      -o Dpkg::Options::=--force-confold -o Dpkg::Options::=--force-confdef "$PWD/${1#./}"
    [ "$(dpkg-query -W -f='${Version}' caddy)" = "$(cat "$BK/package-version")" ]
    caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
    systemctl restart caddy
    systemctl is-active caddy
)
```

Relay-/Website- und externe TLS-Prüfungen wiederholen. Unterstützt die alte Version kein hybrides TLS, kehrt diese Einschränkung zurück; den Hybrid-Test als fehlgeschlagen melden.

### Notfall: nur die Binärdatei wiederherstellen

Ist Paketwiederherstellung unmöglich, vorübergehend die gesicherte Datei einsetzen:
`systemctl stop caddy && cp -a "$BK/caddy" /usr/bin/caddy && systemctl start caddy`.
Dies stellt den Paketverwaltungszustand nicht wieder her; vor dem nächsten Update mit dem gesicherten Paket abgleichen. Nicht stillschweigend Ubuntus älteres Caddy einsetzen, da die postquantenfeste TLS-Unterstützung entfallen kann. strfry, Datenbank, Timer und Firewall gehören nicht zu diesem Verfahren.
