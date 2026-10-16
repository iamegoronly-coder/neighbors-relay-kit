#!/usr/bin/env python3
"""Real, disposable LMDB and loopback relay. Never uses production configuration."""
import argparse
import asyncio
import hashlib
import json
import secrets
import socket
import subprocess
import tempfile
import time
import sys
from pathlib import Path
from contextlib import AsyncExitStack
import urllib.request

from coincurve import PrivateKey
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus


def event(kind=1, tags=None, content="integration-test", created_at=None):
    key = PrivateKey()
    pubkey = key.public_key_xonly.format().hex()
    timestamp = int(time.time()) if created_at is None else created_at
    tags = tags or []
    payload = [0, pubkey, timestamp, kind, tags, content]
    event_id = hashlib.sha256(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    return dict(id=event_id, pubkey=pubkey, created_at=timestamp, kind=kind, tags=tags,
                content=content, sig=key.sign_schnorr(bytes.fromhex(event_id)).hex())


async def message(ws):
    return json.loads(await asyncio.wait_for(ws.recv(), 4))


async def publish(ws, ev):
    await ws.send(json.dumps(["EVENT", ev]))
    response = await message(ws)
    assert response[:3] == ["OK", ev["id"], True], response[:3]


async def query(ws, filt):
    sub = secrets.token_hex(8)
    await ws.send(json.dumps(["REQ", sub, filt]))
    result = []
    while True:
        response = await message(ws)
        if response[:2] == ["EOSE", sub]:
            break
        assert response[:2] == ["EVENT", sub], response[:2]
        result.append(response[2]["id"])
    await ws.send(json.dumps(["CLOSE", sub]))
    return result


async def scenarios(uri, cli, capacity, through_caddy):
    options = dict(proxy=None, compression=None, open_timeout=4)
    async with connect(uri, **options) as pub, connect(uri, **options) as reader:
        # Hold all slots; test rejection and unrelated HTTP availability through Caddy.
        async with AsyncExitStack() as extra:
            for _ in range(capacity - 2):
                peer = await extra.enter_async_context(connect(uri, **options))
                assert await query(peer, {"ids": ["00" * 32]}) == []
            try:
                async with connect(uri, **options) as excess:
                    try:
                        await message(excess)
                        raise AssertionError("connection above configured limit was accepted")
                    except ConnectionClosed as closed:
                        assert closed.rcvd is not None and closed.rcvd.code == 1013, closed
            except InvalidStatus as rejected:
                assert through_caddy and rejected.response.status_code == 503
            if through_caddy:
                with urllib.request.urlopen(uri.replace("ws://", "http://") + "/site", timeout=3) as page:
                    assert page.status == 200 and page.read() == b"site-ok"
        assert await query(reader, {"ids": ["00" * 32]}) == []
        print(f"PASS limit={capacity}; excess refused; accepted peers survive; caddy={through_caddy}", flush=True)

        live = event(created_at=int(time.time()) - 10)
        deadline = int(time.time()) + 3
        expiring = event(tags=[["expiration", str(deadline)]])
        await publish(pub, live)
        await publish(pub, expiring)
        assert await query(reader, {"kinds": [1], "limit": 1}) == [expiring["id"]]
        await asyncio.sleep(max(0, deadline - time.time()) + 0.1)
        assert await query(reader, {"ids": [expiring["id"]]}) == []
        # Expired candidates must not consume limit and hide the valid older event.
        assert await query(reader, {"kinds": [1], "limit": 1}) == [live["id"]]
        print("PASS expiration at read time and limit=1 backfill", flush=True)

        # Keep a live subscription open across deletion of all retained records.
        await reader.send(json.dumps(["REQ", "live", {"kinds": [1401]}]))
        assert await message(reader) == ["EOSE", "live"]
        for index in range(3):
            drop = event(kind=1401)
            await publish(pub, drop)
            received = await message(reader)
            assert received[:2] == ["EVENT", "live"] and received[2]["id"] == drop["id"]
            await asyncio.sleep(1.1)
            subprocess.run([sys.executable, str(Path(__file__).resolve().parent.parent / "bin" / "strfry-prune-events"),
                            "--binary", cli[0], "--config", cli[2], "--age-seconds", "1"],
                           check=True, stdout=subprocess.DEVNULL)
            assert subprocess.check_output(cli + ["scan", "{}"]).strip() == b""
            await asyncio.sleep(0.2)
        await reader.send(json.dumps(["CLOSE", "live"]))
        print("PASS live delivery across three complete DB deletions", flush=True)

    # Closing accepted peers frees a slot.
    async with connect(uri, **options) as replacement:
        assert await query(replacement, {"ids": ["00" * 32]}) == []
        await replacement.send("[")
        try:
            response = await message(replacement)
            assert response[0] in ("NOTICE", "CLOSED"), response[0]
        except ConnectionClosed:
            pass
    async with connect(uri, **options) as healthy:
        assert await query(healthy, {"ids": ["00" * 32]}) == []
    print("PASS slots reusable, malformed JSON refused, independent client healthy", flush=True)

    if capacity == 2 and not through_caddy:
        async with connect(uri, **options) as pub:
            marker = secrets.token_hex(8)
            for _ in range(160):
                await publish(pub, event(tags=[["t", marker]], content="x" * 60000))
            raw = socket.socket()
            raw.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
            raw.setblocking(False)
            port = int(uri.rsplit(":", 1)[1])
            await asyncio.get_running_loop().sock_connect(raw, ("127.0.0.1", port))
            async with connect(uri, sock=raw, max_queue=1, close_timeout=1, **options) as slow:
                await slow.send(json.dumps(["REQ", "slow", {"#t": [marker], "limit": 500}]))
                deadline = time.monotonic() + 15
                while True:
                    await asyncio.sleep(.3)
                    try:
                        async with connect(uri, **options) as probe:
                            assert await query(probe, {"ids": ["00" * 32]}) == []
                        break
                    except ConnectionClosed as closed:
                        assert closed.rcvd is not None and closed.rcvd.code == 1013
                        assert time.monotonic() < deadline, "slow reader never released its slot"
            assert await query(pub, {"ids": ["00" * 32]}) == []
        print("PASS slow reader is dropped; other client remains responsive", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--capacity", type=int, default=2)
    parser.add_argument("--caddy", action="store_true")
    args = parser.parse_args()
    assert 2 <= args.capacity <= 100
    with tempfile.TemporaryDirectory(prefix="strfry-integration-") as temp:
        root = Path(temp)
        (root / "db").mkdir()
        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            port = reserve.getsockname()[1]
        config = root / "strfry.conf"
        config.write_text(f'''db = "{root / 'db'}"
dbParams {{ mapsize = 67108864 }}
events {{ rejectEventsNewerThanSeconds = 1200 }}
relay {{
    bind = "127.0.0.1"
    port = {port}
    nofiles = 0
    maxConnections = {args.capacity}
    auth {{
        enabled = false
        restrictedReadKinds = ""
        restrictReadToInvolvedPubkey = false
    }}
    negentropy {{ enabled = false }}
    compression {{ enabled = false }}
    maxPendingOutboundBytes = 1048576
}}
''')
        cli = [args.binary, "--config", str(config), "--verbosity=WARNING"]
        with (root / "relay.log").open("w+") as log:
            relay = subprocess.Popen(cli + ["relay"], stdout=log, stderr=log)
            proxy = None
            try:
                for _ in range(80):
                    if relay.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(log.read())
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=.2):
                            break
                    except OSError:
                        time.sleep(.1)
                else:
                    raise TimeoutError("test relay did not start")
                client_port = port
                if args.caddy:
                    with socket.socket() as reserve:
                        reserve.bind(("127.0.0.1", 0))
                        client_port = reserve.getsockname()[1]
                    proxy_config = root / "Caddyfile"
                    proxy_config.write_text(f'''{{
    admin off
    auto_https off
}}
http://127.0.0.1:{client_port} {{
    handle /site {{
        respond "site-ok"
    }}
    handle {{
        reverse_proxy 127.0.0.1:{port} {{
            fail_duration 10s
            max_fails 3
            unhealthy_request_count {args.capacity}
        }}
    }}
}}
''')
                    proxy = subprocess.Popen(["caddy", "run", "--config", str(proxy_config)], stdout=log, stderr=log)
                    for _ in range(50):
                        try:
                            with socket.create_connection(("127.0.0.1", client_port), timeout=.2):
                                break
                        except OSError:
                            time.sleep(.1)
                    else:
                        raise TimeoutError("isolated Caddy did not start")
                asyncio.run(scenarios(f"ws://127.0.0.1:{client_port}", cli, args.capacity, args.caddy))
            finally:
                if proxy is not None:
                    proxy.terminate()
                    proxy.wait(timeout=10)
                relay.terminate()
                relay.wait(timeout=10)
    print("PASS disposable LMDB removed; production was not used")


if __name__ == "__main__":
    main()
