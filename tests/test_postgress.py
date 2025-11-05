import json
import os
import secrets
from app.pg_helper import PGHandler
from app.models import SignedResponse, ChatCompletionRequest
from dotenv import load_dotenv
load_dotenv()


TEST_DB_URL = os.getenv("POSTGRESS_DB_URL", "")
if not TEST_DB_URL:
    raise ValueError("TEST_DB_URL not set in environment variables")


def test_insert_signed_response():
    """Unit test for PGHandler.insert_signed_response."""
    # Setup test data
    unique_id = f"test_id_{secrets.token_hex(8)}"
    print(f"TEST Using request_id: {unique_id}")
    signed_response = SignedResponse(
        response={
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1695180000,
            "model": "gpt-4o-mini",
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"total_tokens": 10}
        },
        proof={
            "unique_id": unique_id,
            "request_hash": "reqhash123",
            "response_hash": "reshash123",
            "hotkey": "test_hotkey",
            "model": "gpt-4o-mini"
        },
        signature="test_signature_abc",
        timestamp="2024-06-20T12:00:00Z",
        ttl="2024-06-27T12:00:00Z"
    )
    
    completion_request = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Test message"}]
    )
    
    # Create handler
    handler = PGHandler(TEST_DB_URL)

    result = handler.insert_signed_response(
        request_id=unique_id,
        response=signed_response,       
        duration=1.23,
        provider="test_provider",
        x_nonce="test_nonce_456",
        x_hotkey="test_hotkey",
        completion_request=completion_request
    )

    print(f"Insert result: {result}")
    
    # Assert success
    assert result is True, "Insert should succeed"
    
    # Optional: Verify by querying the DB (integration-style)
    conn = handler.connect()
    with conn.cursor() as cur:
        cur.execute("SELECT unique_id FROM vi.signed_responses WHERE unique_id = %s", (unique_id,))
        row = cur.fetchone()
        assert row is not None, "Record should exist"
    conn.close()


def test_select_signed_response_by_miner_hotkey():
    """Unit test for PGHandler.select_signed_response_by_miner_hotkey."""
    hotkey = "test_hotkey"
    
    # Create handler
    handler = PGHandler(TEST_DB_URL)

    result = handler.select_signed_response_by_miner_hotkey(hotkey=hotkey, limit=5)

    print(f"Select result for hotkey {hotkey}: {result}")
    
    # Assert we get a dictionary (could be empty if no records)
    assert isinstance(result, dict), "Result should be a dictionary"


def test_select_signed_responses():
    """Unit test for PGHandler.select_signed_responses."""
    # Create handler
    handler = PGHandler(TEST_DB_URL)

    results = handler.select_signed_responses(limit=10)
    pretty_results = json.dumps(results, indent=2, default=str)  # Add default=str to handle datetime
    print(f"Select signed responses result: {pretty_results}")

    print(f"Select signed responses result count: {len(results)}")
    
    # Assert we get a list
    assert isinstance(results, list), "Results should be a list"
    assert len(results) <= 10, "Results should not exceed the limit of 10"


def test_render_verfied_stats_from_pg():
    """Integration test for rendering verified stats from PG."""
    from app.html_stats import HTMLStats

    # Create handler
    handler = PGHandler(TEST_DB_URL)

    verified = handler.select_signed_responses(limit=100)
    html_content = HTMLStats.render_verified_stats(
        verified=verified,
        bt_network="testnet",
        bt_netuid=1
    )

    print(f"Rendered HTML content length: {len(html_content)}")
    
    # Assert some content was generated
    assert len(html_content) > 0, "HTML content should not be empty"

def test_select_signed_response_by_miner_hotkey_since():
    """Unit test for PGHandler.select_signed_response_by_miner_hotkey_since."""
    from datetime import datetime, timedelta, timezone

    hotkey = "test_hotkey"
    since_date = datetime.now(timezone.utc) - timedelta(days=365)
    
    # Create handler
    handler = PGHandler(TEST_DB_URL)

    results = handler.select_signed_response_by_miner_hotkey_since(hotkey=hotkey, since_date=since_date, limit=10)

    print(f"Select results for hotkey {hotkey} since {since_date}: {results}")
    print(f" length: {len(results)} ")
    
    # Assert we get a list
    assert isinstance(results, list), "Results should be a list"
    assert len(results) >= 5, "Results should have at least 5 entries"
