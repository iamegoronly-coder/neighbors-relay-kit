# v0.1.0-test.6 — values-file installer and the clean-VPS installation

Date: 2026-10-22. Private, locally prepared test candidate; not approval for public publication.
Nothing was pushed, uploaded or published. All earlier tags and archives remain unchanged.
The strfry binary, upstream commit, patch and toolchain lock are identical to test.4 and test.5.

## What changed since test.5

- `install.conf` + `sudo sh install.sh`: fill in the values (domain; AUTH on by default; optional
  NIP-11 name and contact; language) and install without questions. The wizard gained `--config`,
  `--name` and `--contact`; installation and `--check` end with a summary for the operator.
- Documentation consistency test, changelog, release process, quick start, localized anchors,
  and READMEs that describe the app's relay page (in the app's main branch, not yet shipped).
- Six EN/RU/DE README/quickstart references point at test.6. The source tag and bundled docs use
  `COPY_SHA256_FROM_TEST_6_RELEASE_NOTES`; main pins the final archive checksum after packaging.

Canonical binary SHA-256 (unchanged):
`be71c12620a1eee1fcc436b9ce0dfa0ce7cb69f2747a5cd00062b811b1c3a18d`.

## Clean-VPS installation (2026-10-22)

The maintainer installed a local bundle built from the same tree as this candidate (commit
`d49cfd5`; this tag adds only documentation and the manifest) on a fresh, dedicated Ubuntu 24.04
x86_64 VPS with a domain pointing at it. Bundle `neighbors-relay-local-20261022.tar.gz`,
SHA-256 `70f200152f4ba0d5bab93594c7b46a273c9901d4fb5ef6574c74178e185ccf0e`.

Steps, in this order: copy the archive and its `.sha256` to the server with `scp`;
`sha256sum -c`; `tar -xzf`; set `DOMAIN` in `install.conf` (everything else at its default,
so `AUTH=yes`, binary mode); `sudo sh install.sh`. The installer printed the operator summary
with the `wss://<domain>/relay` address and the authentication explanation.

Verified from a Mac outside the VPS:

- NIP-11 over HTTPS with the exact `/relay` path: NIP-01 and NIP-42 advertised,
  `max_subscriptions` 20, `max_message_length` 131072, the 26-hour description.
- `/relay/` and `/metrics` answer 404 through Caddy; the certificate chain and hostname verify.
- `scripts/check-pq-tls.sh <domain>` with OpenSSL 3.6: PASS for X25519MLKEM768 and for X25519.

Companion app (main branch at `63d610e` and later) on a physical iPhone: the relay page
accepted the address after the NIP-11 preflight, the switch succeeded and the app connected
with NIP-42 handled automatically, as reported by the maintainer. This run found and fixed an app
bug: the confirmation dialog cancelled the switch before it ran (`63d610e`).

Not covered by this run: source mode, `sudo sh setup.sh --check` on the server after a reboot,
timers and the prune stamp over time, the external smoke test with cleanup, message exchange
between two devices on the relay, ARM64, Debian, installation next to an existing Caddy.

## Local validation of the packaged archive

Source tag `v0.1.0-test.6` points to the "release: prepare test.6" commit; all 91 packaged repository
files match that tag byte for byte, all payload hashes match the manifest, and no file outside
`README*`, `docs/`, `CHANGELOG.md` and `release/` differs from the installed tree (`d49cfd5`).
`tests/run-unit-tests.sh`: 75 unit tests and shell syntax PASS in the checkout and from the
extracted archive. Container integration, the acceptance boundary and the app TLS stand were run
on this same code for test.5 and are unchanged.

Archive SHA-256:
`c161fc34317a049622c4d54b1666f3dc2b13db35cf8b43f82d9dfb90efda33ed`.

No existing archive or tag was replaced. All six main-branch README/quickstart commands pin
this hash; immutable bundled instructions use the release-notes placeholder by design.

## Gates before users/public publication

- The app release that contains the relay page; the installed build must reach users before
  AUTH relays are recommended to them.
- A second device on the same relay exchanging messages, and the items listed above as not
  covered, at least source mode and `--check` after a reboot.
- A separate decision on public visibility; afterwards an anonymous download check from a
  machine without GitHub credentials. Never replace a published asset to make an old checksum work.
