# Einfache Installation auf einem neuen VPS

[English](quickstart.md) · [Русский](quickstart.ru.md) · [Deutsch](quickstart.de.md)

`setup.sh` installiert Abhängigkeiten, Caddy, Relay und Timer und prüft HTTPS. Die Umsetzung steht in `scripts/setup-relay.py`, `scripts/install.sh` und den Konfigurationsdateien. Prüfen Sie diese vor der Ausführung als root. Klonen ermöglicht eine Prüfung, garantiert aber keine Sicherheit.

**Status:** Repository und Releases bleiben privat. Diese anonymen HTTPS-Befehle sind für eine spätere Veröffentlichung vorbereitet; ohne Repository-Zugriff schlagen sie derzeit fehl (meist HTTP 404). Sie ändern die Sichtbarkeit nicht. `v0.1.0-test.5` ist eine Testversion, keine Empfehlung für den Produktivbetrieb.

**Prüfung:** test.1 wurde aus dem privaten Release heruntergeladen, per SHA-256 geprüft und auf einem frischen Ubuntu-24.04-VPS installiert; externe TLS- und WebSocket-Prüfungen bestanden. Test.5 enthält die Ereignisgrenze von 60 KiB, die ausschließlich altersindizierte Wartung, ein 180-Sekunden-Limit für den Policy-Smoke-Test und 26 Stunden Aufbewahrung normaler Ereignisse. Die Neuinstallation von test.5 auf einem frischen VPS steht noch aus; der frühere Testserver wurde gelöscht. Lokale Containertests ersetzen keine echte systemd/TLS-Installation. Die Relay-Seite der App liegt im main-Zweig und ist noch in keiner veröffentlichten Version; AUTH bleibt standardmäßig aus. Test.5 enthält optionales `--auth` und benötigt dafür einen kompatiblen Client; siehe Authentifizierung im README.


## Sprachauswahl

Bei `sudo sh setup.sh` fragt der interaktive Assistent zuerst nach der Sprache. Sonst gelten `LC_ALL`, `LC_MESSAGES`, dann `LANG`, mit Englisch als Rückfall. Explizite Auswahl: `sudo sh setup.sh --lang de` (oder `en` / `ru`); gilt auch für `--help`, `--plan` und `--check`. Systemwerkzeuge für Pakete und Builds können eigene Meldungen ausgeben.

## Voraussetzungen

- Neues Ubuntu 24.04 x86_64 mit systemd, sudo/root und synchronisierter NTP-Uhr.
- Binärinstallation: 1 vCPU, etwa 1 GiB RAM, mindestens 4 GiB frei auf dem Dateisystem von `/var/lib`.
- Kompilierung: mindestens 2,5 GiB RAM + Swap und 6 GiB frei auf `/var/lib` und `/opt` (insgesamt 6 GiB bei gemeinsamem Dateisystem). Der Assistent legt keinen Swap an.
- A/AAAA-Einträge der Domain zeigen auf den VPS; TCP 80/443 sind von außen erreichbar. AAAA nur bei funktionierendem IPv6 eintragen. Port 7777 bleibt auf Loopback und darf nicht freigegeben werden.
- Zugriff auf Ubuntu-Pakete, das offizielle Caddy-Repository und die Zertifizierungsstelle; für Quellcode zusätzlich GitHub und die Upstream-Abhängigkeiten. Keine Offline-Installation.

Der Assistent zeigt DNS-Adressen, beweist aber nicht, dass sie diesem VPS gehören. Vergleichen Sie diese mit dem Hosting-Panel. Vorhandene Caddy-/Relay-Dateien oder belegte Ports 80/443/7777 stoppen die Installation. Für vorhandene Server gilt die [manuelle Anleitung](deployment.de.md); löschen Sie keine Konfiguration, um diese Prüfung zu umgehen.

## Zwei Befehle nach öffentlicher Veröffentlichung

**Status:** Repository und Releases bleiben privat. Diese anonymen HTTPS-Befehle sind für eine spätere Veröffentlichung vorbereitet; ohne Repository-Zugriff schlagen sie derzeit fehl (meist HTTP 404). Sie ändern die Sichtbarkeit nicht. `v0.1.0-test.5` ist eine Testversion, keine Empfehlung für den Produktivbetrieb.

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
  --output "$relay_work/neighbors-relay-v0.1.0-test.5.tar.gz" \
  https://github.com/iamegoronly-coder/neighbors-relay-kit/releases/download/v0.1.0-test.5/neighbors-relay-v0.1.0-test.5.tar.gz
```

2. In derselben SSH-Sitzung die festgelegte Prüfsumme prüfen, dann entpacken und den Assistenten starten:

```sh
(cd "${relay_work:?Run the download command first}" &&
  printf '%s  %s\n' '457b11c75de953abf053952d0c299ee32896cd746119882c1925433916436fb4' 'neighbors-relay-v0.1.0-test.5.tar.gz' | sha256sum --check - &&
  tar -xzf neighbors-relay-v0.1.0-test.5.tar.gz &&
  cd neighbors-relay && sudo sh setup.sh)
```

Der Assistent fragt nach Sprache, Domain und Installationsart und zeigt einen Plan zur Bestätigung. Für die mitgelieferte Binärdatei **1** wählen. Nach Veröffentlichung sind weder GitHub CLI noch Token nötig. Das Archiv bleibt in `$relay_work`; HTTP- oder Prüfsummenfehler vor dem Fortfahren beheben. Geprüfte, entpackte Skripte können vor `sudo sh setup.sh` gelesen werden. Die Prüfsumme steht fest in dieser Anleitung und stammt nicht nur aus einem benachbarten Download; sie ist keine Release-Signatur.

### Klonen und aus Quellen bauen

Nach Veröffentlichung denselben konkreten Tag per HTTPS klonen und aus Quellen bauen. Das private Repository erfordert derzeit weiterhin Zugriff. Ein neues Verzeichnis verwenden; vorhandene Relay-Installationen werden nicht ersetzt.

```sh
git clone --branch v0.1.0-test.5 --single-branch \
  https://github.com/iamegoronly-coder/neighbors-relay-kit.git neighbors-relay-source
```

```sh
(cd neighbors-relay-source && sudo sh setup.sh --mode source)
```

Der Quellmodus lädt festgelegte Quellen und kompiliert das Relay, statt eine fertige Relay-Binärdatei zu verwenden. Er benötigt mindestens 2,5 GiB RAM + Swap und 6 GiB freien Speicher auf `/var/lib` und `/opt` (insgesamt 6 GiB bei gemeinsamem Dateisystem). Native Ubuntu-Builds können andere Hashes haben; für bytegenauen Vergleich den kanonischen Docker-Build nutzen.

## Lokales Binärpaket

Archiv und `.sha256` auf den VPS kopieren, prüfen und in ein leeres Arbeitsverzeichnis entpacken, nicht über einen vorhandenen Checkout:

```sh
sha256sum -c neighbors-relay-v0.1.0-test.5.tar.gz.sha256
tar -xzf neighbors-relay-v0.1.0-test.5.tar.gz
cd neighbors-relay
sudo sh setup.sh
```

Domain eingeben, **1** für die mitgelieferte Binärdatei wählen, Plan lesen und mit `yes`, `ja` oder `да` bestätigen. Der Assistent prüft SHA-256 und ELF-Architektur, installiert Caddy 2.11.7 aus dem [offiziellen APT-Repository](https://caddyserver.com/docs/install#debian-ubuntu-raspbian), prüft zuvor den festgelegten Schlüsselfingerabdruck, setzt `apt-mark hold`, installiert Relay und Timer und richtet HTTPS ein. Nach erfolgreichen Bereitschaftsprüfungen erscheint `wss://your-domain/relay`.

Zu `payload/strfry` gehören die vollständigen entsprechenden Quellen samt Submodulen in `payload/source.tar.gz`, GPL-Lizenz, Patch, Build-Metadaten und Prüfsummen. Der geprüfte lokale Kandidat steht in `release/local-candidate.json`. Eine Prüfsumme neben dem Archiv prüft die Integrität, aber nicht die Identität des Herausgebers, wenn beide ersetzt wurden. Dieses lokale Paket ist nicht signiert.

Vorprüfung und Plan ohne Änderungen:

```sh
sudo sh setup.sh --mode binary --domain relay.example.org --plan
```

Eine ausdrücklich gewählte Binärdatei installieren, beispielsweise einen eigenen kanonischen Build:

```sh
sudo sh setup.sh --mode binary --domain relay.example.org \
  --binary /path/to/strfry --sha256 "$EXPECTED_SHA256"
```

`EXPECTED_SHA256` vorher aus einem geprüften Build oder authentifizierten Release-Nachweis beziehen. Nach Prüfung des Plans kann eine Automatisierung `--yes` verwenden; sonst schlägt die nichtinteraktive Installation fehl. `--tls-timeout 600` verlängert die HTTPS-Wartezeit von 180 auf 600 Sekunden.


## Wertedatei

Statt die Fragen des Assistenten zu beantworten, füllen Sie `install.conf` neben `setup.sh` aus und starten `sudo sh install.sh`. Die Schlüssel: `DOMAIN` (Pflicht), `AUTH` (`yes` als Standard: nur die adressierte App kann einen Umschlag lesen; `no` lässt das Lesen öffentlich), `LANGUAGE` (`en`, `ru`, `de`), `NAME` und `CONTACT` (optionale NIP-11-Angaben), `MODE` (`binary` oder `source`) und `TLS_TIMEOUT`. Der Wrapper übergibt `--config install.conf --yes` an `setup.sh`; weitere Optionen haben Vorrang vor der Datei. Vorprüfung, Plan, Sperre und Wiederherstellungsregeln sind dieselben wie beim Assistenten. Die Zusammenfassung am Ende nennt die Relay-Adresse, die Stelle in der App, die Bedeutung der Authentifizierung, `--check` und den Pfad des gespeicherten Zustands; `--check` gibt sie jederzeit erneut aus.

## Prüfung und Wiederherstellung

Installiertes Relay ohne Änderungen prüfen:

```sh
sudo sh setup.sh --check
```

Geprüft werden Dienste, Health, lokales HTTPS mit Hostnamen-/Zertifikatsprüfung, NIP-11 und 404 für `/metrics`. Die Domain stammt aus dem gespeicherten Zustand oder aus `--domain`. Es werden keine Ereignisse veröffentlicht und keine WebSocket-Nachrichtenübertragung getestet.

Nach einem Zertifikats-Timeout DNS/Ports korrigieren und `--check` wiederholen. Das installiert keine Pakete und aktualisiert nicht die gespeicherte Installationsphase. Letzte Phase und Binärprüfsumme stehen in `/var/lib/neighbors-relay-setup/state.json`. Diagnose:

```sh
systemctl status caddy strfry --no-pager
journalctl -u caddy -n 50 --no-pager
/usr/local/libexec/strfry-health
```

Waren die Dienste beim Fehler noch nicht installiert, holt `--check` dies nicht nach. Ausgabe sichern, Ursache prüfen und fehlende Schritte manuell ausführen. Automatisches Fortsetzen und Paket-Rollback sind nicht implementiert. Datenbank/Zustandsdatei nicht für einen erneuten Versuch löschen. Scheitert das Caddy-Neuladen, stellt der Assistent die Paket-Standardkonfiguration wieder her; vorhandene Betreiberkonfigurationen werden nie ersetzt.

Von einem anderen Rechner mit OpenSSL 3.5+:

```sh
OPENSSL=/path/to/openssl sh scripts/check-pq-tls.sh relay.example.org
```

Nur ein externer Handshake bestätigt Erreichbarkeit und `X25519MLKEM768`; die Caddy-Version allein reicht nicht. Für Nachrichtentests siehe [Smoke-Test und Bereinigung](../README.de.md#manuelle-installation). Hybrides TLS macht die Ende-zu-Ende-Verschlüsselung der App nicht postquantenfest.

Die Installation ändert weder SSH, Firewall noch DNS, legt keinen Swap an und startet den Server nicht neu. Die festgehaltene Caddy-Version erfordert geplante [Updates und Rollbacks](caddy.de.md#aktualisierung).

## Lokales Paket erstellen

Auf dem Vorbereitungsrechner mit `out/v0.1.0-test.5` und Python 3.11+:

```sh
python3 scripts/package-local.py --output out/neighbors-relay-local.tar.gz
```

Das Packwerkzeug prüft Binärdatei, Quellen, Patch, Toolchain-Lock und Manifest. Es übernimmt nur freigegebene Kit-Verzeichnisse und Kandidatendateien, schließt `.git`, andere `out`-Dateien, die `.env` im Stammverzeichnis und Python-Caches aus und lehnt symbolische Links ab. Keine Geheimnisse in Dokumentation/Konfiguration/Skripten ablegen: Diese Verzeichnisse werden übernommen. Vorhandene Archive werden nie überschrieben. Nichts wird hochgeladen.

## Vor dem öffentlichen Start

Vor dem öffentlichen Start das endgültige Release auswählen und prüfen, Tag, Archivname und festgelegten SHA-256 gemeinsam in allen drei READMEs und Schnellstartanleitungen aktualisieren und beide Wege auf frischen VPS testen. Nach Veröffentlichung anonymen Download von einem Rechner ohne GitHub-Zugangsdaten prüfen. Keine vorhandenen Release-Dateien ersetzen, um eine alte Prüfsumme passend zu machen. Sichtbarkeitsänderungen benötigen eine separate Entscheidung; diese Anleitung erteilt keine Freigabe zur Veröffentlichung.
