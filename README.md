# Neighbors relay kit

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md)

Deployment kit for a public [Nostr](https://github.com/nostr-protocol/nips) relay used by
**Neighbors**, the private chat in the Home Bills app. It is based on the app's built-in relays: [strfry](https://github.com/hoytech/strfry) behind
Caddy, with a short retention window, hard resource limits and post-quantum TLS. The website
served by our own hosts is not included. The 2026-10-21 updates reduce event size to 60 KiB, remove the redundant full-database
maintenance scan and shorten normal-event retention to 26 h; both built-in relays use the first
two fixes and keep 48 h. The new test candidate is `v0.1.0-test.8`; it fixes installer language selection and clarifies AUTH defaults and validation status. The test.6 contents were installed on a clean Ubuntu 24.04 x86_64 VPS on 2026-10-22 from `install.conf` with AUTH on; the maintainer reported a connection from one physical iPhone. Test.7 added the domain prompt. Test.8 has not been re-run on a VPS; the two-device exchange remains pending. Earlier test tags/archives are retained unchanged.

First-release target: **a dedicated, clean Ubuntu 24.04 x86_64 VPS**. ARM64, Debian and automatic installation alongside an existing Caddy are separate follow-up stages; use the manual deployment guide for an existing server.


> **Status.** This kit deploys a relay; it does not change client settings automatically.
> Connecting to a custom relay needs the app release that includes the relay page (chat settings → Internet → Relay);
> as of 2026-10-21 it is in the app's main branch and not yet in a shipped build.
> The repository and test releases remain private; see the publication status below.

[Relay/client boundary audit and validation (2026-10-21)](docs/relay-client-audit-2026-10-21.md).

[Test.8 candidate: installer language and publication preparation](docs/test-release-test8-2026-10-22.md).

[Test.7 candidate: domain prompt](docs/test-release-test7-2026-10-22.md) · [Test.6 candidate: values-file installer and the clean-VPS installation](docs/test-release-test6-2026-10-22.md).

[Test.5 candidate: 26-hour retention and local validation](docs/test-release-test5-2026-10-21.md).

[Test.4 validation and deferred clean-VPS check](docs/test-release-test4-2026-10-21.md).

## Quick start

1. A clean Ubuntu 24.04 x86_64 VPS, a domain with an A/AAAA record pointing at it, TCP 80 and 443 open, about 1 GiB RAM and 4 GiB free on `/var/lib`.
2. The two commands under [Install](#install): download the pinned archive, verify its SHA-256, extract it and run `sudo sh setup.sh`. The wizard asks for language, domain and mode, shows a plan and, once confirmed, sets up Caddy, the relay and the timers. Or run `sudo sh install.sh`: it asks only for the domain and installs with authentication on.
3. At the end the wizard prints `wss://your-domain/relay`; that is the address users enter in the app as their own relay. Verify at any time with `sudo sh setup.sh --check`.

Details, the non-interactive mode and recovery: [docs/quickstart.md](docs/quickstart.md). While the repository is private the download commands answer 404; a local archive installs the same way, see the quickstart.

## What the relay sees — and what it does not

The relay stores and forwards signed Nostr events. Message content is end-to-end encrypted by the
app before it reaches the relay; the relay cannot read it and does not try to (`content` is never
parsed or logged).

| The relay sees | The relay does not see |
|---|---|
| Connection IP addresses and times | Message text, photos, voice, names in messages |
| Outer event keys and tags: a private envelope (kind 1059) has a one-time outer key and the recipient's relay key in its `p` tag | The sender’s persistent identity key inside a private envelope (this does not guarantee sender anonymity) |
| Event sizes and `created_at` (randomized ±15 min for private envelopes) | The decrypted contact list or readable chat history |

The relay can associate an incoming event with its connection, source IP, timing and recipient
tags, and observe subscription filters. Correlating these can reveal relationships and activity;
a one-time outer key does not make the sender anonymous. These confidentiality claims concern
properly encrypted private envelopes from the app. This public relay also accepts other events,
including plaintext and public application records; it does not encrypt those for their authors.

`OK` from the relay means "accepted for storage", not "delivered". Deleting an event from LMDB
does not guarantee the bytes are physically erased, and a hosting provider may keep disk snapshots.
Do not promise users guaranteed erasure.

### IP handling in this configuration

Caddy terminates client connections and therefore sees their IP addresses. With strfry bound to
loopback and `realIpHeader = ""`, strfry treats Caddy (`127.0.0.1`) as its peer, ignoring forwarded
client-IP headers. The example Caddyfile does not enable HTTP access logs; strfry runs at WARNING
without event dumps. This reduces routine logging; it is **not** a promise that IPs are never
recorded: Caddy error/runtime logs, host/provider logs and operator changes are separate.

### Authentication

The NIP-42 AUTH default depends on the installation entry point:

- `sudo sh setup.sh` without `--config` leaves AUTH **off**; add `--auth` to enable it.
- `sudo sh install.sh` reads the supplied `install.conf`, whose default is **`AUTH=yes`**. Set `AUTH=no` in that file for public reads, or use `setup.sh --config <file>` with your chosen value. An explicit `--auth` enables AUTH even if the file says `AUTH=no`.
- Both built-in relays keep AUTH off; this kit does not change them.

Wait for the app release with the relay page before recommending AUTH relays to users. The page is in the app's main branch: exact-address NIP-11 preflight before saving, warnings about the limits below, AUTH status with an explicit retry, and removal of an address together with that network's data.

With `--auth`, the wizard sets `enabled = true`, `serviceUrl = "wss://<domain>/relay"`,
`restrictedReadKinds = "1059"` and `restrictReadToInvolvedPubkey = true` before starting strfry.
It saves the choice; subsequent `--check` requires NIP-11 to advertise 42. This check verifies the
advertisement, not access control; the real-server integration test checks the restrictions.
The client proves ownership of its **separate inbox key for this custom network**, not its Bluetooth
identity, and retries its closed inbox subscription after the matching AUTH acknowledgement.
An AUTH refusal ends that attempt rather than causing an automatic reconnect loop.

Only an authenticated involved key (the recipient's `p` key or outer event author's key) may read
kind 1059. Writes remain public: anyone may submit a correctly signed envelope to a `p` address;
end-to-end checks still decide what the app accepts. Other kinds are not restricted by this option.
AUTH does not hide metadata from the operator. Subscription filters already reveal requested
inbox keys; AUTH additionally proves ownership and links that key to the connection. Caddy sees
its IP address. Normal logging remains unchanged.

**Custom relays support direct Internet delivery only: gateways and couriers are unavailable, with
or without AUTH.** The app enforces this boundary; the relay page shows this warning before switching.
Bluetooth and ordinary Bluetooth mesh remain available. No gateway delegation is implemented.
See [the AUTH validation record](docs/custom-relay-auth-2026-10-21.md) and
[NIP-42](https://github.com/nostr-protocol/nips/blob/master/42.md).

The app exchanges signed inbox addresses scoped to the selected network over Bluetooth for contacts and groups; custom mode ignores legacy unscoped addresses. Neighbors reach each other over the Internet only when they picked the same relay. A connection from one physical iPhone to an AUTH relay was reported on 2026-10-22; exchanging messages between two physical devices on that relay remains pending.

### Event kinds

| Kind | Used by Neighbors for |
|---|---|
| 1059 | Private envelopes (gift wrap layout; bitchat-derived encryption): direct and group messages, media parcels, receipts. The app subscribes to its own `#p` |
| 30078 | NIP-78 application records (for example the author-reception status record) |
| 1401, 20000, 20001 | Not published by Neighbors today; accepted for bitchat compatibility (courier drops, ephemeral and location channels) and covered by the smoke test |

## Policy and limits

- **History:** normal events are accepted if `created_at` is at most 26 h old and at most 20 min in
  the future; they are served and kept until `created_at + 26 h`, then pruned every 2 minutes.
  The app requests envelopes from roughly the last 24 h, so 26 h is headroom, not a delivery
  promise; a device offline for longer than a day misses messages on any relay.
- **Ephemeral kinds 20000–29999:** accepted within ±60 s of the relay clock, kept on disk for a
  90 s buffer from `created_at`; internal indexed cleanup runs about every 9 s (normally 90–99 s from an event dated now; up to about 160 s after receipt with the allowed +60 s clock skew, longer under load or downtime), never an offline mailbox.
- **NIP-40 `expiration`:** already-expired events are rejected; expired events are filtered at read
  time (patched strfry) and physically removed by the internal expiration-index cron.
  The external 2-minute job only runs `delete --age 93600`; its success stamp monitors age maintenance, not the internal cron.
- **NIP-42 AUTH:** off with plain `setup.sh`, on with the supplied `install.sh` / `AUTH=yes`. See Authentication above for explicit selection. Writes and resource limits remain unchanged.

| Limit | Mechanism |
|---|---|
| 1 vCPU, 512 MiB RAM, 64 tasks, 256 file descriptors | systemd `CPUQuota`, `MemoryMax`, `TasksMax`, `LimitNOFILE` |
| 100 WebSocket connections | `relay.maxConnections` (exact, patched) and Caddy `unhealthy_request_count` (early 503) |
| Database < 1.5 GiB and > 2 GiB free on its filesystem | `strfry-disk-guard` before start and every minute; stops only the relay |
| Event ≤ 60 KiB (61,440 bytes), WebSocket message ≤ 128 KiB | `events.maxEventSize`, `relay.maxWebsocketPayloadSize` |
| 20 subscriptions per connection, 500 events per filter, 1 MiB outbound buffer | `strfry.conf` |
| Relay log ≤ 50 MiB / 7 days, volatile | `journald@strfry.conf` namespace; no event bodies, keys or tags are logged |

The connection limit is not a per-IP rate limit, and the guard checks the disk once a minute:
a burst inside that minute, network saturation or a host failure are out of its scope.

## Post-quantum TLS

Caddy 2.10+ offers the hybrid key exchange `X25519MLKEM768` (X25519 + ML-KEM-768) by default.
When a client actually negotiates this hybrid, the key exchange is designed to resist known
classical and quantum attacks, including “harvest now, decrypt later”. Apple enables support in
`URLSession` on iOS/macOS 26, but OS/server versions alone do not prove which group an individual
connection negotiated. Older clients can negotiate classic X25519 and keep working.
This protects transport only up to the TLS-terminating server. It does not make the app’s existing
end-to-end message encryption post-quantum or protect stored envelopes from the relay itself.

`scripts/install.sh` refuses to run with an older Caddy (`bin/require-pq-caddy`), and
`scripts/check-pq-tls.sh <domain>` verifies both key exchanges from outside, including certificate
trust, hostname and OpenSSL exit status (Python 3 and OpenSSL 3.5+ required). Each OpenSSL process
has a 15-second timeout, configurable with `--timeout`. The version guard is only a prerequisite;
the external handshake is the actual TLS check.

## Requirements

- Ubuntu 24.04 x86_64 (the tested platform), 1 vCPU / 1 GiB RAM is enough to run the relay.
  Building strfry needs about 2.5 GiB of memory (add swap on a small VPS) and some time.
- At least 4 GiB free on the filesystem of `/var/lib/strfry` (1.5 GiB database budget + 2 GiB reserve).
- A domain name with an A/AAAA record to the server (no CDN proxy in front unless you know it
  forwards WebSockets), TCP 80 and 443 open, 7777 **not** exposed.
- An accurate clock (NTP): events are judged by `created_at`.

## Deployment choices

You can build from source or install a published binary using the same service/configuration
installer. For independent comparison, use the pinned canonical Docker build and compare the
result byte-for-byte with the release file. The native Ubuntu build remains available but is
not guaranteed to produce the same hash with different compiler/library versions.

See [both deployment paths and verification](docs/deployment.md) and [how a test candidate is cut](docs/release-process.md); [CHANGELOG.md](CHANGELOG.md) lists the candidates. Private test Releases are available; no signing identity is configured. The local `setup.sh` wizard now prepares
dependencies, Caddy, the domain, relay and timers on a clean VPS.
The installer preserves the exact verified binary bytes.
Two clean local canonical builds matched byte-for-byte; see the
[validation record](docs/reproducibility-check-2026-10-15.md) in three languages. Independent-host validation remains pending.

## Install

**Status:** the repository and Releases remain private. These anonymous HTTPS commands are prepared for future publication; today they will fail without repository access (typically HTTP 404). They do not change visibility. `v0.1.0-test.8` is a test release, not a production recommendation.

For a **clean Ubuntu 24.04 x86_64 VPS** with systemd and synchronized NTP. Point the domain at this VPS and allow TCP 80/443 first. The binary path needs about 1 GiB RAM and at least 4 GiB free on `/var/lib`.

Commands assume `curl`, `ca-certificates`, `tar`, `sha256sum`, Python 3 and sudo/root; the source path also needs Git. If missing, install the download/clone tools once:

```sh
sudo apt-get update && sudo apt-get -o DPkg::Lock::Timeout=600 install -y ca-certificates curl git
```

When logged in as root, omit `sudo`.

1. Download the pinned archive into a new temporary directory:

```sh
relay_work=$(mktemp -d -t neighbors-relay.XXXXXXXX) &&
curl --fail --show-error --location --proto '=https' --proto-redir '=https' \
  --output "$relay_work/neighbors-relay-v0.1.0-test.8.tar.gz" \
  https://github.com/iamegoronly-coder/neighbors-relay-kit/releases/download/v0.1.0-test.8/neighbors-relay-v0.1.0-test.8.tar.gz
```

2. In the same SSH session, verify the pinned checksum before extracting and starting the wizard:

```sh
(cd "${relay_work:?Run the download command first}" &&
  printf '%s  %s\n' 'COPY_SHA256_FROM_TEST_8_RELEASE_NOTES' 'neighbors-relay-v0.1.0-test.8.tar.gz' | sha256sum --check - &&
  tar -xzf neighbors-relay-v0.1.0-test.8.tar.gz &&
  cd neighbors-relay && sudo sh setup.sh)
```

The wizard asks for language, domain and installation mode, then shows a plan for confirmation. Choose **1** for the bundled binary. No GitHub CLI or token is needed after publication. The archive is kept in `$relay_work`; an HTTP or checksum failure must be resolved before continuing. You can inspect the verified, extracted scripts before running `sudo sh setup.sh`. In the source tag/bundled README, replace `COPY_SHA256_FROM_TEST_8_RELEASE_NOTES` with the archive SHA-256 from the test.8 release notes before running the command. The main-branch README pins that hash after packaging (an archive cannot contain its own checksum). This checksum is not a release signature.

### Values file instead of questions

Fill in `install.conf` in the extracted directory (at least `DOMAIN`; `AUTH=yes` is the default, `NAME` and `CONTACT` are optional NIP-11 identity) and run one command:

```sh
sudo sh install.sh
```

If `DOMAIN` is empty, it asks for the domain first. It runs the same preflight and plan as the wizard and installs without further questions. At the end it prints a summary: the relay address, where to enter it in the app, what the authentication setting means and how to check the relay later; `sudo sh setup.sh --check` repeats that summary. The file is parsed line by line as `KEY=VALUE`, never executed; `setup.sh --config install.conf` accepts command-line options that take precedence over it.

### Clone and build from source

After publication, clone the same specific tag over HTTPS and run source mode. Today this private repository still requires access. Use a new directory; the wizard refuses existing relay installations.

```sh
git clone --branch v0.1.0-test.8 --single-branch \
  https://github.com/iamegoronly-coder/neighbors-relay-kit.git neighbors-relay-source
```

```sh
(cd neighbors-relay-source && sudo sh setup.sh --mode source)
```

Source mode fetches pinned upstream sources and builds the relay instead of using a prebuilt relay binary. It needs at least 2.5 GiB RAM + swap and 6 GiB free on `/var/lib` and `/opt` (6 GiB total if shared). Native Ubuntu builds may have different hashes; use the canonical Docker build for byte-for-byte comparison.

[Quickstart](docs/quickstart.md) · [Build / comparison](docs/deployment.md)

### Manual installation

For operators who need individual steps. Run as root on the server, from a private copy of this repository (for example `/root/neighbors-relay`).

1. **Caddy 2.10+** from the official repository — [docs/caddy.md](docs/caddy.md#new-server).
2. **Build strfry** at the pinned commit with the patch ([docs/patch.md](docs/patch.md)):
   ```sh
   sh scripts/build-strfry.sh
   ```
3. **Name your relay** in `config/strfry.conf` (`info.name`, `description`, `contact`), then install
   the service, helpers and timers:
   ```sh
   sh scripts/install.sh
   ```
4. **Publish it through Caddy.** Copy `config/Caddyfile.example` into `/etc/caddy/Caddyfile`
   (or merge its site block into an existing file), replace `relay.example.org`, then:
   ```sh
   caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
   systemctl reload caddy
   ```
5. **Check it.**
   ```sh
   /usr/local/libexec/strfry-health                      # healthy: true
   curl -fsS -H 'Accept: application/nostr+json' https://relay.example.org/relay
   curl -s -o /dev/null -w '%{http_code}\n' https://relay.example.org/metrics   # 404
   ```
   From a machine with OpenSSL 3.5+ (on a Mac: Homebrew OpenSSL):
   ```sh
   sh scripts/check-pq-tls.sh relay.example.org          # two PASS lines
   ```
   Optionally run the external acceptance test (Python 3.12, `websockets==15.0.1`, `coincurve==21.0.0`).
   It publishes synthetic events. For each run choose a new manifest filename; existing files are
   never overwritten. Attempted IDs are flushed to disk **before** sending, so cleanup remains
   possible after a failed test or a lost ACK (rejected IDs are harmless to delete).
   ```sh
   RELAY_HOST=relay.example.org python3 tests/smoke_test.py initial --manifest /tmp/relay-smoke-run.jsonl
   ```
   Copy that manifest to a private directory on the target server, then run:
   ```sh
   /usr/local/libexec/strfry-cleanup-smoke-events --manifest /root/relay-smoke-run.jsonl --relay wss://relay.example.org/relay
   /usr/local/libexec/strfry-cleanup-smoke-events --manifest /root/relay-smoke-run.jsonl --relay wss://relay.example.org/relay --execute
   ```
   Review the exact IDs in the dry run. Use only manifests from your own test runs; the WSS URL
   must match the manifest and the local database you intend to clean. No content-prefix search
   is used. Keep the manifest until cleanup succeeds; a damaged manifest is rejected entirely.

## Operations

```sh
systemctl status caddy strfry.service strfry-prune.timer strfry-disk-guard.timer --no-pager
/usr/local/libexec/strfry-health
journalctl --namespace=strfry -u strfry.service -u strfry-prune.service --since '1 hour ago' --no-pager
sudo -u nostr-relay /usr/local/bin/strfry --config /etc/strfry/strfry.conf --verbosity=WARNING info
```

`strfry-health` prints aggregates only (activity, loopback metrics, connections, database bytes,
free space, memory, last prune, timers, NTP) and exits non-zero when anything is wrong. It assumes
the paths and port used by this kit (`/var/lib/strfry`, `127.0.0.1:7777`).

- Relay settings changed: `systemctl restart strfry.service` (Caddy is not touched).
- Caddy settings changed: `caddy validate …` first, then `systemctl reload caddy`.
- **If the disk guard stopped the relay**, do not restart it blindly: check free space and the
  database first, then `systemctl start strfry.service`.

## Updating

- **Caddy:** planned, with backup and rollback — [docs/caddy.md](docs/caddy.md#upgrading).
- **strfry:** the patch is tied to the pinned commit. A new upstream version means reviewing and
  re-testing the patch, building separately, keeping the previous binary and config, then replacing
  only the binary while the relay is stopped. Never run the old and the patched binary on the same
  database; never use a floating `latest`. Details: [docs/patch.md](docs/patch.md).

To take the relay offline without deleting data: remove its site block from the Caddyfile, validate
and reload Caddy, then `systemctl disable --now strfry.service strfry-prune.timer strfry-disk-guard.timer`.
`/var/lib/strfry/db` is never deleted automatically.

## Tests

| Command | Needs | Checks |
|---|---|---|
| `sh tests/run-unit-tests.sh` | Python 3.11+ | Health policy, prune selection, disk guard, manifest cleanup, TLS failure paths, Caddy update/rollback and key verification, binary verification/comparison, setup wizard, packaging, documentation links and candidate references, shell syntax |
| `OPENSSL=/path/to/openssl python3 tests/test_pq_tls_local.py` | OpenSSL 3.5+ | Disposable loopback TLS: matching/mismatched hostname and untrusted certificate; both groups |
| `python3 tests/test_integration.py --binary /opt/strfry-src/strfry` | patched strfry, `websockets`, `coincurve` | Disposable LMDB on loopback: connection limit, NIP-40 with `limit=1`, live delivery across full prunes, malformed JSON, slow reader |
| same with `--capacity 100 --caddy` | + `caddy` in `PATH` | The same behind Caddy, plus an unrelated HTTP path staying available when the relay is full |
| `RELAY_HOST=… python3 tests/smoke_test.py initial --manifest /tmp/new-run.jsonl` | a deployed relay | External WSS/NIP-01/NIP-11/NIP-40 acceptance (modes: `initial`/`policy` require a new manifest; `replay`/`absent` take event IDs) |

These are targeted acceptance checks, not a long-running load test.

## Licenses

- This kit (scripts, configuration, documentation, tests): [Apache License 2.0](LICENSE).
- `patch/strfry-neighbors.patch` modifies strfry and is distributed under
  [GPL-3.0](LICENSES/GPL-3.0.txt), like strfry itself. strfry is built from its upstream source.

Security issues: see [SECURITY.md](SECURITY.md).
