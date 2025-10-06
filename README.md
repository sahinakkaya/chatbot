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

## Quick Start

### 1. Environment Setup
You don't need to do anything else if you just want to run with docker. If you want to run locally, copy `.env.example` files to `.env` and change it based on your needs. You will need python3.13+ and [`uv`](https://docs.astral.sh/uv/)

### 2. Start Services

```bash
cd infra/docker
docker compose up --build -d
```
### 3. Use the App
The websocket server will be running on `8080` by default. There is an endpoint in websocket-server in order to obtain a token. After getting your token, make a websocket connection with your user id and token. If your token matches with your user id, you will be connected through the websocket and you can send messages to be answered by AI. You can visit http://localhost:8080/ in order to quickly test it via simple ui.

### 4. Some notes
- I've decided to use prometheus for metrics but didn't touch anything else. All the code related with metrics are written by claude. It is supposed to track the performance criteria we are interested in but doesn't work well. Prometheus and grafana is also setup by claude. Grafana is running at `3000` with default credentials (admin, admin). You will need to import dashboard from `./infra/grafana/dashboards/nova-prime-dashboard.json` if you want to see the dashboard.

- I've used `./scripts/load-test.py` for testing the application under different loads. I've achieved 100+ message throughput multiple times but it really depends on responsiveness of OpenAI. I am getting 50+ message/second throughput on average.

- All the code related to testing is also vibe coded with claude. It is better than nothing I guess.
