import json
import logging
import requests
from dotenv import load_dotenv
load_dotenv()
from app.models import SignedResponse
logger = logging.getLogger(__name__)

class D1Handler:
    def __init__(self, account_id: str, token: str, database_id: str):
        self.account_id = account_id
        self.token = token
        self.database_id = database_id
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}"    

    async def select_all_signed_responses(self, top: int = 100):
        """Select all SignedResponses from D1, limited by 'top'."""
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
                # Access the nested results correctly
                return result['result'][0]['results']
            else:
                logger.error(f"Failed to fetch signed responses: {result}")
                return []
        except Exception as e:
            print(f"Error fetching signed responses: {e}")
            logger.error(f"Error fetching signed responses: {e}")
            return []    


    def insert_signed_response(self, response: SignedResponse, request_id: str = None, duration: float = 0) -> bool:        
        """Insert a single SignedResponse into D1. request_id is optional (not in schema, but can be logged or used if added)."""
        try:
            url = f"{self.base_url}/query"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            duration = round(duration, 4)
            sql = """
            INSERT INTO signed_responses (unique_id, request_hash, response_hash, hotkey, model, signature, timestamp, ttl, response_json, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = [
                response.proof['unique_id'],
                response.proof['request_hash'],
                response.proof['response_hash'],
                response.proof['hotkey'],
                response.proof['model'],
                response.signature,
                response.timestamp,
                response.ttl,
                json.dumps(response.response),
                duration
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
            print(f"Error inserting SignedResponse: {e}")
            logger.error(f"Error inserting SignedResponse: {e}")
            return False

    # def insert_multiple_signed_responses(self, responses: List[SignedResponse], request_ids: List[str] = None):
    #     """Insert multiple SignedResponse objects into D1 (append-only). request_ids optional."""
    #     results = []
    #     for i, response in enumerate(responses):
    #         req_id = request_ids[i] if request_ids and i < len(request_ids) else None
    #         result = self.insert_signed_response(response, req_id)
    #         results.append(result)
    #     return results