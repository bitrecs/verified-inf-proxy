import os
import time
import json
import httpx
import pytest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from app.main import SignedResponse

load_dotenv()
BASE_URL = "http://127.0.0.1:8000"
OPENAI_KEY = os.environ.get("OPENAI_KEY")
HOTKEY = os.environ.get("HOTKEY")

async def call_proxy(
    request: dict,
    headers: dict
) -> SignedResponse:
    """Call v1/chat/completions with an openai key."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/v1/chat/completions",
            json=request,
            headers=headers
        )
        return response.json()

@pytest.mark.asyncio
async def test_call_proxy_gpt5():
    request = {
        "model": "gpt-5-nano",
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Hello, how are you?"
                    }
                ]
            }
        ],
        "text": {
            "format": {
                "type": "text"
            },
            "verbosity": "low"
        },
        "reasoning": {
            "effort": "low"
        },
        "tools": [],
        "store": True,
        "include": ["reasoning.encrypted_content"]
    }
    headers = {"Authorization": f"Bearer {OPENAI_KEY}",
               "x-hotkey": HOTKEY,
               "x-provider": "CHAT_GPT"}

    response = await call_proxy(request, headers)
    print(response)
    assert response is not None
    assert "response" in response
    # GPT-5 responses have different structure - check for output content
    assert "output" in response["response"]
    assert len(response["response"]["output"]) > 0
    # Find the message output
    message_output = None
    for output in response["response"]["output"]:
        if output.get("type") == "message":
            message_output = output
            break
    assert message_output is not None
    assert "content" in message_output
    assert len(message_output["content"]) > 0
    assert "text" in message_output["content"][0]
    assert len(message_output["content"][0]["text"]) > 0