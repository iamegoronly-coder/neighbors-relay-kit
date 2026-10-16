# Sicherheitsrichtlinie

[English](SECURITY.md) · [Русский](SECURITY.ru.md) · [Deutsch](SECURITY.de.md)

Schwachstellen bitte vertraulich über GitHub melden: **Security → Report a vulnerability** in diesem Repository. Kein öffentliches Issue für Sicherheitsprobleme eröffnen.

Hilfreich sind betroffene Datei/Einstellung, Schritte zur Reproduktion und erwartete Auswirkungen, etwa Datenoffenlegung, Dienstverweigerung oder Umgehung eines Limits.

Zum Umfang gehören Konfiguration, Skripte, systemd-Units, strfry-Patch und Dokumentation, die zu unsicherer Installation führen kann. Schwachstellen in strfry oder Caddy selbst bitte den jeweiligen Projekten melden; informieren Sie auch uns, falls das Kit die Auswirkungen verstärkt.

Keine fremden Relays testen. `tests/smoke_test.py` veröffentlicht synthetische Ereignisse und ist für Ihre eigene Installation gedacht.
