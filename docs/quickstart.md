# Simple setup on a clean VPS

[English](quickstart.md) · [Русский](quickstart.ru.md) · [Deutsch](quickstart.de.md)

`setup.sh` combines dependencies, Caddy, the relay, timers and HTTPS checks. Its implementation
is in `scripts/setup-relay.py`, `scripts/install.sh` and this kit's configuration files. Read them
before running as root. Cloning makes inspection possible; it does not itself make code safe.

**Status:** `v0.1.0-test.8` is an experimental prerelease for evaluation, not a stable release or a production recommendation. Check [GitHub Releases](https://github.com/iamegoronly-coder/neighbors-relay-kit/releases/tag/v0.1.0-test.8) for availability. Two-device delivery and the remaining deployment checks are still pending; see the [validation record](test-release-test8-2026-10-22.md). Publishing the source and prerelease does not mark those checks as passed.

**Validation:** the test.6 contents were installed on a clean Ubuntu 24.04 x86_64 VPS on 2026-10-22 using `install.conf` and `sudo sh install.sh` (binary mode, AUTH on). External hybrid TLS and NIP-11 passed; the maintainer reported a connection from one physical iPhone. See the [record](test-release-test6-2026-10-22.md). Test.7 added the domain prompt; [test.8](test-release-test8-2026-10-22.md) fixes language selection and clarifies these instructions. Neither change has been re-run on a VPS. Two-device message exchange, source installation, reboot/health/timer checks and external smoke-test cleanup remain pending. Local container tests do not replace those checks. The app's relay page is in main but not yet in a shipped build; release the compatible app before recommending AUTH relays to users.

**Authentication defaults:** plain `sudo sh setup.sh` without `--config` leaves AUTH off; `sudo sh setup.sh --auth` enables it. `sudo sh install.sh` reads `install.conf` with **`AUTH=yes` by default**; set `AUTH=no` there for public reads. `--auth` explicitly enables AUTH even if a values file says no. The built-in relays are unchanged.


## Language selection

With `sudo sh setup.sh` the interactive wizard first offers a language choice. For `install.sh` or `setup.sh --config <file>`, the priority is `--lang` → a non-empty `LANGUAGE` in the file → the process locale (`LC_ALL`, then `LC_MESSAGES`, then `LANG`) → English if the locale is unsupported or missing. An empty or omitted `LANGUAGE` preserves the locale; file values `en`, `ru`, `de` are case-insensitive. Select a language explicitly with `sudo sh install.sh --lang en` or `sudo sh setup.sh --lang en` (also `ru` / `de`); this applies to `--help`, `--plan` and `--check` on `setup.sh`. System package/build tools can still print their own messages.

## Prerequisites

- Clean Ubuntu 24.04 x86_64, running systemd, sudo/root access and synchronized NTP.
- Binary installation: 1 vCPU, about 1 GiB RAM, at least 4 GiB free on the `/var/lib` filesystem.
- Source compilation: at least 2.5 GiB RAM + swap and 6 GiB free on `/var/lib` and `/opt`
  (6 GiB total when they share one filesystem). The wizard does not create swap.
- Domain A/AAAA records pointing to the VPS; externally reachable TCP 80/443. Do not add AAAA
  unless IPv6 works. Port 7777 stays on loopback and must not be exposed.
- Network access to Ubuntu packages, Caddy's official repository and the certificate authority;
  source mode also needs GitHub and upstream dependencies. This is not an offline installer.

The wizard displays DNS addresses but does not prove that they belong to this VPS. Verify them
against your hosting panel. Existing Caddy/relay files or listeners on 80/443/7777 stop setup
before installation. Use the [manual guide](deployment.md) for an existing server; do not delete
its configuration merely to bypass this protection.

## Download the public prerelease


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
  printf '%s  %s\n' 'a4c3268886661ae2b5a44a8d4ee9499301bdff06acc4687effa42aa96cde1e5d' 'neighbors-relay-v0.1.0-test.8.tar.gz' | sha256sum --check - &&
  tar -xzf neighbors-relay-v0.1.0-test.8.tar.gz &&
  cd neighbors-relay && sudo sh setup.sh)
```

The wizard asks for language, domain and installation mode, then shows a plan for confirmation. Choose **1** for the bundled binary. Public release downloads do not require GitHub CLI or a token. The archive is kept in `$relay_work`; an HTTP or checksum failure must be resolved before continuing. You can inspect the verified, extracted scripts before running `sudo sh setup.sh`. The checksum is pinned here rather than trusted only from a neighboring download; it is not a release signature.

### Clone and build from source

Clone the same specific tag over HTTPS and run source mode. Use a new directory; the wizard refuses existing relay installations.

```sh
git clone --branch v0.1.0-test.8 --single-branch \
  https://github.com/iamegoronly-coder/neighbors-relay-kit.git neighbors-relay-source
```

```sh
(cd neighbors-relay-source && sudo sh setup.sh --mode source)
```

Source mode fetches pinned upstream sources and builds the relay instead of using a prebuilt relay binary. It needs at least 2.5 GiB RAM + swap and 6 GiB free on `/var/lib` and `/opt` (6 GiB total if shared). Native Ubuntu builds may have different hashes; use the canonical Docker build for byte-for-byte comparison.

## Local binary bundle

Copy the archive and its `.sha256` file to the VPS. Verify and extract into an empty working
location, not over another checkout:

```sh
sha256sum -c neighbors-relay-v0.1.0-test.8.tar.gz.sha256
tar -xzf neighbors-relay-v0.1.0-test.8.tar.gz
cd neighbors-relay
sudo sh setup.sh
```

Enter the domain, choose **1** for the bundled binary, read the plan and confirm with `yes` or
`да` or `ja`. The wizard checks SHA-256 and ELF architecture, installs Caddy 2.11.7 using its
[official APT repository](https://caddyserver.com/docs/install#debian-ubuntu-raspbian), verifies the pinned repository key fingerprint before trusting it, applies
`apt-mark hold`, installs the relay, enables timers and configures HTTPS. It prints
`wss://your-domain/relay` when its readiness checks pass.

`payload/strfry` is accompanied by the complete corresponding source/submodules in
`payload/source.tar.gz`, GPL license, patch, build metadata and checksums. The reviewed local
candidate is specified in `release/local-candidate.json`. A checksum next to the archive checks
integrity, not the publisher's identity if both files were replaced. This local bundle is unsigned.

Read-only preflight and plan:

```sh
sudo sh setup.sh --mode binary --domain relay.example.org --plan
```

Install an explicitly selected binary, including your own canonical rebuild:

```sh
sudo sh setup.sh --mode binary --domain relay.example.org \
  --binary /path/to/strfry --sha256 "$EXPECTED_SHA256"
```

Obtain `EXPECTED_SHA256` from a checked build or an authenticated release record first. After
reviewing the plan, automation can use `--yes`; noninteractive installation otherwise fails.
Use `--tls-timeout 600` to increase HTTPS waiting from 180 to 600 seconds.


## Values file

Instead of answering the wizard, fill in `install.conf` next to `setup.sh` and run `sudo sh install.sh`. With `DOMAIN` left empty the command asks for the domain and continues without other questions. The keys: `DOMAIN` (required), `AUTH` (`yes` by default: reading kind 1059 requires proof of the recipient or outer author key; `no` leaves reads public), `LANGUAGE` (`en`, `ru`, `de`), `NAME` and `CONTACT` (optional NIP-11 identity), `MODE` (`binary` or `source`) and `TLS_TIMEOUT`. The wrapper passes `--config install.conf --yes` to `setup.sh`; any further options win over the file. The preflight, the plan, the lock and the recovery rules are the same as for the wizard. The final summary names the relay address, the place in the app where it is entered, the meaning of the authentication setting, `--check` and the saved-state path; `--check` prints it again at any time.

## Verification and recovery

Read-only verification of an installed relay:

```sh
sudo sh setup.sh --check
```

This checks services, health, local HTTPS with hostname/certificate validation, NIP-11 and
`/metrics` returning 404. It reads the domain from saved state, or accepts `--domain` explicitly.
It does not publish events or test WebSocket message delivery.

After a certificate timeout, fix DNS/ports and retry `--check`. This does not reinstall packages
or update the saved setup phase. The last phase and binary checksum are stored in
`/var/lib/neighbors-relay-setup/state.json`. Diagnostics:

```sh
systemctl status caddy strfry --no-pager
journalctl -u caddy -n 50 --no-pager
/usr/local/libexec/strfry-health
```

If failure occurred before services were installed, `--check` will not finish installing them.
Preserve the output, investigate and complete the required manual steps. Automatic resume and
package rollback are not implemented. Do not delete the database/state file to force a retry.
If Caddy reload fails, the wizard restores Caddy's package-default configuration; it never
replaces a preexisting operator configuration.

From another machine, run the external TLS check with OpenSSL 3.5+:

```sh
OPENSSL=/path/to/openssl sh scripts/check-pq-tls.sh relay.example.org
```

Only an external handshake confirms reachability and `X25519MLKEM768`; installing a Caddy version
alone does not. Use the [smoke test and cleanup procedure](../README.md#manual-installation) for
message-delivery checks. Hybrid TLS does not make the app's end-to-end encryption post-quantum.

Setup does not change SSH/firewall/DNS, create swap or reboot. A held Caddy version needs planned
operator updates; follow the [upgrade/rollback guide](caddy.md#upgrading).

## Create the local bundle

On the preparation machine with `out/v0.1.0-test.8` and Python 3.11+:

```sh
python3 scripts/package-local.py --output out/neighbors-relay-local.tar.gz
```

The packager checks the binary, sources, patch, toolchain lock and manifest. It only includes the
allowlisted kit directories and candidate assets, excluding `.git`, other `out` files, root `.env`
and Python caches, and refusing symlinks. Keep secrets out of documentation/configuration/script
directories: their contents are included. Existing archives are never overwritten. Nothing is uploaded.

## Before a stable release

An experimental prerelease may be published with the outstanding checks stated explicitly. Before recommending a stable release, complete the two-device exchange and remaining clean-VPS checks in the [validation record](test-release-test8-2026-10-22.md). For every new release, update the tag, asset name and pinned archive SHA-256 together in all three READMEs and quickstarts. Verify the public download without GitHub credentials. Never replace an existing tag or release asset to make an old checksum work.
