# Simple setup on a clean VPS

[English](quickstart.md) · [Русский](quickstart.ru.md) · [Deutsch](quickstart.de.md)

`setup.sh` combines dependencies, Caddy, the relay, timers and HTTPS checks. Its implementation
is in `scripts/setup-relay.py`, `scripts/install.sh` and this kit's configuration files. Read them
before running as root. Cloning makes inspection possible; it does not itself make code safe.

**Status:** local and unpublished. The wizard has not yet completed a fresh-VPS end-to-end trial.
The wizard supports English, Russian and German (`--lang en|ru|de`). The released app uses its built-in
relays; a setting for custom relays is still planned. This relay has no AUTH; anyone who knows its
address can connect, not just invited participants.

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

## Local binary bundle

Copy the archive and its `.sha256` file to the VPS. Verify and extract into an empty working
location, not over another checkout:

```sh
sha256sum -c neighbors-relay-local-20261015.tar.gz.sha256
tar -xzf neighbors-relay-local-20261015.tar.gz
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

## Source checkout or future git clone

From a local source-only copy:

```sh
cd neighbors-relay
sudo sh setup.sh --mode source
```

This fetches pinned strfry sources, applies the patch, builds with Ubuntu's toolchain and runs the
same Caddy/service installation. It does not download a ready-made relay or use the bundled binary.
After publication the process will be: clone a specific tag, enter the directory, run this command.
No public repository URL/tag exists yet; Git itself must be installed before cloning.

A native Ubuntu build can have a different SHA-256. For byte-for-byte verification use the
[canonical Docker build and comparison](deployment.md#canonical-build-for-byte-for-byte-comparison)
on a separate build machine, then pass the resulting file with `--binary` and `--sha256`.
Two functioning VPSs alone do not prove binary equality.

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

On the preparation machine with `out/candidate-20261015` and Python 3.11+:

```sh
python3 scripts/package-local.py --output out/neighbors-relay-local-20261015.tar.gz
```

The packager checks the binary, sources, patch, toolchain lock and manifest. It only includes the
allowlisted kit directories and candidate assets, excluding `.git`, other `out` files, root `.env`
and Python caches, and refusing symlinks. Keep secrets out of documentation/configuration/script
directories: their contents are included. Existing archives are never overwritten. Nothing is uploaded.
