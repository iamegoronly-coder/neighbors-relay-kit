#!/bin/sh
# Canonical release recipe. Run inside build/Dockerfile, not on a live VPS.
set -eu
KIT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT=${1:?usage: build-canonical.sh NEW_OUTPUT_DIRECTORY}
[ "$(uname -m)" = x86_64 ]
[ ! -e "$OUT" ] || { echo "output already exists" >&2; exit 1; }
[ ! -e /build/strfry ] || { echo "source path already exists; use a fresh container" >&2; exit 1; }
# A changed or unavailable toolchain must fail rather than silently substitute versions.
dpkg-query -W | LC_ALL=C sort > /tmp/relay-actual-packages
LC_ALL=C sort "$KIT/build/packages.lock" > /tmp/relay-expected-packages
diff -u /tmp/relay-expected-packages /tmp/relay-actual-packages
export LC_ALL=C TZ=UTC PERL_HASH_SEED=0 PERL_PERTURB_KEYS=0
umask 022
COMMIT=4cd3cf64850caf47dda46c2a2abbbf3525a64d10
mkdir -p /build
cd /build
git init -q strfry
cd strfry
git remote add origin https://github.com/hoytech/strfry.git
git fetch --depth=1 --no-tags origin "$COMMIT"
git checkout -q --detach FETCH_HEAD
[ "$(git rev-parse HEAD)" = "$COMMIT" ]
git submodule update --init
make setup-golpe
git apply --check "$KIT/patch/strfry-neighbors.patch"
git apply "$KIT/patch/strfry-neighbors.patch"
SOURCE_DATE_EPOCH=$(git show -s --format=%ct HEAD)
export SOURCE_DATE_EPOCH
FLAGS='-std=c++20 -O2 -g0 -Wall -fPIC -DDOCOPT_HEADER_ONLY -ffile-prefix-map=/build/strfry=.'
make -j1 NPROC=1 CXXFLAGS="$FLAGS"
mkdir -p "$OUT"
strip --strip-all -o "$OUT/strfry" strfry
chmod 0755 "$OUT/strfry"
{
    printf 'upstream_commit=%s\nsource_date_epoch=%s\ncxxflags=%s\n' "$COMMIT" "$SOURCE_DATE_EPOCH" "$FLAGS"
    printf 'architecture=linux/amd64\nsource_path=/build/strfry\nperl_hash_seed=0\nperl_perturb_keys=0\n'
    c++ --version
    strip --version
    git submodule status --recursive
} > "$OUT/build-info.txt"
cp "$KIT/build/packages.lock" "$OUT/packages.lock"
cp "$KIT/patch/strfry-neighbors.patch" "$OUT/strfry-neighbors.patch"
cp "$KIT/LICENSES/GPL-3.0.txt" "$OUT/COPYING"
# Complete source used for this binary, including initialized submodules and Git metadata.
# This is not a build cache: generated files and compiled objects are omitted.
tar --sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner \
    --exclude='./build' --exclude='./strfry' --exclude='*.o' --exclude='*.d' \
    --exclude='*.a' --exclude='*.so' -cf "$OUT/source.tar" .
gzip -n "$OUT/source.tar"
cd "$OUT"
sha256sum strfry source.tar.gz build-info.txt packages.lock strfry-neighbors.patch COPYING > SHA256SUMS
cat SHA256SUMS
