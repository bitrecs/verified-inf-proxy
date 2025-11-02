import json
import logging
import traceback
import requests
from datetime import datetime, timezone
from typing import Any, Dict, List
from dotenv import load_dotenv
load_dotenv()
from app.models import ChatCompletionRequest, SignedResponse
logger = logging.getLogger(__name__)


class D1Handler:
    def __init__(self, account_id: str, token: str, database_id: str):
        self.account_id = account_id
        self.token = token
        self.database_id = database_id
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}"    

    async def select_signed_responses_by_hotkey_since(self, hotkey: str, since_date: datetime, top: int = 100) -> List[Dict[str, Any]]:
        """Select SignedResponses from D1 by hotkey and since_timestamp, limited by 'top', and reconstruct the 'proof' dict from individual fields."""
        try:
            since_date = since_date.isoformat()
            #2025-10-07T16:01:27.254289+00:00
            url = f"{self.base_url}/query"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            sql = "SELECT * FROM signed_responses WHERE hotkey = ? AND timestamp >= ? ORDER BY timestamp DESC LIMIT ?"
            params = [hotkey, since_date, top]
            payload = {
                "sql": sql,
                "params": params
            }
            resp = requests.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            if result.get('success'):
                rows = result['result'][0]['results']                
                for row in rows:
                    row['proof'] = {                        
                        'request_hash': row.get('request_hash'),
                        'response_hash': row.get('response_hash'),
                        'hotkey': row.get('hotkey'),
                        'model': row.get('model'),
                        'provider': row.get('provider'),
                        'unique_id': row.get('unique_id')
                    }
                return rows
            else:
                logger.error(f"Failed to fetch signed responses by hotkey since timestamp: {result}")
                return []
        except Exception as e:
            print(f"Error fetching signed responses by hotkey since timestamp: {e}")
            logger.error(f"Error fetching signed responses by hotkey since timestamp: {e}")
            return []
    

    async def select_all_signed_responses(self, top: int = 100) -> List[Dict[str, Any]]:
        """Select all SignedResponses from D1, limited by 'top', and reconstruct the 'proof' dict from individual fields."""
        try:
            url = f"{self.base_url}/query"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            sql = "SELECT * FROM signed_responses ORDER BY timestamp DESC LIMIT ?"
            params = [top]
            payload = {
                "sql": sql,
                "params": params
            }
            resp = requests.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            if result.get('success'):
                rows = result['result'][0]['results']                
                for row in rows:
                    row['proof'] = {                        
                        'request_hash': row.get('request_hash'),
                        'response_hash': row.get('response_hash'),
                        'hotkey': row.get('hotkey'),
                        'model': row.get('model'),
                        'provider': row.get('provider'),
                        'unique_id': row.get('unique_id')
                    }
                return rows
            else:
                logger.error(f"Failed to fetch signed responses: {result}")
                return []
        except Exception as e:
            print(f"Error fetching signed responses: {e}")
            logger.error(f"Error fetching signed responses: {e}")
            return []    


    def insert_signed_response(self, response: SignedResponse, request_id: str = None, duration: float = 0, provider: str = "") -> bool:
        """Insert a single SignedResponse into D1."""
        try:
            url = f"{self.base_url}/query"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            duration_rounded = round(duration, 4)
            
            # Serialize response_json safely
            try:
                response_json = json.dumps(response.response, default=str, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                logger.error(f"Serialization failed for response.response: {e}")
                return False
            
            # Size limit check
            if len(response_json.encode('utf-8')) > 1000000:  # 1MB in bytes
                logger.error("Response JSON too large")
                return False
            
            sql = """
            INSERT INTO signed_responses (unique_id, request_hash, response_hash, hotkey, model, signature, timestamp, ttl, response_json, duration, provider)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            # Build params with defaults
            params = [
                response.proof.get('unique_id') or '',
                response.proof.get('request_hash') or '',
                response.proof.get('response_hash') or '',
                response.proof.get('hotkey') or '',
                response.proof.get('model') or '',
                response.signature or '',
                response.timestamp or '',
                response.ttl or '',
                response_json,
                str(duration_rounded),
                provider or ''
            ]
            
            # Ensure all params are strings
            params = [str(p) for p in params]
            
            payload = {"sql": sql, "params": params}
            
            # Debug log (remove later)
            logger.debug(f"Payload: {json.dumps(payload)}")
            
            resp = requests.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            return result.get('success', False)
        except Exception as e:
            logger.error(f"Insert failed: {e}")
            return False
        
    def insert_completion_request(self, unique_id: str, hotkey: str, provider: str, cr: ChatCompletionRequest) -> bool:
        """Insert a completion request into D1 for logging purposes."""
        try:
            url = f"{self.base_url}/query"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            sql = """
            INSERT INTO completion_requests (unique_id, hotkey, provider, model, messages_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            request_json = json.dumps(cr.model_dump(), sort_keys=True, default=str)
            timestamp = datetime.now(timezone.utc).isoformat()
            params = [
                unique_id,
                hotkey,
                provider,
                str(cr.model),
                request_json,
                timestamp
            ]
            payload = {
                "sql": sql,
                "params": params
            }
            resp = requests.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            is_success = result.get('success', False)  # Checks top-level 'success'
            return is_success
        except Exception as e:
            print(f"Error inserting completion request: {e}")
            logger.error(f"Error inserting completion request: {e}")
            return False        
            

           
        
        
        
    def insert_used_nonce(self, nonce: str, hotkey: str) -> bool:
        """Insert a used nonce into D1 to prevent replay attacks."""
        try:
            url = f"{self.base_url}/query"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            sql = "INSERT INTO used_nonces (nonce, hotkey, timestamp) VALUES (?, ?, ?)"
            timestamp = datetime.now(timezone.utc).isoformat()
            params = [nonce, hotkey, timestamp]
            payload = {
                "sql": sql,
                "params": params
            }
            resp = requests.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            is_success = result.get('success', False)  # Checks top-level 'success'
            return is_success
        except Exception as e:
            print(f"Error inserting used nonce: {e}")
            logger.error(f"Error inserting used nonce: {e}")
            return False
        
        
    def check_nonce_used(self, nonce: str) -> bool:
        """Check if a nonce has already been used for a given hotkey."""
        try:
            url = f"{self.base_url}/query"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            sql = "SELECT COUNT(*) as count FROM used_nonces WHERE nonce = ? "
            params = [nonce]
            payload = {
                "sql": sql,
                "params": params
            }
            resp = requests.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            if result.get('success'):
                count = result['result'][0]['results'][0]['count']
                return count > 0
            else:
                logger.error(f"Failed to check nonce usage: {result}")
                return False
        except Exception as e:
            print(f"Error checking nonce usage: {e}")
            logger.error(f"Error checking nonce usage: {e}")
            return False
        
    
    def insert_batch_request_data(self,
        signed_response: SignedResponse,
        request_id: str,
        duration: float,
        provider: str,
        x_nonce: str,
        x_hotkey: str,
        completion_request: ChatCompletionRequest
    ) -> bool:
        """Batch insert all request-related data into D1 using a single API call."""
        try:
            url = f"{self.base_url}/query"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            # Prepare batch queries
            queries = []
            
            # 1. Insert signed response
            duration_rounded = round(duration, 4)
            sql1 = """
            INSERT INTO signed_responses (unique_id, request_hash, response_hash, hotkey, model, signature, timestamp, ttl, response_json, duration, provider)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params1 = [
                signed_response.proof['unique_id'],
                signed_response.proof['request_hash'],
                signed_response.proof['response_hash'],
                signed_response.proof['hotkey'],
                signed_response.proof['model'],
                signed_response.signature,
                signed_response.timestamp,
                signed_response.ttl,
                json.dumps(signed_response.response),
                duration_rounded,
                provider
            ]
            queries.append({"sql": sql1, "params": params1})
            
            # 2. Insert used nonce
            sql2 = "INSERT INTO used_nonces (nonce, hotkey, timestamp) VALUES (?, ?, ?)"
            timestamp_now = datetime.now(timezone.utc).isoformat()
            params2 = [x_nonce, x_hotkey, timestamp_now]
            queries.append({"sql": sql2, "params": params2})
            
            # 3. Insert completion request
            sql3 = """
            INSERT INTO completion_requests (unique_id, hotkey, provider, model, messages_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            request_json = json.dumps(completion_request.model_dump(), sort_keys=True, default=str)
            params3 = [
                request_id,
                x_hotkey,
                provider,
                str(completion_request.model),
                request_json,
                timestamp_now
            ]
            queries.append({"sql": sql3, "params": params3})
            
            # Send batch request
            payload = queries  # Array of query objects
            resp = requests.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            
            # Check if all succeeded (D1 returns an array of results)
            if result.get('success') and len(result.get('result', [])) == len(queries):
                logger.debug(f"Batch insert succeeded for request {request_id}")
                return True
            else:
                logger.error(f"Batch insert failed for request {request_id}: {result}")
                return False
        except Exception as e:
            logger.error(f"Error in batch insert for request {request_id}: {str(e)}")
            return False