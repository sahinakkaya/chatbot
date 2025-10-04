.PHONY: help start-dependencies stop-dependencies start-monitoring stop-monitoring start-backend stop-backend start-all stop-all restart-all logs clean

help:
	@echo "Available commands:"
	@echo "  make start-dependencies  - Start Kafka, Zookeeper, and Redis"
	@echo "  make stop-dependencies   - Stop dependencies"
	@echo "  make start-monitoring    - Start Prometheus and Grafana"
	@echo "  make stop-monitoring     - Stop monitoring services"
	@echo "  make start-backend       - Start all backend services (WebSocket, AI Consumer, Message Relay, Nginx)"
	@echo "  make stop-backend        - Stop backend services"
	@echo "  make start-all           - Start all services"
	@echo "  make stop-all            - Stop all services"
	@echo "  make restart-all         - Restart all services"
	@echo "  make logs                - Show logs from all services"
	@echo "  make clean               - Remove all containers and volumes"

start-dependencies:
	docker compose -f docker-compose.dependencies.yml up -d

stop-dependencies:
	docker compose -f docker-compose.dependencies.yml down

start-monitoring:
	docker compose -f docker-compose.monitoring.yml up -d

stop-monitoring:
	docker compose -f docker-compose.monitoring.yml down

start-backend:
	docker compose -f docker-compose.dependencies.yml -f docker-compose.backend.yml up -d

stop-backend:
	docker stop ws-server-1 ws-server-2 ai-consumer message-relay nginx 2>/dev/null || true
	docker rm ws-server-1 ws-server-2 ai-consumer message-relay nginx 2>/dev/null || true

start-all:
	docker compose -f docker-compose.dependencies.yml -f docker-compose.monitoring.yml -f docker-compose.backend.yml up -d

stop-all:
	docker compose -f docker-compose.dependencies.yml -f docker-compose.monitoring.yml -f docker-compose.backend.yml down

restart-all: stop-all start-all

logs:
	docker compose -f docker-compose.dependencies.yml -f docker-compose.monitoring.yml -f docker-compose.backend.yml logs -f

clean:
	docker compose -f docker-compose.dependencies.yml -f docker-compose.monitoring.yml -f docker-compose.backend.yml down -v
	rm -rf docker-logs/*
