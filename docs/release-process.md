# Cutting a test candidate

How `v0.1.0-test.N` candidates are prepared locally. Nothing here publishes anything: public
visibility and release uploads are separate decisions. `tests/test_docs.py` enforces the
documentation side of these steps, so a missed reference fails the unit tests.

## 1. Green tree

```sh
sh tests/run-unit-tests.sh
```

For relay-policy changes also run the container checks from the previous record: `tests/test_integration.py`
and `tests/test_auth_integration.py` against the canonical binary in a disposable Linux/amd64
container, and `tests/test_install_container.sh` in a fresh Ubuntu 24.04 container.

## 2. Prepare the candidate commit

1. `release/local-candidate.json`: new `version`, `prepared_at`, the pending-validation note.
   `sha256` and `patch_sha256` change only when the binary or patch changed.
2. The six install documents (`README.md`, `README.ru.md`, `README.de.md`, `docs/quickstart.md`,
   `docs/quickstart.ru.md`, `docs/quickstart.de.md`): the new tag in the download URL, archive
   name and `git clone --branch`, and the placeholder `COPY_SHA256_FROM_TEST_N_RELEASE_NOTES`
   in the `sha256sum --check` command. No other candidate version may remain in those files.
3. `docs/test-release-testN-<date>.md`: what changed, the canonical binary SHA-256, a
   placeholder for the local validation and the gates still open. Link it from the READMEs.
4. `CHANGELOG.md`: a section for the candidate.
5. Commit as `release: prepare test.N …` and tag:

```sh
git tag -a v0.1.0-test.N -m 'Private test.N candidate; … validation pending'
```

The tag and the bundled documents keep the placeholder by design: an archive cannot contain
its own checksum.

## 3. Package

Candidate assets live in `out/v0.1.0-test.N/` (`strfry`, `source.tar.gz`, `build-info.txt`,
`packages.lock`, `strfry-neighbors.patch`, `COPYING`, `SHA256SUMS`). When the binary is unchanged,
copy the previous candidate directory; otherwise build it with `scripts/build-canonical.sh`
and compare with `scripts/compare-binaries.py`.

```sh
python3 scripts/package-local.py --output out/neighbors-relay-v0.1.0-test.N.tar.gz
```

The packager verifies every payload hash against the manifest and refuses to overwrite.

## 4. Validate the extracted archive

Extract into a new empty directory and check, from that copy: every packaged repository file
equals the tag (`git show v0.1.0-test.N:<path>`), payload hashes match `SHA256SUMS`,
`tests/run-unit-tests.sh` passes, the container checks from step 1 pass. Record the results
in the candidate's `docs/test-release-testN-<date>.md`.

## 5. Pin the checksum

Replace the placeholder in the six install documents with the archive SHA-256 from
`out/neighbors-relay-v0.1.0-test.N.tar.gz.sha256`, add the checksum to the record and commit as
`docs: pin test.N archive …`. `tests/test_docs.py` checks that all six agree and match the archive.

## 6. Publish an experimental prerelease

Public source visibility and a test prerelease do not require all stable-release acceptance
checks to be complete. They require an explicit publication decision, the exact validated tag
and archive, LICENSE and SECURITY documentation, and a clear list of remaining checks.

1. Push the reviewed main branch and the specific annotated tag. Do not move existing tags.
2. Open the repository when authorized, and publish the exact archive and its checksum as a
   GitHub **prerelease**, not as a stable/latest release.
3. Release notes must distinguish completed checks from pending physical-device and VPS tests.
   Tagged/bundled documentation is an immutable preparation snapshot: point readers to current
   main-branch instructions and supply the archive checksum in the release notes.
4. Verify repository visibility, prerelease metadata and anonymous download without GitHub
   credentials. Compare the downloaded archive with the pinned SHA-256 and record the result.
   Never replace a published asset to make an old checksum work.

## 7. Acceptance before a stable recommendation

- Complete the outstanding clean Ubuntu 24.04 x86_64 deployment checks in default and AUTH
  modes, binary and source paths, real Caddy/systemd/NTP, external classic and hybrid TLS,
  reboot, timer/prune health, smoke test and cleanup. Preserve credit for already completed checks.
- Verify the companion app on two physical devices: selected-network address exchange,
  private and group delivery, recipient receipts, reconnect/backfill and no duplicates.
- Ship the compatible app with its relay-selection page before recommending AUTH relays to
  ordinary users. Custom relays do not support gateways or couriers.

See the current candidate's validation record for evidence and the exact outstanding items.
