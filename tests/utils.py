import base64
import hashlib
import secrets
import httpx
import json
from typing import Any, Dict, Tuple
from dotenv import load_dotenv
load_dotenv()
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fiber import (
    Keypair
)


async def call_proxy_server_with_signing(
    base_url: str,
    request: dict,     
    hotkey: str,
    keypair: Keypair,
    provider: str, 
    auth_key: str
) -> Dict[str, Any]:
    """Call the proxy server with a request."""
    headers = {
        "Authorization": f"Bearer {auth_key}",
        "x-hotkey": hotkey,
        "x-provider": provider        
    }
    signature, nonce = sign_verified_request(keypair, provider, request)
    headers["x-signature"] = signature
    headers["x-nonce"] = nonce

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{base_url}/v1/chat/completions",
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


async def get_public_key(base_url: str) -> Ed25519PublicKey:
    """Get public key from proxy server."""    
    if not base_url:
        raise ValueError("base_url must be provided")
    async with httpx.AsyncClient(timeout=30.0) as client:
        public_key_response = await client.get(f"{base_url}/public_key")
        public_key_response.raise_for_status()
        public_key_string = json.loads(public_key_response.text)["public_key"]
        raw_bytes = bytes.fromhex(public_key_string)
        return Ed25519PublicKey.from_public_bytes(raw_bytes)
        