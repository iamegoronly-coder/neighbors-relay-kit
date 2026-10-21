#!/usr/bin/env python3
"""External WSS/NIP-01 acceptance test against a deployed relay.

Uses disposable keys and synthetic events whose content starts with "relay-smoke-".
They expire with the relay's 48-hour history; remove them sooner on the server with
scripts/cleanup-smoke-events with the manifest from this run (dry run first).
The manifest records attempted IDs before transmission, even if an ACK is lost.

    RELAY_HOST=relay.example.org python3 tests/smoke_test.py initial --manifest /tmp/relay-smoke-run.jsonl
"""

import argparse
import asyncio
import hashlib
import http.client
import json
import os
import secrets
import socket
import ssl
import time
from contextlib import asynccontextmanager
from email.utils import parsedate_to_datetime

from smoke_manifest import SmokeManifest

from coincurve import PrivateKey
from websockets import connect

# Target relay: RELAY_HOST is required. RELAY_IP optionally pins the address (TLS still
# verifies RELAY_HOST), useful before DNS changes propagate. RELAY_PATH defaults to /relay.
MANIFEST = None
HOST = os.environ.get("RELAY_HOST", "")
DIRECT_IP = os.environ.get("RELAY_IP") or None
PATH = os.environ.get("RELAY_PATH", "/relay")
RELAY = f"wss://{HOST}{PATH}"
WS_OPTIONS = {
    "proxy": None,
    "compression": None,
    "max_size": 131072,
    "open_timeout": 20,
}
if DIRECT_IP:
    WS_OPTIONS |= {"host": DIRECT_IP, "port": 443, "server_hostname": HOST}


def relay_info():
    """NIP-11 document and the relay's clock (HTTP Date), optionally via RELAY_IP."""
    connection = http.client.HTTPSConnection(HOST, timeout=10)
    if DIRECT_IP:
        connection.connect = lambda: setattr(
            connection,
            "sock",
            ssl.create_default_context().wrap_socket(
                socket.create_connection((DIRECT_IP, 443), timeout=10),
                server_hostname=HOST,
            ),
        )
    try:
        connection.request("GET", PATH, headers={"Accept": "application/nostr+json"})
        response = connection.getresponse()
        assert response.status == 200, response.status
        return json.loads(response.read()), int(parsedate_to_datetime(response.getheader("Date")).timestamp())
    finally:
        connection.close()


@asynccontextmanager
async def connected():
    """Retry a transient network handshake without repeating any publication."""
    for attempt in range(3):
        try:
            ws = await connect(RELAY, **WS_OPTIONS)
            break
        except (TimeoutError, OSError):
            if attempt == 2:
                raise
            await asyncio.sleep(2)
    try:
        yield ws
    finally:
        await ws.close()


def make_event(key, kind, tags, content, created_at=None):
    pubkey = key.public_key_xonly.format().hex()
    created_at = int(time.time()) if created_at is None else created_at
    canonical = json.dumps(
        [0, pubkey, created_at, kind, tags, content],
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    event_id = hashlib.sha256(canonical).hexdigest()
    return {
        "id": event_id,
        "pubkey": pubkey,
        "created_at": created_at,
        "kind": kind,
        "tags": tags,
        "content": content,
        "sig": key.sign_schnorr(bytes.fromhex(event_id)).hex(),
    }


async def wait_type(ws, verb, sub=None, timeout=8):
    async with asyncio.timeout(timeout):
        while True:
            message = json.loads(await ws.recv())
            if message[0] == verb and (sub is None or message[1] == sub):
                return message


async def publish(ws, event):
    if MANIFEST is None:
        raise RuntimeError("a durable manifest is required before publication")
    MANIFEST.record(event)
    await ws.send(json.dumps(["EVENT", event], separators=(",", ":")))
    response = await wait_type(ws, "OK")
    assert response[1] == event["id"], response
    return response


async def query(ws, filters):
    sub = secrets.token_hex(5)
    await ws.send(json.dumps(["REQ", sub, *filters], separators=(",", ":")))
    events = []
    async with asyncio.timeout(10):
        while True:
            msg = json.loads(await ws.recv())
            if msg[0] == "EVENT" and msg[1] == sub:
                events.append(msg[2])
            if msg[0] == "EOSE" and msg[1] == sub:
                break
    await ws.send(json.dumps(["CLOSE", sub]))
    return events


async def initial():
    nip11, server_now = relay_info()
    assert nip11["limitation"]["max_message_length"] == 131072
    assert nip11["limitation"]["max_subscriptions"] == 20
    assert 42 not in nip11["supported_nips"]
    assert 40 in nip11["supported_nips"]

    first, second = PrivateKey(), PrivateKey()
    ptag = secrets.token_hex(32)
    xtag, gtag, rtag = (f"test-{secrets.token_hex(7)}" for _ in range(3))
    token = f"relay-smoke-{secrets.token_hex(6)}"
    now = server_now
    ev1059 = make_event(first, 1059, [["p", ptag]], token + "-1059", now)
    ev1401 = make_event(second, 1401, [["x", xtag]], token + "-1401", now)
    ev20000 = make_event(first, 20000, [["g", gtag], ["r", rtag]], token + "-20000", now)
    ev20001 = make_event(second, 20001, [["g", gtag], ["r", rtag]], token + "-20001", now)

    # Independent consumer is online before the first publication.
    async with connected() as publisher:
        async with connected() as receiver:
            await receiver.send(json.dumps(["REQ", "live", {"#p": [ptag], "kinds": [1059]}]))
            await wait_type(receiver, "EOSE", "live")
            assert (await publish(publisher, ev1059))[2] is True
            live = await wait_type(receiver, "EVENT", "live")
            assert live[2]["id"] == ev1059["id"]
            await receiver.send(json.dumps(["CLOSE", "live"]))

        # Receiver is disconnected here. Events must be replayed on reconnect.
        for event in (ev1401, ev20000, ev20001):
            assert (await publish(publisher, event))[2] is True
        assert (await publish(publisher, ev1059))[1] == ev1059["id"]

        async with connected() as reader:
            await remaining_tests(
                publisher, reader, server_now, now, first, second,
                ptag, xtag, gtag, rtag, token, ev1059, ev1401, ev20000, ev20001, nip11
            )


async def remaining_tests(publisher, reader, server_now, now, first, second,
                          ptag, xtag, gtag, rtag, token, ev1059, ev1401,
                          ev20000, ev20001, nip11):
    for filt, expected in (
        ({"#p": [ptag], "kinds": [1059]}, ev1059),
        ({"#x": [xtag], "kinds": [1401]}, ev1401),
        ({"#g": [gtag], "kinds": [20000]}, ev20000),
        ({"#r": [rtag], "kinds": [20001]}, ev20001),
        ({"ids": [ev1059["id"]]}, ev1059),
        ({"authors": [ev1401["pubkey"]], "kinds": [1401]}, ev1401),
        ({"since": now - 5, "until": now + 5, "kinds": [1059], "limit": 1}, ev1059),
    ):
        events = await query(reader, [filt])
        assert [item["id"] for item in events] == [expected["id"]], (filt, events)
    assert await query(reader, [{"#p": ["ff" * 32], "kinds": [1059]}]) == []

    unsigned = make_event(first, 1, [], token + "-badsig")
    badsig = dict(unsigned, sig="00" * 64)
    assert (await publish(publisher, badsig))[2] is False
    old = make_event(first, 1, [], token + "-old", now - 172900)
    assert (await publish(publisher, old))[2] is False
    future = make_event(first, 1, [], token + "-future", now + 1300)
    assert (await publish(publisher, future))[2] is False
    oversized = make_event(first, 1, [], "x" * 70000)
    assert (await publish(publisher, oversized))[2] is False

    expired = make_event(
        first, 1, [["expiration", str(server_now - 120)]], token + "-expired", server_now
    )
    assert (await publish(publisher, expired))[2] is False
    _, expiry_base = relay_info()
    expiration = expiry_base + 15
    near = make_event(first, 1, [["expiration", str(expiration)]], token + "-expires", expiry_base)
    assert (await publish(publisher, near))[2] is True
    assert len(await query(reader, [{"ids": [near["id"]]}])) == 1
    await asyncio.sleep(17)
    assert await query(reader, [{"ids": [near["id"]]}]) == [], "expired NIP-40 event was served"

    # Malformed JSON is checked on an isolated WebSocket, which may be closed.
    from websockets.exceptions import ConnectionClosed
    async with connected() as ws:
        try:
            await ws.send("[")
            reply = json.loads(await asyncio.wait_for(ws.recv(), 5))
            assert reply[0] in ("NOTICE", "CLOSED"), reply[0]
        except ConnectionClosed:
            pass
    assert await query(reader, [{"ids": [ev1059["id"]]}]) == [ev1059]

    print(json.dumps({
        "status": "PASS",
        "kinds": [1059, 1401, 20000, 20001],
        "replay_ids": [ev1059["id"], ev1401["id"]],
        "test_authors": [ev1059["pubkey"], ev1401["pubkey"]],
        "ephemeral_ids": [ev20000["id"], ev20001["id"]],
        "nip11": nip11,
    }, sort_keys=True))


async def replay(ids):
    async with connected() as reader:
        for event_id in ids:
            events = await query(reader, [{"ids": [event_id]}])
            assert [ev["id"] for ev in events] == [event_id], events
    print(json.dumps({"status": "PASS", "replayed_after_restart": ids}))


async def absent(ids):
    async with connected() as reader:
        for event_id in ids:
            events = await query(reader, [{"ids": [event_id]}])
            assert events == [], events
    print(json.dumps({"status": "PASS", "absent_ids": ids}))


async def policy():
    _, now = relay_info()
    key = PrivateKey()
    normal = make_event(key, 1059, [["p", secrets.token_hex(32)]],
                        "relay-smoke-future-normal", now + 900)
    too_future = make_event(key, 20000, [["g", "relay-smoke-test"]],
                            "relay-smoke-future-ephemeral", now + 65)
    present = make_event(key, 20001, [["g", "relay-smoke-test"]],
                         "relay-smoke-present", now)
    async with connected() as publisher:
        async with connected() as reader:
            assert (await publish(publisher, normal))[2] is True
            assert (await publish(publisher, too_future))[2] is False
            assert (await publish(publisher, present))[2] is True
            assert len(await query(reader, [{"ids": [present["id"]]}])) == 1
            started = time.monotonic()
            # Bound the whole wait, including a slow query, not just polling intervals.
            async with asyncio.timeout(180):
                while await query(reader, [{"ids": [present["id"]]}]):
                    await asyncio.sleep(5)
    print(json.dumps({
        "status": "PASS",
        "future_normal_accepted": True,
        "future_ephemeral_rejected": True,
        "ephemeral_absent_after_seconds": round(time.monotonic() - started, 1),
        "test_author": key.public_key_xonly.format().hex(),
        "normal_id": normal["id"],
    }, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("initial", "replay", "absent", "policy"))
    parser.add_argument("ids", nargs="*")
    parser.add_argument("--manifest", help="new output file, required for initial/policy; never overwritten")
    args = parser.parse_args()
    if not HOST:
        parser.error("set RELAY_HOST to the relay's domain, e.g. RELAY_HOST=relay.example.org")
    action = {"initial": initial, "replay": replay, "absent": absent, "policy": policy}[args.mode]
    if args.mode in ("initial", "policy"):
        if not args.manifest:
            parser.error("--manifest is required for publishing tests")
        MANIFEST = SmokeManifest(args.manifest, RELAY)
    try:
        asyncio.run(action() if args.mode in ("initial", "policy") else action(args.ids))
    finally:
        if MANIFEST is not None:
            MANIFEST.close()
