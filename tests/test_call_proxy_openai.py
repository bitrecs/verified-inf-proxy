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
OPENAI_KEY = os.environ.get("OPENAI_KEY")


@pytest.mark.asyncio
async def test_call_openai():    
    request = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello, how are you?"}]
    }
    
    wallet_name = os.environ.get("TEST_WALLET_NAME")
    wallet_hotkey = os.environ.get("TEST_WALLET_HOTKEY")
    
    miner_keypair = chain_utils.load_hotkey_keypair(wallet_name, wallet_hotkey)
    assert miner_keypair is not None, "Failed to load miner_keypair"

    public_key = await get_public_key(base_url=BASE_URL)
    response = await call_proxy_server_with_signing(BASE_URL, request, miner_keypair.ss58_address, miner_keypair, "CHAT_GPT", OPENAI_KEY)
    print(f"Response: {response}")

    assert verify_signature(response, public_key), "Signature verification failed"
    
    assert response is not None
    assert "response" in response
    assert "choices" in response["response"]
    assert len(response["response"]["choices"]) > 0
    assert "message" in response["response"]["choices"][0]
    assert "content" in response["response"]["choices"][0]["message"]
    assert len(response["response"]["choices"][0]["message"]["content"]) > 0




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
  
    wallet_name = os.environ.get("TEST_WALLET_NAME")
    wallet_hotkey = os.environ.get("TEST_WALLET_HOTKEY")
    
    miner_keypair = chain_utils.load_hotkey_keypair(wallet_name, wallet_hotkey)
    assert miner_keypair is not None, "Failed to load miner_keypair"

    public_key = await get_public_key(base_url=BASE_URL)
    response = await call_proxy_server_with_signing(BASE_URL, request, miner_keypair.ss58_address, miner_keypair, "CHAT_GPT", OPENAI_KEY)
    print(f"Response: {response}")

    assert verify_signature(response, public_key), "Signature verification failed"

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



@pytest.mark.asyncio
async def test_call_proxy_legacy():
    request = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello, how are you?"}]
    }
    wallet_name = os.environ.get("TEST_WALLET_NAME")
    wallet_hotkey = os.environ.get("TEST_WALLET_HOTKEY")
    
    miner_keypair = chain_utils.load_hotkey_keypair(wallet_name, wallet_hotkey)
    assert miner_keypair is not None, "Failed to load miner_keypair"

    public_key = await get_public_key(base_url=BASE_URL)
    response = await call_proxy_server_with_signing(BASE_URL, request, miner_keypair.ss58_address, miner_keypair, "CHAT_GPT", OPENAI_KEY)
    print(f"Response: {response}")

    assert verify_signature(response, public_key), "Signature verification failed"
    assert response is not None
    assert "response" in response
    assert "choices" in response["response"]
    assert len(response["response"]["choices"]) > 0
    assert "message" in response["response"]["choices"][0]
    assert "content" in response["response"]["choices"][0]["message"]
    assert len(response["response"]["choices"][0]["message"]["content"]) > 0