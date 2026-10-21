# Neighbors relay kit

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md)

Deployment kit for a public [Nostr](https://github.com/nostr-protocol/nips) relay used by
**Neighbors**, the private chat in the Home Bills app. It is based on the app's built-in relays: [strfry](https://github.com/hoytech/strfry) behind
Caddy, with a short retention window, hard resource limits and post-quantum TLS. The website
served by our own hosts is not included. The 2026-10-21 update reduces event size to 60 KiB and removes the redundant full-database
maintenance scan; both built-in relays already use these fixes. The new test candidate is
`v0.1.0-test.3`. Earlier test tags/archives are retained unchanged. A fresh clean-VPS
installation of this candidate is pending; the former test VPS has been deleted.


> **Status.** This kit deploys a relay; it does not change client settings automatically.
> Connecting to a custom relay requires an app build that supports custom-relay routing.
> The repository and test releases remain private; see the publication status below.

[Relay/client boundary audit and validation (2026-10-21)](docs/relay-client-audit-2026-10-21.md).

[Test.3 validation and deferred clean-VPS check](docs/test-release-2026-10-21.md).

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

NIP-42 AUTH is deliberately disabled because Neighbors does not yet answer AUTH challenges,
including on connections reading delegated gateway inboxes. Today anyone can query ciphertext
and visible tags, and can submit correctly signed events addressed to someone else's `#p`;
end-to-end validation still determines which messages the app accepts. AUTH plus
`restrictedReadKinds = "4, 1059"` and `restrictReadToInvolvedPubkey = true` would restrict reading
those kinds to an authenticated involved key (the recipient's `p` key or the event's outer author
key), reducing bulk collection. This does not encrypt metadata, block unsolicited writes or hide
traffic from the operator. Do not simply enable it for current clients: client signing, service-URL
validation and gateway delegation need coordinated support first.

### Event kinds

| Kind | Used by Neighbors for |
|---|---|
| 1059 | Private envelopes (gift wrap layout; bitchat-derived encryption): direct and group messages, media parcels, receipts. The app subscribes to its own `#p` |
| 30078 | NIP-78 application records (for example the author-reception status record) |
| 1401, 20000, 20001 | Not published by Neighbors today; accepted for bitchat compatibility (courier drops, ephemeral and location channels) and covered by the smoke test |

## Policy and limits

- **History:** normal events are accepted if `created_at` is at most 48 h old and at most 20 min in
  the future; they are served and kept until `created_at + 48 h`, then pruned every 2 minutes.
- **Ephemeral kinds 20000–29999:** accepted within ±60 s of the relay clock, kept on disk for a
  90 s buffer from `created_at`; internal indexed cleanup runs about every 9 s (normally 90–99 s from an event dated now; up to about 160 s after receipt with the allowed +60 s clock skew, longer under load or downtime), never an offline mailbox.
- **NIP-40 `expiration`:** already-expired events are rejected; expired events are filtered at read
  time (patched strfry) and physically removed by the internal expiration-index cron.
  The external 2-minute job only runs `delete --age 172800`; its success stamp monitors age maintenance, not the internal cron.
- **No NIP-42 AUTH.** The relay is public; abuse limits are resource limits.

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

See [both deployment paths and verification](docs/deployment.md). Private test Releases are available; no signing identity is configured. The local `setup.sh` wizard now prepares
dependencies, Caddy, the domain, relay and timers on a clean VPS.
The installer preserves the exact verified binary bytes.
Two clean local canonical builds matched byte-for-byte; see the
[validation record](docs/reproducibility-check-2026-10-15.md) in three languages. Independent-host validation remains pending.

## Install

**Status:** the repository and Releases remain private. These anonymous HTTPS commands are prepared for future publication; today they will fail without repository access (typically HTTP 404). They do not change visibility. `v0.1.0-test.3` is a test release, not a production recommendation.

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
  --output "$relay_work/neighbors-relay-v0.1.0-test.3.tar.gz" \
  https://github.com/iamegoronly-coder/neighbors-relay-kit/releases/download/v0.1.0-test.3/neighbors-relay-v0.1.0-test.3.tar.gz
```

2. In the same SSH session, verify the pinned checksum before extracting and starting the wizard:

```sh
(cd "${relay_work:?Run the download command first}" &&
  printf '%s  %s\n' '81d19a2efcf7adae66ca127e041849b2f114196759a4f8b21fc06cbd52fcd0c0' 'neighbors-relay-v0.1.0-test.3.tar.gz' | sha256sum --check - &&
  tar -xzf neighbors-relay-v0.1.0-test.3.tar.gz &&
  cd neighbors-relay && sudo sh setup.sh)
```

The wizard asks for language, domain and installation mode, then shows a plan for confirmation. Choose **1** for the bundled binary. No GitHub CLI or token is needed after publication. The archive is kept in `$relay_work`; an HTTP or checksum failure must be resolved before continuing. You can inspect the verified, extracted scripts before running `sudo sh setup.sh`. In the source tag/bundled README, replace `COPY_SHA256_FROM_TEST_3_RELEASE_NOTES` with the archive SHA-256 from the test.3 release notes before running the command. The main-branch README pins that hash after packaging (an archive cannot contain its own checksum). This checksum is not a release signature.

### Clone and build from source

After publication, clone the same specific tag over HTTPS and run source mode. Today this private repository still requires access. Use a new directory; the wizard refuses existing relay installations.

```sh
git clone --branch v0.1.0-test.3 --single-branch \
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
| `sh tests/run-unit-tests.sh` | Python 3.11+ | Health policy, prune selection, disk guard, manifest cleanup, TLS failure paths, Caddy update/rollback and key verification, binary verification/comparison, setup wizard, packaging, shell syntax |
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
