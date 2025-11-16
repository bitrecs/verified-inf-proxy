import json
import os
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

def load_json_file(file_path: str) -> str:
    """Load a JSON file and return its content as a string."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def test_tiktoken_small_json_count():
    from app.utils import get_token_count
    from app.models import ChatCompletionRequest
    small_json = load_json_file("tests/test_data/small_json_example.json")
    print(f"small json: {small_json}")
    completion_request = ChatCompletionRequest.model_validate_json(small_json)
    token_count = get_token_count(completion_request)
    print(f"Token count for small_json: {token_count}")
    assert token_count == 229

def test_tiktoken_large_json_xai_count():
    from app.utils import get_token_count
    from app.models import ChatCompletionRequest
    large_json = load_json_file("tests/test_data/large_json_example.json")
    completion_request = ChatCompletionRequest.model_validate_json(large_json)
    token_count = get_token_count(completion_request)
    print(f"Token count for large_json: {token_count}")
    assert token_count == 10133

def test_tiktoken_large_json_gemini_count():
    from app.utils import get_token_count
    from app.models import ChatCompletionRequest
    large_json = load_json_file("tests/test_data/large_json_gemini_example.json")
    completion_request = ChatCompletionRequest.model_validate_json(large_json)
    token_count = get_token_count(completion_request)
    print(f"Token count for large_json_gemini: {token_count}")
    assert token_count == 5759
  
def test_tiktoken_medium_json_count():
    from app.utils import get_token_count
    from app.models import ChatCompletionRequest
    medium_json = load_json_file("tests/test_data/medium_json_woo_example.json")
    completion_request = ChatCompletionRequest.model_validate_json(medium_json)
    token_count = get_token_count(completion_request)
    print(f"Token count for medium_json: {token_count}")
    assert token_count == 5891