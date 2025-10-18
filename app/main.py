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
import threading
import tracemalloc
from dotenv import load_dotenv
load_dotenv()
from app.d1 import D1Handler
from app.html_templates import HTMLTemplates
from app.llm_providers import LLMProvider, LLMProviderStats
from app.utils import is_valid_hotkey, load_version_info, verify_miner_request, verify_time
from app.metagraph_sync_manager import MetagraphSyncManager
from app.models import ChatCompletionRequest, SignedResponse
from cachetools import TTLCache
from typing import Union, Dict
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from fastapi.responses import JSONResponse, HTMLResponse
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, Header, HTTPException
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware

def get_platform():
    if os.environ.get('GOOGLE_CLOUD_PROJECT') and os.environ.get('K_SERVICE'):
        return 'gcp'
    elif os.environ.get('DO_APP_ID'):
        return 'do'
    else:
        return 'unknown'

log_level = logging.INFO
if get_platform() == 'gcp':   
    log_level = logging.DEBUG
    
logging.basicConfig(
    level=log_level,
    format='%(asctime)s | %(levelname)s | %(name)s:%(lineno)d - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

METAGRAPH_CACHE_DURATION = 900  # 15 minutes

verified_display_cache = None
verified_display_cache_timestamp = None
VERIFIED_DISPLAY_CACHE_DURATION = 1800

IS_VERIFIED_CACHE = TTLCache(maxsize=10000, ttl=900)  # 15 minutes
IS_VERIFIED_HOUR_DELTA = 4  # Look back this many hours for recent verification
PROVIDER_PING_CACHE = TTLCache(maxsize=10, ttl=3600)  # 1 hour

client = httpx.AsyncClient(
    timeout=httpx.Timeout(30.0),
    limits=httpx.Limits(
        max_connections=50,
        max_keepalive_connections=10,
        keepalive_expiry=15.0
    )
)

BT_NETWORK = os.environ.get("BT_NETWORK", "test")
BT_NETUID = int(os.environ.get("BT_NETUID", 296))
B64_PRIVATE_KEY = os.environ.get("B64_PRIVATE_KEY")
if not B64_PRIVATE_KEY:
    raise ValueError("B64_PRIVATE_KEY environment variable not set")
PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(base64.b64decode(B64_PRIVATE_KEY))
PUBLIC_KEY = PRIVATE_KEY.public_key()
MIN_ALPHA_STAKE = 100  # Minimum stake for alpha access

CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "")
CF_D1_TOKEN = os.environ.get("CF_D1_TOKEN", "")
CF_D1_DATABASE_ID = os.environ.get("CF_D1_DATABASE_ID", "")
if not any([CF_ACCOUNT_ID, CF_D1_TOKEN, CF_D1_DATABASE_ID]):
    raise ValueError("Missing one of CF_ACCOUNT_ID, CF_D1_TOKEN, CF_D1_DATABASE_ID in environment variables")

d1_client = D1Handler(
    account_id=CF_ACCOUNT_ID,
    token=CF_D1_TOKEN,
    database_id=CF_D1_DATABASE_ID
)

metagraph_manager = MetagraphSyncManager(
    network=BT_NETWORK,
    netuid=BT_NETUID,
    sync_interval=METAGRAPH_CACHE_DURATION
)
metagraph_snapshot = {"nodes": {}}


async def check_hotkey_stake(
    hotkey: str,
    stake: float
) -> bool:
    if hotkey is None or stake is None:
        return False
    snapshot, _ = metagraph_manager.get_snapshot()
    node = snapshot.get(hotkey)
    logger.info(f"check_hotkey_stake {hotkey} : {node['stake'] if node else 'N/A'}, required {stake}")
    return node["stake"] > stake if node else False


async def check_request_ip(
    hotkey: str,
    request_ip: str,
) -> bool:
    if hotkey is None or request_ip is None:
        return False
    snapshot, _ = metagraph_manager.get_snapshot()
    node = snapshot.get(hotkey)
    return node["ip"] == request_ip if node else False


def get_client_ip(request: Request) -> str:
    logger.debug(
        f"IP headers - x-real-ip: {request.headers.get('x-real-ip')}, "
        f"x-forwarded-for: {request.headers.get('x-forwarded-for')}, "
        f"do-connecting-ip: {request.headers.get('do-connecting-ip')}")
     
    if "do-connecting-ip" in request.headers:
        return request.headers.get('do-connecting-ip').strip()
    if "x-forwarded-for" in request.headers:
        forwarded_for = request.headers.get('x-forwarded-for')
        ips = [ip.strip() for ip in forwarded_for.split(",")]
        if ips:
            return ips[0]
    if "x-real-ip" in request.headers:
        return request.headers["x-real-ip"].strip()
    if request.client:
        return str(request.client.host)
    return "unknown"


async def refresh_provider_pings():
    while True:
        try:
            logger.info("Refreshing provider pings cache")
            output = LLMProviderStats.print_all_providers_info_html()
            PROVIDER_PING_CACHE["provider_infos_html"] = output
            logger.info(f"Provider pings cache updated: {len(output)} characters")            
        except Exception as e:
            logger.error(f"Error refreshing provider pings: {e}")
        await asyncio.sleep(1800)  # Refresh every 30 minutes



limiter = Limiter(key_func=get_client_ip)

@asynccontextmanager
async def lifespan(app: FastAPI):    
    logger.info("Server starting up")
    tracemalloc.start()    
    app.state.thread_pool = ThreadPoolExecutor(
        max_workers=2,
        thread_name_prefix="D1-Writer"
    )    
    app.state.last_updated = None
    app.state.total_requests = 0
    app.state.exceptions = 0    
    # Start the metagraph manager
    metagraph_manager.start()
    
    # Background task to restart manager if dead
    async def restart_manager():
        logger.info("Starting restart_manager task")
        while True:
            try:
                if not metagraph_manager._process or not metagraph_manager._process.is_alive():
                    logger.warning("Restarting dead MetagraphSyncManager process")
                    metagraph_manager.start()
                snapshot, _ = metagraph_manager.get_snapshot()
                metagraph_snapshot["nodes"] = snapshot
                logger.info(f"Metagraph snapshot updated with {len(snapshot)} nodes")
            except Exception as e:
                logger.error(f"Error in restart_manager: {e}")
            await asyncio.sleep(60)

    app.state.restart_task = asyncio.create_task(restart_manager())
    app.state.refresh_task = asyncio.create_task(refresh_provider_pings())

    try:
        yield
    finally:
        logger.info("Starting shutdown...")
        app.state.restart_task.cancel()
        app.state.refresh_task.cancel()
        try:
            await app.state.restart_task
            await app.state.refresh_task
        except asyncio.CancelledError:
            pass
        
        # Stop metagraph manager
        metagraph_manager.stop()
        await client.aclose()
        logger.info("Shutting down D1 writer thread pool...")
        app.state.thread_pool.shutdown(wait=True, cancel_futures=False)
        gc.collect()
        logger.info(f"Shutdown complete. Final thread count: {threading.active_count()}")


version_info = load_version_info()
app_version = version_info if version_info else "0.8.8"

app = FastAPI(
    title="Bitrecs Verified Inference",
    version=app_version,
    description="Proxy for verified inference with Bittensor integration, providing secure LLM completions.",
    debug=False,
    lifespan=lifespan,
    # openapi_url="/api-docs.json"  # Optional: Change OpenAPI JSON path
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'none'; object-src 'none';"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    return response


@app.get("/")
@limiter.limit("60/minute")
async def read_root(request: Request):
    ts = str(int(time.time()))
    request_ip = get_client_ip(request)
    logger.info(f"Root endpoint accessed from IP {request_ip} at {ts}")
    return JSONResponse(
        status_code=200,
        content={"message": "Bitrecs Verified 🤝 Inference ",
                 "ts": str(ts), 
                 "network": BT_NETWORK,
                 "uid": BT_NETUID,
                 "total_requests": app.state.total_requests,
                 "exceptions": app.state.exceptions, 
                 "min_alpha_stake": MIN_ALPHA_STAKE})


@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    client_ip = get_client_ip(request)
    logger.info(f"Health check from IP: {client_ip}")  
    snapshot, synced_at = metagraph_manager.get_snapshot()
    node_count = len(snapshot)
    thread_count = threading.active_count()
    message = "OK"
    if thread_count > 10:
        message = "WARNING: High thread count"
        logger.warning(f"High thread count: {thread_count}")
        logger.warning("Active threads:")
        for thread in threading.enumerate():
            logger.warning(f"  - {thread.name} (daemon={thread.daemon}, alive={thread.is_alive()})")

    if thread_count > 50:
        message = "CRITICAL: Very high thread count"
        logger.error(f"CRITICAL: Thread count {thread_count}")            
    
    current, peak = tracemalloc.get_traced_memory()
    version_file = load_version_info()
    return {
        "status": "healthy",
        "nodes": node_count,
        "total_requests": app.state.total_requests,
        "exceptions": app.state.exceptions,
        "threads": thread_count,
        "metagraph_last_synced": int(synced_at) if synced_at else None,
        "metagraph_age_seconds": round(time.time() - synced_at, 2) if synced_at else None,        
        "thread_pool_workers": len(app.state.thread_pool._threads) if hasattr(app.state.thread_pool, '_threads') else 0,
        "memory_current_mb": round(current / 1024 / 1024, 2),
        "memory_peak_mb": round(peak / 1024 / 1024, 2),        
        "message": message,
        "version": version_file.strip() if version_file else "N/A"
    }


@app.get("/public_key")
@limiter.limit("120/minute")
async def get_public_key(request: Request):
    client_ip = get_client_ip(request)
    logger.info(f"Public key requested from IP: {client_ip}")
    public_key_raw_bytes = PUBLIC_KEY.public_bytes(
        encoding=Encoding.Raw,
        format=PublicFormat.Raw
    )
    public_key_hex = public_key_raw_bytes.hex()
    return JSONResponse(status_code=200, content={"public_key": public_key_hex})


@app.get("/log")
@limiter.limit("60/minute")
async def verified_log(request: Request):
    global verified_display_cache, verified_display_cache_timestamp
    request_ip = get_client_ip(request)
    ts = str(int(time.time()))    
    logger.info(f"verified_log endpoint accessed from IP {request_ip} at {ts}")    
    current_time = time.time()
    if (verified_display_cache is not None and
        verified_display_cache_timestamp is not None and
        (current_time - verified_display_cache_timestamp) < VERIFIED_DISPLAY_CACHE_DURATION):        
        return HTMLResponse(content=verified_display_cache)    
    # Fetch fresh data
    verified = await d1_client.select_all_signed_responses(top=250)    
    html_content = HTMLTemplates.render_verified_display(
        verified=verified,
        bt_network=BT_NETWORK,
        bt_netuid=BT_NETUID
    )
    # Update cache
    verified_display_cache = html_content
    verified_display_cache_timestamp = current_time
    logger.info("Updated verified_log cache")
    return HTMLResponse(content=html_content)



@app.get("/providers")
@limiter.limit("60/minute")
async def provider_log(request: Request):
    request_ip = get_client_ip(request)
    logger.info(f"providers endpoint accessed from IP {request_ip}")
    #its already cached
    cache_key = "provider_infos_html"
    if cache_key in PROVIDER_PING_CACHE:
        logger.info(f"providers endpoint accessed from IP {request_ip} - using cached data")
        infos = PROVIDER_PING_CACHE[cache_key]
        return HTMLResponse(content=infos)
    logging.warning("Cache Broken")
    return HTMLResponse(content="<pre>Cache Empty</pre>")


@app.get("/is_verified")
@limiter.limit("120/minute")
async def is_verified(request: Request, hotkey: str):
    client_ip = get_client_ip(request)
    logger.info(f"is_verified called for hotkey {hotkey} from IP: {client_ip}")
    if not hotkey:
        raise HTTPException(400, "Missing hotkey parameter")
    if not is_valid_hotkey(hotkey):
        raise HTTPException(400, "Invalid hotkey format")    
    
    cached_result = IS_VERIFIED_CACHE.get(hotkey)
    if cached_result:
        logger.info(f"Cache hit for hotkey {hotkey}")
        return JSONResponse(status_code=200, content=cached_result)
    
    since_date = datetime.now(timezone.utc) - timedelta(hours=IS_VERIFIED_HOUR_DELTA)
    latest = await d1_client.select_signed_responses_by_hotkey_since(hotkey=hotkey, since_date=since_date, top=1)
    if not latest:
        result = {"verified": False, "hotkey": hotkey, "message": "No verified responses found"}
    else:
        latest_response = latest[0]
        timestamp_str = latest_response.get("timestamp")
        model = latest_response.get("model")
        provider = latest_response.get("provider")
        #logger.info(f"Latest response timestamp: {timestamp_str}, model: {model}, provider: {provider}")
        if not timestamp_str:
            result = {"verified": False, "hotkey": hotkey, "message": "No timestamp in latest response"}
        else:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                result = {"verified": False, "message": "Invalid timestamp format"}
            else:
                age_seconds = (datetime.now(timezone.utc) - timestamp).total_seconds()
                if age_seconds > IS_VERIFIED_HOUR_DELTA * 3600:
                    result = {"verified": False, "hotkey": hotkey, "message": f"Latest response is older than {IS_VERIFIED_HOUR_DELTA} hours"}
                else:
                    result = {"verified": True, "hotkey": hotkey, "message": f"Hotkey has a recent verified response (since {IS_VERIFIED_HOUR_DELTA} hours ago)", "latest_timestamp": timestamp_str, "latest_model": model, "latest_provider": provider}
    
    IS_VERIFIED_CACHE[hotkey] = result
    logger.info(f"\033[32mCached result for hotkey {hotkey}: {result['verified']}\033[0m")
    return JSONResponse(status_code=200, content=result)



@app.post("/v1/chat/completions", response_model=SignedResponse)
@limiter.limit("120/minute")
async def forward_proxy_request(
    request: Request,
    completion_request: ChatCompletionRequest,
    authorization: str = Header(),  
    x_hotkey: str = Header(),
    x_provider: str = Header(),
    x_nonce: str = Header(),
    x_signature: str = Header(),
    x_timestamp: str = Header()
) -> SignedResponse:
    
    client_ip = get_client_ip(request)    
    request_id = str(uuid.uuid4())
    logger.info(f"Request {request_id} from hotkey: {x_hotkey}, IP: {client_ip}, model: {completion_request.model}")
    st = time.perf_counter()

    try:
        if not authorization or not authorization.startswith("Bearer "):
            logger.error(f"Request {request_id} missing or invalid Authorization header")
            raise HTTPException(401, "MISSING OR INVALID AUTHORIZATION HEADER")
        
        if 1==1:
            if not verify_time(int(x_timestamp)):
                logger.error(f"\033[31mRequest {request_id} failed timestamp verification: {x_timestamp} \033[0m")
                raise HTTPException(401, "INVALID REQUEST: TIMESTAMP VERIFICATION FAILED")
        if 1==1:
            payload_data = json.loads((await request.body()).decode('utf-8'))
            verified = verify_miner_request(
                hotkey=x_hotkey,
                provider=x_provider,
                nonce=x_nonce,
                signature=x_signature,
                payload=payload_data,
                ts=x_timestamp
            )
            if not verified:
                logger.error(f"\033[31mRequest {request_id} failed signature verification for hotkey {x_hotkey} \033[0m")
                #raise HTTPException(401, "INVALID REQUEST: SIGNATURE VERIFICATION FAILED")
            else:
                logger.info(f"\033[32mRequest {request_id} passed signature verification for hotkey {x_hotkey} \033[0m")
        
        snapshot, _ = metagraph_manager.get_snapshot()
        if not snapshot:
            logger.error(f"Metagraph snapshot is empty for request {request_id}")
            raise HTTPException(503, "Service unavailable: Metagraph data not ready")

        if 1==1:
            min_stake = MIN_ALPHA_STAKE
            min_stake = 0
            if not await check_hotkey_stake(x_hotkey, min_stake):
                logger.warning(f"Hotkey {x_hotkey} does not have sufficient stake ({min_stake}) in the metagraph")
                raise HTTPException(401, f"INVALID REQUEST: INSUFFICIENT STAKE - min {min_stake}")
        if 1==2:
            if not await check_request_ip(x_hotkey, client_ip):
                logger.warning(f"Request IP {client_ip} does not match hotkey {x_hotkey}'s axon IP")
                raise HTTPException(401, "INVALID REQUEST: IP MISMATCH")
    
  
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
            case LLMProvider.CLAUDE:
                url = "https://api.anthropic.com/v1/chat/completions"
            case _:
                logger.warning(f"Unknown provider for request {request_id}")
                raise HTTPException(400, "Unknown provider")

        payload = completion_request.model_dump(exclude_unset=True)
        response = await client.post(
            url,
            json=payload,
            headers={"Authorization": authorization, 
                     "Referer": "verified.bitrecs.ai", 
                     "X-Title": "Bitrecs Verified Proxy",
                     "X-Request-ID": request_id}
        )
        
        if response.status_code != 200:
            logger.error(f"Upstream error for request {request_id}: {response.status_code}")
            logger.error(f"Response content: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        proof = {
            "request_hash": hashlib.sha256(json.dumps(completion_request.model_dump()).encode()).hexdigest(),
            "response_hash": hashlib.sha256(response.content).hexdigest(),
            "hotkey": x_hotkey,
            "model": completion_request.model,
            "provider": str(provider),
            "unique_id": request_id
        }
        
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

        # Write to D1 in background thread
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
        logger.info(f"\033[32mRequest {request_id} took {duration:.2f} seconds on {provider.name}\033[0m")
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
@limiter.limit("120/minute")
async def verify_endpoint(
    request: Request,
    response: SignedResponse
) -> Dict[str, Union[bool, str, None]]:
    client_ip = get_client_ip(request)
    logger.info(f"Verify endpoint called from IP: {client_ip}")
    try:        
        PUBLIC_KEY.verify(
            base64.b64decode(response.signature), 
            json.dumps(response.proof, sort_keys=True).encode()
        )
        logger.info(f"verify_endpoint Signature valid for hotkey {response.proof.get('hotkey')}, unique_id {response.proof.get('unique_id')}")
        return {
            "valid": True,
            "hotkey": response.proof.get("hotkey"),
            "timestamp": response.timestamp,  # Use response.timestamp instead of response.proof.get("timestamp")
            "model": response.proof.get("model"),
            "provider": response.proof.get("provider"),
            "unique_id": response.proof.get("unique_id")
        }
    except Exception as e:
        logger.warning(f"Verification failed: {str(e)}")
        return {
            "valid": False,
            "error": "Invalid signature"
        }