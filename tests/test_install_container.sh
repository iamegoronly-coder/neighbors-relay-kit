#!/bin/sh
# Run ONLY in a fresh disposable Ubuntu Docker container, with the kit at /kit and binary at /artifact/strfry.
# This checks real file installation. Caddy, systemd and health are explicit test doubles;
# it does not claim a real systemd boot or a network health check.
set -eu
[ "${NEIGHBORS_INSTALL_TEST:-}" = 1 ] && [ -f /.dockerenv ] && [ "$(id -u)" = 0 ]
[ ! -e /etc/systemd/system/strfry.service ]
cp -a /kit /tmp/install-kit
mkdir -p /usr/local/bin
cat > /usr/local/bin/caddy <<'STUB'
#!/bin/sh
printf 'v2.11.7\n'
STUB
for tool in systemctl systemd-analyze; do
    cat > "/usr/local/bin/$tool" <<'STUB'
#!/bin/sh
printf '%s\n' "$*" >> /tmp/service-calls.log
STUB
    chmod +x "/usr/local/bin/$tool"
done
chmod +x /usr/local/bin/caddy
printf '#!/bin/sh\nexit 0\n' > /tmp/install-kit/bin/strfry-health
BAD=0000000000000000000000000000000000000000000000000000000000000000
if sh /tmp/install-kit/scripts/install.sh --binary /artifact/strfry --sha256 "$BAD"; then
    echo 'accepted wrong hash' >&2; exit 1
fi
[ ! -e /etc/systemd/system/strfry.service ]
[ ! -e /usr/local/bin/strfry ]
[ ! -e /tmp/service-calls.log ]
HASH=$(sha256sum /artifact/strfry | cut -d ' ' -f 1)
if [ "${NEIGHBORS_INSTALL_NO_START:-0}" = 1 ]; then
    sh /tmp/install-kit/scripts/install.sh --binary /artifact/strfry --sha256 "$HASH" --no-start
    if grep -Eq '^(enable|start) ' /tmp/service-calls.log; then
        echo 'no-start unexpectedly activated services' >&2; exit 1
    fi
else
    sh /tmp/install-kit/scripts/install.sh --binary /artifact/strfry --sha256 "$HASH"
    grep -q '^enable --now strfry.service' /tmp/service-calls.log
fi
cmp /artifact/strfry /usr/local/bin/strfry
cmp /kit/config/strfry.conf /etc/strfry/strfry.conf
cmp /kit/systemd/strfry.service /etc/systemd/system/strfry.service
[ "$(stat -c '%a:%U:%G' /var/lib/strfry/db)" = '700:nostr-relay:nostr-relay' ]
[ "$(stat -c '%a:%U:%G' /etc/strfry/strfry.conf)" = '640:root:nostr-relay' ]
[ "$(stat -c '%a:%U:%G' /usr/local/bin/strfry)" = '755:root:root' ]
[ "$(stat -c '%a:%U:%G' /etc/systemd/system/strfry.service)" = '644:root:root' ]
if sh /tmp/install-kit/scripts/install.sh --binary /artifact/strfry --sha256 "$HASH"; then
    echo 'overwrote existing service' >&2; exit 1
fi
printf 'PASS corrupt binary refused before service/file changes; installed bytes/config/unit preserved; repeat install refused\n'
