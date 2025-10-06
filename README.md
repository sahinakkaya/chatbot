# Real-time AI Conversation System

A distributed microservices architecture for real-time AI conversations using WebSocket connections, Kafka message queuing, and Redis pub/sub.

## Architecture Overview

```
Client → Nginx → WebSocket Server (2 instances) → Kafka (incoming_messages)
                      ↑                                      ↓
                      |                                AI Consumer → OpenAI API
                      |                                      ↓
                  Redis ← Message Relay ← Kafka (responses)
```

## Tech Stack

- **Language**: Python 3.13
- **Web Framework**: FastAPI with WebSocket support
- **Message Queue**: Apache Kafka with kafka-python
- **Cache/Pub-Sub**: Redis with redis-py
- **AI Integration**: OpenAI API (GPT-3.5-turbo)
- **Package Manager**: uv
- **Containerization**: Docker & Docker Compose
- **Load Balancer**: Nginx (least_conn strategy)
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structured JSON logging with correlation IDs

## Services

### 1. WebSocket Server (`websocket-server/`)
- **Handles** WebSocket connections from clients
- **Uses** token-based authentication
- **Publishes** user messages to Kafka `incoming_messages` topic
- **Subscribes** to Redis channels for user-specific responses
- **Implements** per-user rate limiting
- **Scales** horizontally (2 instances load-balanced by Nginx)

**Endpoints:**
- `GET /ws?token=<token>&userid=<userid>` - WebSocket connection
- `POST /token?userid=<userid>` - Generate authentication token
- `GET /health` - Health check endpoint
- `GET /metrics` - Prometheus metrics

### 2. AI Consumer (`ai-consumer/`)
- **Consumes** messages from `incoming_messages` Kafka topic
- **Processes** messages with OpenAI API (GPT-3.5-turbo)
- **Publishes** AI responses to `responses` Kafka topic
- **Handles** API rate limiting with exponential backoff retry (7 attempts)
- **Processes** concurrently using ThreadPoolExecutor (50 workers)

### 3. Message Relay (`message-relay/`)
- **Consumes** messages from `responses` Kafka topic
- **Publishes** to user-specific Redis channels (`user:{userid}`)
- **Routes** messages back to WebSocket servers
- **Ensures** reliable message delivery

## Prerequisites

- Docker and Docker Compose
- Python 3.13+ (for local development)
- OpenAI API key

## Quick Start

### 1. Environment Setup
You don't need to do anything else if you just want to run with docker. If you want to run locally, copy `.env.example` files to `.env` and change based on your needs.

```

### 2. Start Services

```bash
# Start all services
make start-all

# Or start individually:
make start-dependencies    # Kafka, Zookeeper, Redis
make start-backend        # WebSocket servers, AI Consumer, Message Relay,
make start-monitoring     # Prometheus, Grafana
```
### 3. Use the App
There is an endpoint in websocket-server in order to obtain a token. After getting your token, make a websocket connection with your user id and token. If your token matches with your user id, you will be connected through the websocket and you can send messages to be answered by AI. 

Notice: Some part of this application is completely vibe coded with AI. These are:
- Metrics
- Tests
- Prometheus and grafana integration

Whenever you see a metric registered, you can assume I didn't wrote that line. Whenever you see a test case, you can assume I didn't wrote it.
```

## License

This project is for interview demonstration purposes.

## Contact

For questions or issues, please contact the development team.
