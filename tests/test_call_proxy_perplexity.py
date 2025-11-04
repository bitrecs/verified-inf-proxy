import os
import pytest
import pathlib
import sys
from tests.utils import call_proxy_server_with_signing, get_public_key, verify_proof
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from fiber.chain import chain_utils
load_dotenv()


BASE_URL = "http://127.0.0.1:8000"
#BASE_URL = "https//verified.bitrecs.ai"
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")


@pytest.mark.asyncio
async def test_call_perplexity():    
    request = {
        "model": "sonar",
        "messages": [{"role": "user", "content": "What is 1+1?"}]
    }
    
    wallet_name = os.environ.get("TEST_WALLET_NAME")
    wallet_hotkey = os.environ.get("TEST_WALLET_HOTKEY")
    
    miner_keypair = chain_utils.load_hotkey_keypair(wallet_name, wallet_hotkey)
    assert miner_keypair is not None, "Failed to load miner_keypair"

    public_key = await get_public_key(base_url=BASE_URL)
    response = await call_proxy_server_with_signing(BASE_URL, request, miner_keypair.ss58_address, miner_keypair, "PERPLEXITY", PERPLEXITY_API_KEY)
    print(f"Response: {response}")

    assert verify_proof(response, public_key), "Signature verification failed"
    
    assert response is not None
    


