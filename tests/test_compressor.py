"""
python challenges

1) lets compress the giant product catalog from ordered JSON to something more compact but LLM's must be able to understand it

from:

["{sku=123, price=10, name=T shirt A},
{sku=124, price=10, name=T shirt B},
{sku=125, price=10, name=T shirt C}]

to:
sku,price,name
123,10,T shirt A
124,10,T shirt B
125,10,T shirt C

"""
from app.compressor import compress_json, decompress_json

def test_compress_json():
    """Test compressing a list of dicts to CSV-like string."""
    data = [
        {"sku": 123, "price": 10, "name": "T shirt A"},
        {"sku": 124, "price": 10, "name": "T shirt B"},
        {"sku": 125, "price": 10, "name": "T shirt C"}
    ]
    
    compressed = compress_json(data)
    expected = "sku,price,name\n123,10,T shirt A\n124,10,T shirt B\n125,10,T shirt C"
    
    assert compressed == expected, f"Expected {expected}, got {compressed}"

def test_decompress_json():
    """Test decompressing CSV-like string back to list of dicts."""
    compressed = "sku,price,name\n123,10,T shirt A\n124,10,T shirt B\n125,10,T shirt C"
    
    decompressed = decompress_json(compressed)
    expected = [
        {"sku": "123", "price": "10", "name": "T shirt A"},
        {"sku": "124", "price": "10", "name": "T shirt B"},
        {"sku": "125", "price": "10", "name": "T shirt C"}
    ]
    
    assert decompressed == expected, f"Expected {expected}, got {decompressed}"

def test_round_trip():
    """Test that compress -> decompress is lossless."""
    original = [
        {"sku": 123, "price": 10.5, "name": "T shirt A"},
        {"sku": 124, "price": 20, "name": "T shirt B"}
    ]
    
    compressed = compress_json(original)
    decompressed = decompress_json(compressed)
    
    # Note: Values become strings in CSV, so compare accordingly
    expected_decompressed = [
        {"sku": "123", "price": "10.5", "name": "T shirt A"},
        {"sku": "124", "price": "20", "name": "T shirt B"}
    ]
    
    assert decompressed == expected_decompressed

def test_empty_data():
    """Test edge cases."""
    assert compress_json([]) == ""
    assert decompress_json("") == []
    assert decompress_json("sku,price\n") == []  # Header only