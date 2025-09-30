import os
import time
import json
import httpx
import pytest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from app.main import SignedResponse, get_metagraph_data, check_hotkey_stake, check_request_ip

@pytest.mark.asyncio
async def test_stake_and_ip_checks():
    metagraph = await get_metagraph_data()

    # Test that basic functionality works - find any hotkey with stake > 0
    has_high_stake = False
    test_hotkey = None
    for neuron in metagraph['uids']:
        if neuron['stake'] > 100:
            has_high_stake = True
            test_hotkey = neuron['hotkey']
            break

    # Test low stake hotkey
    low_stake_hotkey = None
    for neuron in metagraph['uids']:
        if neuron['stake'] < 10:
            low_stake_hotkey = neuron['hotkey']
            break

    if low_stake_hotkey:
        assert(not await check_hotkey_stake(metagraph, low_stake_hotkey, 100))

    if has_high_stake and test_hotkey:
        assert(await check_hotkey_stake(metagraph, test_hotkey, 100))

    # Test IP matching - find a hotkey with valid IP
    test_ip_hotkey = None
    test_ip = None
    for neuron in metagraph['uids']:
        if neuron['axon_ip'] and neuron['axon_ip'] != '':
            test_ip_hotkey = neuron['hotkey']
            test_ip = neuron['axon_ip']
            break

    if test_ip_hotkey and test_ip:
        assert(await check_request_ip(metagraph, test_ip_hotkey, test_ip))
        assert(not await check_request_ip(metagraph, test_ip_hotkey, "1.2.3.4"))


