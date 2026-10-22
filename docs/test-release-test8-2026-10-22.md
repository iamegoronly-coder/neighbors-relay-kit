# v0.1.0-test.8 — installer language and publication preparation

Date: 2026-10-22. Private, locally prepared test candidate; not approval for public publication.
Nothing was pushed, uploaded or published. Earlier tags and archives remain unchanged.

## Changes since test.7

- Empty or missing `LANGUAGE` in `install.conf` preserves the process locale. Explicit file
  values accept mixed case, matching validation. `--lang` has priority over the file; locale
  variables keep the order `LC_ALL`, `LC_MESSAGES`, `LANG`, with English as the fallback.
- Regression tests reproduce the old failure and cover the fixed selection behavior.
- EN/RU/DE READMEs and quickstarts distinguish plain `setup.sh` (AUTH off) from `install.sh`
  with the supplied `AUTH=yes`, describe explicit overrides, and clarify device validation.
- The configuration comment accurately names the recipient and outer author keys allowed to
  read kind 1059 with AUTH. No relay defaults, limits or access-control rules changed.

The strfry binary, upstream commit, patch, Caddy version and toolchain lock are unchanged.
Canonical binary SHA-256:
`be71c12620a1eee1fcc436b9ce0dfa0ce7cb69f2747a5cd00062b811b1c3a18d`.

## Local validation

- `tests/run-unit-tests.sh`: 79 unit tests and shell syntax PASS in both the checkout and
  a separately extracted copy of the final archive.
- The new language cases reproduced nine failing subcases before the fix; all six language
  tests now pass, including empty/omitted config values and mixed-case overrides.
- Documentation links, candidate references, shared checksum placeholder and retention checks pass.
- `install.sh --help` from the extracted archive selects Russian for `ru_RU.UTF-8`, German
  for `de_DE.UTF-8` and English for `C.UTF-8` with the supplied empty `LANGUAGE=`.
- All 93 packaged repository files match `v0.1.0-test.8` byte for byte; all six payload hashes
  match `SHA256SUMS`. The binary and patch match the unchanged candidate manifest.
- All six main-branch install documents pin the final archive hash. The immutable tag and
  bundled instructions carry `COPY_SHA256_FROM_TEST_8_RELEASE_NOTES` by design.

Archive SHA-256: `a4c3268886661ae2b5a44a8d4ee9499301bdff06acc4687effa42aa96cde1e5d`.
Earlier archive hashes and tag object IDs were checked again and are unchanged.

Two sandboxed staging runs reported exit 2 instead of 1 in the existing mock-OpenSSL
unverified-certificate test. The isolated diagnostic run and the full checkout suite outside
that sandbox passed without changing the TLS helper or its tests. No real TLS connection or
certificate verification was bypassed by these installer-language changes.

## External validation and publication gates

The [test.6 record](test-release-test6-2026-10-22.md) reports a clean Ubuntu 24.04 x86_64 binary
installation with AUTH on, external TLS/NIP-11 checks and a connection from one physical iPhone.
It does not establish two-device message delivery. Test.7's domain prompt and test.8's language
selection have not been re-run on that VPS.

Before a user-facing release:

- The compatible app with the relay-selection page must reach users before AUTH relays are
  recommended to them; the page is currently documented as main-only.
- The user will check two physical devices separately: address exchange on the selected relay,
  direct and group messages, recipient receipts, reconnect/backfill and absence of duplicates.
- Complete the supported deployment checks on a clean Ubuntu 24.04 x86_64 VPS: binary and source
  paths, AUTH on/off, `setup.sh --check` after reboot, timers/prune health over time, and the
  external smoke test with removal of its synthetic events. Credit the completed test.6 checks
  above; do not mark the remaining checks as passed based on local mocks or unit tests.
- Decide public visibility and upload the exact tagged archive separately; then verify anonymous
  download and the pinned SHA-256 without GitHub credentials. Never replace a published asset.

ARM64, Debian and installation alongside an existing Caddy remain deferred support work,
not additional gates for the first Ubuntu 24.04 x86_64 release. No live relay or VPS was changed
while preparing this candidate.
