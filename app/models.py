import json
import hashlib
from pydantic import BaseModel, ConfigDict
from dataclasses import dataclass

class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[dict] | None = None  #V1 ChatCompletions
    input: list[dict] | None = None  #For GPT Responses API
    
    # Optional params
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    stream: bool = False
    stop: str | list[str] | None = None
    
    # OpenRouter params
    provider: dict | None = None
    transforms: list[str] | None = None
    route: str | None = None

    model_config = ConfigDict(extra="allow")

    text: dict | None = None  # For GPT5
    reasoning: dict | None = None  # For GPT5


class SignedResponse(BaseModel):
    response: dict
    proof: dict
    signature: str
    timestamp: str
    ttl: str

    def to_hash(self) -> str:
        thing = self.model_dump()
        encoded = json.dumps(thing, sort_keys=True).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()




@dataclass
class Proof:
    miner_id: str
    model_name: str
    base_reward: float
    timestamp: float


