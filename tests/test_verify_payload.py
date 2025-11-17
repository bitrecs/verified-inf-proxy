from dataclasses import asdict
import json
import os
import pytest
from dotenv import load_dotenv
from app.models import ChatCompletionRequest
from app.product import Product
from tests.utils import call_proxy_server_with_signing, get_public_key, verify_proof
load_dotenv()
from fiber.chain import chain_utils

BASE_URL = "http://localhost:8000"
#BASE_URL = "https://verified.bitrecs.ai"

OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")

def load_json_file(file_path: str) -> str:
    """Load a JSON file and return its content as a string."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


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



@pytest.mark.asyncio
async def test_verify_signature_with_signing_full_catalog():
    """Fetch the public key, make request, sign, then verify."""  
    wallet_name = os.environ.get("TEST_WALLET_NAME")
    wallet_hotkey = os.environ.get("TEST_WALLET_HOTKEY")
    
    miner_keypair = chain_utils.load_hotkey_keypair(wallet_name, wallet_hotkey)
    assert miner_keypair is not None, "Failed to load miner_keypair"

    public_key = await get_public_key(base_url=BASE_URL)
    
    medium_json = load_json_file("tests/test_data/medium_json_woo_example.json")
    completion_request = ChatCompletionRequest.model_validate_json(medium_json)
    
    products = Product.extract_products_from_prompt(completion_request, exclude_last_n=0)
    product_json = json.dumps([asdict(p) for p in products], indent=2)
    print(f"Extracted {len(products)} products from medium_json")
    test_prompt = f"""
    Please provide a count of the following products, only return the number no extra text.
    <context>
     {product_json}
    </context>
    """
    
    request = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": test_prompt}]
    }

    # Returns a SignedResponse object with openrouter package, proof, signature
    response = await call_proxy_server_with_signing(BASE_URL, request, miner_keypair.ss58_address, miner_keypair, "OPEN_ROUTER", OPENROUTER_KEY)
    print(f"Response: {response}")

    assert verify_proof(response, public_key), "Signature verification failed"
