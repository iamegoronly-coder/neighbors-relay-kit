# v0.1.0-test.3 — preparation and local validation

Date: 2026-10-21. Private test candidate; not approved for first public publication.
The previous test VPS was deleted. The maintainer explicitly deferred a new clean-VPS run.
Earlier tags and archives remain unchanged; test.3 replaces them for further testing.

## Included changes

- Event limit 61,440 bytes with a 131,072-byte WebSocket limit; no AUTH change.
- External maintenance uses only indexed age deletion and a success stamp. Internal strfry
  cron handles ephemeral/NIP-40 expiration; no repeating full-database scan.
- Smoke-policy wait is bounded to 180 seconds, including query time, with 5-second polls.
- Candidate metadata and EN/RU/DE installation instructions refer to test.3.
- Binary, upstream commit, patch and toolchain lock are unchanged. The packager verifies all
  binary/source/license payload checksums before reusing the payload. Configuration and scripts
  come from the new source tag. The archive never overwrites an earlier output.

The source tag/bundled README requires the archive checksum from the release notes. After
packaging, main's README pins that checksum. This avoids an archive containing its own hash;
source and payload checksums are independently checkable. No signing identity is configured.

## Completed checks

- `sh tests/run-unit-tests.sh`: PASS (helper tests, package verification and shell syntax).
- Fresh disposable Ubuntu Linux/amd64 container, external network disabled, 1 CPU / 1 GiB:
  file installation PASS; wrong hash refused before mutations, exact binary/config/unit bytes,
  permissions/ownership checked, repeated installation refused. Caddy, systemd and health are
  explicit test doubles in this test; it is not a systemd boot or external TLS test.
- `tests/test_integration.py` against real canonical strfry and temporary LMDB in a separate
  isolated Linux/amd64 container: PASS. 61,440-byte event and wrapper delivered;
  61,441/65,519/65,536 rejected while the socket remained usable; 200-event replay + EOSE;
  physical ephemeral/NIP-40 deletion; age cleanup with live subscribers; connection-slot reuse
  and slow-reader handling. Test-only timestamp tolerance is widened for accelerated expiry.
- App commit `ad50e6b`: outgoing guards agree on 61,440 bytes in RelayPool, RelaySocket and
  DirectRelayTransport. Incoming events retain 65,536-byte compatibility. NeighborsRelayTests:
  **190 tests / 17 suites PASS**, including single/multiple relay publication boundaries.
- Both built-in live relays received the config/maintenance fixes on 2026-10-21; bounded WSS
  tests and synthetic-event cleanup passed. This update is separate from a clean kit installation.

Canonical binary SHA-256:
`be71c12620a1eee1fcc436b9ce0dfa0ce7cb69f2747a5cd00062b811b1c3a18d`.

## Still required before first public publication

1. Provide a new clean Ubuntu 24.04 x86_64 VPS, DNS and SSH access.
2. Download the exact test.3 archive from its private release and verify its recorded SHA-256.
3. Run the setup wizard with real Caddy/systemd/NTP; verify restart, timers, HTTPS and both
   classic and hybrid TLS handshakes externally, then WSS smoke policy and replay.
4. Remove only the synthetic events recorded in that run's manifest. Record evidence and
   agree the public release separately. Do not treat the old test.1 VPS results as test.3 results.

No new VPS was provisioned, no public visibility was enabled, and no physical client or
full 1.5 GiB database load measurement was performed in this preparation step.
