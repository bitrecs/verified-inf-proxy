# Bitrecs Verified Inference Proxy

A simple FastAPI proxy for chat/completitons with ed25519 signing

## Configure Environment

### `.env` (server)
```
B64_PRIVATE_KEY=ed25519 key
CF_ACCOUNT_ID=cloudflare account
CF_D1_TOKEN=cloudflare token
CF_D1_DATABASE_ID=cloudflare database
```

### `/tests/.env` (testing)
```
OPENROUTER_KEY=sk-or-v1-xxxxx
OPENAI_KEY=sk-xxxxx
HOTKEY=your-miner-hotkey
```

## Run
```bash
uv sync
uv run uvicorn app.main:app
```

## Test
start the server first then:
```bash
uv run pytest
```

## Endpoints
Server runs on `http://127.0.0.1:8000`
* `GET /` - root
* `GET /health` - health
* `GET /log` - verified log
* `GET /providers` - provider pings
* `GET /public_key` - public key
* `GET /is_verified` - miner verified lookup
* `POST /v1/chat/completions` - Proxy endpoint

