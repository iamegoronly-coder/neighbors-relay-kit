#!/bin/sh
# Builds the pinned strfry commit with patch/strfry-neighbors.patch on Ubuntu 24.04.
# Run as root. The source tree stays in $SRC (default /opt/strfry-src) for install.sh.
set -eu

COMMIT=4cd3cf64850caf47dda46c2a2abbbf3525a64d10
SRC=${SRC:-/opt/strfry-src}
KIT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PATCH="$KIT/patch/strfry-neighbors.patch"

[ "$(id -u)" -eq 0 ] || { echo "build-strfry: run as root" >&2; exit 1; }

apt-get -o DPkg::Lock::Timeout=600 install -y git g++ make libssl-dev zlib1g-dev liblmdb-dev libflatbuffers-dev libsecp256k1-dev libzstd-dev

if [ ! -d "$SRC/.git" ]; then
    git clone https://github.com/hoytech/strfry.git "$SRC"
fi
if [ "$(git -C "$SRC" rev-parse HEAD)" != "$COMMIT" ]; then
    git -C "$SRC" fetch --quiet origin
    git -C "$SRC" checkout --quiet "$COMMIT"
fi
[ "$(git -C "$SRC" rev-parse HEAD)" = "$COMMIT" ]
git -C "$SRC" submodule update --init
make -C "$SRC" setup-golpe

if git -C "$SRC" apply --reverse --check "$PATCH" 2>/dev/null; then
    echo "build-strfry: patch already applied"
else
    git -C "$SRC" apply --check "$PATCH"
    git -C "$SRC" apply "$PATCH"
fi

# One job and no debug info: a debug build exceeded 1.5 GiB of RAM on a small VPS.
nice -n 10 make -C "$SRC" -j1 NPROC=1 CXXFLAGS='-std=c++20 -O2 -g0 -Wall -fPIC -DDOCOPT_HEADER_ONLY'
sha256sum "$SRC/strfry"
