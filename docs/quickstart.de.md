# Einfache Installation auf einem neuen VPS

[English](quickstart.md) · [Русский](quickstart.ru.md) · [Deutsch](quickstart.de.md)

`setup.sh` installiert Abhängigkeiten, Caddy, Relay und Timer und prüft HTTPS. Die Umsetzung steht in `scripts/setup-relay.py`, `scripts/install.sh` und den Konfigurationsdateien. Prüfen Sie diese vor der Ausführung als root. Klonen ermöglicht eine Prüfung, garantiert aber keine Sicherheit.

**Status:** noch nicht öffentlich veröffentlicht. Der Assistent wurde noch nicht vollständig auf einem neuen VPS erprobt. Er unterstützt Englisch, Russisch und Deutsch (`--lang en|ru|de`). Die veröffentlichte App nutzt die eingebauten Relays; eine Einstellung für eigene Relays folgt später. Dieses Relay verwendet kein AUTH: Jeder, der die Adresse kennt, kann sich verbinden.

## Sprachauswahl

Bei `sudo sh setup.sh` fragt der interaktive Assistent zuerst nach der Sprache. Sonst gelten `LC_ALL`, `LC_MESSAGES`, dann `LANG`, mit Englisch als Rückfall. Explizite Auswahl: `sudo sh setup.sh --lang de` (oder `en` / `ru`); gilt auch für `--help`, `--plan` und `--check`. Systemwerkzeuge für Pakete und Builds können eigene Meldungen ausgeben.

## Voraussetzungen

- Neues Ubuntu 24.04 x86_64 mit systemd, sudo/root und synchronisierter NTP-Uhr.
- Binärinstallation: 1 vCPU, etwa 1 GiB RAM, mindestens 4 GiB frei auf dem Dateisystem von `/var/lib`.
- Kompilierung: mindestens 2,5 GiB RAM + Swap und 6 GiB frei auf `/var/lib` und `/opt` (insgesamt 6 GiB bei gemeinsamem Dateisystem). Der Assistent legt keinen Swap an.
- A/AAAA-Einträge der Domain zeigen auf den VPS; TCP 80/443 sind von außen erreichbar. AAAA nur bei funktionierendem IPv6 eintragen. Port 7777 bleibt auf Loopback und darf nicht freigegeben werden.
- Zugriff auf Ubuntu-Pakete, das offizielle Caddy-Repository und die Zertifizierungsstelle; für Quellcode zusätzlich GitHub und die Upstream-Abhängigkeiten. Keine Offline-Installation.

Der Assistent zeigt DNS-Adressen, beweist aber nicht, dass sie diesem VPS gehören. Vergleichen Sie diese mit dem Hosting-Panel. Vorhandene Caddy-/Relay-Dateien oder belegte Ports 80/443/7777 stoppen die Installation. Für vorhandene Server gilt die [manuelle Anleitung](deployment.de.md); löschen Sie keine Konfiguration, um diese Prüfung zu umgehen.

## Lokales Binärpaket

Archiv und `.sha256` auf den VPS kopieren, prüfen und in ein leeres Arbeitsverzeichnis entpacken, nicht über einen vorhandenen Checkout:

```sh
sha256sum -c neighbors-relay-local-20261015.tar.gz.sha256
tar -xzf neighbors-relay-local-20261015.tar.gz
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

## Quellcode-Checkout oder später git clone

Aus einer lokalen Kopie ohne Binärdatei:

```sh
cd neighbors-relay
sudo sh setup.sh --mode source
```

Dies lädt die festgelegten strfry-Quellen, wendet den Patch an, kompiliert mit Ubuntus Werkzeugen und führt dieselbe Caddy-/Dienstinstallation aus. Es lädt kein fertiges Relay und verwendet keine mitgelieferte Binärdatei. Nach Veröffentlichung: konkreten Tag klonen, ins Verzeichnis wechseln, diesen Befehl ausführen. Eine öffentliche Repository-URL/ein öffentlicher Tag existiert noch nicht; Git muss zum Klonen bereits installiert sein.

Ein nativer Ubuntu-Build kann einen anderen SHA-256 haben. Für einen bytegenauen Vergleich verwenden Sie den [kanonischen Docker-Build](deployment.de.md#canonical-build-for-byte-for-byte-comparison) auf einem separaten Build-Rechner und übergeben das Ergebnis mit `--binary` und `--sha256`. Zwei funktionierende VPS beweisen allein keine Binärgleichheit.

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

Nur ein externer Handshake bestätigt Erreichbarkeit und `X25519MLKEM768`; die Caddy-Version allein reicht nicht. Für Nachrichtentests siehe [Smoke-Test und Bereinigung](../README.de.md#manual-installation). Hybrides TLS macht die Ende-zu-Ende-Verschlüsselung der App nicht postquantenfest.

Die Installation ändert weder SSH, Firewall noch DNS, legt keinen Swap an und startet den Server nicht neu. Die festgehaltene Caddy-Version erfordert geplante [Updates und Rollbacks](caddy.de.md#upgrading).

## Lokales Paket erstellen

Auf dem Vorbereitungsrechner mit `out/candidate-20261015` und Python 3.11+:

```sh
python3 scripts/package-local.py --output out/neighbors-relay-local-20261015.tar.gz
```

Das Packwerkzeug prüft Binärdatei, Quellen, Patch, Toolchain-Lock und Manifest. Es übernimmt nur freigegebene Kit-Verzeichnisse und Kandidatendateien, schließt `.git`, andere `out`-Dateien, die `.env` im Stammverzeichnis und Python-Caches aus und lehnt symbolische Links ab. Keine Geheimnisse in Dokumentation/Konfiguration/Skripten ablegen: Diese Verzeichnisse werden übernommen. Vorhandene Archive werden nie überschrieben. Nichts wird hochgeladen.
