# Simple setup on a clean VPS

[English](quickstart.md) · [Русский](quickstart.ru.md) · [Deutsch](quickstart.de.md)

`setup.sh` combines dependencies, Caddy, the relay, timers and HTTPS checks. Its implementation
is in `scripts/setup-relay.py`, `scripts/install.sh` and this kit's configuration files. Read them
before running as root. Cloning makes inspection possible; it does not itself make code safe.

**Status:** the repository and Releases remain private. These anonymous HTTPS commands are prepared for future publication; today they will fail without repository access (typically HTTP 404). They do not change visibility. `v0.1.0-test.6` is a test release, not a production recommendation.

**Validation:** test.1 was downloaded from the private Release, checksum-verified and installed on a clean Ubuntu 24.04 VPS; external TLS and WebSocket checks passed. Test.6 includes the 60 KiB event cap, indexed-only maintenance, a 180-second smoke-policy timeout and 26-hour retention of normal events. The test.6 contents were installed on a clean Ubuntu 24.04 VPS on 2026-10-22 with `install.conf` and `sudo sh install.sh` (binary mode, AUTH on); external hybrid TLS, NIP-11 and a physical-device connection passed, see the [record](test-release-test6-2026-10-22.md). Local container tests do not replace a real systemd/TLS installation. The app's relay page exists in its main branch and is not yet in a shipped build; AUTH is off by default. Test.6 includes optional `--auth`; it requires a compatible custom-relay client. See the README Authentication section.


## Language selection

With `sudo sh setup.sh` the interactive wizard first offers a language choice. Otherwise it uses `LC_ALL`, `LC_MESSAGES`, then `LANG`, falling back to English. Select a language explicitly with `sudo sh setup.sh --lang en` (or `ru` / `de`); this also applies to `--help`, `--plan` and `--check`. System package/build tools can still print their own messages.

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

## Two commands after public release

**Status:** the repository and Releases remain private. These anonymous HTTPS commands are prepared for future publication; today they will fail without repository access (typically HTTP 404). They do not change visibility. `v0.1.0-test.6` is a test release, not a production recommendation.

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
  --output "$relay_work/neighbors-relay-v0.1.0-test.6.tar.gz" \
  https://github.com/iamegoronly-coder/neighbors-relay-kit/releases/download/v0.1.0-test.6/neighbors-relay-v0.1.0-test.6.tar.gz
```

2. In the same SSH session, verify the pinned checksum before extracting and starting the wizard:

```sh
(cd "${relay_work:?Run the download command first}" &&
  printf '%s  %s\n' 'COPY_SHA256_FROM_TEST_6_RELEASE_NOTES' 'neighbors-relay-v0.1.0-test.6.tar.gz' | sha256sum --check - &&
  tar -xzf neighbors-relay-v0.1.0-test.6.tar.gz &&
  cd neighbors-relay && sudo sh setup.sh)
```

The wizard asks for language, domain and installation mode, then shows a plan for confirmation. Choose **1** for the bundled binary. No GitHub CLI or token is needed after publication. The archive is kept in `$relay_work`; an HTTP or checksum failure must be resolved before continuing. You can inspect the verified, extracted scripts before running `sudo sh setup.sh`. The checksum is pinned here rather than trusted only from a neighboring download; it is not a release signature.

### Clone and build from source

After publication, clone the same specific tag over HTTPS and run source mode. Today this private repository still requires access. Use a new directory; the wizard refuses existing relay installations.

```sh
git clone --branch v0.1.0-test.6 --single-branch \
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
sha256sum -c neighbors-relay-v0.1.0-test.6.tar.gz.sha256
tar -xzf neighbors-relay-v0.1.0-test.6.tar.gz
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

Instead of answering the wizard, fill in `install.conf` next to `setup.sh` and run `sudo sh install.sh`. The keys: `DOMAIN` (required), `AUTH` (`yes` by default: only the app an envelope is addressed to can read it; `no` leaves reads public), `LANGUAGE` (`en`, `ru`, `de`), `NAME` and `CONTACT` (optional NIP-11 identity), `MODE` (`binary` or `source`) and `TLS_TIMEOUT`. The wrapper passes `--config install.conf --yes` to `setup.sh`; any further options win over the file. The preflight, the plan, the lock and the recovery rules are the same as for the wizard. The final summary names the relay address, the place in the app where it is entered, the meaning of the authentication setting, `--check` and the saved-state path; `--check` prints it again at any time.

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

On the preparation machine with `out/v0.1.0-test.6` and Python 3.11+:

```sh
python3 scripts/package-local.py --output out/neighbors-relay-local.tar.gz
```

The packager checks the binary, sources, patch, toolchain lock and manifest. It only includes the
allowlisted kit directories and candidate assets, excluding `.git`, other `out` files, root `.env`
and Python caches, and refusing symlinks. Keep secrets out of documentation/configuration/script
directories: their contents are included. Existing archives are never overwritten. Nothing is uploaded.

## Before public launch

Before public launch, select and validate the final release, update the tag, asset name and pinned archive SHA-256 together in all three READMEs and quickstarts, and test both paths on clean VPSs. After publication, verify an anonymous download from a machine without GitHub credentials. Never replace an existing release asset to make an old checksum work. Visibility changes require a separate decision; these instructions do not authorize publication.
