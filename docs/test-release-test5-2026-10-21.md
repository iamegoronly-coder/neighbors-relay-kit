# v0.1.0-test.5 — 26-hour retention candidate

Date: 2026-10-21. Private, locally prepared test candidate; not approval for public publication.
Nothing was pushed, uploaded or published. All earlier tags and archives remain unchanged.
The strfry binary, upstream commit, patch and toolchain lock are identical to test.4.

## What changed since test.4

- Normal-event retention is 26 h instead of 48 h: `events.rejectEventsOlderThanSeconds = 93600`
  in `config/strfry.conf` and the same default in `bin/strfry-prune-events`. A unit test keeps
  the two values equal. The app requests inbox envelopes from roughly the last 24 h and rejects
  older ones, so the extra day only stored data no client would ask for. Built-in relays keep 48 h.
- NIP-11 description, prune service/timer descriptions and the three READMEs say 26 h and explain
  that it is headroom, not a delivery promise.
- A read-only GitHub Actions workflow runs `tests/run-unit-tests.sh` on push and pull request.
  It is not part of the bundle.
- Six EN/RU/DE README/quickstart references point at test.5. The source tag and bundled docs use
  `COPY_SHA256_FROM_TEST_5_RELEASE_NOTES`; main pins the final archive checksum after packaging.

Canonical binary SHA-256 (unchanged):
`be71c12620a1eee1fcc436b9ce0dfa0ce7cb69f2747a5cd00062b811b1c3a18d`.

## Local validation

VALIDATION_PLACEHOLDER

## Gates before users/public publication

The gates from the [test.4 record](test-release-test4-2026-10-21.md) still apply: a clean
dedicated Ubuntu 24.04 x86_64 VPS in default and `--auth` modes with real Caddy/systemd/NTP and
external TLS; the relay-selection screen and a physical-device run in the companion app; removal
of the run's synthetic events; a separate decision on public visibility; and an anonymous download
check afterwards. Spend the next VPS run on test.5, not on test.4.
