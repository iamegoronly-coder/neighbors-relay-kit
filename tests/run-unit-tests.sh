#!/bin/sh
# Fast checks that need neither strfry nor network: helper policies and shell syntax.
set -eu
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")/.."
python3 tests/test_health.py
python3 tests/test_prune.py
python3 tests/test_disk_guard.py
python3 tests/test_smoke_cleanup.py
python3 tests/test_pq_tls.py
python3 tests/test_caddy_instructions.py
python3 tests/test_binary_verification.py
python3 tests/test_setup.py
python3 tests/test_setup_languages.py
python3 tests/test_caddy_key.py
python3 tests/test_local_package.py
for script in bin/require-pq-caddy bin/strfry-prune-stamp scripts/*.sh tests/fake-systemctl.sh tests/test_install_container.sh; do
    sh -n "$script"
done
sh -n setup.sh
echo "PASS shell syntax"
