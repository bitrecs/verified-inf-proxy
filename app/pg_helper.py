import json
import logging
import os
import traceback
import psycopg
from datetime import datetime, timezone
from typing import Any, Dict, List
from dotenv import load_dotenv
load_dotenv()
from app.models import ChatCompletionRequest, SignedResponse

logger = logging.getLogger(__name__)


BT_NETUID = os.getenv("BT_NETUID", "296")
TABLE_NAME = "vi.signed_responses" if BT_NETUID == "296" else "vi.signed_responses_mainnet"


class PGHandler:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = None

    def connect(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg.connect(self.db_url)
        return self.conn
    
    def select_signed_responses(self, limit=100) -> List[Dict[str, Any]]:
        """Select signed responses from the database."""
        results = []
        try:
            conn = self.connect()
            with conn.cursor() as cur:
                sql = f"SELECT * FROM {TABLE_NAME} ORDER BY created_at DESC LIMIT {limit}"
                cur.execute(sql)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                for row in rows:
                    result = dict(zip(columns, row))
                    results.append(result)
                logger.debug(f"Selected {len(results)} signed responses")
        except Exception as e:
            logger.error(f"Select failed: {e}")
        finally:
            if conn:
                conn.close()
        return results

    def select_signed_response_by_miner_hotkey(self, hotkey: str, limit=100) -> Dict[str, Any]:
        """Select a signed response by miner hotkey."""
        try:
            conn = self.connect()
            with conn.cursor() as cur:
                sql = f"SELECT * FROM {TABLE_NAME} WHERE hotkey = %s ORDER BY created_at DESC LIMIT {limit}"
                cur.execute(sql, (hotkey,))
                row = cur.fetchone()
                if row:
                    columns = [desc[0] for desc in cur.description]
                    result = dict(zip(columns, row))
                    logger.debug(f"Selected signed response for hotkey: {hotkey}")
                    return result
                else:
                    logger.debug(f"No signed response found for hotkey: {hotkey}")
                    return {}
        except Exception as e:
            logger.error(f"Select failed: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    def select_signed_response_by_miner_hotkey_since(self, hotkey: str, since_date: datetime, limit=100) -> List[Dict[str, Any]]:
        """Select signed responses by miner hotkey since a given date."""
        results = []
        try:
            conn = self.connect()
            with conn.cursor() as cur:
                sql = f"""
                SELECT * FROM {TABLE_NAME} 
                WHERE hotkey = %s AND created_at >= %s 
                ORDER BY created_at DESC LIMIT {limit}
                """
                cur.execute(sql, (hotkey, since_date))
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                for row in rows:
                    result = dict(zip(columns, row))
                    results.append(result)
                logger.debug(f"Selected {len(results)} signed responses for hotkey: {hotkey} since {since_date}")
        except Exception as e:
            logger.error(f"Select failed: {e}")
        finally:
            if conn:
                conn.close()
        return results
    

    def insert_signed_response(self, unique_id: str,  response: SignedResponse, duration: float = 0, provider: str = "", x_nonce: str = "", x_hotkey: str = "", completion_request: ChatCompletionRequest = None) -> bool:
        """Insert all data into the single {vi.signed_responses} table."""
        try:
            conn = self.connect()
            with conn.cursor() as cur:
                duration_rounded = round(duration, 4)
                
                # Serialize completion_request safely
                completion_request_json = ""
                if completion_request:
                    try:
                        completion_request_json = json.dumps(completion_request.model_dump(), default=str, ensure_ascii=False)
                    except (TypeError, ValueError) as e:
                        logger.error(f"Serialization failed for completion_request: {e}")
                        return False
                
                # Serialize completion_response safely
                completion_response_json = ""
                if response and response.response:
                    try:
                        completion_response_json = json.dumps(response.response, default=str, ensure_ascii=False)
                    except (TypeError, ValueError) as e:
                        logger.error(f"Serialization failed for response.response: {e}")
                        return False
                
                # Size checks (optional, adjust as needed)
                if len(completion_request_json.encode('utf-8')) > 1000000 or len(completion_response_json.encode('utf-8')) > 1000000:
                    logger.error("JSON data too large")
                    return False
                
                if BT_NETUID == "296":
                    sql = """
                    INSERT INTO vi.signed_responses (
                        unique_id, request_hash, response_hash, hotkey, model, signature, timestamp, ttl, duration, provider, nonce, completion_request, completion_response
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                else:
                    sql = """
                    INSERT INTO vi.signed_responses_mainnet (
                        unique_id, request_hash, response_hash, hotkey, model, signature, timestamp, ttl, duration, provider, nonce, completion_request, completion_response
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                
                params = (
                    response.proof.get('unique_id') or '',
                    response.proof.get('request_hash') or '',
                    response.proof.get('response_hash') or '',
                    x_hotkey or '',
                    response.proof.get('model') or '',
                    response.signature or '',
                    response.timestamp or '',
                    response.ttl or '',
                    str(duration_rounded),
                    provider or '',
                    x_nonce or '',
                    completion_request_json,
                    completion_response_json
                )
                
                cur.execute(sql, params)
                conn.commit()
                logger.debug(f"Inserted into signed_responses for unique_id: {unique_id}")
                return True
        except Exception as e:
            logger.error(f"Insert failed: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()