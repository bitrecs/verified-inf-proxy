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
    # Access the global metagraph - wait for it to sync
    import asyncio
    for i in range(30):  # Wait up to 30 seconds for initial sync
        if app.main.metagraph is not None and len(app.main.metagraph.nodes) > 0:
            break
        await asyncio.sleep(1)
    
    assert app.main.metagraph is not None, "Metagraph failed to initialize"
    assert len(app.main.metagraph.nodes) > 0, "Metagraph has no nodes"
    
    metagraph = app.main.metagraph

    # Test that basic functionality works - find any hotkey with stake > 0
    has_high_stake = False
    test_hotkey = None
    for node in metagraph.nodes:
        if node.stake > 100:
            has_high_stake = True
            test_hotkey = node.hotkey
            break

    # Test low stake hotkey
    low_stake_hotkey = None
    for node in metagraph.nodes:
        if node.stake < 10:
            low_stake_hotkey = node.hotkey
            break

    if low_stake_hotkey:
        # Removed metagraph parameter
        assert(not await check_hotkey_stake(low_stake_hotkey, 100))

    if has_high_stake and test_hotkey:
        # Removed metagraph parameter
        assert(await check_hotkey_stake(test_hotkey, 100))

    # Test IP matching - find a hotkey with valid IP
    test_ip_hotkey = None
    test_ip = None
    for node in metagraph.nodes:
        if node.ip and node.ip != '':
            test_ip_hotkey = node.hotkey
            test_ip = node.ip
            break

    if test_ip_hotkey and test_ip:
        # Removed metagraph parameter
        assert(await check_request_ip(test_ip_hotkey, test_ip))
        assert(not await check_request_ip(test_ip_hotkey, "1.2.3.4"))


