# Caddy with post-quantum TLS

[English](caddy.md) · [Русский](caddy.ru.md) · [Deutsch](caddy.de.md)

Caddy 2.10 and later (built with Go 1.24+) offer the hybrid TLS 1.3 key exchange
`X25519MLKEM768` by default, alongside classic X25519. Ubuntu 24.04's own `caddy` package is 2.6.2
and does not, so this kit uses the official Caddy repository on Cloudsmith.

Do **not** add a `curves` directive: the default already prefers the hybrid, and an explicit list
is easy to get wrong (for example, dropping what older clients need).

## New server

Run from the root of this reviewed repository. The complete primary-key fingerprint is pinned
in `scripts/verify-caddy-key.py`:
`65760C51EDEA2017CEA2CA15155B6D79CA56EA34`.
It was checked against [Caddy's official repository metadata](https://cloudsmith.io/~caddy/repos/stable/packages/).
A different, expired, revoked, malformed or additional primary key stops setup before trust is installed.
On key rotation, independently verify the new key and review a kit update; never bypass this check
or obtain the expected fingerprint from the same download you are checking.

```sh
(
  set -eu
  apt-get install -y python3 debian-keyring debian-archive-keyring apt-transport-https curl gnupg
  KEY_WORK=$(mktemp -d)
  trap 'rm -rf "$KEY_WORK"' EXIT HUP INT TERM
  curl --proto '=https' --proto-redir '=https' --tlsv1.2 -fLsS --max-time 60 \
    'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' -o "$KEY_WORK/caddy.key"
  python3 scripts/verify-caddy-key.py "$KEY_WORK/caddy.key"
  gpg --batch --yes --dearmor --output "$KEY_WORK/caddy.gpg" "$KEY_WORK/caddy.key"
  install -m 644 "$KEY_WORK/caddy.gpg" /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  printf '%s\n' 'deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main' \
    > /etc/apt/sources.list.d/caddy-stable.list
  chmod 644 /etc/apt/sources.list.d/caddy-stable.list
  apt-get update
  apt-cache policy caddy
)
```

`Candidate` must come from `dl.cloudsmith.io` and be 2.10 or newer. Install that exact version and
hold it, so upgrades stay deliberate:

```sh
V=2.11.7                      # replace with the exact Candidate version if it is newer
apt-get install -y "caddy=$V"
apt-mark hold caddy
caddy version
sh bin/require-pq-caddy       # from this kit
```

Then configure the site from `config/Caddyfile.example` (README, step 4).

## Upgrading

For a server already running an older Caddy in front of the relay. Takes 15–20 minutes. Open
WebSockets drop for a few seconds when Caddy restarts; clients reconnect, and stored events are not
affected (strfry keeps running). If you run several relays, upgrade one at a time.

Shell variables below live only in the current SSH session; set them again after reconnecting.
Run each block only after the preceding block succeeds. Stop on failure; do not continue to a restart.

### 1. Back up (server)

```sh
BK=/root/caddy-before-upgrade-$(date -u +%Y%m%dT%H%M%SZ); mkdir -m 700 "$BK"
caddy version | tee "$BK/version.txt"; dpkg -l caddy | tail -1 | tee -a "$BK/version.txt"
cp -a "$(command -v caddy)" "$BK/caddy"
cp -a /etc/caddy "$BK/etc-caddy"
OLD_VERSION=$(dpkg-query -W -f='${Version}' caddy)
printf '%s\n' "$OLD_VERSION" > "$BK/package-version"
mkdir -m 700 "$BK/package"
(
    set -eu
    cd "$BK/package"
    apt-get download "caddy=$OLD_VERSION"
    set -- ./caddy_*.deb
    [ "$#" -eq 1 ] && [ -f "$1" ]
    [ "$(dpkg-deb -f "$1" Package)" = caddy ]
    [ "$(dpkg-deb -f "$1" Version)" = "$OLD_VERSION" ]
    sha256sum "$1" > SHA256SUMS
)
ls -la /var/lib/caddy/.local/share/caddy/certificates/*/ | tee "$BK/certs.txt"
/usr/local/libexec/strfry-health
```

Do not upgrade unless the exact installed `.deb` has been saved and verified. If its version is
no longer downloadable, recover that exact package from your trusted package cache/archive and
perform the same Package/Version/checksum checks; do not substitute the current candidate.
The saved executable alone is an emergency fallback, not a complete package rollback.

If the same Caddy also serves a website, record a fingerprint of a page to compare afterwards:
`curl -fsS https://your.domain/ | sha256sum | tee "$BK/site.sha256"`.

### 2. Add the repository

As in [New server](#new-server), up to `apt-cache policy caddy`, then set `V` to the exact
`Candidate` version (2.10+).

### 3. Validate the current Caddyfile with the new binary — before installing

Installing the package restarts Caddy, so the configuration is checked first with an unpacked copy
(certificates and live data are not touched):

```sh
(
    set -eu
    T=$(mktemp -d)
    trap 'rm -rf "$T"' 0
    cd "$T"
    apt-get download "caddy=$V"
    dpkg-deb -x caddy_*.deb x
    ./x/usr/bin/caddy version
    XDG_DATA_HOME="$T/data" XDG_CONFIG_HOME="$T/config" \
      ./x/usr/bin/caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
)
```

Expect `Valid configuration`. Warnings such as "input is not formatted" are cosmetic — do not run
`caddy fmt --overwrite`, it would rewrite the file. Stop on any error.

### 4. Install

`--force-confold` keeps your `/etc/caddy/Caddyfile` instead of the packaged default.

```sh
(
    set -eu
    # Reapply this kit's hold policy on success AND if apt fails.
    trap 'apt-mark hold caddy' 0
    apt-mark unhold caddy
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
      -o Dpkg::Options::=--force-confold -o Dpkg::Options::=--force-confdef "caddy=$V"
    cmp /etc/caddy/Caddyfile "$BK/etc-caddy/Caddyfile"
    echo "Caddyfile unchanged"
    systemctl restart caddy
    sleep 3
    systemctl is-active caddy
    journalctl -u caddy --since '2 min ago' --no-pager | grep -E '"level":"(error|warn)"|obtaining' | tail -20
)
```

An unexpected certificate issuance attempt for a domain with a valid certificate warrants checking
storage paths and permissions before proceeding; the log line alone does not prove storage loss.

### 5. Verify

On the server: `/usr/local/libexec/strfry-health`, the NIP-11 `curl`, `/metrics` → 404, and the
site fingerprint if you recorded one. From a machine with OpenSSL 3.5+:

```sh
sh scripts/check-pq-tls.sh your.domain
```

### Rollback to the exact saved package

Set `BK` to the backup directory from step 1. Keep the Cloudsmith repository configured. This
procedure restores the saved version, not the distribution candidate. It also reapplies the hold
if installation fails. The package manager may restart Caddy, so restore and validate the saved
configuration first. Existing certificate storage is not replaced.

```sh
(
    set -eu
    cd "$BK/package"
    sha256sum -c SHA256SUMS
    set -- ./caddy_*.deb
    [ "$#" -eq 1 ] && [ -f "$1" ]
    [ "$(dpkg-deb -f "$1" Package)" = caddy ]
    [ "$(dpkg-deb -f "$1" Version)" = "$(cat "$BK/package-version")" ]
    CHECK_DIR=$(mktemp -d)
    trap 'rm -rf "$CHECK_DIR"' 0
    cp -a "$BK/etc-caddy/." /etc/caddy/
    XDG_DATA_HOME="$CHECK_DIR/data" XDG_CONFIG_HOME="$CHECK_DIR/config" \
      "$BK/caddy" validate --config /etc/caddy/Caddyfile --adapter caddyfile
    trap 'apt-mark hold caddy; rm -rf "$CHECK_DIR"' 0
    apt-mark unhold caddy
    DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades \
      -o Dpkg::Options::=--force-confold -o Dpkg::Options::=--force-confdef "$PWD/${1#./}"
    [ "$(dpkg-query -W -f='${Version}' caddy)" = "$(cat "$BK/package-version")" ]
    caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
    systemctl restart caddy
    systemctl is-active caddy
)
```

Repeat the relay/site and external TLS checks after rollback. If the previous version predates
hybrid TLS, restoring it also restores that limitation; report the hybrid check as failed.

### Emergency binary fallback

If restoring the saved package is impossible, temporarily restore the saved executable:
`systemctl stop caddy && cp -a "$BK/caddy" /usr/bin/caddy && systemctl start caddy`.
This does not restore package-manager state; reconcile it with the saved package before the next
upgrade. Do not silently substitute Ubuntu's older Caddy: it can remove post-quantum TLS support.
strfry, its database, timers and firewall are not part of this procedure.
