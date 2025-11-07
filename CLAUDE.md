# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a distributed microservices architecture for real-time AI conversations using WebSocket connections, Kafka message queuing, and Redis pub/sub. Built as a Python backend interview challenge project.

## Architecture

The system consists of three main Python services that communicate through Kafka and Redis:

1. **WebSocket Server** (`websocket-server/`) - FastAPI service handling WebSocket connections
   - Accepts connections at `/ws?token=<token>&userid=<userid>`
   - Publishes incoming client messages to `incoming_messages` Kafka topic
   - Subscribes to Redis channels (`user:{userid}`) for responses
   - Load-balanced across 2 instances via Nginx
   - Entry point: `websocket_server/main.py`

2. **AI Consumer** (`ai-consumer/`) - OpenAI integration service
   - Consumes from `incoming_messages` Kafka topic
   - Processes messages via OpenAI API (gpt-3.5-turbo)
   - Publishes responses to `responses` Kafka topic
   - Uses ThreadPoolExecutor for concurrent processing
   - Entry point: `ai_consumer/main.py`

3. **Message Relay** (`message-relay/`) - Redis pub/sub bridge
   - Consumes from `responses` Kafka topic
   - Publishes to user-specific Redis channels (`user:{userid}`)
   - Routes messages back to appropriate WebSocket connections
   - Entry point: `message_relay/main.py`

**Message Flow:**
```
Client → Nginx → WebSocket Server → Kafka (incoming_messages) → AI Consumer → OpenAI
                      ↑                                                ↓
                      ←─────── Redis ←────── Message Relay ←──── Kafka (responses)
```

## Common Commands

### Development
```bash
# Start all services
make start-all

# Start only dependencies (Kafka, Zookeeper, Redis)
make start-dependencies

# Start backend services only
make start-backend

# Start monitoring (Prometheus, Grafana)
make start-monitoring

# View logs
make logs

# Stop all services
make stop-all

# Clean up containers and volumes
make clean
```

### Docker Compose Files
The project uses split compose files:
- `docker-compose.dependencies.yml` - Kafka, Zookeeper, Redis
- `docker-compose.backend.yml` - WebSocket servers, AI Consumer, Message Relay, Nginx
- `docker-compose.monitoring.yml` - Prometheus, Grafana
- `docker-compose.yml` - Combined configuration

### Testing
- Load test: `python load-test.py`
- Test UI: http://localhost:8080/test-ui.html (served by Nginx)
- WebSocket endpoint: ws://localhost:8080/ws?token=<token>&userid=<userid>

## Project Structure

### Services
Each service (`websocket-server/`, `ai-consumer/`, `message-relay/`) follows the same structure:
- `pyproject.toml` - Dependencies managed with `uv`
- `Dockerfile` - Multi-stage build using `uv`
- `{service_name}/main.py` - Entry point
- `{service_name}/dependencies.py` - Core business logic
- `{service_name}/config.py` - Pydantic settings from environment
- `.env.example` - Template for environment variables

### Common Libraries
Located in `common/`:
- `logger/` - Shared logging configuration with structured logging
- `metrics/` - Prometheus metrics for each service type
  - `websocket.py` - WebSocket connection metrics
  - `ai_consumer.py` - AI processing metrics
  - `message_relay.py` - Relay metrics

Both are path dependencies referenced in service `pyproject.toml` files.

### Infrastructure
- `nginx/nginx.conf` - Load balancer config with least_conn strategy
- `prometheus/` - Metrics collection config
- `grafana/` - Dashboards and data sources
- `docker-logs/` - Shared volume for service logs

## Key Technologies

- **Language**: Python 3.13
- **Package Manager**: `uv` (fast pip/poetry replacement)
- **Web Framework**: FastAPI with WebSocket support
- **Message Queue**: Apache Kafka (kafka-python)
- **Pub/Sub**: Redis (redis-py)
- **AI**: OpenAI API (gpt-3.5-turbo)
- **Monitoring**: Prometheus + Grafana
- **Load Balancer**: Nginx (least_conn)

## Environment Variables

Each service requires `.env` file based on `.env.example`:

**WebSocket Server:**
- `SERVER_ID` - Instance identifier (server_1, server_2)
- `APP_NAME` - Service name for logging
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka brokers
- `REDIS_HOST`, `REDIS_PORT` - Redis connection

**AI Consumer:**
- `OPENAI_API_KEY` - OpenAI API key
- `KAFKA_BOOTSTRAP_SERVERS`
- `MAX_WORKERS` - ThreadPoolExecutor workers

**Message Relay:**
- `KAFKA_BOOTSTRAP_SERVERS`
- `REDIS_HOST`, `REDIS_PORT`

## Message Protocol

**Client → Server:**
```json
{
  "type": "message",
  "content": "Hello, how are you?",
  "userid": "user123"
}
```

**Server → Client:**
```json
{
  "type": "response",
  "content": "I'm doing well, thank you!",
  "userid": "user123",
  "timestamp": "2024-01-01T12:00:00Z",
  "processing_time_ms": 1200
}
```

**Error Response:**
```json
{
  "type": "error",
  "message": "Service temporarily unavailable",
  "userid": "user123"
}
```

## Health Checks

- WebSocket Server: http://localhost:8080/health
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## Performance Characteristics

- **WebSocket Servers**: 2 instances, load-balanced with least_conn
- **AI Consumer**: ThreadPoolExecutor with configurable workers, 2-second OpenAI timeout
- **Kafka**: LZ4 compression, batch size 16KB, 10ms linger
- **Connection limits**: 512MB RAM, 1.0 CPU per WebSocket instance
- **Concurrent connections**: Designed for 100+ concurrent users
- **Message throughput**: 100+ messages/second

## Development Notes

- All services use structured logging with correlation IDs
- WebSocket server uses `CorrelationIdMiddleware` for request tracking
- AI Consumer has retry logic (3 attempts, exponential backoff) for OpenAI failures
- Kafka auto-creates topics on first use
- Redis pub/sub uses channels named `user:{userid}`
- Nginx proxies WebSocket upgrade headers correctly
- All containers log to `docker-logs/` directory for persistence
