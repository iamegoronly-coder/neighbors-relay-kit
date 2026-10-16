#!/bin/sh
# Installs the relay service, helpers and timers from this kit on Ubuntu 24.04.
# Run as root after a source build, or pass --binary FILE --sha256 EXPECTED_HASH.
# Caddy 2.10+ and runtime libraries must be installed first (docs/deployment.md).
# Does not touch Caddy or the firewall; configure them separately (README, step 4).
set -eu

COMMIT=4cd3cf64850caf47dda46c2a2abbbf3525a64d10
SRC=${SRC:-/opt/strfry-src}
KIT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

START=1
MODE=source
BINARY=
EXPECTED=
while [ "$#" -gt 0 ]; do
    case "$1" in
        --no-start) START=0; shift ;;
        --binary) [ "$#" -ge 2 ] || exit 2; MODE=binary; BINARY=$2; shift 2 ;;
        --sha256) [ "$#" -ge 2 ] || exit 2; EXPECTED=$2; shift 2 ;;
        *) echo "usage: install.sh [--binary FILE --sha256 EXPECTED_HASH] [--no-start]" >&2; exit 2 ;;
    esac
done
if [ "$MODE" = binary ]; then
    [ -n "$BINARY" ] && [ -n "$EXPECTED" ] || { echo "--binary requires --sha256" >&2; exit 2; }
elif [ -n "$EXPECTED" ]; then
    echo "--sha256 requires --binary" >&2
    exit 2
fi

[ "$(id -u)" -eq 0 ] || { echo "install: run as root" >&2; exit 1; }
# The relay is published only through Caddy; refuse a Caddy without post-quantum TLS.
sh "$KIT/bin/require-pq-caddy"
if [ -e /etc/systemd/system/strfry.service ]; then
    echo "install: strfry.service already exists; see README, 'Updating'" >&2
    exit 1
fi
# Snapshot the chosen executable before verification; install these exact bytes.
STAGED=$(mktemp -d)
trap 'rm -rf "$STAGED"' 0
trap 'exit 1' 1 2 3 15
if [ -n "$BINARY" ]; then
    install -m 0755 -- "$BINARY" "$STAGED/strfry"
    python3 "$KIT/scripts/verify-binary.py" "$STAGED/strfry" --sha256 "$EXPECTED"
else
    [ "$(git -C "$SRC" rev-parse HEAD)" = "$COMMIT" ]
    git -C "$SRC" apply --reverse --check "$KIT/patch/strfry-neighbors.patch"
    [ -x "$SRC/strfry" ]
    install -m 0755 -- "$SRC/strfry" "$STAGED/strfry"
fi

if ! id nostr-relay >/dev/null 2>&1; then
    useradd --system --home-dir /var/lib/strfry --shell /usr/sbin/nologin nostr-relay
fi
install -d -m 0750 -o nostr-relay -g nostr-relay /var/lib/strfry
install -d -m 0700 -o nostr-relay -g nostr-relay /var/lib/strfry/db
install -d -m 0750 -o root -g nostr-relay /etc/strfry
install -d -m 0755 -o root -g root /usr/local/libexec
# Do not strip here: the installed hash must remain the hash the operator verified.
install -m 0755 "$STAGED/strfry" /usr/local/bin/strfry
install -m 0640 -o root -g nostr-relay "$KIT/config/strfry.conf" /etc/strfry/strfry.conf
for helper in strfry-disk-guard strfry-prune-stamp strfry-prune-events strfry-ephemeral-policy strfry-health; do
    install -m 0755 "$KIT/bin/$helper" "/usr/local/libexec/$helper"
done
install -m 0755 "$KIT/scripts/cleanup-smoke-events" /usr/local/libexec/strfry-cleanup-smoke-events
for unit in strfry.service strfry-prune.service strfry-prune.timer strfry-disk-guard.service strfry-disk-guard.timer; do
    install -m 0644 "$KIT/systemd/$unit" "/etc/systemd/system/$unit"
done
install -m 0644 "$KIT/config/journald@strfry.conf" /etc/systemd/journald@strfry.conf

systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/strfry.service /etc/systemd/system/strfry-prune.service /etc/systemd/system/strfry-disk-guard.service
if [ "$START" = 1 ]; then
systemctl enable --now strfry.service
systemctl enable --now strfry-prune.timer strfry-disk-guard.timer
systemctl start strfry-prune.service
/usr/local/libexec/strfry-health
fi
sha256sum /usr/local/bin/strfry
