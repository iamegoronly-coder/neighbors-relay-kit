# v0.1.0-test.4 — AUTH candidate

Date: 2026-10-21. Private test candidate, not approval for public publication.
The previous test VPS was deleted; a new clean-VPS run is explicitly deferred by the maintainer.
All earlier tags and archives remain unchanged. Do not spend the next VPS run on test.3.

## Contents

- All test.3 fixes: 61,440-byte event cap, 131,072-byte frame cap, indexed age maintenance,
  internal ephemeral/NIP-40 expiry, bounded 180-second smoke-policy wait.
- Optional `setup.sh --auth` for a fresh installation, applied before service start in binary
  and source modes; saved mode and NIP-11 checks. Default remains AUTH-off.
- Reduced binary runtime dependencies. Source mode still installs its build tools.
- Matching test.4 metadata and all six EN/RU/DE README/quickstart references.
- Typed AUTH errors/explicit retry and NIP-11 foundation in the companion app; no released
  relay selector yet. Network-scoped inbox-address exchange is a client prerequisite.

The strfry binary, upstream commit, patch and toolchain lock are unchanged. The packager checks
all payload hashes and refuses an existing output. The source tag and bundled docs use
`COPY_SHA256_FROM_TEST_4_RELEASE_NOTES`; main pins the final archive checksum after packaging.
An archive cannot contain its own checksum. Checksums are not release signatures.

Canonical binary SHA-256:
`be71c12620a1eee1fcc436b9ce0dfa0ce7cb69f2747a5cd00062b811b1c3a18d`.

## Source validation before packaging

- 65 unit tests and shell syntax PASS.
- Canonical strfry in a disposable Linux/amd64 container with external network disabled:
  AUTH integration PASS using the wizard-generated configuration and a temporary LMDB.
  Anonymous/foreign stored and live inbox reads denied; own inbox readable; bad host,
  challenge, signature and replay on another connection rejected; AUTH never stored;
  writes remain public. Same-host path variants pass because strfry compares host/port.
- Companion app: 251 tests in 26 suites PASS (relay, routing, switching, lifecycle, resources).

Archive extraction/install checks and the final archive checksum are recorded on main after
packaging. Container installation uses explicit Caddy/systemd test doubles and cannot establish
real TLS, systemd boot or physical-device acceptance.

## Gates before users/public publication

1. Finish signed network-scoped contact/group inbox exchange, the relay-selection screen,
   and connect exact-address NIP-11 preflight before saving. Explain that custom relays
   do not support gateways or couriers.
2. Provide a clean dedicated Ubuntu 24.04 x86_64 VPS with DNS/SSH; download the exact test.4
   assets and verify SHA-256. Test default and `--auth`, binary and source installs,
   real Caddy/systemd/NTP, restarts/timers, external classic/hybrid TLS and WSS policy/replay.
3. Test the compatible app on physical Apple devices through TLS: own inbox, foreign-read
   rejection, reconnect/lock/background and group delivery. Release client support first.
4. Remove only the run's recorded synthetic events. Review LICENSE/SECURITY, approve public
   visibility separately, and then verify anonymous asset download without credentials.

No production relay update, new VPS, public visibility change, physical-device test, ARM64,
Debian, existing-Caddy integration or full 1.5 GiB database load test is implied by this candidate.
