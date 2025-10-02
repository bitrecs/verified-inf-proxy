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
from app.utils import read_verified_from_file, write_verified_to_file
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
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives import serialization
from fiber.chain import interface
from fiber.chain.fetch_nodes import get_nodes_for_netuid

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

metagraph_cache = None
metagraph_cache_timestamp = None
CACHE_DURATION = 600 # 10 minutes

verified_display_cache = None
verified_display_cache_timestamp = None
VERIFIED_DISPLAY_CACHE_DURATION = 300  # 5 minutes

client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))


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
    return get_remote_address(request)  # Fallback to slowapi's method


async def get_metagraph_data() -> dict:
    """Get the metagraph data with cache."""
    global metagraph_cache, metagraph_cache_timestamp

    # Check if we have cached data and it's still valid
    current_time = time.time()
    if (metagraph_cache is not None and
        metagraph_cache_timestamp is not None and
        (current_time - metagraph_cache_timestamp) < CACHE_DURATION):
        logger.info("Returning cached metagraph data")
        return metagraph_cache

    substrate = None
    try:        
        network = BT_NETWORK
        netuid = BT_NETUID
        if not network or netuid is None:
            raise ValueError("BT_NETWORK or BT_NETUID environment variables not set")

        logger.info(f'Fetching fresh metagraph data for {network}:{netuid}...')
        logger.info(f'Active threads before fetch: {threading.active_count()}')
        
        # Create a fresh substrate connection for this fetch, then close it
        loop = asyncio.get_event_loop()
        substrate = await loop.run_in_executor(
            None,
            lambda: interface.get_substrate(subtensor_network=network)
        )
        
        # Fetch nodes in executor to avoid blocking
        nodes = await loop.run_in_executor(
            None,
            lambda: get_nodes_for_netuid(substrate=substrate, netuid=netuid)
        )
        
        # Get block info
        head = await loop.run_in_executor(
            None,
            lambda: substrate.get_block()
        )
        block_number = head['header']['number']
        
        # Build data structure
        data = {
            'uids': [],
            'network_info': {
                'netuid': netuid,
                'network': network,
                'block': block_number,
                'total_neurons': len(nodes),
                'timestamp': datetime.now().isoformat()
            },
            'aggregated_stats': {}
        }
        
        neurons = []
        for node in nodes:
            neurons.append({
                'uid': node.node_id,
                'hotkey': node.hotkey,
                'stake': node.stake,
                'axon_ip': node.ip,
                'axon_port': node.port
            })  
             
        data['uids'] = neurons
        total_neurons = len(data['uids'])
        data['aggregated_stats'] = {
            'total_neurons': total_neurons
        }        
        
        logger.info(f'Successfully processed {total_neurons} neurons from block {block_number}')
        
        metagraph_result = {
            'uids': data['uids'],
            'by_hotkey': {neuron['hotkey']: neuron for neuron in data['uids']},
            'by_ip': {neuron['axon_ip']: neuron for neuron in data['uids']},
            'network_info': data['network_info'],
            'aggregated_stats': data['aggregated_stats']
        }

        # Update cache
        metagraph_cache = metagraph_result
        metagraph_cache_timestamp = time.time()
        
        return metagraph_result
        
    except Exception as e:
        logger.error(f'Error fetching metagraph data: {e}')
        logger.error(f'Traceback: {traceback.format_exc()}')
        return None
    
    finally:
        # CRITICAL: Always close substrate connection after use
        if substrate is not None:
            try:
                logger.info("Closing substrate connection")
                
                # Close websocket first if it exists (before calling substrate.close())
                if hasattr(substrate, 'websocket') and substrate.websocket:
                    try:
                        substrate.websocket.close()
                        logger.info("Closed websocket")
                    except Exception as e:
                        logger.warning(f"Error closing websocket: {e}")
                
                # Now close the substrate interface (this may try to access self.ws in __del__)
                if hasattr(substrate, 'close'):
                    try:
                        substrate.close()
                        logger.info("Closed substrate interface")
                    except Exception as e:
                        logger.warning(f"Error closing substrate interface: {e}")
                
                # Don't clear __dict__ - let Python's garbage collector handle it naturally
                # This prevents the AttributeError in __del__
                
            except Exception as e:
                logger.error(f"Error during substrate cleanup: {e}")
            finally:
                # Set to None to allow garbage collection
                substrate = None
        
        # Aggressive garbage collection
        for _ in range(3):
            gc.collect()
        
        logger.info(f"Garbage collected objects after metagraph fetch")
        logger.info(f'Active threads after fetch: {threading.active_count()}')


async def update_metagraph_data(app: FastAPI):
    """Background task to update metagraph data periodically."""
    global metagraph_cache, metagraph_cache_timestamp
    
    while True:
        try:
            logger.info(f"Starting metagraph refresh. Active threads: {threading.active_count()}")
            
            # Store reference to old cache BEFORE fetching new data
            old_cache = metagraph_cache
            old_timestamp = metagraph_cache_timestamp
            
            # Fetch new data
            result = await get_metagraph_data()
            
            if result is not None:
                # get_metagraph_data() already updated the globals, but let's be explicit
                app.state.last_updated = datetime.now(timezone.utc)
                
                # Clean up old cache (now it's actually different from metagraph_cache)
                if old_cache is not None and old_cache is not metagraph_cache:
                    try:
                        old_cache.clear()
                        del old_cache
                    except Exception as e:
                        logger.warning(f"Error clearing old cache: {e}")
                
                if old_timestamp is not None:
                    del old_timestamp
                
                # Force garbage collection
                for _ in range(2):
                    gc.collect()
                    
                logger.info(f"Metagraph updated successfully. Active threads: {threading.active_count()}")
            else:
                logger.warning("Failed to fetch metagraph data, keeping existing cache")
        
        except Exception as e:
            logger.error(f"Error in update_metagraph_data: {e}")
            logger.error(traceback.format_exc())
        
        # Wait before next refresh
        logger.info(f"Sleeping for {CACHE_DURATION} seconds. Active threads: {threading.active_count()}")
        await asyncio.sleep(CACHE_DURATION)


async def check_hotkey_stake(
    metagraph: dict,
    hotkey: str,
    stake: float
) -> bool:
    """Check if hotkey has stake in the metagraph."""
    if metagraph is None or hotkey is None or stake is None:
        return False
    neuron = metagraph['by_hotkey'].get(hotkey)
    return neuron['stake'] > stake if neuron else False

async def check_request_ip(
    metagraph: dict,
    hotkey: str,
    request_ip: str,
) -> bool:
    """Check if request IP matches hotkey's axon IP."""
    if metagraph is None or hotkey is None or request_ip is None:
        return False
    neuron = metagraph['by_hotkey'].get(hotkey)
    return neuron['axon_ip'] == request_ip if neuron else False


@asynccontextmanager
async def lifespan(app: FastAPI):    
    logger.info("Server starting up")        
    app.state.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    app.state.last_updated = None
    app.state.total_requests = 0
    app.state.exceptions = 0
    
    logger.info("Creating metagraph data task")
    loaded_metagraph = asyncio.create_task(update_metagraph_data(app))
    try:
        yield
    finally:
        logger.info("Starting shutdown cleanup...")
        # Cancel background tasks
        loaded_metagraph.cancel()        
        await asyncio.gather(loaded_metagraph, return_exceptions=True)
        
        await client.aclose()
        app.state.thread_pool.shutdown(wait=True)
        
        # Wait for threads to settle
        for i in range(10):
            active_threads = threading.active_count()
            if active_threads <= 1:
                logger.info(f"All threads terminated successfully")
                break
            logger.warning(f"Waiting for {active_threads} threads to terminate... (attempt {i+1}/10)")
            await asyncio.sleep(1)
        
        # Final cleanup
        gc.collect()
        logger.info(f"Shutdown complete. Final thread count: {threading.active_count()}")


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)
limiter = Limiter(key_func=get_client_ip)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    node_count = len(metagraph_cache['uids']) if metagraph_cache else 0
    updated = app.state.last_updated.isoformat() if app.state.last_updated else "never"
    logger.info(f"Health check - network: {BT_NETWORK}, uid: {BT_NETUID}, nodes: {node_count}, last updated: {updated}")
    return {"status": "healthy",
            "nodes": node_count,
            "last_updated": updated,
            "total_requests": app.state.total_requests,
            "exceptions": app.state.exceptions}


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
    # First make sure hotkey has stake in the metagraph, and the request ip matches that hotkey's axon ip
    if 1==2:
        if not await check_hotkey_stake(metagraph_cache, x_hotkey, 100):  # Pass metagraph_cache
            logger.warning(f"Hotkey {x_hotkey} does not have sufficient stake in the metagraph")
            raise HTTPException(400, "INVALID REQUEST: INSUFFICIENT STAKE")
    if 1==2:
        if not await check_request_ip(metagraph_cache, x_hotkey, client_ip):  # Pass metagraph_cache
            logger.warning(f"Request IP {client_ip} does not match hotkey {x_hotkey}'s axon IP")
            raise HTTPException(400, "INVALID REQUEST: IP MISMATCH")
    
    try:
        provider = LLMProvider.from_str(x_provider)
        match provider:
            case LLMProvider.CHAT_GPT:
                # Check if it's GPT-5 family model
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

        # Time metadata (NOT signed)
        timestamp = datetime.now(timezone.utc).isoformat()
        ttl = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

        # Sign only the core proof
        serialized_proof = json.dumps(proof, sort_keys=True).encode()
        signature = PRIVATE_KEY.sign(serialized_proof)
        signed_response = SignedResponse(
            response=response.json(),
            proof=proof,
            signature=base64.b64encode(signature).decode(),
            timestamp=timestamp,
            ttl=ttl
        )
        et = time.perf_counter()
        duration = et - st

        asyncio.create_task(write_verified_to_file(request_id, [signed_response]))        
        asyncio.get_event_loop().run_in_executor(app.state.thread_pool, d1_client.insert_signed_response, signed_response, request_id, duration, str(provider))

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