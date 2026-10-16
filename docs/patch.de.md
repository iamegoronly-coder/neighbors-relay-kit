# strfry-Patch

[English](patch.md) · [Русский](patch.ru.md) · [Deutsch](patch.de.md)

Basis: strfry-Commit `4cd3cf64850caf47dda46c2a2abbbf3525a64d10` (die NIP-11-Version hängt von Git-Historie und Tags ab und weist den Patch nicht nach). Den Binär-SHA-256 mit demselben kanonischen Build/Release vergleichen; siehe [Installation und Prüfung](deployment.de.md). Patch: [`patch/strfry-neighbors.patch`](../patch/strfry-neighbors.patch), wie strfry unter GPL-3.0.

Der Patch ändert die Relay-Implementierung. Ereignisformat, Signaturen und Clientprotokoll bleiben gleich. Bei jeder Änderung der Upstream-Basis neu prüfen und testen.

## Änderungen

- **Exakte Verbindungsgrenze.** `relay.maxConnections` wird in strfrys einzelner WebSocket-Ereignisschleife erzwungen; zusätzliche Verbindungen schließen mit Code 1013. Mehrere Relay-Prozesse mit `REUSE_PORT` teilen keine globale Grenze. Caddys `unhealthy_request_count` zählt die gesamte Anfrage einschließlich Upgrade und liefert meist vorher 503; das Relay erzwingt die endgültige Grenze auch bei gleichzeitigen Handshakes.
- **Ablaufprüfung beim Lesen.** Der anfängliche Backfill überspringt abgelaufene NIP-40-, kurzlebige und zu alte Ereignisse **vor** dem Zählen von `limit`; Live-Abonnements prüfen vor dem Einreihen. Vor Ablauf gesendete Ereignisse können später eintreffen, deshalb müssen Clients selbst prüfen.
- **Monotone Ereignisfolge.** Die rohe LMDB-Tabelle `EventSequence` enthält eine monotone Zahl, gespeichert in derselben Transaktion wie das Ereignis und vor Löschungen (auch beim ersten Start mit einer Datenbank ohne diese Tabelle). Sie enthält keine Texte, Client-Schlüssel, Tags oder Ereignis-IDs. Beim Lesen der neuesten internen Nummer gilt dieser Höchststand auch für eine leere Ereignistabelle; das Löschen des letzten Eintrags setzt die von Live-Abonnements benötigte Folge nicht mehr zurück.

## Bauen

`scripts/build-strfry.sh` erledigt dies auf Ubuntu 24.04. Manuell im Checkout des festgelegten Commits mit initialisierten Submodulen und `make setup-golpe`:

```sh
git apply --check /path/to/strfry-neighbors.patch
git apply /path/to/strfry-neighbors.patch
make -j1 CXXFLAGS='-std=c++20 -O2 -g0 -Wall -fPIC -DDOCOPT_HEADER_ONLY'
```

`git apply --reverse --check` bestätigt den angewendeten Patch; `scripts/install.sh` verlangt diese Prüfung. Auf kleinen VPS mit einem Job, niedriger Priorität und genügend Speicher bauen: Mit Debug-Informationen wurden 1,5 GiB überschritten, `-g0` funktioniert bei 2,5 GiB Budget. Das 512-MiB-Limit des laufenden Relays bleibt gleich.

## Tests vor Installation

```sh
python3 tests/test_integration.py --binary /path/to/patched/strfry
python3 tests/test_integration.py --binary /path/to/patched/strfry --capacity 100 --caddy
```

Sie verwenden eine temporäre LMDB und Loopback-Ports und lesen nie eine Produktionsdatenbank.

## Datenbankkompatibilität und Rollback

Ereignisse und Indizes behalten ihr Format; die Sequenz-Tabelle kommt hinzu. Diese nicht im laufenden Betrieb löschen. Alten und gepatchten Build niemals an derselben Datenbank betreiben: Der alte kennt den Höchststand nicht.

Binärdatei nur bei gestopptem Relay und Prune-Timer zurücksetzen. Upstream bringt auch die alten Einschränkungen zurück: keine Ablaufprüfung beim Lesen und unsichere Live-Abonnements beim Löschen des neuesten Ereignisses. Prune-Timer bis zur Lösung gestoppt lassen und den alten Build nicht als gleichwertig beschreiben. Chatdaten nicht als Teil routinemäßiger Konfigurationssicherungen exportieren.
