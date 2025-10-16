import hashlib
import os
import secrets
import httpx
import json
import base64
import pytest
from typing import Dict, Any, Tuple
from dotenv import load_dotenv
load_dotenv()
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fiber.chain import chain_utils, interface
from fiber import (
    Keypair
)

BASE_URL = "http://localhost:8000"
#BASE_URL = "https://verified.bitrecs.ai"

OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")


def sign_verified_request(miner_keypair: Keypair, provider: str, payload: dict) -> Tuple[str, str]:
    nonce = secrets.token_hex(16)    
    payload_str = json.dumps({
        "hotkey": miner_keypair.ss58_address,
        "provider": provider,
        "nonce": nonce,
        "payload": payload
    }, separators=(',', ':'), sort_keys=True)
    payload_hash = hashlib.sha256(payload_str.encode('utf-8')).digest()    
    signature_bytes = miner_keypair.sign(payload_hash)
    signature_hex = signature_bytes.hex()
    return signature_hex, nonce


async def get_public_key() -> Ed25519PublicKey:
    """Get public key from proxy server."""    
    async with httpx.AsyncClient(timeout=30.0) as client:
        public_key_response = await client.get(f"{BASE_URL}/public_key")
        public_key_response.raise_for_status()
        public_key_string = json.loads(public_key_response.text)["public_key"]
        raw_bytes = bytes.fromhex(public_key_string)
        return Ed25519PublicKey.from_public_bytes(raw_bytes)
        

# async def call_proxy_server(
#     request: dict, 
#     openrouter_key: str, 
#     hotkey: str
# ) -> Dict[str, Any]:
#     """Call the proxy server with a request."""
#     headers = {
#         "Authorization": f"Bearer {openrouter_key}",
#         "x-hotkey": hotkey,
#         "x-provider": "OPEN_ROUTER"
#     }
#     async with httpx.AsyncClient(timeout=30.0) as client:
#         response = await client.post(
#             f"{BASE_URL}/v1/chat/completions",
#             json=request,
#             headers=headers
#         )
#         print(f"Response status code: {response.status_code}")
#         print(f"Response content: {response.text}")
#         response.raise_for_status()
#         return response.json()
    

async def call_proxy_server_with_signing(
    request: dict, 
    openrouter_key: str, 
    hotkey: str,
    keypair: Keypair
) -> Dict[str, Any]:
    """Call the proxy server with a request."""
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "x-hotkey": hotkey,
        "x-provider": "OPEN_ROUTER"        
    }
    signature, nonce = sign_verified_request(keypair, "OPEN_ROUTER", request)
    headers["x-signature"] = signature
    headers["x-nonce"] = nonce

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/v1/chat/completions",
            json=request,
            headers=headers
        )
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        response.raise_for_status()
        return response.json()



def verify_signature(
    response: Dict[str, Any], 
    public_key: Ed25519PublicKey
) -> bool:
    """Verify the signature of the response."""
    proof = response["proof"]
    signature_b64 = response["signature"]

    print(f"Proof: {proof}")
    print(f"Signature (base64): {signature_b64}")

    signature_bytes = base64.b64decode(signature_b64)
    serialized_proof = json.dumps(proof, sort_keys=True).encode()

    try:
        public_key.verify(signature_bytes, serialized_proof)
        return True
    except Exception as e:
        print(f"Verification failed: {e}")
        return False

# @pytest.mark.asyncio
# async def test_verify_signature():
#     """Fetch the public key, make request, sign, then verify."""
#     public_key = await get_public_key()

#     request = {
#         "model": "gpt-4o-mini",
#         "messages": [{"role": "user", "content": "Hello, how are you?"}]
#     }

#     # Returns a SignedResponse object with openrouter package, proof, signature
#     response = await call_proxy_server(request, OPENROUTER_KEY, HOTKEY)
#     print(f"Response: {response}")

#     assert verify_signature(response, public_key), "Signature verification failed"



@pytest.mark.asyncio
async def test_verify_signature_with_signing():
    """Fetch the public key, make request, sign, then verify."""  
    wallet_name = os.environ.get("TEST_WALLET_NAME")
    wallet_hotkey = os.environ.get("TEST_WALLET_HOTKEY")
    
    miner_keypair = chain_utils.load_hotkey_keypair(wallet_name, wallet_hotkey)
    assert miner_keypair is not None, "Failed to load miner_keypair"

    public_key = await get_public_key()
    request = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello, how are you?"}]
    }

    # Returns a SignedResponse object with openrouter package, proof, signature
    response = await call_proxy_server_with_signing(request, OPENROUTER_KEY, miner_keypair.ss58_address, miner_keypair)
    print(f"Response: {response}")

    assert verify_signature(response, public_key), "Signature verification failed"


