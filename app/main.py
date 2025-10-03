from concurrent.futures import ThreadPoolExecutor
import os
import gc
import time
import json
import uuid
import hashlib
import base64
import httpx
import asyncio
import logging
import traceback
import threading
import concurrent
from dotenv import load_dotenv
load_dotenv()

from app.llm_providers import LLMProvider
from app.models import ChatCompletionRequest, SignedResponse
from app.utils import read_verified_from_file
from app.d1 import D1Handler
from app.html_templates import HTMLTemplates
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse, HTMLResponse
from typing import Union, Dict
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, Header, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fiber.chain import interface
from fiber.chain.metagraph import Metagraph  # Use fiber's Metagraph class

logger = logging.getLogger(__name__)

# Use fiber's Metagraph instead of manual management
metagraph: Metagraph = None
metagraph_lock = threading.Lock()
METAGRAPH_CACHE_DURATION = 600  # 10 minutes

verified_display_cache = None
verified_display_cache_timestamp = None
VERIFIED_DISPLAY_CACHE_DURATION = 900  # 15 minutes

# Configure httpx client with explicit limits
client = httpx.AsyncClient(
    timeout=httpx.Timeout(60.0),
    limits=httpx.Limits(
        max_connections=10,
        max_keepalive_connections=5,
        keepalive_expiry=30.0
    )
)

BT_NETWORK = os.environ.get("BT_NETWORK", "test")
BT_NETUID = int(os.environ.get("BT_NETUID", 296))
B64_PRIVATE_KEY = os.environ.get("B64_PRIVATE_KEY")
if not B64_PRIVATE_KEY:
    raise ValueError("B64_PRIVATE_KEY environment variable not set")
PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(base64.b64decode(B64_PRIVATE_KEY))
PUBLIC_KEY = PRIVATE_KEY.public_key()

CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
CF_D1_TOKEN = os.environ.get("CF_D1_TOKEN")
CF_D1_DATABASE_ID = os.environ.get("CF_D1_DATABASE_ID")
if not any([CF_ACCOUNT_ID, CF_D1_TOKEN, CF_D1_DATABASE_ID]):
    raise ValueError("Missing one of CF_ACCOUNT_ID, CF_D1_TOKEN, CF_D1_DATABASE_ID in environment variables")
d1_client = D1Handler(
    account_id=CF_ACCOUNT_ID,
    token=CF_D1_TOKEN,
    database_id=CF_D1_DATABASE_ID
)

MIN_ALPHA_STAKE = 100  # Minimum stake for alpha access

# Shutdown event
shutdown_event = threading.Event()


def get_client_ip(request: Request) -> str:    
    if "x-real-ip" in request.headers:
        return request.headers["x-real-ip"].strip()
    if "x-forwarded-for" in request.headers:
        forwarded_for = request.headers["x-forwarded-for"].strip()
        ips = [ip.strip() for ip in forwarded_for.split(",")]
        if ips:            
            return ips[0]
    if request.client:
        return str(request.client.host)
    return get_remote_address(request)


def metagraph_background_worker():
    """Background thread worker - recreate metagraph each sync to avoid leaks."""
    global metagraph
    
    logger.info("Metagraph worker started")
    
    network = BT_NETWORK
    netuid = BT_NETUID
    
    while not shutdown_event.is_set():
        try:
            logger.info("Starting metagraph sync")
            logger.info(f'Active threads: {threading.active_count()}')
            
            # Create fresh metagraph (this auto-syncs on init)
            new_metagraph = Metagraph(
                netuid=netuid,
                substrate=interface.get_substrate(subtensor_network=network)
            )
            
            logger.info(f'Synced {len(new_metagraph.nodes)} neurons')
            
            # Swap in new metagraph and shutdown old one
            with metagraph_lock:
                old_metagraph = metagraph
                metagraph = new_metagraph
            
            # Shutdown old metagraph outside the lock
            if old_metagraph is not None:
                try:
                    old_metagraph.shutdown()
                    del old_metagraph
                except Exception as e:
                    logger.error(f"Error shutting down old metagraph: {e}")
            
            gc.collect()
            logger.info(f'Active threads after sync: {threading.active_count()}')
            
        except Exception as e:
            logger.error(f"Error in metagraph sync: {e}")
            logger.error(traceback.format_exc())
        
        # Sleep in chunks for quick shutdown
        for _ in range(METAGRAPH_CACHE_DURATION // 10):
            if shutdown_event.is_set():
                break
            time.sleep(10)
    
    logger.info("Metagraph worker stopped")


# Start background thread as daemon (like fiber does)
metagraph_thread = threading.Thread(
    target=metagraph_background_worker, 
    daemon=True,  # Changed to daemon=True
    name="MetagraphWorker"
)
metagraph_thread.start()


async def check_hotkey_stake(
    hotkey: str,
    stake: float
) -> bool:
    """Check if hotkey has stake in the metagraph."""
    if metagraph is None or hotkey is None or stake is None:
        return False
    
    with metagraph_lock:
        node = metagraph.nodes.get(hotkey)  # Changed from nodes_by_hotkey to nodes
        return node.stake > stake if node else False  # Changed from alpha_stake to stake


async def check_request_ip(
    hotkey: str,
    request_ip: str,
) -> bool:
    """Check if request IP matches hotkey's axon IP."""
    if metagraph is None or hotkey is None or request_ip is None:
        return False
    
    with metagraph_lock:
        node = metagraph.nodes.get(hotkey)  # Changed from nodes_by_hotkey to nodes
        return node.ip == request_ip if node else False


@asynccontextmanager
async def lifespan(app: FastAPI):    
    logger.info("Server starting up")
    
    # Create bounded thread pool with daemon threads
    app.state.thread_pool = ThreadPoolExecutor(
        max_workers=2,  # Only 2 workers instead of 4
        thread_name_prefix="D1-Writer"
    )
    
    app.state.last_updated = None
    app.state.total_requests = 0
    app.state.exceptions = 0
    
    try:
        yield
    finally:
        logger.info("Starting shutdown...")
        
        # Signal background thread to stop
        shutdown_event.set()
        
        # Call shutdown on metagraph
        if metagraph is not None:
            logger.info("Shutting down metagraph...")
            metagraph.shutdown()
        
        # Wait for daemon thread
        if metagraph_thread.is_alive():
            logger.info("Waiting for metagraph thread to stop...")
            metagraph_thread.join(timeout=15)
        
        await client.aclose()
        
        # Shutdown thread pool properly - wait for tasks but with timeout
        logger.info("Shutting down D1 writer thread pool...")
        app.state.thread_pool.shutdown(wait=True, cancel_futures=False)
        
        gc.collect()
        logger.info(f"Shutdown complete. Final thread count: {threading.active_count()}")


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)

# Fix: Initialize limiter WITHOUT creating background threads
limiter = Limiter(
    key_func=get_client_ip,
    storage_uri="memory://",  # Add explicit in-memory storage
    enabled=True
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    with metagraph_lock:
        node_count = len(metagraph.nodes) if metagraph else 0
    thread_count = threading.active_count()
    
    # Log all active threads for debugging
    if thread_count > 5:
        logger.warning(f"High thread count: {thread_count}")
        logger.warning("Active threads:")
        for thread in threading.enumerate():
            logger.warning(f"  - {thread.name} (daemon={thread.daemon}, alive={thread.is_alive()})")

    if thread_count > 50:
        logger.error(f"CRITICAL: Thread count {thread_count}")
    
    return {
        "status": "healthy",
        "nodes": node_count,
        "total_requests": app.state.total_requests,
        "exceptions": app.state.exceptions,
        "threads": thread_count,
        "thread_pool_workers": len(app.state.thread_pool._threads) if hasattr(app.state.thread_pool, '_threads') else 0
    }


@app.get("/public_key")
@limiter.limit("180/minute")
async def get_public_key(request: Request):
    public_key_raw_bytes = PUBLIC_KEY.public_bytes(
        encoding=Encoding.Raw,
        format=PublicFormat.Raw
    )
    public_key_hex = public_key_raw_bytes.hex()
    return JSONResponse(status_code=200, content={"public_key": public_key_hex})


@app.get("/verified_log")
@limiter.limit("30/minute")
async def verified_log(request: Request):
    ts = str(int(time.time()))
    request_ip = get_client_ip(request)
    logger.info(f"verified_log endpoint accessed from IP {request_ip} at {ts}")
    try:
        recs = await read_verified_from_file() or []
        recs_dicts = [r.model_dump() for r in recs][:5_000]
        return JSONResponse(
            status_code=200,
            content={
                "message": "Hello from Verified Inf Proxy",
                "ts": str(ts),
                "network": BT_NETWORK,
                "netuid": BT_NETUID,
                "verified": recs_dicts
            }
        )
    except Exception as e:
        logger.error(f"Error in /verified_log endpoint: {str(e)}")
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})


@app.get("/verified_display")
@limiter.limit("30/minute")
async def verified_display(request: Request):
    global verified_display_cache, verified_display_cache_timestamp
    
    ts = str(int(time.time()))
    request_ip = get_client_ip(request)
    logger.info(f"verified_display endpoint accessed from IP {request_ip} at {ts}")
    
    # Check if we have cached HTML and it's still valid
    current_time = time.time()
    if (verified_display_cache is not None and
        verified_display_cache_timestamp is not None and
        (current_time - verified_display_cache_timestamp) < VERIFIED_DISPLAY_CACHE_DURATION):
        logger.info("Returning cached verified_display HTML")
        return HTMLResponse(content=verified_display_cache)
    
    # Fetch fresh data
    verified = await d1_client.select_all_signed_responses(top=100)
    print(f"Fetched {len(verified)} verified records from D1")

    html_content = HTMLTemplates.render_verified_display(
        verified=verified,
        bt_network=BT_NETWORK,
        bt_netuid=BT_NETUID
    )
    
    # Update cache
    verified_display_cache = html_content
    verified_display_cache_timestamp = current_time
    logger.info("Updated verified_display cache")

    return HTMLResponse(content=html_content)


@app.post("/v1/chat/completions", response_model=SignedResponse)
@limiter.limit("60/minute")
async def forward_proxy_request(
    request: Request,
    completion_request: ChatCompletionRequest,
    authorization: str = Header(),  
    x_hotkey: str = Header(),
    x_provider: str = Header()
) -> SignedResponse:
    request_id = str(uuid.uuid4())    
    client_ip = get_client_ip(request)
    logger.info(f"Request {request_id} from hotkey: {x_hotkey}, IP: {client_ip}, model: {completion_request.model}")
    st = time.perf_counter()
    
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning(f"Request {request_id} missing or invalid Authorization header")
        raise HTTPException(401, "MISSING OR INVALID AUTHORIZATION HEADER")
    
    if 1==2:
        if not await check_hotkey_stake(x_hotkey, MIN_ALPHA_STAKE):
            logger.warning(f"Hotkey {x_hotkey} does not have sufficient stake in the metagraph")
            raise HTTPException(400, "INVALID REQUEST: INSUFFICIENT STAKE")
    if 1==2:
        if not await check_request_ip(x_hotkey, client_ip):
            logger.warning(f"Request IP {client_ip} does not match hotkey {x_hotkey}'s axon IP")
            raise HTTPException(400, "INVALID REQUEST: IP MISMATCH")
    
    try:
        provider = LLMProvider.from_str(x_provider)
        match provider:
            case LLMProvider.CHAT_GPT:                
                if completion_request.model.startswith("gpt-5"):
                    url = "https://api.openai.com/v1/responses"
                else:
                    url = "https://api.openai.com/v1/chat/completions"
            case LLMProvider.OPEN_ROUTER:
                url = "https://openrouter.ai/api/v1/chat/completions"
            case LLMProvider.GEMINI:
                url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            case LLMProvider.CHUTES:
                url = "https://llm.chutes.ai/v1/chat/completions"
            case LLMProvider.GROQ:
                url = "https://api.groq.com/openai/v1/chat/completions"
            case LLMProvider.CEREBRAS:
                url = "https://api.cerebras.ai/v1/chat/completions"
            case LLMProvider.GROK:  
                url = "https://api.x.ai/v1/chat/completions"
            case _:
                logger.warning(f"Unknown provider for request {request_id}")
                raise HTTPException(400, "Unknown provider")

        payload = completion_request.model_dump(exclude_unset=True)        
        response = await client.post(
            url,
            json=payload,
            headers={"Authorization": authorization}
        )
        
        if response.status_code != 200:
            logger.error(f"Upstream error for request {request_id}: {response.status_code}")
            logger.error(f"Response content: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)

        # Core proof (what gets signed - NO time data)
        proof = {
            "request_hash": hashlib.sha256(json.dumps(completion_request.model_dump()).encode()).hexdigest(),
            "response_hash": hashlib.sha256(response.content).hexdigest(),
            "hotkey": x_hotkey,
            "model": completion_request.model,
            "provider": str(provider),
            "unique_id": request_id
        }

        # Sign only the core proof
        serialized_proof = json.dumps(proof, sort_keys=True).encode()
        signature = PRIVATE_KEY.sign(serialized_proof)
        
        # Time metadata (NOT signed)
        timestamp = datetime.now(timezone.utc).isoformat()
        ttl = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        signed_response = SignedResponse(
            response=response.json(),
            proof=proof,
            signature=base64.b64encode(signature).decode(),
            timestamp=timestamp,
            ttl=ttl
        )
        et = time.perf_counter()
        duration = et - st

        # Submit to thread pool - it will reuse threads properly
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            app.state.thread_pool,  # Use the bounded pool
            d1_client.insert_signed_response,
            signed_response,
            request_id,
            duration,
            str(provider)
        )

        app.state.total_requests += 1
        logger.info(f"Request {request_id} took {duration:.2f} seconds")
        return signed_response
    
    except httpx.TimeoutException:
        logger.error(f"Timeout for request {request_id}")
        app.state.exceptions += 1
        raise HTTPException(504, "Upstream timeout")
    except httpx.HTTPError as e:
        logger.error(f"HTTP error for request {request_id}: {str(e)}")
        app.state.exceptions += 1
        raise HTTPException(502, f"Upstream error: {str(e)}")
    except HTTPException as e:
        app.state.exceptions += 1
        raise e
    except Exception as e:
        logger.error(f"Unexpected error for request {request_id}: {str(e)}")
        app.state.exceptions += 1
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/verify")
@limiter.limit("60/minute")
async def verify_endpoint(
    request: Request,
    response: SignedResponse
) -> Dict[str, Union[bool, str]]:
    try:        
        PUBLIC_KEY.verify(
            base64.b64decode(response.signature), 
            json.dumps(response.proof, sort_keys=True).encode()
        )
        return {
            "valid": True,
            "hotkey": response.proof.get("hotkey"),
            "timestamp": response.proof.get("timestamp"),
            "model": response.proof.get("model"),
            "provider": response.proof.get("provider")
        }
    except Exception as e:
        logger.warning(f"Verification failed: {str(e)}")
        return {
            "valid": False,
            "error": "Invalid signature"
        }