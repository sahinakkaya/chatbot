# Python Backend Developer Interview Challenge

Welcome to the Python Backend Developer interview challenge! You'll be building a distributed microservices architecture with WebSocket support, AI integration, and message queuing for real-time AI conversations.

## Challenge Overview

You'll be creating a Python-based microservices system that:
- Handles WebSocket connections for real-time communication
- Processes AI requests through Kafka message queues
- Manages Redis pub/sub for message distribution
- Demonstrates distributed system design and best practices

## Your Microservices (To Build)

You'll create three Python services that work together:

### 1. WebSocket Server Service
- **Handles** WebSocket connections from clients
- **Subscribes** to Redis for incoming AI responses
- **Manages** client sessions and message routing
- **Scales** horizontally with load balancing

### 2. AI Consumer Service
- **Consumes** messages from `incoming_messages` Kafka topic
- **Integrates** with OpenAI API for AI processing
- **Publishes** responses to `responses` Kafka topic
- **Handles** AI API rate limiting and error recovery

### 3. Message Relay Service
- **Consumes** from `responses` Kafka topic
- **Publishes** messages to Redis for WebSocket distribution
- **Manages** message routing and delivery
- **Ensures** reliable message delivery

## Technical Stack

- **Language**: Python 3.9+
- **WebSocket**: `websockets` or `fastapi` with WebSocket support
- **Message Queue**: Apache Kafka with `kafka-python`
- **Cache/Pub-Sub**: Redis with `redis-py`
- **AI Integration**: OpenAI API
- **Containerization**: Docker & Docker Compose
- **Reverse Proxy**: Nginx
- **Load Balancing**: Nginx upstream configuration

## Architecture Overview

```
Client → Nginx → WebSocket Server (2 instances) → Redis
                ↓
            Kafka (incoming_messages) → AI Consumer → OpenAI API
                ↓
            Kafka (responses) → Message Relay → Redis → WebSocket Server
```

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.9+ (for local development)
- OpenAI API key

### Project Structure
```
your-project/
├── docker-compose.yml
├── nginx/
│   └── nginx.conf
├── websocket-server/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
├── ai-consumer/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
├── message-relay/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
└── README.md
```

## Service Requirements

### 1. WebSocket Server Service

**Features**:
- Accept WebSocket connections on `/ws` endpoint
- Query parameters: `token` and `userid`
- Subscribe to Redis channel for user-specific responses
- Send messages to `incoming_messages` Kafka topic
- Handle connection management and cleanup

**API Endpoints**:
- `GET /ws?token=<token>&userid=<userid>` - WebSocket connection

**Message Protocol**:
```json
// Client to Server
{
  "type": "message",
  "content": "Hello, how are you?",
  "userid": "user123"
}

// Server to Client
{
  "type": "response",
  "content": "I'm doing well, thank you!",
  "userid": "user123"
}
```

### 2. AI Consumer Service

**Features**:
- Consume from `incoming_messages` Kafka topic
- Process messages with OpenAI API
- Publish responses to `responses` Kafka topic
- Handle API rate limiting and retries

**Environment Variables**:
- `OPENAI_API_KEY` - Your OpenAI API key
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka broker addresses
- `REDIS_URL` - Redis connection string

### 3. Message Relay Service

**Features**:
- Consume from `responses` Kafka topic
- Publish messages to Redis channels
- Route messages to correct user channels
- Ensure message delivery and persistence
- Handle message serialization/deserialization

## Docker Compose Configuration

Your `docker-compose.yml` should include:

### Services
- **nginx**: Reverse proxy and load balancer
- **redis**: Pub/sub and caching
- **kafka**: Message queue (with Zookeeper)
- **websocket-server-1**: First WebSocket instance
- **websocket-server-2**: Second WebSocket instance
- **ai-consumer**: AI processing service
- **message-relay**: Message routing service

### Nginx Configuration
- Load balance between 2 WebSocket server instances
- WebSocket proxy configuration
- Health check endpoints
- Proper upstream configuration

### Environment Variables
- OpenAI API key
- Kafka and Redis connection strings
- Service discovery configuration

## Required Features

### Core Functionality
- **WebSocket Management**: Handle multiple concurrent connections
- **Message Queuing**: Reliable message processing through Kafka
- **AI Integration**: OpenAI API integration with proper error handling
- **Load Balancing**: Distribute WebSocket connections across instances
- **Pub/Sub**: Redis-based message distribution
- **Health Checks**: Service health monitoring endpoints

### Error Handling
- **Connection Failures**: WebSocket reconnection logic
- **API Errors**: OpenAI API error handling and retries
- **Message Failures**: Dead letter queues and retry mechanisms
- **Service Failures**: Graceful degradation and recovery

### Performance
- **Concurrent Connections**: Support 100+ concurrent WebSocket connections
- **Message Throughput**: Process 100+ messages per second
- **Resource Management**: Proper connection pooling and cleanup
- **Monitoring**: Logging and metrics collection

## Recommended Features

### Advanced Functionality
- **Message Persistence**: Store message history in Redis
- **Rate Limiting**: Per-user message rate limiting
- **Authentication**: Token validation and user management
- **Metrics**: Prometheus metrics and monitoring
- **Configuration**: Environment-based configuration management

### Production Readiness
- **Logging**: Structured logging with correlation IDs
- **Testing**: Unit and integration tests
- **Documentation**: API documentation and deployment guides
- **Security**: Input validation and sanitization
- **Monitoring**: Health checks and alerting

## API Reference

### WebSocket Connection
```
ws://localhost:8080/ws?token=your-token&userid=user123
```

### Message Formats

**Client Message**:
```json
{
  "type": "message",
  "content": "Hello, AI!",
  "userid": "user123"
}
```

**AI Response**:
```json
{
  "type": "response",
  "content": "Hello! How can I help you today?",
  "userid": "user123",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Error Message**:
```json
{
  "type": "error",
  "message": "Service temporarily unavailable",
  "userid": "user123"
}
```

## Success Criteria

We're looking for candidates who can:

- **Build functional microservices** that work together seamlessly
- **Implement clean, maintainable code** with proper Python patterns
- **Handle distributed systems challenges** like message ordering and failure handling
- **Create scalable architecture** that can handle production loads
- **Demonstrate problem-solving skills** when debugging distributed systems
- **Show understanding of backend development** best practices and patterns
