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

Source tag `v0.1.0-test.5` points to `2e567c7`; all 85 packaged repository files match that tag
byte for byte, and all payload hashes match the manifest. Everything below ran on the
preparation Mac from the extracted archive, without a VPS, without network access inside the
containers and without touching production relays or system trust.

- `tests/run-unit-tests.sh`: 66 unit tests and shell syntax PASS, both in the checkout and from
  the extracted archive (the new test keeps the prune default equal to the relay configuration).
- `tests/test_integration.py` against the canonical binary in a disposable Ubuntu 24.04 amd64
  container with the 26-hour configuration: PASS (event/frame boundaries, 200-event replay + EOSE,
  expiration, indexed age cleanup, live delivery across full prunes, slots and slow readers).
- `tests/test_auth_integration.py` in the same container: PASS (anonymous/foreign reads denied,
  own inbox readable, bad URL/challenge/replay refused, AUTH not stored, writes public).
- Acceptance boundary on a disposable relay with this configuration: events dated 25 h and
  25 h 59 min ago accepted; 26 h 01 min and 27 h ago rejected with `created_at too early`.
- `tests/test_install_container.sh` in fresh offline containers, normal and `--no-start`: PASS
  (wrong hash refused before mutation, exact bytes/permissions, repeat install refused). Caddy,
  systemd and health are explicit test doubles there.
- Companion app TLS stand (`Scripts/run_neighbors_relay_tls.py`): real URLSession → Caddy 2.11.7
  → this strfry with the wizard-generated 26-hour configuration in default and `--auth` modes:
  PASS; NIP-11 advertised the new 26 h description.

Archive SHA-256:
`457b11c75de953abf053952d0c299ee32896cd746119882c1925433916436fb4`.

No existing archive or tag was replaced. All six main-branch README/quickstart commands pin
this hash; immutable bundled instructions use the release-notes placeholder by design.

## Gates before users/public publication

The gates from the [test.4 record](test-release-test4-2026-10-21.md) still apply: a clean
dedicated Ubuntu 24.04 x86_64 VPS in default and `--auth` modes with real Caddy/systemd/NTP and
external TLS; the relay-selection screen and a physical-device run in the companion app; removal
of the run's synthetic events; a separate decision on public visibility; and an anonymous download
check afterwards. Spend the next VPS run on test.5, not on test.4.
