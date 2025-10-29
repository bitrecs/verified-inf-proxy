import os
import sys
import pytest
import pathlib
from tests.utils import call_proxy_server_with_signing, get_public_key, verify_proof
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv()
from fiber.chain import chain_utils
from app.llm_providers import LLMProviderStats, LLMProvider

BASE_URL = "http://127.0.0.1:8000"
#BASE_URL = "https//verified.bitrecs.ai"
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")

@pytest.mark.asyncio
async def test_ping_provider():
    ping_result = LLMProviderStats.ping_provider_html(LLMProvider.NVIDIA)
    assert ping_result is not None
    print(f"NVIDIA ping result: {ping_result}")


@pytest.mark.asyncio
async def test_call_nvidia():    
    request = {
        "model": "qwen/qwen3-next-80b-a3b-instruct",
        "messages": [{"role": "user", "content": "Hello, how are you?"}]
    }
    
    wallet_name = os.environ.get("TEST_WALLET_NAME")
    wallet_hotkey = os.environ.get("TEST_WALLET_HOTKEY")
    
    miner_keypair = chain_utils.load_hotkey_keypair(wallet_name, wallet_hotkey)
    assert miner_keypair is not None, "Failed to load miner_keypair"

    public_key = await get_public_key(base_url=BASE_URL)
    response = await call_proxy_server_with_signing(BASE_URL, request, miner_keypair.ss58_address, miner_keypair, "NVIDIA", NVIDIA_API_KEY)
    print(f"Response: {response}")

    assert verify_proof(response, public_key), "Signature verification failed"
    
    assert response is not None
    # assert "response" in response
    # assert "choices" in response["response"]
    # assert len(response["response"]["choices"]) > 0
    # assert "message" in response["response"]["choices"][0]
    # assert "content" in response["response"]["choices"][0]["message"]
    # assert len(response["response"]["choices"][0]["message"]["content"]) > 0

