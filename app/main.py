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
import numpy as np
import bittensor as bt
from dotenv import load_dotenv
load_dotenv()

from app.models import ChatCompletionRequest, SignedResponse
from app.utils import read_verified_from_file, write_verified_to_file
from app.d1 import D1Handler
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from typing import Union, Dict
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, Header, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives import serialization
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


global metagraph
metagraph_cache = None
metagraph_cache_timestamp = None
CACHE_DURATION = 600
BT_NETWORK = os.environ.get("BT_NETWORK", "test")
BT_NETUID = int(os.environ.get("BT_NETUID", 296))
B64_PRIVATE_KEY = os.environ.get("B64_PRIVATE_KEY")
if not B64_PRIVATE_KEY:
    raise ValueError("B64_PRIVATE_KEY environment variable not set")
PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(base64.b64decode(B64_PRIVATE_KEY))
PUBLIC_KEY = PRIVATE_KEY.public_key()

client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))

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
        for _ in range(5):  # Try for 5 seconds
            if threading.active_count() <= 5:
                break
            logger.warning(f"Waiting for {threading.active_count()} threads to terminate...")
            await asyncio.sleep(1)
        logger.info("Shutdown complete.")


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)
#limiter = Limiter(key_func=get_remote_address)
limiter = Limiter(key_func=get_client_ip)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)



@app.get("/health")
@limiter.limit("180/minute")
async def health(request: Request):
    node_count = len(metagraph['uids']) if metagraph else 0
    updated = app.state.last_updated.isoformat() if app.state.last_updated else "never"
    #request_ip = get_client_ip(request)
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
async def recs_log(request: Request):
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
        if not await check_hotkey_stake(metagraph, x_hotkey, 100):  # Minimum 100 TAO stake
            logger.warning(f"Hotkey {x_hotkey} does not have sufficient stake in the metagraph")
            raise HTTPException(400, "INVALID REQUEST: INSUFFICIENT STAKE")
    if 1==2:
        if not await check_request_ip(metagraph, x_hotkey, client_ip):
            logger.warning(f"Request IP {client_ip} does not match hotkey {x_hotkey}'s axon IP")
            raise HTTPException(400, "INVALID REQUEST: IP MISMATCH")
    
    try:
        match x_provider.upper().strip():
            case "CHAT_GPT":
                # Check if it's GPT-5 family model
                if completion_request.model.startswith("gpt-5"):
                    url = "https://api.openai.com/v1/responses"
                else:
                    url = "https://api.openai.com/v1/chat/completions"
            case "OPEN_ROUTER":
                url = "https://openrouter.ai/api/v1/chat/completions"
            case "GEMINI":
                url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            case "CHUTES":
                url = "https://llm.chutes.ai/v1/chat/completions"
            case "GROQ":
                url = "https://api.groq.com/openai/v1/chat/completions"
            case "CEREBRAS":
                url = "https://api.cerebras.ai/v1/chat/completions"
            case "GROK":                
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
            #logger.error(f"{traceback.format_exc()}")
            raise HTTPException(status_code=response.status_code, detail=response.text)

        # Core proof (what gets signed - NO time data)
        proof = {
            "request_hash": hashlib.sha256(json.dumps(completion_request.model_dump()).encode()).hexdigest(),
            "response_hash": hashlib.sha256(response.content).hexdigest(),
            "hotkey": x_hotkey,
            "model": completion_request.model,
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
        
        asyncio.create_task(write_verified_to_file(request_id, [signed_response]))
        #asyncio.create_task(d1_client.insert_signed_response(signed_response, request_id))
        asyncio.get_event_loop().run_in_executor(app.state.thread_pool, d1_client.insert_signed_response, signed_response, request_id)

        app.state.total_requests += 1
        et = time.perf_counter()
        logger.info(f"Request {request_id} took {et - st:.2f} seconds")

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
        public_key : Ed25519PublicKey = serialization.load_pem_public_key(PUBLIC_KEY)
        public_key.verify(
            base64.b64decode(response.signature), 
            json.dumps(response.proof).encode()
        )
        return {
            "valid": True,
            "hotkey": response.proof.get("hotkey"),
            "timestamp": response.proof.get("timestamp"),
            "model": response.proof.get("model")
        }
    except Exception as e:
        logger.warning(f"Verification failed: {str(e)}")
        return {
            "valid": False,
            "error": "Invalid signature"
        }


async def update_metagraph_data(app: FastAPI):
    while True:
        global metagraph
        result = await get_metagraph_data()
        if result is not None:
            metagraph = result
            app.state.last_updated = datetime.now(timezone.utc)
        await asyncio.sleep(600)


async def get_metagraph_data() -> dict:
    """Get the metagraph data with 5-minute cache."""
    global metagraph_cache, metagraph_cache_timestamp

    # Check if we have cached data and it's still valid
    current_time = time.time()
    if (metagraph_cache is not None and
        metagraph_cache_timestamp is not None and
        (current_time - metagraph_cache_timestamp) < CACHE_DURATION):
        logger.info("Returning cached metagraph data")
        return metagraph_cache

    try:        
        network = BT_NETWORK
        netuid = BT_NETUID
        if not network or netuid is None:
            raise ValueError("BT_NETWORK or BT_NETUID environment variables not set")

        logger.info(f'Fetching fresh metagraph data for {network}:{netuid}...')
        subnet = bt.metagraph(netuid=netuid, network=network)

        # Extract all relevant data from metagraph
        data = {
            'uids': [],
            'network_info': {
                'netuid': netuid,
                'network': network,
                'block': int(subnet.block) if hasattr(subnet, 'block') else None,
                'total_neurons': len(subnet.uids),
                'timestamp': datetime.now().isoformat()
            },
            'aggregated_stats': {}
        }

        for i, uid in enumerate(subnet.uids.tolist()):
            try:
                # Safer data extraction with bounds checking
                def safe_get_value(tensor, uid, default=0.0):
                    try:
                        if tensor is not None and len(tensor) > uid:
                            value = tensor[uid]
                            return float(value) if not np.isnan(value) and np.isfinite(value) else default
                    except Exception:
                        pass
                    return default
                
                try:
                    stake = float(subnet.S[uid])
                except Exception:
                    stake = 0.0

                hotkey = ''
                coldkey = ''
                axon_ip = ''
                axon_port = 0
                
                try:
                    if hasattr(subnet, 'hotkeys') and len(subnet.hotkeys) > uid:
                        hotkey = str(subnet.hotkeys[uid])
                except Exception:
                    pass
                
                try:
                    if hasattr(subnet, 'coldkeys') and len(subnet.coldkeys) > uid:
                        coldkey = str(subnet.coldkeys[uid])
                except Exception:
                    pass
                
                # Extract axon information 
                try:
                    if hasattr(subnet, 'axons') and len(subnet.axons) > uid:
                        axon = subnet.axons[uid]
                        if hasattr(axon, 'ip'):
                            axon_ip = str(axon.ip)
                        if hasattr(axon, 'port'):
                            axon_port = int(axon.port) if axon.port is not None else 0
                except Exception as e:
                    logger.info(f'Error extracting axon info for uid {uid}: {e}')
                    pass
                
                neuron_data = {
                    'uid': int(uid),
                    'hotkey': hotkey,
                    'stake': stake,
                    'axon_ip': axon_ip,
                    'axon_port': axon_port,
                }
                data['uids'].append(neuron_data)
                
            except Exception as e:
                logger.error(f'Error processing uid {uid}: {e}')
                continue

        total_neurons = len(data['uids'])
        data['aggregated_stats'] = {
            'total_neurons': total_neurons,
        }
        
        logger.info(f'Successfully processed {total_neurons} neurons')
        del subnet
        gc.collect()

        metagraph_result = {
            'uids': data['uids'],  # original list
            'by_hotkey': {neuron['hotkey']: neuron for neuron in data['uids']},  # O(1) lookup
            'by_ip': {neuron['axon_ip']: neuron for neuron in data['uids']},     # O(1) lookup
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
        gc.collect()


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