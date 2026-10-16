# Security policy

[English](SECURITY.md) · [Русский](SECURITY.ru.md) · [Deutsch](SECURITY.de.md)

Please report vulnerabilities privately through GitHub: **Security → Report a vulnerability** on
this repository. Do not open a public issue for a security problem.

Useful to include: affected file or setting, how to reproduce, and the impact you expect
(for example data exposure, denial of service, bypass of a limit).

In scope: the configuration, scripts, systemd units and the strfry patch in this repository, and
documentation that could lead an operator to an insecure setup. Vulnerabilities in strfry itself
or in Caddy should go to those projects; tell us too if this kit makes them worse.

Do not test against relays you do not operate. `tests/smoke_test.py` publishes synthetic events and
is meant for your own deployment.
