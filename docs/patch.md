# strfry patch

[English](patch.md) · [Русский](patch.ru.md) · [Deutsch](patch.de.md)

Base: strfry commit `4cd3cf64850caf47dda46c2a2abbbf3525a64d10` (the NIP-11 version depends on Git history and tags; it does not reveal the patch).
Compare the binary SHA-256 against the same canonical build/release; see
[deployment and verification](deployment.md).
Patch: [`patch/strfry-neighbors.patch`](../patch/strfry-neighbors.patch), GPL-3.0 like strfry.

The patch changes the implementation of a standard relay. Event format, signatures and the client
protocol are unchanged. Review and re-test it whenever the upstream base changes.

## What it changes

- **Exact connection limit.** `relay.maxConnections` is enforced in strfry's single WebSocket event
  loop; an extra connection is closed with code 1013. Do not run several relay processes with
  `REUSE_PORT` expecting a shared global limit. Caddy's `unhealthy_request_count` counts the whole
  request lifetime including the upgrade and usually answers 503 before the backend — an early
  barrier; the relay enforces the final limit, including during simultaneous handshakes.
- **Expiry at read time.** The initial backfill skips expired NIP-40, ephemeral and too-old events
  **before** counting `limit`; live subscriptions check expiry before queueing an event. An event
  sent before its expiry may still arrive later over the network, so clients must check expiry too.
- **Monotonic event sequence.** A raw LMDB table `EventSequence` holds one monotonic number, written
  in the same transaction as the event and saved before deletions (including the first start on a
  database without the table). It contains no text, client keys, tags or event ids. Reading the
  latest internal number honours this watermark even when the event table is empty, so pruning the
  last record no longer resets the sequence that live subscriptions rely on.

## Build

`scripts/build-strfry.sh` does this on Ubuntu 24.04. Manually, in a checkout of the pinned commit
with initialised submodules and `make setup-golpe`:

```sh
git apply --check /path/to/strfry-neighbors.patch
git apply /path/to/strfry-neighbors.patch
make -j1 CXXFLAGS='-std=c++20 -O2 -g0 -Wall -fPIC -DDOCOPT_HEADER_ONLY'
```

`git apply --reverse --check` confirms the patch is applied; `scripts/install.sh` requires it.
On a small VPS build with one job, low priority and enough memory: with debug info the build
exceeded 1.5 GiB, `-g0` with a 2.5 GiB budget works. This does not change the running relay's
512 MiB limit.

## Tests before installing

```sh
python3 tests/test_integration.py --binary /path/to/patched/strfry
python3 tests/test_integration.py --binary /path/to/patched/strfry --capacity 100 --caddy
```

They use a disposable LMDB and loopback ports and never read a production database.

## Database compatibility and rollback

Existing events and indexes keep their format; the sequence table is added. Do not delete it while
the relay runs, and never run the old and the patched binary on the same database: the old one does
not know the watermark.

Roll back the binary only with the relay and the prune timer stopped. Going back to upstream also
brings back its limitations: no read-time expiry, and deleting the newest event is unsafe for live
subscriptions — keep the prune timer stopped until that is resolved, and do not describe the old
build as equivalent. Do not export chat data as part of a routine configuration backup.
