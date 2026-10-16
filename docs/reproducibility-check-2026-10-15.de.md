# Reproduzierbarkeitsprüfung: 15. Oktober 2026

[English](reproducibility-check-2026-10-15.md) · [Русский](reproducibility-check-2026-10-15.ru.md) · [Deutsch](reproducibility-check-2026-10-15.de.md)

Zwei saubere Relay-Builds in getrennten Docker-Build-Stages auf einem ARM64-Mac (`--platform linux/amd64`) ergaben **bytegenau identische ausführbare Dateien**. Die Kompilierungen liefen separat mit `BUILD_RUN=first` und `BUILD_RUN=second`, ohne Objektdateien oder fertige Relays zu übernehmen. Die Compilerumgebung verwendete dieselben festgelegten Paketversionen. Dies ist eine lokale Prüfung, kein unabhängiges Audit auf zwei VPS.

- strfry: `4cd3cf64850caf47dda46c2a2abbbf3525a64d10`.
- Linux x86_64; Ubuntu 24.04.
- GCC 13.3.0 (`13.3.0-6ubuntu2~24.04.1`).
- SHA-256: `be71c12620a1eee1fcc436b9ce0dfa0ce7cb69f2747a5cd00062b811b1c3a18d`.
- `compare-binaries.py`: `IDENTICAL: every byte matches`.

Jede Binärdatei ist 3101064 Bytes groß.

## Festgelegte Eingabedateien

| Datei | SHA-256 |
|---|---|
| `build/Dockerfile` | `b11c3e6abf24dd710f3ed28f219543e2cc56991c0b2e4d9538ccd0e766e56a3b` |
| `build/packages.lock` | `68bcc4a098a77d4594feca152c34721254e31bbd6ee397c6e3f5e7a6033d5c72` |
| `scripts/build-canonical.sh` | `2ed54837ae171d845a50b0dea481e3eccc1811a2b4ee73b3a9330acf774c1fb9` |
| `patch/strfry-neighbors.patch` | `c6d67a1e8103bc538a70409ec92484636d3e3ddaec62f65b00022796d0634407` |

## Geprüft

- Alle vorhandenen schnellen Kit-Prüfungen und 7 neue Tests für Binärprüfung/-vergleich.
- Falsche Hashes werden vor Anlegen von Relay-Dateien und Starten von Diensten abgelehnt; Binärbytes bleiben unverändert; vorhandene Dienste werden nicht überschrieben. Dieser Test lief im temporären Ubuntu-Container mit ausdrücklichen Caddy-, systemd- und Health-Attrappen und beweist keinen echten systemd-Start.
- Der **installierte** kanonische Build bestand Integrationstests mit echter temporärer LMDB und WebSocket auf Loopback unter 1 CPU / 1 GiB RAM: Verbindungslimit, Ablaufprüfung vor LIMIT, Zustellung nach drei vollständigen Datenbankbereinigungen, Freigabe von Verbindungsplätzen, fehlerhaftes JSON und langsamer Empfänger.
- Prüfsummen beider Ausgabepakete und Quellen/Submodule in den Archiven wurden geprüft. Bytegleichheit wird für die Binärdatei bestätigt; zusätzliche Git-Daten in Quellarchiven können zwischen Klonen abweichen.

## Vor öffentlichem Release noch erforderlich

Auf einem unabhängigen Rechner nachbauen, beide Wege auf neuen VPS mit echtem systemd/Caddy testen, GitHub Release und Release-Authentifizierung vorbereiten. Für langfristige Reproduzierbarkeit Compiler-Pakete archivieren oder einen Ubuntu-Snapshot festlegen.

Dieser kanonische Build wurde weder auf dem Test-VPS noch auf Produktionsrelays installiert. Der zuvor geprüfte Test-VPS verwendet einen normalen Build mit anderem Hash. Dateigleichheit beweist weder Fehlerfreiheit noch die Konfiguration eines fremden Servers.
