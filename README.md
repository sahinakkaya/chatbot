# Real-time AI Chatbot

A WebSocket-based AI chatbot for a personal website. It accepts a user message,
uses OpenAI to generate a response, and sends that response back over the same
real-time connection.

The service includes token-based WebSocket access, per-user rate limiting,
optional conversation history, Cloudflare Turnstile support, structured logging,
and retrieval-augmented responses using the included resume context.

## Requirements

- Docker and Docker Compose for the recommended setup
- An OpenAI API key

For local development without Docker, you also need Python 3.13+ and
[uv](https://docs.astral.sh/uv/).

## Run with Docker

Create a local environment file and set your OpenAI key:

```bash
cp src/chatbot/.env.example src/chatbot/.env
```

Set `OPENAI_API_KEY` in `src/chatbot/.env`, then start the application:

```bash
cd infra/docker
docker compose up --build -d
```

The chatbot is available at `http://localhost:8080`.

To inspect logs or stop it:

```bash
docker compose logs -f chatbot
docker compose down
```

## Run locally

Start Redis:

```bash
docker compose -f infra/docker/docker-compose.dependencies.yml up -d redis
```

Configure and start the chatbot:

```bash
cd src/chatbot
cp .env.example .env
# Set OPENAI_API_KEY in .env
set -a; source .env; set +a
uv sync
uv run uvicorn chatbot.main:app --reload
```

The local server listens on `http://localhost:8000`.

## Connect to the chatbot

First request a token. User IDs must be UUIDs.

```bash
curl -X POST 'http://localhost:8080/token?userid=550e8400-e29b-41d4-a716-446655440000' \
  -H 'Content-Type: application/json' \
  -d '{"captcha":"development"}'
```

When `TURNSTILE_SECRET_KEY` is empty, the `captcha` value is accepted for local
development. Configure a Turnstile secret in production.

Use the returned token to open a WebSocket connection:

```text
ws://localhost:8080/ws?userid=550e8400-e29b-41d4-a716-446655440000&token=<token>
```

Send messages in this format:

```json
{
  "type": "message",
  "content": "Tell me about your experience with Python."
}
```

Responses contain the generated text, user ID, timestamp, processing time, and
correlation ID.

## Configuration

`src/chatbot/.env.example` documents all settings. The most useful ones are:

- `OPENAI_API_KEY`: required OpenAI API key.
- `OPENAI_MODEL`: chat model to use.
- `REDIS_HOST` and `REDIS_PORT`: Redis connection details.
- `USER_RATE_LIMIT_MAX_REQUESTS` and `USER_RATE_LIMIT_WINDOW_SECONDS`: per-user request limit.
- `KEEP_HISTORY`, `CHAT_HISTORY_MAX_MESSAGES`, and `CHAT_HISTORY_TTL`: conversation-history behavior.
- `CONTEXT_FILE_PATH`: context file used for retrieval-augmented responses.
- `TURNSTILE_SECRET_KEY`: enables Cloudflare Turnstile verification.

## Health check

```bash
curl http://localhost:8080/health
```
