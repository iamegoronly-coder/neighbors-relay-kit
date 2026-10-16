# Zwei Installationswege und unabhängige Prüfung

[English](deployment.md) · [Русский](deployment.ru.md) · [Deutsch](deployment.de.md)

Beide Wege verwenden dieselbe Konfiguration, Hilfsprogramme, systemd-Units und denselben Installer. Das Relay läuft als `nostr-relay`; die Installation braucht root. Lesen, Kompilieren und Vergleichen benötigen auf dem Host keine root-Rechte (Docker selbst hat privilegierten Zugriff). Kein Befehl leitet ein heruntergeladenes Skript direkt an eine Shell weiter.

**Status:** Repository und Releases bleiben privat. Diese anonymen HTTPS-Befehle sind für eine spätere Veröffentlichung vorbereitet; ohne Repository-Zugriff schlagen sie derzeit fehl (meist HTTP 404). Sie ändern die Sichtbarkeit nicht. `v0.1.0-test.2` ist eine Testversion, keine Empfehlung für den Produktivbetrieb.

**Prüfung:** test.1 wurde aus dem privaten Release heruntergeladen, per SHA-256 geprüft und auf einem frischen Ubuntu-24.04-VPS installiert; externe TLS- und WebSocket-Prüfungen bestanden. Test.2 enthält die verbesserte Speicherplatzdiagnose und bestand lokale Tests, wurde aber noch nicht auf einem frischen VPS installiert. Die App-Einstellung für eigene Relays ist noch geplant; das Relay hat kein AUTH, jeder mit Kenntnis der Adresse kann sich verbinden.

[Schnellstart](quickstart.de.md)

## Manuelle Vorbereitung

1. Domain auf einen neuen Ubuntu-24.04-x86_64-VPS richten; TCP 80/443 öffnen und SSH-Zugriff erhalten.
2. Kit mit **demselben konkreten Release-Tag** wie die heruntergeladene Binärdatei klonen. `scripts/install.sh`, Build-Rezept und Konfiguration vor Ausführung prüfen. Nach Setzen der veröffentlichten Werte für `REPOSITORY_URL` und `RELEASE_TAG`:
   ```sh
   git clone --branch "$RELEASE_TAG" --single-branch "$REPOSITORY_URL" neighbors-relay
   cd neighbors-relay
   ```
3. Caddy gemäß [Caddy-Anleitung](caddy.de.md#new-server) installieren. Laufzeitbibliotheken auf dem Relay-VPS installieren (hier wird kein Relay kompiliert oder heruntergeladen):
   ```sh
   sudo apt-get -o DPkg::Lock::Timeout=600 install -y --no-install-recommends \
     python3 git curl liblmdb0 libssl3t64 zlib1g libsecp256k1-1 libzstd1 libstdc++6
   ```
4. Identitätsfelder in `config/strfry.conf` bearbeiten. Beide Wege verwenden danach denselben Installer. Anschließend Domain über Caddy bereitstellen und README-Prüfungen ausführen. Nur bei diesem manuellen Weg sind das getrennte Schritte; `setup.sh` verbindet sie.

## A. Aus Quellen bauen

<a id="canonical-build-for-byte-for-byte-comparison"></a>
### Kanonischer Build für einen bytegenauen Vergleich

Separaten Build-VPS mit Docker, x86_64, mindestens 3 GiB verfügbarem RAM und genügend Platz für Image und Quellen verwenden (6 GiB einplanen). Der Laufzeit-VPS kann bei 1 vCPU / 1 GiB bleiben. Ein ARM-Mac kann mit `--platform linux/amd64` bauen; das Ergebnis ist kein ARM-Relay.

Im geklonten Kit:

```sh
docker build --platform linux/amd64 --file build/Dockerfile \
  --output type=local,dest=./out .
```

Dies lädt den festgelegten strfry-Commit mit festgelegten Submodulen, wendet den öffentlichen Patch an und kompiliert. Es lädt kein fertiges Relay. Das Dockerfile fixiert Ubuntu per Digest und alle Pakete in `build/packages.lock`; Compiler-Flags, Quellpfad, Locale, Perl-Hash-Reihenfolge sowie Git-Tiefe/Tags sind festgelegt. `out/strfry` wird beim Build gestrippt, nicht bei der Installation.

Fehlt eine genaue Ubuntu-Paketversion, schlägt der Build fehl. Nicht unbemerkt durch eine neuere Version ersetzen und weiter denselben Hash versprechen. Für langfristige Reproduzierbarkeit müssen Paketdateien archiviert oder ein geprüfter Ubuntu-Snapshot eingesetzt werden. Das aktuelle Rezept enthält kein Offline-Archiv der Compiler-Pakete.

Veröffentlichte Datei separat als `downloaded/strfry` laden, ohne sie auszuführen. Vergleichen:

```sh
python3 scripts/compare-binaries.py out/strfry downloaded/strfry
```

`IDENTICAL: every byte matches` bedeutet Gleichheit jedes Bytes, nicht nur bestandene Tests. Jede Abweichung führt zum Fehler. Eine abweichende Datei nicht als identisch installieren; zuerst Toolchain, Quellrevision, Patch und Rezept untersuchen.

Selbst gebaute Datei auf den Laufzeit-VPS kopieren und dort aus dem geklonten Kit installieren:

```sh
sudo sh scripts/install.sh --binary /path/to/source-built/strfry \
  --sha256 "$EXPECTED_SHA256"
```

`EXPECTED_SHA256` ist die vor Installation ermittelte Prüfsumme des unabhängig verglichenen Builds/Releases. Der Installer erstellt eine Zwischenkopie, prüft SHA-256 und ELF-Architektur vor dem Anlegen von Relay-Dateien und installiert exakt diese Bytes. Er strippt oder verändert sie nicht.

### Nativer Build mit eigener Toolchain

Der ursprüngliche native Weg bleibt verfügbar:

```sh
sudo sh scripts/build-strfry.sh
sudo sh scripts/install.sh
```

Er nutzt Compiler/Bibliotheken aus den aktuellen Ubuntu-Repositories und vorhandene Git-Tags. Dies ist **nicht** das kanonische Release-Rezept. Auch bei gleichem Commit und Patch sind andere Hashes möglich. Für unabhängigen Binärvergleich das Docker-Rezept verwenden. Eine umgekehrte Patch-Prüfung allein beweist nicht, dass eine vorhandene Binärdatei aus diesen Quellen stammt.

## B. Veröffentlichte Binärdatei installieren

Auf dem Laufzeit-VPS denselben Kit-Release klonen und prüfen. `strfry` und Metadaten aus **diesem konkreten GitHub Release** herunterladen, ohne sie auszuführen. Erwarteten SHA-256 aus unabhängig geprüftem Build oder authentifiziertem Release-Nachweis beziehen:

```sh
python3 scripts/verify-binary.py /path/to/downloaded/strfry --sha256 "$EXPECTED_SHA256"
sudo sh scripts/install.sh --binary /path/to/downloaded/strfry --sha256 "$EXPECTED_SHA256"
```

Eine Prüfsumme neben dem Download erkennt Beschädigungen relativ zu dieser Summe; wer beide ersetzen kann, kann die Prüfung täuschen. Signaturen/Herkunftsnachweise brauchen einen separat etablierten Vertrauensanker. Im lokalen Entwurf ist keine Signaturidentität eingerichtet; Artefakte noch nicht als signiert oder unabhängig authentifiziert bezeichnen.

Für `scripts/install.sh` müssen Caddy und Domain separat vorbereitet sein. Es ändert weder Caddyfile noch Firewall, legt keinen Swap an und überschreibt keinen vorhandenen Relay-Dienst. `setup.sh` richtet Caddy nur auf einem neuen VPS ein und lehnt vorhandene Installationen ab. Für die Binärdatei braucht ein kleiner VPS weder Docker noch Compiler.

## Zwei installierte VPS vergleichen

Auf jedem VPS:

```sh
sha256sum /usr/local/bin/strfry
```

Für dieselbe kanonische Binärdatei müssen die Hashes gleich sein. Für direkten Bytevergleich beide Dateien auf einen Rechner kopieren und `scripts/compare-binaries.py` ausführen.

Binärgleichheit bedeutet nicht Gleichheit der gesamten Installation. Auch Kit-Tag, Patch, Hilfsskripte, systemd-Units, Caddy-Version und Konfiguration vergleichen. Domain, Betreiberidentität, TLS-Zertifikate und aktive Datenbank dürfen sich unterscheiden; keine privaten Schlüssel oder Datenbanken nur zum Vergleich kopieren. Der kanonische Build bindet OS-Bibliotheken dynamisch ein: Paketversionen mit `dpkg-query -W`, Abhängigkeiten mit `ldd` am eigenen Build vergleichen. `ldd` nicht vor Herkunftsprüfung auf einen unvertrauten Download anwenden; das Vergleichsskript liest nur Bytes.

Unabhängiges Nachbauen liefert Hinweise, dass Binärdatei und geprüfte Quellen/Build-Eingaben zusammenpassen. Es beweist **nicht**, dass Quellen fehlerfrei sind, der Compiler vertrauenswürdig ist, Betreiber keine Logs führen oder ein fremder Server die behauptete Datei ausführt.

## Vor Veröffentlichung eines Releases

- Kit-Tag, Upstream-Commit, Patch, Compiler-Paket-Lock und Rezept festschreiben.
- Zwei saubere kanonische Kompilierungen ausführen. Compiler-Cache ist kein zweiter Build: unterschiedliche `--build-arg BUILD_RUN=first` / `--build-arg BUILD_RUN=second` und Ausgabeverzeichnisse verwenden. Die Toolchain-Installation darf wiederverwendet werden, kompilierte Relay-Objekte nicht. Zusätzlich auf einem unabhängigen Host nachbauen; zwei lokale Builds sind nur eine lokale Prüfung.
- `compare-binaries.py` muss bestehen; Unit- und Integrationstests am endgültigen Build ausführen.
- `strfry`, `SHA256SUMS`, `source.tar.gz`, `strfry-neighbors.patch`, `COPYING`, `packages.lock`, `build-info.txt`, Kit-Quelltag und Prüfergebnisse gemeinsam veröffentlichen. Das Quellarchiv enthält vollständige Quellen und initialisierte Build-Submodule samt deren Lizenzen. Die entsprechenden GPL-Quellen mitliefern, nicht nur eine unpassende Upstream-Revision verlinken.
- Release-Prüfsumme authentifiziert veröffentlichen und Prüfung dokumentieren; Signatur-/Herkunftsidentität festlegen, bevor authentifizierte Releases versprochen werden.
- Beide Installationswege auf neuen Ubuntu-VPS testen und externe TLS-/Relay-Prüfungen wiederholen. Produktionsrelays nicht automatisch während der Release-Vorbereitung ersetzen.
