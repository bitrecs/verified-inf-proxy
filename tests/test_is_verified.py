import os
import httpx
import json
import base64
import pytest
from typing import Dict, Any
from dotenv import load_dotenv
load_dotenv()
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

BASE_URL = "http://localhost:8000"
#BASE_URL = "https://verified.bitrecs.ai"
HOTKEY = os.environ.get("HOTKEY")


def test_is_hotkey_verified():
    """Test the /is_verified endpoint."""
    if not HOTKEY:
        pytest.skip("HOTKEY environment variable not set")
    response = httpx.get(f"{BASE_URL}/is_verified", params={"hotkey": HOTKEY})
    assert response.status_code == 200
    data = response.json()
    print(data)
    assert "verified" in data
    assert isinstance(data["verified"], bool)
    assert "message" in data
    if data["verified"]:
        assert "latest_timestamp" in data
        print(f"Hotkey is verified. Latest timestamp: {data['latest_timestamp']}")
    else:
        print(f"Hotkey is not verified. Message: {data['message']}")