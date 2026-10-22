# v0.1.0-test.7 — domain prompt

Date: 2026-10-22. Private, locally prepared test candidate; not approval for public publication.
Nothing was pushed, uploaded or published. All earlier tags and archives remain unchanged.
The strfry binary, upstream commit, patch and toolchain lock are identical to test.4 through test.6.

## What changed since test.6

- `sudo sh install.sh` with an empty `DOMAIN` in `install.conf` asks for the domain in a
  terminal and then continues without other questions (AUTH on by default, binary mode).
  Without a terminal the empty value remains an error, as before.
- Six EN/RU/DE README/quickstart references point at test.7. The source tag and bundled docs use
  `COPY_SHA256_FROM_TEST_7_RELEASE_NOTES`; main pins the final archive checksum after packaging.

The clean-VPS installation recorded for [test.6](test-release-test6-2026-10-22.md) covers this
candidate's code except the prompt itself, which is exercised by a wizard unit test; it was not
re-run on a VPS.

Canonical binary SHA-256 (unchanged):
`be71c12620a1eee1fcc436b9ce0dfa0ce7cb69f2747a5cd00062b811b1c3a18d`.

## Local validation of the packaged archive

VALIDATION_PLACEHOLDER

## Gates before users/public publication

Unchanged from the [test.6 record](test-release-test6-2026-10-22.md).
