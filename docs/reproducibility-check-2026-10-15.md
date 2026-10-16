# Reproducibility check: October 15, 2026

[English](reproducibility-check-2026-10-15.md) · [Русский](reproducibility-check-2026-10-15.ru.md) · [Deutsch](reproducibility-check-2026-10-15.de.md)

Two clean relay builds in separate Docker build stages on one ARM64 Mac (`--platform linux/amd64`) produced **byte-for-byte identical executables**. Compilation ran separately with `BUILD_RUN=first` and `BUILD_RUN=second`, without transferring object files or ready-made relays between them. The compiler environment shared the same pinned package versions. This is local validation, not an independent audit on two VPSs.

- strfry: `4cd3cf64850caf47dda46c2a2abbbf3525a64d10`.
- Linux x86_64; Ubuntu 24.04.
- GCC 13.3.0 (`13.3.0-6ubuntu2~24.04.1`).
- SHA-256: `be71c12620a1eee1fcc436b9ce0dfa0ce7cb69f2747a5cd00062b811b1c3a18d`.
- `compare-binaries.py`: `IDENTICAL: every byte matches`.

Each binary is 3101064 bytes.

## Pinned input files

| File | SHA-256 |
|---|---|
| `build/Dockerfile` | `b11c3e6abf24dd710f3ed28f219543e2cc56991c0b2e4d9538ccd0e766e56a3b` |
| `build/packages.lock` | `68bcc4a098a77d4594feca152c34721254e31bbd6ee397c6e3f5e7a6033d5c72` |
| `scripts/build-canonical.sh` | `2ed54837ae171d845a50b0dea481e3eccc1811a2b4ee73b3a9330acf774c1fb9` |
| `patch/strfry-neighbors.patch` | `c6d67a1e8103bc538a70409ec92484636d3e3ddaec62f65b00022796d0634407` |

## Checked

- All existing fast kit checks and 7 new binary verification/comparison tests.
- A wrong hash is rejected before relay files are created or services started; the binary is installed without changing its bytes; existing services are not overwritten. This test ran in a disposable Ubuntu container with explicit Caddy, systemd and health stubs; it does not establish real systemd startup.
- The **installed** canonical binary passed integration tests with a real temporary LMDB and WebSocket on loopback under a 1 CPU / 1 GiB RAM container limit: connection capacity, expiry filtering before LIMIT, delivery after three complete database prunes, slot release, malformed JSON and a slow receiver.
- Checksums for both output bundles and sources/submodules in the archives were verified. Byte equality is claimed for the binary; auxiliary Git data in source archives can differ between clones.

## Still required before public release

Repeat the build on an independent machine, test both paths on clean VPSs with real systemd/Caddy, prepare a GitHub Release and release authentication. Archiving compiler packages or pinning an Ubuntu snapshot is required for long-term reproducibility.

This canonical binary was not installed on the test VPS or production relays. The previously verified test VPS uses an ordinary build with a different hash. Identical files do not prove absence of vulnerabilities or the configuration of somebody else's server.
