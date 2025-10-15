import os
import re
import json
import logging
from typing import List
from app.models import SignedResponse
from fiber import (
    Keypair,
)

logger = logging.getLogger("verified")


async def read_verified_from_file() -> List[SignedResponse]:
    try:
        log_file = "data/verified_results.json"
        json_file_path = os.path.join(os.path.dirname(__file__), log_file)
        if not os.path.exists(json_file_path):
            logger.warning(f"File {json_file_path} does not exist. Returning empty list.")
            return []

        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return [SignedResponse(**item) for item in data if isinstance(item, dict)]
    except Exception as e:
        print(f"Error reading recommendations from file: {e}")
        logger.error(f"Error reading recommendations from file: {e}")
        return []


async def write_verified_to_file(request_id: str, verified: list) -> bool:  
    try:
        train_file = "data/verified_results.json"
        json_file_path = os.path.join(os.path.dirname(__file__), train_file)
        os.makedirs(os.path.dirname(json_file_path), exist_ok=True)

        # Load existing data if file exists
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r', encoding='utf-8') as file:
                try:
                    data = json.load(file)
                    if not isinstance(data, list):
                        data = []
                except Exception:
                    data = []
        else:
            data = []
        for v in verified:
            entry = v.model_dump()
            entry["row_hash"] = v.to_hash()
            entry["request_id"] = request_id
            data.append(entry)
        # # Append new recs with scores
        # for rec, score in recs_with_scores:
        #     entry = rec.to_dict()
        #     entry["similarity_score"] = round(score, 4)
        #     entry["row_hash"] = rec.to_hash()
        #     entry["batch_elected_id"] = elected.to_hash() if elected else None
        #     data.append(entry)
        
        with open(json_file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
        print(f"Verified appended to {json_file_path}")        
        return True
    except Exception as e:
        print(f"Error writing Verified to file: {e}")
        return False
    

def load_version_info() -> str:
    try:
        version_file_path = os.path.join(os.path.dirname(__file__), '..', 'version.txt')
        if os.path.exists(version_file_path):
            with open(version_file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                if len(lines) >= 2:
                    branch = lines[0].strip()
                    commit_sha = lines[1].strip()
                    return f"Branch: {branch}, Commit: {commit_sha}"
        return "Version info not available"
    except Exception as e:
        logger.error(f"Error loading version info: {e}")
        return "Error loading version info"
    

def is_valid_hotkey(hotkey: str) -> bool:
    pattern = r'^5[1-9A-Za-z]{47}$'
    return re.match(pattern, hotkey) is not None


def verify_miner_request(hotkey: str, provider: str, nonce: str, signature: str, payload: bytes) -> bool:
    payload_str = json.dumps({
        "hotkey": hotkey,
        "provider": provider,
        "nonce": nonce,
        "payload": payload
    }, separators=(',', ':'), sort_keys=True)
    keypair = Keypair(hotkey)
    return keypair.verify(
        payload_str.encode('utf-8'),
        signature.encode('utf-8')
    )
   