import os
import pytest
import pathlib
import sys
from tests.utils import call_proxy_server_with_signing, get_public_key, verify_signature
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from fiber.chain import chain_utils
load_dotenv()


BASE_URL = "http://127.0.0.1:8000"
#BASE_URL = "https//verified.bitrecs.ai"
GROK_API_KEY = os.environ.get("GROK_API_KEY")


@pytest.mark.asyncio
async def test_call_grok():    
    request = {
        "model": "grok-4-fast-non-reasoning",
        "messages": [{"role": "user", "content": "Hello, how are you?"}]
    }
    
    wallet_name = os.environ.get("TEST_WALLET_NAME")
    wallet_hotkey = os.environ.get("TEST_WALLET_HOTKEY")
    
    miner_keypair = chain_utils.load_hotkey_keypair(wallet_name, wallet_hotkey)
    assert miner_keypair is not None, "Failed to load miner_keypair"

    public_key = await get_public_key(base_url=BASE_URL)
    response = await call_proxy_server_with_signing(BASE_URL, request, miner_keypair.ss58_address, miner_keypair, "GROK", GROK_API_KEY)
    print(f"Response: {response}")

    assert verify_signature(response, public_key), "Signature verification failed"
    
    assert response is not None
    assert "response" in response
    assert "choices" in response["response"]
    assert len(response["response"]["choices"]) > 0
    assert "message" in response["response"]["choices"][0]
    assert "content" in response["response"]["choices"][0]["message"]
    assert len(response["response"]["choices"][0]["message"]["content"]) > 0

