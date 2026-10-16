# Local setup wizard validation — October 15, 2026

[English](setup-validation-2026-10-15.md) · [Русский](setup-validation-2026-10-15.ru.md) · [Deutsch](setup-validation-2026-10-15.de.md)

`setup.sh` was prepared for first installation on clean Ubuntu 24.04 x86_64: a verified binary or native source build, official Caddy 2.11.7, relay service and timers, HTTPS, NIP-11 and blocked `/metrics`.

Validation is local. Publication, app changes and modifications to test/production VPSs are outside this work. This report records the state on October 15.

## Completed

- Full `tests/run-unit-tests.sh` on macOS and Ubuntu 24.04 amd64: health, pruning, disk guard, smoke manifests, TLS failures, Caddy update/rollback, binaries, wizard, packaging and shell syntax.
- 14 scenarios in `tests/test_setup.py`: domain/unsafe inputs, prerequisites, existing files/busy ports, memory/disk/DNS, hash, read-only plan, user refusal, binary/source paths, APT failure, Caddyfile restoration, certificate timeout, NIP-11 and health. APT/systemd/curl and compilation use **test implementations** here.
- 5 scenarios in `tests/test_local_package.py`: archive contents/sources/license, damaged files, incomplete/invalid manifests, refusal to overwrite and refusal of symlinks.
- `tests/test_install_container.sh` in two fresh disposable Ubuntu 24.04 amd64 containers: normal mode and `NEIGHBORS_INSTALL_NO_START=1`. File installation is real; binary preservation, ownership/permissions, configuration and units are checked. Wrong hashes and repeated installation are rejected. Caddy, systemctl, systemd-analyze and health are **test stubs**.
- Local bundle extracted in a disposable Ubuntu container: archive checksum, all six files in `payload/SHA256SUMS`, and `setup.sh --help` checked. Local Markdown file links were also checked.

The canonical binary used has SHA-256:

```text
be71c12620a1eee1fcc436b9ce0dfa0ce7cb69f2747a5cd00062b811b1c3a18d
```

Its two clean builds and real loopback LMDB/WebSocket validation are described in the [previous report](reproducibility-check-2026-10-15.md).

## What these checks do not establish

A full installation **using the new wizard** on a clean VPS, real ACME certificate issuance, service startup through real systemd and external TLS/WSS have not yet been completed. The earlier manually deployed test VPS does not replace this acceptance test. Separate binary/source trials and external checks are required before recommending public installation.

The wizard's native build does not promise equality with the canonical binary. Independent verification requires the pinned Docker recipe and byte comparison on another machine. Public URLs, a signed release and automatic resumption of partial installation are not yet available.
