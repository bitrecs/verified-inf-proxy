import os
from app.utils import get_token_count
from app.models import ChatCompletionRequest
from app.product import Product

def load_json_file(file_path: str) -> str:
    """Load a JSON file and return its content as a string."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def test_tiktoken_small_json_count():  
    small_json = load_json_file("tests/test_data/small_json_example.json")
    print(f"small json: {small_json}")
    completion_request = ChatCompletionRequest.model_validate_json(small_json)
    token_count = get_token_count(completion_request)
    print(f"Token count for small_json: {token_count}")
    assert token_count == 229


def test_extract_products_from_prompt_small():
    small_json = load_json_file("tests/test_data/small_json_example.json")
    completion_request = ChatCompletionRequest.model_validate_json(small_json)

    # Extract products from the prompt (with no exclusion since this is just a response)
    products = Product.extract_products_from_prompt(completion_request, exclude_last_n=0)
    print(f"Extracted {len(products)} products from prompt")

    # Verify count - small_json has 6 products and NO context tags, so with exclude_last_n=0 it gets all
    assert len(products) == 6
     
    # Test count method with no exclusion
    product_count = Product.count_products_in_prompt(completion_request, exclude_last_n=0)
    assert product_count == 6


def test_extract_products_from_prompt_large():    
    large_json = load_json_file("tests/test_data/large_json_example.json")
    completion_request = ChatCompletionRequest.model_validate_json(large_json)

    # Extract products from the prompt - large_json should have <context> tags
    products = Product.extract_products_from_prompt(completion_request)
    print(f"Extracted {len(products)} products from prompt")

    # Large example has <context> tags, so it should extract all products inside
    assert len(products) >= 190  # Expect at least 190 (200 minus ~10 if no context tags)
     
    # Test count method
    product_count = Product.count_products_in_prompt(completion_request)
    assert product_count >= 190


def test_extract_products_with_context_tags():
    """Test extraction when <context> tags are present (most reliable)"""    

    # Use the large example which should have context tags
    large_json = load_json_file("tests/test_data/large_json_gemini_example.json")
    completion_request = ChatCompletionRequest.model_validate_json(large_json)

    products = Product.extract_products_from_prompt(completion_request)
    print(f"Extracted {len(products)} products from <context> tags")

    # Should extract all products from context (no trimming needed)
    assert len(products) >= 90  # Gemini example has 100+ products


def test_extract_products_without_context_tags():
    """Test extraction when NO <context> tags (uses trimming strategy)"""    

    medium_json = load_json_file("tests/test_data/medium_json_woo_example.json")
    completion_request = ChatCompletionRequest.model_validate_json(medium_json)

    # With default exclude_last_n=10, should trim last 10 products
    products = Product.extract_products_from_prompt(completion_request, exclude_last_n=10)
    print(f"Extracted {len(products)} products (trimmed last 10)")

    # Medium has 200+ products, so after trimming should have 190+
    assert len(products) >= 185



def test_get_dupe_counts():   
    #woo has MS01 duped once
    small_json = load_json_file("tests/test_data/medium_json_woo_example.json")
    completion_request = ChatCompletionRequest.model_validate_json(small_json)

    products = Product.extract_products_from_prompt(completion_request, exclude_last_n=0)
    print(f"Extracted {len(products)} products from prompt with duplicates")

    dupe_counts = Product.get_dupe_count(products)
    print(f"Duplicate counts: {dupe_counts}")

    assert 1 == dupe_counts


def test_get_dupe_percentage():    
    #woo has MS01 duped once
    small_json = load_json_file("tests/test_data/medium_json_woo_example.json")
    completion_request = ChatCompletionRequest.model_validate_json(small_json)

    products = Product.extract_products_from_prompt(completion_request, exclude_last_n=0)
    print(f"Extracted {len(products)} products from prompt with duplicates")

    dupe_percentage = Product.get_dupe_percentage(products)
    print(f"Duplicate percentage: {dupe_percentage}")

    assert dupe_percentage > 0
   