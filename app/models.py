from pydantic import BaseModel, ConfigDict


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
