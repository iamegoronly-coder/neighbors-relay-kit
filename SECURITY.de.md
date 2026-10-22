# Sicherheitsrichtlinie

[English](SECURITY.md) · [Русский](SECURITY.ru.md) · [Deutsch](SECURITY.de.md)

GitHub **Private vulnerability reporting ist für dieses Repository derzeit deaktiviert**.
Vereinbaren Sie vor dem Senden von Schwachstellendetails einen vertraulichen Meldeweg mit dem
Projektbetreiber. Falls noch keiner besteht, öffnen Sie ein Issue mit dem Titel
**Anfrage nach einem vertraulichen Sicherheitskontakt** und bitten Sie nur um einen privaten
Kontaktweg. Veröffentlichen Sie dort keine Schwachstellendetails, Reproduktionsschritte,
Zugangsdaten oder Daten betroffener Nutzer. Senden Sie den Bericht erst, wenn ein vertraulicher
Kanal vereinbart wurde.

Hilfreich sind betroffene Datei/Einstellung, Schritte zur Reproduktion und erwartete Auswirkungen, etwa Datenoffenlegung, Dienstverweigerung oder Umgehung eines Limits.

Zum Umfang gehören Konfiguration, Skripte, systemd-Units, strfry-Patch und Dokumentation, die zu unsicherer Installation führen kann. Schwachstellen in strfry oder Caddy selbst bitte den jeweiligen Projekten melden; informieren Sie auch uns, falls das Kit die Auswirkungen verstärkt.

Keine fremden Relays testen. `tests/smoke_test.py` veröffentlicht synthetische Ereignisse und ist für Ihre eigene Installation gedacht.
