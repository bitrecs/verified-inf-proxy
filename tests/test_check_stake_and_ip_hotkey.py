import os
import time
import json
import httpx
import pytest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from app.main import SignedResponse, check_hotkey_stake, check_request_ip
import app.main

@pytest.mark.asyncio
async def test_stake_and_ip_checks():
    import asyncio

    nodes_snapshot = {}
    for _ in range(60):
        with app.main.metagraph_lock:
            nodes_snapshot = dict(app.main.metagraph_snapshot["nodes"])
        if nodes_snapshot:
            break
        await asyncio.sleep(1)

    assert nodes_snapshot, "Metagraph snapshot has no nodes"

    has_high_stake = False
    test_hotkey = None
    for hotkey, node in nodes_snapshot.items():
        if node.get("stake", 0) > 100:
            has_high_stake = True
            test_hotkey = hotkey
            break

    low_stake_hotkey = None
    for hotkey, node in nodes_snapshot.items():
        if node.get("stake", 0) < 10:
            low_stake_hotkey = hotkey
            break

    if low_stake_hotkey:
        assert not await check_hotkey_stake(low_stake_hotkey, 100)

    if has_high_stake and test_hotkey:
        assert await check_hotkey_stake(test_hotkey, 100)

    test_ip_hotkey = None
    test_ip = None
    for hotkey, node in nodes_snapshot.items():
        ip = node.get("ip")
        if ip:
            test_ip_hotkey = hotkey
            test_ip = ip
            break

    if test_ip_hotkey and test_ip:
        assert await check_request_ip(test_ip_hotkey, test_ip)
        assert not await check_request_ip(test_ip_hotkey, "1.2.3.4")


