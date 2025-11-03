import os
import pytest
from dotenv import load_dotenv
from tests.utils import call_proxy_server_with_signing, get_public_key, verify_proof
load_dotenv()
from fiber.chain import chain_utils

BASE_URL = "http://localhost:8000"
#BASE_URL = "https://verified.bitrecs.ai"

OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")


@pytest.mark.asyncio
async def test_verify_signature_with_signing():
    """Fetch the public key, make request, sign, then verify."""  
    wallet_name = os.environ.get("TEST_WALLET_NAME")
    wallet_hotkey = os.environ.get("TEST_WALLET_HOTKEY")
    
    miner_keypair = chain_utils.load_hotkey_keypair(wallet_name, wallet_hotkey)
    assert miner_keypair is not None, "Failed to load miner_keypair"

    public_key = await get_public_key(base_url=BASE_URL)
    request = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello, how are you?"}]
    }

    # Returns a SignedResponse object with openrouter package, proof, signature
    response = await call_proxy_server_with_signing(BASE_URL, request, miner_keypair.ss58_address, miner_keypair, "OPEN_ROUTER", OPENROUTER_KEY)
    print(f"Response: {response}")

    assert verify_proof(response, public_key), "Signature verification failed"


