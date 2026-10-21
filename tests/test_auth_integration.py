#!/usr/bin/env python3
"""NIP-42 against real strfry and disposable LMDB; no external network or live relay."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
import urllib.request

from coincurve import PrivateKey
from websockets.asyncio.client import connect

KIT = Path(__file__).resolve().parents[1]
SERVICE = 'wss://auth.example.org/relay'


def signed(key, kind, tags, content=''):
    pubkey = key.public_key_xonly.format().hex()
    timestamp = int(time.time())
    event_id = hashlib.sha256(json.dumps([0, pubkey, timestamp, kind, tags, content],
                                        separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    return dict(id=event_id, pubkey=pubkey, created_at=timestamp, kind=kind, tags=tags,
                content=content, sig=key.sign_schnorr(bytes.fromhex(event_id)).hex())


async def receive(ws):
    return json.loads(await asyncio.wait_for(ws.recv(), 4))


async def query(ws, filters):
    sub = secrets.token_hex(6)
    await ws.send(json.dumps(['REQ', sub, *filters]))
    events, challenge, closed = [], None, None
    while True:
        frame = await receive(ws)
        if frame[0] == 'AUTH':
            challenge = frame[1]
        elif frame[:2] == ['EVENT', sub]:
            events.append(frame[2])
        elif frame[:2] == ['CLOSED', sub]:
            closed = frame[2]
            break
        elif frame[:2] == ['EOSE', sub]:
            break
        else:
            raise AssertionError(frame[0])
    await ws.send(json.dumps(['CLOSE', sub]))
    return events, challenge, closed


async def proof(ws, key, challenge, service=SERVICE):
    value = signed(key, 22242, [['relay', service], ['challenge', challenge]])
    await ws.send(json.dumps(['AUTH', value]))
    reply = await receive(ws)
    assert reply[:2] == ['OK', value['id']], reply
    return reply[2], value


async def scenarios(uri, cli):
    options = dict(proxy=None, compression=None, open_timeout=4)
    owner, foreign, sender = PrivateKey(), PrivateKey(), PrivateKey()
    inbox = owner.public_key_xonly.format().hex()
    other_inbox = foreign.public_key_xonly.format().hex()
    mine = signed(sender, 1059, [['p', inbox]], 'test-encrypted-envelope-owner')
    other = signed(sender, 1059, [['p', other_inbox]], 'test-encrypted-envelope-other')
    async with connect(uri, **options) as publisher, connect(uri, **options) as reader:
        # AUTH restricts reads; unauthenticated publication is deliberately still allowed.
        for value in [mine, other]:
            await publisher.send(json.dumps(['EVENT', value]))
            assert (await receive(publisher))[:3] == ['OK', value['id'], True]
        values, challenge, closed = await query(reader, [{'kinds': [1059], '#p': [inbox]}])
        assert not values and challenge and closed and closed.removeprefix('ERROR: ').startswith('auth-required:'), (values, challenge, closed)
        for filters in [[{}], [{'#p': [inbox]}], [{'kinds': [1, 1059]}], [{'kinds': [1]}, {'kinds': [1059]}]]:
            values, _, _ = await query(reader, filters)
            assert not values, 'anonymous read bypassed restricted kind'
        accepted, _ = await proof(reader, owner, 'wrong-challenge')
        assert not accepted
        accepted, _ = await proof(reader, owner, challenge, 'wss://different.example.org/relay')
        assert not accepted
        tampered = signed(owner, 22242, [['relay', SERVICE], ['challenge', challenge]])
        tampered['sig'] = '00' * 64
        await reader.send(json.dumps(['AUTH', tampered]))
        assert (await receive(reader))[:3] == ['OK', tampered['id'], False]
        accepted, auth_event = await proof(reader, owner, challenge)
        assert accepted
        values, _, closed = await query(reader, [{'kinds': [1059], '#p': [inbox]}])
        assert not closed and [v['id'] for v in values] == [mine['id']]
        for filters in [[{'kinds': [1059], '#p': [other_inbox]}], [{}], [{'kinds': [1059], '#p': [inbox, other_inbox]}]]:
            values, _, _ = await query(reader, filters)
            assert all(v['id'] == mine['id'] for v in values), 'authenticated reader saw another inbox'
        assert not subprocess.check_output(cli + ['scan', json.dumps({'ids': [auth_event['id']]})]).strip()
        # The same restriction must also apply to future events, not only stored history.
        await reader.send(json.dumps(['REQ', 'live-own', {'kinds': [1059], '#p': [inbox], 'limit': 0}]))
        assert await receive(reader) == ['EOSE', 'live-own']
        async with connect(uri, **options) as anonymous:
            await anonymous.send(json.dumps(['REQ', 'live-broad', {'limit': 0}]))
            assert await receive(anonymous) == ['EOSE', 'live-broad']
            for recipient in [other_inbox, inbox]:
                value = signed(sender, 1059, [['p', recipient]], 'live-test')
                await publisher.send(json.dumps(['EVENT', value]))
                assert (await receive(publisher))[:3] == ['OK', value['id'], True]
            received = await receive(reader)
            assert received[:2] == ['EVENT', 'live-own'] and received[2]['id'] == value['id']
            try:
                await asyncio.wait_for(anonymous.recv(), .3)
                raise AssertionError('anonymous live subscription leaked a restricted event')
            except asyncio.TimeoutError:
                pass
        await reader.send(json.dumps(['CLOSE', 'live-own']))
        # The valid proof belongs to this connection only, even with the same inbox key.
        async with connect(uri, **options) as fresh:
            _, fresh_challenge, _ = await query(fresh, [{'kinds': [1059], '#p': [inbox]}])
            assert fresh_challenge != challenge
            await fresh.send(json.dumps(['AUTH', auth_event]))
            assert (await receive(fresh))[:3] == ['OK', auth_event['id'], False]
            assert (await proof(fresh, foreign, fresh_challenge))[0]
            values, _, _ = await query(fresh, [{'kinds': [1059], '#p': [inbox]}])
            assert not values
            values, _, _ = await query(fresh, [{'kinds': [1059], '#p': [other_inbox]}])
            assert other['id'] in [v['id'] for v in values] and all(v['tags'] == [['p', other_inbox]] for v in values)
    print('PASS AUTH: anonymous/foreign reads denied, own inbox readable, bad URL/challenge/replayed proof refused; AUTH not stored; writes public')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('setup_relay', KIT / 'scripts/setup-relay.py')
    setup_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup_module)
    setup = setup_module.Setup(); setup.auth = True
    with tempfile.TemporaryDirectory(prefix='strfry-auth-') as folder:
        root = Path(folder); (root / 'db').mkdir()
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
        config = setup.relay_configuration('auth.example.org')
        config = config.replace('/var/lib/strfry/db', str(root / 'db')).replace('port = 7777', f'port = {port}')
        config = config.replace('nofiles = 256', 'nofiles = 0').replace('mapsize = 2147483648', 'mapsize = 67108864')
        config = config.replace('/usr/local/libexec/strfry-ephemeral-policy', str(KIT / 'bin/strfry-ephemeral-policy'))
        path = root / 'strfry.conf'; path.write_text(config)
        cli = [args.binary, '--config', str(path), '--verbosity=WARNING']
        with (root / 'relay.log').open('w+') as log:
            process = subprocess.Popen(cli + ['relay'], stdout=log, stderr=log)
            try:
                for _ in range(80):
                    if process.poll() is not None:
                        log.seek(0); raise RuntimeError(log.read())
                    try:
                        with socket.create_connection(('127.0.0.1', port), timeout=.2): break
                    except OSError: time.sleep(.1)
                else: raise TimeoutError('test relay did not start')
                req = urllib.request.Request(f'http://127.0.0.1:{port}', headers={'Accept': 'application/nostr+json'})
                with urllib.request.urlopen(req, timeout=4) as response:
                    assert 42 in json.load(response)['supported_nips']
                asyncio.run(scenarios(f'ws://127.0.0.1:{port}', cli))
            finally:
                process.terminate(); process.wait(timeout=10)
    print('PASS temporary AUTH database removed; no production service used')


if __name__ == '__main__':
    main()
