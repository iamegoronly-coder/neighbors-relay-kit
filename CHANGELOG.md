# Changelog

All candidates are private test releases unless a record says otherwise. Earlier tags and
archives are never replaced; a checksum next to an archive proves integrity, not authorship.
Dates are the day the tag was created. Validation records live in `docs/`.

## Unreleased

Nothing yet.

## v0.1.0-test.6 — 2026-10-22

- First clean-VPS installation of the kit's current contents: `install.conf` with AUTH on,
  `sudo sh install.sh`, external hybrid TLS and NIP-11 checks, and the companion app connecting
  from a physical iPhone. [Record](docs/test-release-test6-2026-10-22.md).
- Documentation consistency test (`tests/test_docs.py`): relative links and heading anchors,
  the six install commands naming one candidate and one checksum, retention numbers quoted
  in the READMEs. Runs with `tests/run-unit-tests.sh` and in CI.
- Russian and German docs now link to their own heading anchors instead of the English ones.
- Changelog, [release process](docs/release-process.md) and a quick-start block at the top of
  the three READMEs.
- `install.conf` + `sudo sh install.sh`: fill in the values (domain, AUTH on by default, optional NIP-11
  name and contact) and install without questions. The wizard gained `--config`, `--name` and
  `--contact`, and both the install and `--check` end with a summary: relay address, where to enter
  it in the app, what the authentication setting means.
- READMEs and quickstarts describe the app's relay page (in the app's main branch since
  2026-10-21, not yet in a shipped build) instead of a planned selector.

## v0.1.0-test.5 — 2026-10-21

- Normal-event retention shortened from 48 h to 26 h (`rejectEventsOlderThanSeconds = 93600`,
  same prune default, unit test keeps both equal). The app requests inbox envelopes from
  roughly the last 24 h; built-in relays keep 48 h.
- Read-only GitHub Actions workflow for the unit tests.
- Same binary, patch and toolchain as test.4. [Record](docs/test-release-test5-2026-10-21.md).

## v0.1.0-test.4 — 2026-10-21

- Optional NIP-42 AUTH for custom relays: `setup.sh --auth` (restricted reads of kind 1059 to
  the involved inbox key), saved mode, `--check` requires 42 in NIP-11, real-strfry AUTH
  integration test. Default stays AUTH-off.
- Binary mode no longer installs `git` and `binutils`.
- [Record](docs/test-release-test4-2026-10-21.md) and [AUTH validation](docs/custom-relay-auth-2026-10-21.md).

## v0.1.0-test.3 — 2026-10-21

- Event size cap 61,440 bytes and WebSocket frame cap 131,072 bytes, matching the built-in
  relays and the app's publish policy.
- Age maintenance uses strfry's indexed `delete --age` only; the redundant full-database scan
  is gone. Ephemeral and NIP-40 expiry stay with the patched internal cron.
- Smoke-policy wait bounded to 180 s. [Record](docs/test-release-2026-10-21.md).

## v0.1.0-test.2 — 2026-10-16

- Setup diagnostics show available and required disk space.

## v0.1.0-test.1 — 2026-10-16

- Initial kit: pinned strfry `4cd3cf6` with the GPL patch, Caddy 2.10+ with post-quantum TLS,
  `setup.sh` wizard in English, Russian and German, systemd units, disk guard, health and
  prune helpers, external smoke test with cleanup, canonical Docker build and byte-for-byte
  comparison. [Reproducibility](docs/reproducibility-check-2026-10-15.md) and
  [setup validation](docs/setup-validation-2026-10-15.md).
