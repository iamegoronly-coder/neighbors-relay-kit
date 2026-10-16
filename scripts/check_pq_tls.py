#!/usr/bin/env python3
"""Verify TLS 1.3 hybrid/classic exchange, certificate trust and DNS identity."""
import argparse
import math
import os
import re
import subprocess
import sys


def probe(openssl, host, group, timeout):
    command = [openssl, "s_client", "-connect", f"{host}:443", "-servername", host,
               "-verify_hostname", host, "-groups", group, "-tls1_3", "-verify_return_error"]
    try:
        result = subprocess.run(command, input="", text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "handshake timed out"
    except OSError as error:
        return False, str(error)
    output = result.stdout + result.stderr
    if result.returncode != 0:
        return False, f"OpenSSL failed (exit {result.returncode}); check certificate, hostname and TLS support"
    if not re.search(r"^Verification: OK\s*$", output, re.MULTILINE):
        return False, "certificate verification was not confirmed"
    negotiated = re.search(rf"^Negotiated TLS1\.3 group: {re.escape(group)}\s*$", output, re.MULTILINE)
    if group == "X25519":
        negotiated = negotiated or re.search(r"^Peer Temp Key: X25519(?:,|\s*$)", output, re.MULTILINE)
    if not negotiated:
        return False, "requested TLS 1.3 group was not negotiated"
    return True, "certificate and hostname verified"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=15, help="seconds per OpenSSL process (default: 15)")
    parser.add_argument("hosts", nargs="+", help="DNS names, without scheme, port or path")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")
    for host in args.hosts:
        if len(host) > 253 or any(not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                                 for label in host.split(".")):
            parser.error("use DNS hostnames only (international names must use punycode)")
    openssl = os.environ.get("OPENSSL", "openssl")
    try:
        support = subprocess.run([openssl, "list", "-kem-algorithms"], capture_output=True,
                                 text=True, timeout=args.timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"check-pq-tls: cannot run OpenSSL: {error}", file=sys.stderr)
        return 2
    if support.returncode != 0 or "ML-KEM" not in support.stdout.upper():
        print("check-pq-tls: OpenSSL 3.5+ with ML-KEM is required; set OPENSSL to its executable path", file=sys.stderr)
        return 2
    status = 0
    for host in args.hosts:
        for group in ("X25519MLKEM768", "X25519"):
            ok, detail = probe(openssl, host, group, args.timeout)
            print(f"{'PASS' if ok else 'FAIL'} {host} {group}: {detail}")
            if not ok:
                status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
