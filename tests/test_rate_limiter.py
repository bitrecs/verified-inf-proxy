import os
import httpx
import time
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple
from dotenv import load_dotenv
load_dotenv()

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
#BASE_URL = "https://verified.bitrecs.ai"


def check_server_running() -> bool:
    """Check if the server is running before starting tests."""
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=2.0)
        return response.status_code in [200, 429]
    except:
        return False


def make_health_request() -> Tuple[int, float, str]:
    """Make a single request to /health endpoint.
    
    Returns:
        Tuple of (status_code, response_time_ms, error_message)
    """
    start = time.time()
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        elapsed_ms = (time.time() - start) * 1000
        return (response.status_code, elapsed_ms, "")
    except httpx.ConnectError as e:
        elapsed_ms = (time.time() - start) * 1000
        return (0, elapsed_ms, f"Connection error: {str(e)}")
    except httpx.TimeoutException as e:
        elapsed_ms = (time.time() - start) * 1000
        return (0, elapsed_ms, f"Timeout: {str(e)}")
    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        return (0, elapsed_ms, f"Error: {str(e)}")


def test_rate_limit_health_sequential():
    """Test rate limiting on /health endpoint with sequential requests.
    
    The rate limit is 60 requests per minute (1 per second average).
    This test sends requests sequentially and verifies some get rate limited.
    """
    # Check server is running first
    if not check_server_running():
        pytest.skip(f"Server not running at {BASE_URL}. Start with: uv run uvicorn app.main:app")
    
    num_requests = 70  # More than the 60/min limit
    results = []
    errors = []
    
    print(f"\nTesting against: {BASE_URL}")
    print(f"Sending {num_requests} sequential requests to /health...")
    start_time = time.time()
    
    for i in range(num_requests):
        status_code, response_time, error_msg = make_health_request()
        results.append(status_code)
        if error_msg:
            errors.append((i, error_msg))
        
        if (i + 1) % 10 == 0:
            print(f"  Completed {i + 1}/{num_requests} requests")
    
    total_time = time.time() - start_time
    
    # Count responses
    success_count = sum(1 for code in results if code == 200)
    rate_limited_count = sum(1 for code in results if code == 429)
    error_count = sum(1 for code in results if code not in [200, 429])
    
    print(f"\nResults after {total_time:.2f} seconds:")
    print(f"  ✅ Success (200): {success_count}")
    print(f"  ⛔ Rate Limited (429): {rate_limited_count}")
    print(f"  ❌ Errors: {error_count}")
    
    if errors:
        print(f"\nFirst 3 errors:")
        for idx, (req_num, msg) in enumerate(errors[:3]):
            print(f"  Request {req_num}: {msg}")
    
    # Assertions - adjusted for reality
    assert error_count == 0, f"Got {error_count} connection errors. Is the server running at {BASE_URL}?"
    
    # Since all requests come from same IP (127.0.0.1), we expect:
    # - First ~60 requests succeed
    # - Remaining ~10 get rate limited
    assert success_count >= 55 and success_count <= 60, \
        f"Expected 55-60 successful requests, got {success_count}"
    assert rate_limited_count >= 10, \
        f"Expected at least 10 rate-limited requests, got {rate_limited_count}"
    
    print(f"\n✅ Rate limiter working correctly!")
    print(f"   Allowed {success_count}/60 requests within limit")
    print(f"   Blocked {rate_limited_count} requests exceeding limit")


# def test_rate_limit_health_concurrent(num_threads: int = 10, requests_per_thread: int = 10):
#     """Test rate limiting with concurrent requests using thread pool.
    
#     Args:
#         num_threads: Number of concurrent threads to use
#         requests_per_thread: Number of requests each thread should make
#     """
#     # Check server is running first
#     if not check_server_running():
#         pytest.skip(f"Server not running at {BASE_URL}. Start with: uv run uvicorn app.main:app")
    
#     total_requests = num_threads * requests_per_thread
#     results = []
#     errors = []
    
#     print(f"\nTesting against: {BASE_URL}")
#     print(f"Sending {total_requests} concurrent requests ({num_threads} threads × {requests_per_thread} requests)...")
#     start_time = time.time()
    
#     with ThreadPoolExecutor(max_workers=num_threads) as executor:
#         # Submit all requests
#         futures = [executor.submit(make_health_request) for _ in range(total_requests)]
        
#         # Collect results as they complete
#         completed = 0
#         for future in as_completed(futures):
#             status_code, response_time, error_msg = future.result()
#             results.append(status_code)
#             if error_msg:
#                 errors.append(error_msg)
#             completed += 1
            
#             if completed % 20 == 0:
#                 print(f"  Completed {completed}/{total_requests} requests")
    
#     total_time = time.time() - start_time
    
#     # Count responses
#     success_count = sum(1 for code in results if code == 200)
#     rate_limited_count = sum(1 for code in results if code == 429)
#     error_count = sum(1 for code in results if code not in [200, 429])
    
#     print(f"\nResults after {total_time:.2f} seconds:")
#     print(f"  ✅ Success (200): {success_count}")
#     print(f"  ⛔ Rate Limited (429): {rate_limited_count}")
#     print(f"  ❌ Errors: {error_count}")
#     print(f"  📊 Requests/sec: {total_requests / total_time:.2f}")
    
#     if errors:
#         print(f"\nFirst error: {errors[0]}")
    
#     # Assertions
#     assert error_count == 0, f"Got {error_count} connection errors. Is the server running at {BASE_URL}?"
#     assert success_count > 0, "Should have some successful requests"
#     assert rate_limited_count > 0, "Should have rate-limited requests under concurrent load"
    
#     # The rate limit is 60/min, so even with concurrent requests,
#     # we should not exceed ~60 successful requests per minute
#     if total_time < 60:
#         max_expected_success = int((60 / 60) * total_time * 1.1)  # 1.1x buffer for timing variance
#         assert success_count <= max_expected_success + 10, \
#             f"Too many successful requests ({success_count}) for {total_time:.1f}s window"


# @pytest.mark.parametrize("threads,requests", [
#     (5, 20),   # Light load: 100 total requests
#     (10, 10),  # Medium load: 100 total requests  
#     (20, 5),   # Heavy load: 100 total requests
# ])
# def test_rate_limit_health_parametrized(threads: int, requests: int):
#     """Parametrized test for different concurrency levels.
    
#     Args:
#         threads: Number of concurrent threads
#         requests: Number of requests per thread
#     """
#     test_rate_limit_health_concurrent(num_threads=threads, requests_per_thread=requests)




# if __name__ == "__main__":
#     # Check if server is running
#     print("=" * 60)
#     print("Rate Limiter Test Suite")
#     print("=" * 60)
#     print(f"\nChecking if server is running at {BASE_URL}...")
    
#     if not check_server_running():
#         print(f"\n❌ Server is NOT running at {BASE_URL}")
#         print("\nTo start the server, run:")
#         print("  uv run uvicorn app.main:app")
#         print("\nOr to test against production:")
#         print("  export TEST_BASE_URL=https://verified.bitrecs.ai")
#         print("  python tests/test_rate_limiter.py")
#         exit(1)
    
#     print(f"✅ Server is running!\n")
    
#     # Run tests directly for quick testing
#     test_rate_limit_health_sequential()
#     print("\n" + "=" * 60 + "\n")
    
#     #test_rate_limit_health_concurrent(num_threads=10, requests_per_thread=10)
#     print("\n" + "=" * 60 + "\n")
    
#     # Uncomment to test recovery (takes 61+ seconds)
#     # test_rate_limit_recovery()
