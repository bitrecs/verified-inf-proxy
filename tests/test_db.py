import json
import os
import requests
import secrets
from dotenv import load_dotenv
load_dotenv()
from app.d1 import D1Handler
from app.models import SignedResponse


CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_D1_TOKEN = os.getenv("CF_D1_TOKEN")
CF_D1_DATABASE_ID = os.getenv("CF_D1_DATABASE_ID")
if not any([CF_ACCOUNT_ID, CF_D1_TOKEN, CF_D1_DATABASE_ID]):
    raise ValueError("Missing one of CF_ACCOUNT_ID, CF_D1_TOKEN, CF_D1_DATABASE_ID in environment variables")


def test_d1_list_db():
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/d1/database"
    headers = {        
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {CF_D1_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    print(response)
    assert response.status_code == 200
    data = response.json()
    print("D1 Databases:", data)
    assert "result" in data
    assert isinstance(data["result"], list)
    print("D1 Databases:", data["result"])  


def test_d1_query_db():  
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/d1/database/{CF_D1_DATABASE_ID}/query"
    headers = {        
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {CF_D1_TOKEN}"
    }
    sql_query = "SELECT * FROM signed_responses LIMIT 5;"
    payload = {
        "sql": sql_query,
        "params": []
    }
    response = requests.post(url, headers=headers, json=payload)
    print(response)
    assert response.status_code == 200
    data = response.json()
    print("D1 Query Result:", data)
    assert "result" in data
    assert isinstance(data["result"], list)
    print("D1 Query Rows:", data["result"])



def test_d1_insert_signed_response():
    unique_id = secrets.token_hex(16)
    SignedResponse_example = SignedResponse(
        response={
            "id": "chatcmpl-7aX8bYzEXAMPLE",
            "object": "chat.completion",
            "created": 1695180000,
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",    
                        "content": "Hello! How can I assist you today?"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 10,
                "total_tokens": 20
            }
        },
        proof={
            "unique_id": unique_id,
            "request_hash": "reqhash1234567890abcdef",
            "response_hash": "resphash1234567890abcdef",
            "hotkey": "test_hotkey_123",
            "model": "gpt-4o-mini"
        },
        signature="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        timestamp="2024-06-20T12:00:00Z",
        ttl="2024-06-27T12:00:00Z"
    )   


    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/d1/database/{CF_D1_DATABASE_ID}/query"
    headers = {        
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {CF_D1_TOKEN}"
    }
    sql_query = """INSERT INTO signed_responses (unique_id, request_hash, response_hash, hotkey, model, signature, timestamp, ttl, response_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"""
    payload = {
        "sql": sql_query,
        "params": [
            SignedResponse_example.proof['unique_id'],
            SignedResponse_example.proof['request_hash'],
            SignedResponse_example.proof['response_hash'],
            SignedResponse_example.proof['hotkey'],
            SignedResponse_example.proof['model'],
            SignedResponse_example.signature,
            SignedResponse_example.timestamp,
            SignedResponse_example.ttl,
            json.dumps(SignedResponse_example.response)
        ]
    }
    response = requests.post(url, headers=headers, json=payload)
    print(response)
    print(response.text)
    assert response.status_code == 200
    data = response.json()
    print("D1 Insert Result:", data)
    assert "result" in data
    assert data["success"] is True



def test_d1_insert_signed_response_using_helper():
    unique_id = secrets.token_hex(16)    
    SignedResponse_example = SignedResponse(
        response={
            "id": "chatcmpl-7aX8bYzEXAMPLE",
            "object": "chat.completion",
            "created": 1695180000,
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",    
                        "content": "Hello! How can I assist you today?"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 10,
                "total_tokens": 20
            }
        },
        proof={
            "unique_id": unique_id,
            "request_hash": "reqhash1234567890abcdef",
            "response_hash": "resphash1234567890abcdef",
            "hotkey": "test_hotkey_123",
            "model": "gpt-4o-mini"
        },
        signature="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        timestamp="2024-06-20T12:00:00Z",
        ttl="2024-06-27T12:00:00Z"
    )   

    d1_handler = D1Handler(
        account_id=CF_ACCOUNT_ID,
        token=CF_D1_TOKEN,
        database_id=CF_D1_DATABASE_ID
    )
    result = d1_handler.insert_signed_response(SignedResponse_example, request_id="test_request_id_123")
    print("D1 Insert via Helper Result:", result)
    assert True is result


def test_used_nonce_denied():
    d1_handler = D1Handler(
        account_id=CF_ACCOUNT_ID,
        token=CF_D1_TOKEN,
        database_id=CF_D1_DATABASE_ID
    )
    nonce = secrets.token_hex(16)
    hotkey = f"test_hotkey_nonce_{nonce}"
    
    first_insert = d1_handler.insert_used_nonce(nonce, hotkey)
    print("First nonce insert result:", first_insert)
    assert first_insert is True

    exists = d1_handler.check_nonce_used(nonce)
    print("Nonce exists after first insert:", exists)
    assert exists is True


# def test_insert_batch_request():
#     d1_handler = D1Handler(
#         account_id=CF_ACCOUNT_ID,
#         token=CF_D1_TOKEN,
#         database_id=CF_D1_DATABASE_ID
#     )
#     unique_id = secrets.token_hex(16)    
#     SignedResponse_example = SignedResponse(
#         response={
#             "id": "chatcmpl-7aX8bYzEXAMPLE",
#             "object": "chat.completion",
#             "created": 1695180000,
#             "model": "gpt-4o-mini",
#             "choices": [
#                 {
#                     "index": 0,
#                     "message": {
#                         "role": "assistant",    
#                         "content": "Hello! How can I assist you today?"
#                     },
#                     "finish_reason": "stop"
#                 }
#             ],
#             "usage": {
#                 "prompt_tokens": 10,
#                 "completion_tokens": 10,
#                 "total_tokens": 20
#             }
#         },
#         proof={
#             "unique_id": unique_id,
#             "request_hash": "reqhash1234567890abcdef",
#             "response_hash": "resphash1234567890abcdef",
#             "hotkey": "test_hotkey_123",
#             "model": "gpt-4o-mini"
#         },
#         signature="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
#         timestamp="2024-06-20T12:00:00Z",
#         ttl="2024-06-27T12:00:00Z"
#     )   

#     # Add missing arguments for the batch method
#     from app.models import ChatCompletionRequest  # Import if needed
#     completion_request = ChatCompletionRequest(
#         model="gpt-4o-mini",
#         messages=[{"role": "user", "content": "Test message"}]
#     )
#     provider = "test_provider"
#     x_nonce = secrets.token_hex(16)
#     x_hotkey = "test_hotkey_batch"

#     result = d1_handler.insert_batch_request_data(
#         signed_response=SignedResponse_example,
#         request_id="test_request_id_batch_123",
#         duration=1.23,
#         provider=provider,
#         x_nonce=x_nonce,
#         x_hotkey=x_hotkey,
#         completion_request=completion_request
#     )
#     print("D1 Insert Batch Request Result:", result)
#     assert True is result