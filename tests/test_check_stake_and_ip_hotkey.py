import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
import app.main
from app.main import check_hotkey_stake, check_request_ip


@pytest.mark.asyncio
async def test_stake_and_ip_checks():
    import asyncio

    # Start the manager (simulates lifespan startup)
    app.main.metagraph_manager.start()

    nodes_snapshot = {}
    for _ in range(60):
        # Fetch from manager's queue and update metagraph_snapshot (simulates restart_manager)
        snapshot, _ = app.main.metagraph_manager.get_snapshot()
        app.main.metagraph_snapshot["nodes"] = snapshot

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

    # Optional: Stop the manager after test
    app.main.metagraph_manager.stop()


