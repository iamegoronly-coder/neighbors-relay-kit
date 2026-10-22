# Security policy

[English](SECURITY.md) · [Русский](SECURITY.ru.md) · [Deutsch](SECURITY.de.md)

GitHub **Private vulnerability reporting is currently disabled** for this repository.
Please agree a private reporting channel with the maintainer before sending vulnerability details.
If you do not have one, open an issue titled **Private security contact request**, asking only
how to contact the maintainer privately. Do not include vulnerability details, reproduction
steps, credentials or affected users' data in that public request. Send the report only after
a private channel has been agreed.

Useful to include: affected file or setting, how to reproduce, and the impact you expect
(for example data exposure, denial of service, bypass of a limit).

In scope: the configuration, scripts, systemd units and the strfry patch in this repository, and
documentation that could lead an operator to an insecure setup. Vulnerabilities in strfry itself
or in Caddy should go to those projects; tell us too if this kit makes them worse.

Do not test against relays you do not operate. `tests/smoke_test.py` publishes synthetic events and
is meant for your own deployment.
