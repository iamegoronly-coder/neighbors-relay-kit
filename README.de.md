# Neighbors Relay-Kit

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md)

Installationspaket für das öffentliche [Nostr](https://github.com/nostr-protocol/nips)-Relay von **Neighbors**, dem privaten Chat in Home Bills. Es basiert auf unseren eingebauten Relays: [strfry](https://github.com/hoytech/strfry) hinter Caddy, kurze Aufbewahrung, feste Ressourcengrenzen und postquantenfestes TLS. Unsere Website ist nicht enthalten. Kit-Vorgaben können sich unabhängig von laufenden Servern ändern: Dieser Checkout senkt die Ereignisgrenze auf 60 KiB und entfernt den redundanten vollständigen Datenbankscan. Bestehende Testarchive und laufende Server bleiben unverändert.

> **Status.** Das Kit stellt ein Relay bereit und ändert keine Client-Einstellungen automatisch.
> Ein eigenes Relay setzt eine App-Version mit entsprechender Routing-Unterstützung voraus.
> Repository und Test-Releases bleiben privat; Veröffentlichungsstatus siehe unten.

[Relay-/Client-Grenzen und Prüfergebnisse (2026-10-21, EN)](docs/relay-client-audit-2026-10-21.md).

## Was das Relay sieht

Das Relay speichert und übermittelt signierte Nostr-Ereignisse. Die App verschlüsselt Nachrichten vor der Übertragung Ende zu Ende. Das Relay kann ihren Inhalt nicht lesen; `content` wird weder ausgewertet noch protokolliert.

| Sichtbar für das Relay | Nicht sichtbar |
|---|---|
| Verbindungs-IP-Adressen und Zeitpunkte | Nachrichtentext, Fotos, Sprachnachrichten und Namen innerhalb von Nachrichten |
| Äußere Schlüssel und Tags: eine private Hülle (Kind 1059) hat einen einmaligen äußeren Schlüssel und den Relay-Schlüssel des Empfängers im `p`-Tag | Dauerhafter Identitätsschlüssel des Absenders innerhalb der privaten Hülle (keine Anonymitätsgarantie) |
| Ereignisgröße und `created_at` (für private Hüllen um ±15 Minuten zufällig verschoben) | Entschlüsselte Kontaktliste oder lesbarer Chatverlauf |

Das Relay kann Ereignisse mit Verbindung, Quell-IP, Zeitpunkt und Empfänger-Tags verknüpfen und Abonnementfilter beobachten. Korrelation kann Beziehungen und Aktivität erkennen lassen; ein einmaliger äußerer Schlüssel macht den Absender nicht anonym. Diese Vertraulichkeitsaussagen gelten für korrekt verschlüsselte private App-Hüllen. Das öffentliche Relay akzeptiert auch andere Ereignisse einschließlich Klartext und öffentlicher Anwendungsdaten und verschlüsselt diese nicht für ihre Autoren.

`OK` bedeutet „zur Speicherung angenommen“, nicht „zugestellt“. Löschen aus LMDB garantiert keine physische Löschung der Bytes; Hosting-Anbieter können Datenträger-Snapshots aufbewahren. Keine garantierte Löschung versprechen.

### IP-Adressen in dieser Konfiguration

Caddy nimmt Client-Verbindungen an und sieht deren IP-Adressen. strfry hört auf Loopback und
behandelt mit `realIpHeader = ""` nur Caddy (`127.0.0.1`) als Gegenstelle; weitergeleitete Client-IP-
Header werden ignoriert. Das Beispiel-Caddyfile aktiviert kein HTTP-Zugriffslog, strfry läuft auf
WARNING ohne Ereignis-Dumps. Das reduziert die reguläre Protokollierung, garantiert aber **nicht**,
dass IPs nirgends gespeichert werden: Caddy-Fehler-/Laufzeitlogs, Host-/Providerlogs und spätere
Betreiberänderungen sind davon getrennt.

### Authentifizierung

NIP-42 AUTH ist absichtlich deaktiviert: Neighbors beantwortet AUTH-Challenges noch nicht, auch
nicht beim Lesen delegierter Gateway-Postfächer. Jeder kann daher Chiffretext und sichtbare Tags
abfragen sowie korrekt signierte Ereignisse an fremde `#p` senden; die App prüft Nachrichten
weiterhin Ende zu Ende vor der Annahme. AUTH mit `restrictedReadKinds = "4, 1059"` und
`restrictReadToInvolvedPubkey = true` würde das Lesen dieser Kinds auf authentifizierte beteiligte
Schlüssel begrenzen (Empfänger im `p`-Tag oder äußerer Ereignisautor). Das erschwert massenhaftes
Sammeln, verhindert aber weder unerwünschtes Schreiben noch die Sichtbarkeit beim Betreiber.
Nicht einfach für aktuelle Clients einschalten: Challenge-Signaturen, Relay-URL-Prüfung und
Gateway-Delegation müssen zuerst gemeinsam unterstützt werden.

### Ereignistypen

| Kind | Verwendung in Neighbors |
|---|---|
| 1059 | Private Hüllen (Gift-Wrap-Struktur, von bitchat abgeleitete Verschlüsselung): Direkt-/Gruppennachrichten, Medienpakete, Bestätigungen. Die App abonniert ihr eigenes `#p` |
| 30078 | NIP-78-Anwendungsdaten, etwa der Empfangsstatus des Autors |
| 1401, 20000, 20001 | Aktuell nicht von Neighbors veröffentlicht; für bitchat-Kompatibilität akzeptiert (Kurierablagen, kurzlebige und Standortkanäle) und im Smoke-Test abgedeckt |

## Richtlinien und Grenzen

- **Verlauf:** normale Ereignisse werden angenommen, wenn `created_at` höchstens 48 Stunden alt und höchstens 20 Minuten in der Zukunft liegt. Bereitstellung und Aufbewahrung bis `created_at + 48 h`, Bereinigung alle 2 Minuten.
- **Kurzlebige Kinds 20000–29999:** Annahme innerhalb ±60 Sekunden zur Relay-Uhr; 90 Sekunden ab `created_at`, interner Ablaufindex-Cron etwa alle 9 Sekunden (normalerweise 90–99 Sekunden bei aktueller Datierung, mit erlaubtem Zeitvorlauf von 60 Sekunden bis etwa 160 Sekunden ab Empfang; unter Last oder bei Stillstand länger), kein Offline-Postfach.
- **NIP-40 `expiration`:** bereits abgelaufene Ereignisse werden abgelehnt, beim Lesen herausgefiltert (gepatchtes strfry) und durch den internen Ablaufindex-Cron entfernt. Der externe 2-Minuten-Job führt nur `delete --age 172800` aus; sein Erfolgsstempel überwacht die Altersbereinigung, nicht den internen Cron.
- **Kein NIP-42 AUTH.** Öffentliches Relay; Missbrauch wird durch Ressourcenlimits begrenzt.

| Grenze | Mechanismus |
|---|---|
| 1 vCPU, 512 MiB RAM, 64 Tasks, 256 Dateideskriptoren | systemd `CPUQuota`, `MemoryMax`, `TasksMax`, `LimitNOFILE` |
| 100 WebSocket-Verbindungen | `relay.maxConnections` (exakt, gepatcht) und Caddy `unhealthy_request_count` (frühe 503) |
| Datenbank < 1,5 GiB und > 2 GiB frei auf ihrem Dateisystem | `strfry-disk-guard` vor Start und minütlich; stoppt nur das Relay |
| Ereignis ≤ 60 KiB (61.440 Bytes), WebSocket-Nachricht ≤ 128 KiB | `events.maxEventSize`, `relay.maxWebsocketPayloadSize` |
| 20 Abonnements pro Verbindung, 500 Ereignisse pro Filter, 1 MiB Ausgabepuffer | `strfry.conf` |
| Relay-Log ≤ 50 MiB / 7 Tage, flüchtig | Namensraum `journald@strfry.conf`; keine Ereignisinhalte, Schlüssel oder Tags |

Das Verbindungslimit ist kein Limit pro IP. Der Datenträger wird einmal pro Minute geprüft; Lastspitzen innerhalb dieser Minute, Netzwerksättigung und Host-Ausfälle sind dadurch nicht abgedeckt.

## Postquantenfestes TLS

Caddy 2.10+ bietet standardmäßig `X25519MLKEM768` (X25519 + ML-KEM-768). Wird dieser hybride Austausch tatsächlich ausgehandelt, soll er bekannten klassischen und Quantenangriffen einschließlich „heute sammeln, später entschlüsseln“ widerstehen. Apple unterstützt ihn in `URLSession` ab iOS/macOS 26; OS-/Serverversion allein beweist jedoch nicht die ausgehandelte Gruppe einer Verbindung. Ältere Clients können weiterhin klassisches X25519 verwenden.

Dies schützt nur den Transport bis zum TLS-terminierenden Server. Die bestehende Ende-zu-Ende-Verschlüsselung der App wird dadurch nicht postquantenfest; gespeicherte Hüllen erhalten dadurch keinen zusätzlichen Schutz vor dem Relay selbst.

`scripts/install.sh` lehnt älteres Caddy ab (`bin/require-pq-caddy`). `scripts/check-pq-tls.sh <domain>` prüft beide Verfahren von außen samt Zertifikatsvertrauen, Hostnamen und OpenSSL-Exitstatus (Python 3 und OpenSSL 3.5+ erforderlich). Pro OpenSSL-Prozess gelten 15 Sekunden Timeout, einstellbar mit `--timeout`. Die Versionsprüfung ist eine Voraussetzung; erst der externe Handshake prüft das tatsächliche TLS.

## Voraussetzungen

- Ubuntu 24.04 x86_64 (getestet); 1 vCPU / 1 GiB RAM genügt für den Betrieb. Kompilieren benötigt etwa 2,5 GiB Speicher (auf kleinem VPS Swap ergänzen) und Zeit.
- Mindestens 4 GiB frei auf dem Dateisystem von `/var/lib/strfry` (1,5 GiB Datenbank + 2 GiB Reserve).
- Domain mit A/AAAA zum Server (CDN-Proxy nur bei gesicherter WebSocket-Weiterleitung); TCP 80/443 offen, 7777 **nicht** freigeben.
- Genaue Uhr via NTP, da Ereignisse anhand `created_at` bewertet werden.

## Installationswege

Aus Quellen bauen oder veröffentlichte Binärdatei mit demselben Dienst-/Konfigurationsinstaller installieren. Für unabhängige Prüfung den festgelegten kanonischen Docker-Build verwenden und bytegenau mit dem Release vergleichen. Der native Ubuntu-Build bleibt verfügbar; andere Compiler-/Bibliotheksversionen können andere Hashes erzeugen.

Siehe [beide Wege und Vergleich](docs/deployment.de.md). Es gibt noch kein öffentliches GitHub Release und keine Signaturidentität. Der lokale Assistent `setup.sh` richtet auf einem neuen VPS Abhängigkeiten, Caddy, Domain, Relay und Timer ein. Der Installer erhält exakt die geprüften Binärbytes. Zwei saubere lokale kanonische Builds waren bytegleich; siehe [Prüfbericht](docs/reproducibility-check-2026-10-15.de.md). Die Prüfung auf unabhängigem Host steht aus.

## Installation

**Status:** Repository und Releases bleiben privat. Diese anonymen HTTPS-Befehle sind für eine spätere Veröffentlichung vorbereitet; ohne Repository-Zugriff schlagen sie derzeit fehl (meist HTTP 404). Sie ändern die Sichtbarkeit nicht. `v0.1.0-test.2` ist eine Testversion, keine Empfehlung für den Produktivbetrieb.

Für einen **frischen Ubuntu-24.04-x86_64-VPS** mit systemd und synchronisierter NTP-Uhr. Zuerst die Domain auf den VPS richten und TCP 80/443 freigeben. Die Binärinstallation braucht etwa 1 GiB RAM und mindestens 4 GiB freien Speicher auf `/var/lib`.

Benötigt werden `curl`, `ca-certificates`, `tar`, `sha256sum`, Python 3 und sudo/root; für Quellen auch Git. Fehlende Download-/Clone-Werkzeuge einmalig installieren:

```sh
sudo apt-get update && sudo apt-get -o DPkg::Lock::Timeout=600 install -y ca-certificates curl git
```

Bei Anmeldung als root kann `sudo` entfallen.

1. Das Archiv der festgelegten Version in ein neues temporäres Verzeichnis herunterladen:

```sh
relay_work=$(mktemp -d -t neighbors-relay.XXXXXXXX) &&
curl --fail --show-error --location --proto '=https' --proto-redir '=https' \
  --output "$relay_work/neighbors-relay-v0.1.0-test.2.tar.gz" \
  https://github.com/iamegoronly-coder/neighbors-relay-kit/releases/download/v0.1.0-test.2/neighbors-relay-v0.1.0-test.2.tar.gz
```

2. In derselben SSH-Sitzung die festgelegte Prüfsumme prüfen, dann entpacken und den Assistenten starten:

```sh
(cd "${relay_work:?Run the download command first}" &&
  printf '%s  %s\n' '1f4b9832d9bd149be5e453c7ce5fe7886bac8267938a8dfabe0b8e1cfda2cf7e' 'neighbors-relay-v0.1.0-test.2.tar.gz' | sha256sum --check - &&
  tar -xzf neighbors-relay-v0.1.0-test.2.tar.gz &&
  cd neighbors-relay && sudo sh setup.sh)
```

Der Assistent fragt nach Sprache, Domain und Installationsart und zeigt einen Plan zur Bestätigung. Für die mitgelieferte Binärdatei **1** wählen. Nach Veröffentlichung sind weder GitHub CLI noch Token nötig. Das Archiv bleibt in `$relay_work`; HTTP- oder Prüfsummenfehler vor dem Fortfahren beheben. Geprüfte, entpackte Skripte können vor `sudo sh setup.sh` gelesen werden. Die Prüfsumme steht fest in dieser Anleitung und stammt nicht nur aus einem benachbarten Download; sie ist keine Release-Signatur.

### Klonen und aus Quellen bauen

Nach Veröffentlichung denselben konkreten Tag per HTTPS klonen und aus Quellen bauen. Das private Repository erfordert derzeit weiterhin Zugriff. Ein neues Verzeichnis verwenden; vorhandene Relay-Installationen werden nicht ersetzt.

```sh
git clone --branch v0.1.0-test.2 --single-branch \
  https://github.com/iamegoronly-coder/neighbors-relay-kit.git neighbors-relay-source
```

```sh
(cd neighbors-relay-source && sudo sh setup.sh --mode source)
```

Der Quellmodus lädt festgelegte Quellen und kompiliert das Relay, statt eine fertige Relay-Binärdatei zu verwenden. Er benötigt mindestens 2,5 GiB RAM + Swap und 6 GiB freien Speicher auf `/var/lib` und `/opt` (insgesamt 6 GiB bei gemeinsamem Dateisystem). Native Ubuntu-Builds können andere Hashes haben; für bytegenauen Vergleich den kanonischen Docker-Build nutzen.

[Schnellstart](docs/quickstart.de.md) · [Build / Vergleich](docs/deployment.de.md)

<a id="manual-installation"></a>
### Manuelle Installation

Für einzelne Schritte als root auf dem Server aus einer privaten Repository-Kopie arbeiten, beispielsweise `/root/neighbors-relay`.

1. **Caddy 2.10+** aus dem offiziellen Repository: [Anleitung](docs/caddy.de.md#new-server).
2. **strfry bauen**, festgelegter Commit mit [Patch](docs/patch.de.md):
   ```sh
   sh scripts/build-strfry.sh
   ```
3. **Relay benennen** in `config/strfry.conf` (`info.name`, `description`, `contact`), dann Dienst, Hilfsprogramme und Timer installieren:
   ```sh
   sh scripts/install.sh
   ```
4. **Über Caddy bereitstellen.** `config/Caddyfile.example` nach `/etc/caddy/Caddyfile` kopieren oder Site-Block in vorhandene Datei integrieren; `relay.example.org` ersetzen:
   ```sh
   caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
   systemctl reload caddy
   ```
5. **Prüfen.**
   ```sh
   /usr/local/libexec/strfry-health                      # healthy: true
   curl -fsS -H 'Accept: application/nostr+json' https://relay.example.org/relay
   curl -s -o /dev/null -w '%{http_code}\n' https://relay.example.org/metrics   # 404
   ```
   Von einem Rechner mit OpenSSL 3.5+ (Mac: Homebrew OpenSSL):
   ```sh
   sh scripts/check-pq-tls.sh relay.example.org          # two PASS lines
   ```
   Optional externer Abnahmetest (Python 3.12, `websockets==15.0.1`, `coincurve==21.0.0`). Er veröffentlicht synthetische Ereignisse. Für jeden Lauf neuen Manifestnamen wählen; vorhandene Dateien werden nicht überschrieben. Versuchte IDs werden **vor** dem Senden auf Datenträger geschrieben, damit Bereinigung auch nach Testfehler oder verlorenem ACK möglich bleibt (abgelehnte IDs können gefahrlos gelöscht werden).
   ```sh
   RELAY_HOST=relay.example.org python3 tests/smoke_test.py initial --manifest /tmp/relay-smoke-run.jsonl
   ```
   Manifest in ein privates Verzeichnis des Zielservers kopieren:
   ```sh
   /usr/local/libexec/strfry-cleanup-smoke-events --manifest /root/relay-smoke-run.jsonl --relay wss://relay.example.org/relay
   /usr/local/libexec/strfry-cleanup-smoke-events --manifest /root/relay-smoke-run.jsonl --relay wss://relay.example.org/relay --execute
   ```
   Genaue IDs im Probelauf prüfen. Nur eigene Testmanifeste verwenden; WSS-URL muss zu Manifest und lokaler Zieldatenbank passen. Keine Suche nach Inhaltspräfixen. Manifest bis erfolgreicher Bereinigung behalten; beschädigte Manifeste werden vollständig abgelehnt.

## Betrieb

```sh
systemctl status caddy strfry.service strfry-prune.timer strfry-disk-guard.timer --no-pager
/usr/local/libexec/strfry-health
journalctl --namespace=strfry -u strfry.service -u strfry-prune.service --since '1 hour ago' --no-pager
sudo -u nostr-relay /usr/local/bin/strfry --config /etc/strfry/strfry.conf --verbosity=WARNING info
```

`strfry-health` gibt nur Aggregate aus (Aktivität, Loopback-Metriken, Verbindungen, Datenbankgröße, freier Platz, Speicher, letzte Bereinigung, Timer, NTP) und endet bei Fehlern mit einem Fehlerstatus. Es setzt Kit-Pfade und Port voraus (`/var/lib/strfry`, `127.0.0.1:7777`).

- Relay-Einstellungen geändert: `systemctl restart strfry.service`; Caddy bleibt unverändert.
- Caddy-Einstellungen geändert: erst `caddy validate …`, dann `systemctl reload caddy`.
- **Disk Guard hat gestoppt:** zuerst freien Platz und Datenbank prüfen, danach `systemctl start strfry.service`; nicht blind neu starten.

## Updates

- **Caddy:** geplant mit Sicherung und [Rollback](docs/caddy.de.md#upgrading).
- **strfry:** Patch ist an den Commit gebunden. Bei neuer Upstream-Version Patch prüfen und neu testen, separat bauen, bisherige Datei und Konfiguration behalten und nur die Binärdatei bei gestopptem Relay ersetzen. Alten und gepatchten Build nie an derselben Datenbank betreiben; kein bewegliches `latest`. Siehe [Patch](docs/patch.de.md).

Zum Abschalten ohne Datenlöschung Site-Block aus Caddyfile entfernen, Caddy prüfen und neu laden, dann `systemctl disable --now strfry.service strfry-prune.timer strfry-disk-guard.timer`. `/var/lib/strfry/db` wird nie automatisch gelöscht.

## Tests

| Befehl | Voraussetzung | Prüfung |
|---|---|---|
| `sh tests/run-unit-tests.sh` | Python 3.11+ | Health, Bereinigung, Disk Guard, Manifeste, TLS-Fehler, Caddy-Update/Rollback und Schlüssel, Binärvergleich, mehrsprachiger Assistent, Verpackung, Shell-Syntax |
| `OPENSSL=/path/to/openssl python3 tests/test_pq_tls_local.py` | OpenSSL 3.5+ | Temporäres Loopback-TLS: passender/falscher Hostname, unvertrautes Zertifikat, beide Gruppen |
| `python3 tests/test_integration.py --binary /opt/strfry-src/strfry` | gepatchtes strfry, `websockets`, `coincurve` | Temporäre LMDB auf Loopback: Verbindungslimit, NIP-40 mit `limit=1`, Zustellung nach vollständiger Bereinigung, fehlerhaftes JSON, langsamer Leser |
| dasselbe mit `--capacity 100 --caddy` | zusätzlich `caddy` in `PATH` | Dasselbe hinter Caddy; separater HTTP-Pfad bleibt bei vollem Relay verfügbar |
| `RELAY_HOST=… python3 tests/smoke_test.py initial --manifest /tmp/new-run.jsonl` | installiertes Relay | Externe WSS-/NIP-01-/NIP-11-/NIP-40-Prüfung; `initial`/`policy` brauchen neues Manifest, `replay`/`absent` Ereignis-IDs |

Gezielte Abnahmetests, kein dauerhafter Lasttest.

## Lizenzen

- Kit (Skripte, Konfiguration, Dokumentation, Tests): [Apache License 2.0](LICENSE).
- `patch/strfry-neighbors.patch`: wie strfry unter [GPL-3.0](LICENSES/GPL-3.0.txt); strfry wird aus Upstream-Quellen gebaut. Die Original-Lizenztexte bleiben unverändert.

Sicherheitsprobleme: [Sicherheitsrichtlinie](SECURITY.de.md).
