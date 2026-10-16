# Lokale Prüfung des Assistenten — 15. Oktober 2026

[English](setup-validation-2026-10-15.md) · [Русский](setup-validation-2026-10-15.ru.md) · [Deutsch](setup-validation-2026-10-15.de.md)

`setup.sh` wurde für die Erstinstallation auf neuem Ubuntu 24.04 x86_64 vorbereitet: geprüfte Binärdatei oder nativer Quellbuild, offizielles Caddy 2.11.7, Relay-Dienst und Timer, HTTPS, NIP-11 und gesperrtes `/metrics`.

Die Prüfungen sind lokal. Veröffentlichung, App-Änderungen und schreibende Zugriffe auf Test-/Produktions-VPS gehören nicht dazu. Dieser Bericht beschreibt den Stand vom 15. Oktober.

## Durchgeführt

- Vollständiges `tests/run-unit-tests.sh` auf macOS und Ubuntu 24.04 amd64: Health, Bereinigung, Disk Guard, Smoke-Manifeste, TLS-Fehler, Caddy-Update/Rollback, Binärdateien, Assistent, Verpackung und Shell-Syntax.
- 14 Szenarien in `tests/test_setup.py`: Domain/gefährliche Eingaben, Voraussetzungen, vorhandene Dateien/belegte Ports, Speicher/Platz/DNS, Hash, unverändernder Plan, Benutzerablehnung, Binary-/Source-Wege, APT-Fehler, Caddyfile-Wiederherstellung, Zertifikats-Timeout, NIP-11 und Health. APT/systemd/curl und Kompilierung sind hier **Testimplementierungen**.
- 5 Szenarien in `tests/test_local_package.py`: Archivinhalt/Quellen/Lizenz, beschädigte Dateien, unvollständiges/ungültiges Manifest, Ablehnung von Überschreiben und Symlinks.
- `tests/test_install_container.sh` in zwei neuen temporären Ubuntu-24.04-amd64-Containern: normal und `NEIGHBORS_INSTALL_NO_START=1`. Echte Dateiinstallation; geprüft werden unveränderte Binärbytes, Eigentümer/Rechte, Konfiguration und Units. Falscher Hash und erneute Installation werden abgelehnt. Caddy, systemctl, systemd-analyze und Health sind **Testattrappen**.
- Lokales Paket in temporärem Ubuntu-Container entpackt: Archivsumme, alle sechs Dateien in `payload/SHA256SUMS` und `setup.sh --help` geprüft. Lokale Markdown-Dateilinks ebenfalls geprüft.

Kanonische Binärdatei mit SHA-256:

```text
be71c12620a1eee1fcc436b9ce0dfa0ce7cb69f2747a5cd00062b811b1c3a18d
```

Zwei saubere Builds und echte LMDB-/WebSocket-Prüfung auf Loopback stehen im [vorherigen Bericht](reproducibility-check-2026-10-15.de.md).

## Nicht nachgewiesen

Eine vollständige Installation **mit dem neuen Assistenten** auf neuem VPS, echte ACME-Zertifikatsausstellung, Dienststart mit echtem systemd und externes TLS/WSS wurden noch nicht durchlaufen. Der früher manuell eingerichtete Test-VPS ersetzt diese Abnahme nicht. Vor Empfehlung einer öffentlichen Installation sind separate Binary-/Source-Durchläufe und externe Prüfungen nötig.

Der native Build verspricht keinen gleichen Hash wie der kanonische Build. Unabhängige Prüfung benötigt das festgelegte Docker-Rezept und Bytevergleich auf anderem Rechner. Öffentliche URLs, signiertes Release und automatisches Fortsetzen einer Teilinstallation fehlen noch.
