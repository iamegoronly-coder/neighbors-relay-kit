# Two deployment paths and independent verification

[English](deployment.md) · [Русский](deployment.ru.md) · [Deutsch](deployment.de.md)

Both paths use this repository's same configuration, helpers, systemd units and installer.
The relay runs as `nostr-relay`; installation requires root. Reading, building and comparing
files does not require root inside the host OS (Docker itself has privileged access).
No command pipes a downloaded script into a shell.

**Status:** the repository and Releases remain private. These anonymous HTTPS commands are prepared for future publication; today they will fail without repository access (typically HTTP 404). They do not change visibility. `v0.1.0-test.3` is a test release, not a production recommendation.

**Validation:** test.1 was downloaded from the private Release, checksum-verified and installed on a clean Ubuntu 24.04 VPS; external TLS and WebSocket checks passed. Test.3 adds the 60 KiB event cap, indexed-only maintenance and a 180-second smoke-policy timeout. A fresh VPS installation of test.3 is deferred; the old test VPS has been deleted. Local container tests do not replace a real systemd/TLS installation. The app setting for custom relays is still planned; this relay has no AUTH, so anyone who knows its address can connect.

[Quickstart](quickstart.md)

## Manual installation preparation

1. Point the domain at a clean Ubuntu 24.04 x86_64 VPS; open TCP 80/443 and retain SSH access.
2. Clone the kit at the **same specific release tag** used by the downloaded binary. Inspect
   `scripts/install.sh`, the selected build recipe and the configuration before running them.
   Example, after setting `REPOSITORY_URL` and `RELEASE_TAG` to the published values:
   ```sh
   git clone --branch "$RELEASE_TAG" --single-branch "$REPOSITORY_URL" neighbors-relay
   cd neighbors-relay
   ```
3. Install Caddy as described in [caddy.md](caddy.md#new-server). Install runtime libraries on
   the relay VPS (these commands do not compile or download a relay executable):
   ```sh
   sudo apt-get -o DPkg::Lock::Timeout=600 install -y --no-install-recommends \
     python3 git curl liblmdb0 libssl3t64 zlib1g libsecp256k1-1 libzstd1 libstdc++6
   ```
4. Edit `config/strfry.conf` identity fields. Both paths below then use the same installer.
   After installation, publish the domain through Caddy and run the checks in the main README.
   These are separate steps only for this low-level manual path; `setup.sh` combines them.

## A. Build from source

### Canonical build, for byte-for-byte comparison

Use a separate build VPS with Docker, x86_64, at least 3 GiB available RAM and sufficient disk
space for the build image and sources (allow 6 GiB). The runtime VPS can remain 1 vCPU / 1 GiB.
An ARM Mac can build with `--platform linux/amd64`; it does not produce an ARM relay.

From the cloned kit, run:

```sh
docker build --platform linux/amd64 --file build/Dockerfile \
  --output type=local,dest=./out .
```

This fetches upstream strfry at the pinned commit and its pinned submodules, applies the public
patch and compiles them. It never downloads a ready-made relay. The Dockerfile pins the Ubuntu
image by digest and every installed package in `build/packages.lock`; compiler flags, source
path, locale, Perl hash iteration and Git checkout depth/tag handling are fixed. The output
`out/strfry` is stripped during the build, not during installation.

If an exact Ubuntu package version is no longer available, the build fails. Do not replace it
silently with a newer version and still promise the same hash. Release maintenance must archive
those package inputs or adopt a verified Ubuntu snapshot before claiming indefinite rebuildability.
The current recipe does not yet provide an offline archive of the compiler packages.

Download the published `strfry` separately to `downloaded/strfry`, without executing it. Compare:

```sh
python3 scripts/compare-binaries.py out/strfry downloaded/strfry
```

`IDENTICAL: every byte matches` means byte-for-byte equality, not just successful tests.
Any difference exits with failure. Do not install a mismatching artifact on the claim that
it is identical; investigate the toolchain, source revision, patch and build recipe first.

Copy the source-built binary to the runtime VPS and install it from the cloned kit there:

```sh
sudo sh scripts/install.sh --binary /path/to/source-built/strfry \
  --sha256 "$EXPECTED_SHA256"
```

`EXPECTED_SHA256` is the checksum of the independently compared build/release, obtained before
installation. The installer stages a copy, checks its SHA-256 and ELF architecture before creating
relay files, then installs precisely those bytes. It does not strip or otherwise rewrite them.

### Native build, for operators who choose their own toolchain

The original native path remains available:

```sh
sudo sh scripts/build-strfry.sh
sudo sh scripts/install.sh
```

It uses the compiler/libraries provided by the current Ubuntu repositories and existing Git tags.
It is **not** the canonical release recipe. Different hashes are possible even with the same
upstream commit and patch. Use the Docker recipe when the purpose is independent binary comparison.
A reverse patch check alone does not prove that a preexisting binary was built from those sources.

## B. Install the published binary

On the runtime VPS, clone and inspect the same kit release as above. Download `strfry` and its
release metadata from that **specific GitHub Release** without executing them. Obtain the expected
SHA-256 from an independently checked build or an authenticated release record, then run:

```sh
python3 scripts/verify-binary.py /path/to/downloaded/strfry --sha256 "$EXPECTED_SHA256"
sudo sh scripts/install.sh --binary /path/to/downloaded/strfry --sha256 "$EXPECTED_SHA256"
```

A checksum next to a download catches corruption relative to that checksum; an attacker who can
replace both can still fool that check. Release signatures/provenance can authenticate the publisher
or build, but require a separately established trust root. No signing identity is configured in this
local draft, so do not describe the artifacts as signed or independently authenticated yet.

The low-level `scripts/install.sh` requires Caddy and the domain to be prepared separately. It
does not modify Caddyfile, change the firewall, create swap or overwrite an existing relay service.
The higher-level `setup.sh` configures Caddy only on a clean VPS and refuses existing installations. A tiny VPS does not need Docker or a compiler when using the published binary.

## Comparing two deployed VPSs

On each VPS:

```sh
sha256sum /usr/local/bin/strfry
```

The hashes should match for the same canonical binary. For a direct byte comparison, copy both
files to one machine and run `scripts/compare-binaries.py` against them.

Binary equality alone is not equality of the whole deployment. Compare the kit tag, patch, helper
scripts, systemd units, Caddy version and configuration too. The domain, operator identity, TLS
certificates and live database legitimately differ; do not copy private keys or databases merely
to compare two servers. The canonical binary dynamically links OS libraries: list and compare
runtime package versions with `dpkg-query -W` and resolved dependencies with `ldd` on your own build.
Do not use `ldd` on an untrusted download before verifying its origin; it is not needed for the
comparison helper, which only reads bytes.

Independent rebuilding provides evidence that a published binary corresponds to the reviewed
source and build inputs. It does **not** prove that the source has no vulnerabilities, that the
compiler is trustworthy, that an operator keeps no logs, or that a remote server actually runs
the binary it claims. These are separate trust questions.

## Before publishing a release

- Freeze the kit tag, upstream commit, patch, compiler package lock and build recipe.
- Run two clean canonical compilations. A cached compiler result is not a second build:
  use different `--build-arg BUILD_RUN=first` / `--build-arg BUILD_RUN=second` values and different
  output directories. This reuses toolchain installation, not compiled relay objects. Also seek
  an independent rebuild on a different host; two local builds are only a local reproducibility test.
- Require `compare-binaries.py` to pass, and run the unit and integration tests on the final binary.
- Publish `strfry`, `SHA256SUMS`, `source.tar.gz`, `strfry-neighbors.patch`, `COPYING`,
  `packages.lock`, `build-info.txt`, the kit source tag and validation results together.
  The source archive contains the complete checked-out sources and initialized build submodules;
  dependency licenses stay with those sources. Provide the GPL-covered corresponding source with
  the binary, not only a link to an unrelated upstream revision.
- Publish the release checksum through an authenticated channel and document its verification;
  decide and document the signing/provenance identity before claiming authenticated releases.
- Test both installation paths on clean Ubuntu VPSs and repeat the external TLS and relay checks.
  Do not replace production relays automatically as part of preparing release artifacts.
