import httpx
import json
import base64
import time
import hashlib
import secrets
import traceback
from typing import Tuple
from dotenv import load_dotenv
from datetime import datetime, timezone
from app.models import SignedResponse
load_dotenv()
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fiber import (
    Keypair
)
from cryptography.exceptions import InvalidSignature


PERMITTED_CLOCK_DIFF_SECONDS = 300  # 5 minutes


async def call_proxy_server_with_signing(
    base_url: str,
    request: dict,     
    hotkey: str,
    keypair: Keypair,
    provider: str, 
    auth_key: str
) -> SignedResponse:
    """Call the proxy server with a request."""
    headers = {
        "Authorization": f"Bearer {auth_key}",
        "x-hotkey": hotkey,
        "x-provider": provider        
    }
    ts = str(int(time.time()))
    signature, nonce = sign_verified_request(keypair, provider, request, ts)
    headers["x-signature"] = signature
    headers["x-nonce"] = nonce
    headers["x-timestamp"] = str(ts)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{base_url}/v1/chat/completions",
            json=request,
            headers=headers
        )
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        response.raise_for_status()
        thing = response.json()
        result = SignedResponse(**thing)
        return result        



def verify_proof(
    response: SignedResponse, 
    public_key: Ed25519PublicKey
) -> bool:
    proof = response.proof
    signature_b64 = response.signature
    timestamp = response.timestamp
    ttl = response.ttl
    try:
        current_time = datetime.now(timezone.utc)
        proof_time = datetime.fromisoformat(timestamp)
        ttl_time = datetime.fromisoformat(ttl)
        time_diff = abs((current_time - proof_time).total_seconds())
        if time_diff > PERMITTED_CLOCK_DIFF_SECONDS:            
            print(f"Timestamp too old or future: {time_diff} seconds")
            return False
        if current_time > ttl_time:            
            print(f"Proof expired: TTL {ttl_time}, current {current_time}")
            return False
        signed_data = {
            "proof": proof,
            "timestamp": timestamp,
            "ttl": ttl
        }
        serialized_data = json.dumps(signed_data, sort_keys=True).encode()
        signature_bytes = base64.b64decode(signature_b64)
        public_key.verify(signature_bytes, serialized_data)
        return True
    except InvalidSignature:        
        print("verify_proof Verification failed: Invalid signature")
        return False
    except Exception as e:        
        traceback_str = traceback.format_exc()
        print(f"verify_proof Verification failed: {type(e).__name__}: {str(e) or 'No message'}")
        print(f"Traceback:\n{traceback_str}")        
        return False


def sign_verified_request(miner_keypair: Keypair, provider: str, payload: dict, ts: str) -> Tuple[str, str]:
    nonce = secrets.token_hex(16)    
    payload_str = json.dumps({
        "hotkey": miner_keypair.ss58_address,
        "provider": provider,
        "nonce": nonce,
        "payload": payload,
        "timestamp": ts
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
        