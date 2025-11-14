import os
import re
import time
import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import List
from app.models import SignedResponse
from fiber import (
    Keypair
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


def verify_time(ts: int) -> bool:
    try:
        # Basic input validation
        if not isinstance(ts, (int, float)) or ts < 0 or ts > 2**31:  # Reject negative or unreasonably large timestamps
            logger.error(f"Invalid timestamp: {ts}")
            return False
        
        utc_now = time.time()  # Use float for precision
        age = utc_now - ts  # Age in seconds (negative if future)
        
        # Allow a small window for future timestamps (e.g., 5 seconds for clock skew/network delay)
        if age < -5.0:
            logger.error(f"Timestamp {ts} is too far in the future: {-age:.2f} seconds")
            return False
        # Reject timestamps older than 5 minutes
        if age > 300.0:
            logger.error(f"Timestamp {ts} is too old: {age:.2f} seconds ago")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error in verify_time for ts={ts}: {e}")
        return False


def verify_miner_request(hotkey: str, provider: str, nonce: str, signature: str, payload: dict, ts: str) -> bool:
    try:
        payload_str = json.dumps({
            "hotkey": hotkey,
            "provider": provider,
            "nonce": nonce,
            "payload": payload,
            "timestamp": ts
        }, separators=(',', ':'), sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode('utf-8')).digest()
        signature_bytes = bytes.fromhex(signature)
        keypair = Keypair(hotkey)
        return keypair.verify(payload_hash, signature_bytes)
    except ValueError as e:
        logger.error(f"Invalid signature format: {e}")
        return False
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False



def iso_to_relative_time(iso_ts: str) -> str:
    """
    Convert an ISO 8601 timestamp to a relative time string like '10 minutes ago'.
    Assumes the timestamp is in UTC and compares to current UTC time.
    """
    try:
        # Parse the ISO timestamp (handles +00:00 or Z)
        ts_dt = datetime.fromisoformat(iso_ts.replace('Z', '+00:00'))
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)
        
        # Get current UTC time
        now = datetime.now(timezone.utc)
        
        # Calculate difference
        diff = now - ts_dt
        seconds = int(diff.total_seconds())
        
        if seconds < 0:
            return "in the future"  # Handle future timestamps
        
        # Define time units
        units = [
            (31536000, "year"),
            (2592000, "month"),  # Approximate
            (86400, "day"),
            (3600, "hour"),
            (60, "minute"),
            (1, "second")
        ]
        
        for unit_seconds, unit_name in units:
            if seconds >= unit_seconds:
                count = seconds // unit_seconds
                plural = "s" if count > 1 else ""
                return f"{count} {unit_name}{plural} ago"
        
        return "just now"
    except Exception as e:
        logger.error(f"Error converting ISO timestamp {iso_ts}: {e}")
        return iso_ts  # Fallback to original