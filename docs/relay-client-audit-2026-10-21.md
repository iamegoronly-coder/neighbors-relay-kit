# Relay/client boundary audit — 2026-10-21

Scope: the private relay-kit checkout and the application's NeighborsRelay receive path.
No live relay, existing release archive, visibility or application version was changed.

## Findings and changes

1. **Event size versus WebSocket message size.** A 65,536-byte normalised event needs an
   additional NIP-01 wrapper (18 bytes for `inbox`). The previous Apple client limited the
   entire message to 65,536 bytes. The kit now accepts events up to **61,440 bytes** while
   keeping the 131,072-byte inbound WebSocket limit. This gives legacy clients wrapper
   headroom for new events; it does not retroactively purge larger stored events. The app's
   URLSession limit is now **131,072 bytes**, with a separate **65,536-byte event** check and
   **69,632-byte envelope** parsing limit. Oversized events/envelopes within the transport
   cap are ignored and later messages remain readable. A message above the transport cap
   still fails at URLSession: this is a bounded-memory limit, not a promise to discard any
   arbitrary-sized message without disconnecting.
2. **Backfill burst.** A 200-event page plus EOSE exceeds the old 200-message/s threshold.
   The app now allows 512 messages per monotonic one-second window, including a 256-event
   gateway page and control frames. On excess it waits until the next window instead of
   throwing and reconnecting. Every received message, including malformed ones, consumes
   budget. Server slow-consumer/resource limits still apply. Reconnect repetition was a
   real risk; “48 hours” is not an exact client failure duration: inbox requests use a
   roughly 24-hour window, while the relay retains events for 48 hours.
3. **Redundant maintenance.** The pinned, patched strfry has a 9-second expiration-index
   cron. The external helper now only runs `delete --age 172800`. Its systemd success stamp
   is written only after success, and monitors age maintenance, not internal cron health.
   Ephemeral retention is 90 seconds from `created_at`: normally about 90–99 seconds for
   an event dated now, up to roughly 160 seconds after receipt with allowed future skew;
   load/downtime may delay physical cleanup. The patch's read-time filter remains intact.
4. **AUTH.** Kept disabled for compatibility. The current app does not answer NIP-42
   challenges; delegated gateway inboxes also need an explicit authentication design.
   AUTH with restricted kinds and involved-key checks limits ciphertext reads, not writes
   or operator visibility. All three READMEs now explain that tradeoff.
5. **IP logging.** Caddy sees the source IP; strfry sees loopback with `realIpHeader = ""`.
   Access logs are not enabled by the example Caddyfile and strfry uses WARNING without
   event dumps. This reduces routine logging, but Caddy errors, host/provider logs and
   operator changes prevent an absolute “IPs are never logged” promise.

## Evidence

- `sh tests/run-unit-tests.sh`: PASS (all helper suites and shell syntax). An initial run
  hit the existing mock-OpenSSL two-second timeout; the complete rerun passed unchanged.
- `tests/test_integration.py` against the canonical patched binary, in an isolated
  Linux/amd64 container with no external network, 1 CPU / 1 GiB RAM and temporary LMDB:
  PASS. Uses the kit configuration with isolated paths/port, two connection slots and
  a wider *test-only* past timestamp tolerance to observe 90-second expiry quickly.
  Verified: 61,440-byte event accepted and readable below the legacy frame cap;
  61,441 / 65,519 / 65,536 rejected; same connection remains usable; 200 EVENTs + EOSE;
  actual on-disk ephemeral/NIP-40 deletion by internal cron with no external age helper,
  including newest-record expiry, live subscription continuity and retained-event survival;
  expiry before LIMIT, repeated complete age deletion, slot reuse and slow-reader handling.
- Binary SHA-256: `be71c12620a1eee1fcc436b9ce0dfa0ce7cb69f2747a5cd00062b811b1c3a18d`.
  No binary or patch rebuild was needed.
- App: 188 tests in NeighborsRelayTests passed. A standalone macOS loopback probe using
  actual URLSession reproduced the old size failure (NSPOSIXErrorDomain 40) and verified
  the corrected transport and parser continue to a later event and EOSE after discarding
  oversized data. Reusable probe and commands are in the app's `Scripts` directory and `TESTING.md`.

This is not a full-database load measurement, a new VPS deployment, an AUTH-enabled client
acceptance test or a physical iPhone/iPad/Watch test. Existing private test release archives
still contain the previous scripts/configuration; publish a new version rather than silently
replacing their pinned files/checksums. Running relays require a separate planned update.

## Pinned upstream references

- [RelayCron.cpp](https://github.com/hoytech/strfry/blob/4cd3cf64850caf47dda46c2a2abbbf3525a64d10/src/apps/relay/RelayCron.cpp)
- [ReadRestrictor.h](https://github.com/hoytech/strfry/blob/4cd3cf64850caf47dda46c2a2abbbf3525a64d10/src/ReadRestrictor.h)
- [Relay settings](https://github.com/hoytech/strfry/blob/4cd3cf64850caf47dda46c2a2abbbf3525a64d10/src/apps/relay/golpe.yaml)
- [Age deletion](https://github.com/hoytech/strfry/blob/4cd3cf64850caf47dda46c2a2abbbf3525a64d10/src/apps/dbutils/cmd_delete.cpp)
- [Required local patch](../patch/strfry-neighbors.patch)
