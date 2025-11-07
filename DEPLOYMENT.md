# Deployment Guide

This guide covers deploying the RAG-enhanced personal Q&A system to your server.

## Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- Docker and Docker Compose installed
- Domain name configured (optional but recommended for HTTPS)
- OpenAI API key

## Quick Start

### 1. Prepare Your Resume Data

1. Copy your resume data to the `data/` directory:
   ```bash
   cp /path/to/your/resume-data.json data/resume-data.json
   ```

2. Use the example format in `data/resume-data.example.json` as a template

3. Ensure the file is readable:
   ```bash
   chmod 644 data/resume-data.json
   ```

### 2. Configure Environment Variables

1. Set your OpenAI API key in `src/ai-consumer/.env.example`:
   ```bash
   cd src/ai-consumer
   cp .env.example .env
   nano .env  # Add your OPENAI_API_KEY
   ```

2. (Optional) Adjust rate limits and cost controls in `.env`:
   ```
   MAX_TOKENS_PER_RESPONSE=300  # Lower = cheaper
   CACHE_TTL_SECONDS=86400      # 24 hours
   RAG_CONFIDENCE_THRESHOLD=0.3 # Higher = more strict
   ```

### 3. Start the Services

```bash
# From project root
cd infra/docker

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 4. Verify Deployment

1. Check health:
   ```bash
   curl http://localhost:8080/health
   ```

2. Access the chat interface:
   ```
   http://localhost:8080/
   ```

3. Test the system with a question

## Production Deployment

### Using Cloudflare with Your Domain

1. **DNS Configuration**:
   - Point your domain to your server IP
   - Enable Cloudflare proxy (orange cloud) for DDoS protection

2. **HTTPS Setup** (Cloudflare handles SSL):
   - In Cloudflare dashboard: SSL/TLS → Full (recommended)
   - No need for Let's Encrypt on server

3. **Firewall Rules** (Cloudflare):
   - Rate limiting: 10 requests/minute per IP
   - Bot fight mode: Enable
   - Challenge malicious traffic

### Server Hardening

1. **Firewall (UFW)**:
   ```bash
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS (if using)
   sudo ufw enable
   ```

2. **Docker Network Isolation**:
   - Kafka and Redis are on internal network only
   - Only Nginx is exposed on port 8080

3. **Update Nginx Config for Production**:
   ```bash
   # Edit infra/nginx/nginx.conf
   # Change port binding in docker-compose to 80:
   ports:
     - "80:80"  # instead of 8080:80
   ```

### CORS Configuration

If hosting frontend separately, update `src/websocket-server/.env.example`:

```bash
ALLOW_ORIGINS=["https://yourdomain.com"]
ALLOW_CREDENTIALS=true
```

### Monitoring

1. **Check Logs**:
   ```bash
   # All services
   docker-compose logs -f

   # Specific service
   docker-compose logs -f ai-consumer

   # Check for rate limit violations
   docker-compose logs | grep "Rate limit exceeded"
   ```

2. **Resource Usage**:
   ```bash
   docker stats
   ```

3. **OpenAI Cost Tracking**:
   - Check logs for token usage:
     ```bash
     docker-compose logs ai-consumer | grep "Token usage"
     ```
   - Monitor in OpenAI dashboard: https://platform.openai.com/usage

## Cost Optimization

### Current Settings (Budget: $5/3 months ≈ $1.67/month)

With current configuration:
- **Max tokens per response**: 300 tokens
- **Caching enabled**: 24-hour TTL
- **Estimated capacity**:
  - ~50-70 questions/day (without cache hits)
  - ~200-300 questions/day (with 70% cache hit rate)

### Tips to Reduce Costs

1. **Increase Cache TTL**:
   ```bash
   CACHE_TTL_SECONDS=604800  # 7 days instead of 1
   ```

2. **Lower Max Tokens**:
   ```bash
   MAX_TOKENS_PER_RESPONSE=200  # Shorter responses
   ```

3. **Increase RAG Confidence Threshold**:
   ```bash
   RAG_CONFIDENCE_THRESHOLD=0.5  # More strict = better context
   ```

4. **Monitor Usage**:
   ```bash
   # Daily token count
   docker-compose logs ai-consumer --since 24h | grep "total_tokens" | wc -l
   ```

### Setting OpenAI Budget Limits

1. Go to https://platform.openai.com/account/billing/limits
2. Set "Monthly Budget": $2.00 (safety buffer)
3. Enable email notifications at 50% and 80%

## Backup and Updates

### Backup Resume Data

```bash
# Backup resume data
cp data/resume-data.json data/resume-data.backup-$(date +%Y%m%d).json
```

### Update Resume Data (Zero Downtime)

```bash
# Update the file
nano data/resume-data.json

# Restart only AI consumer
docker-compose restart ai-consumer

# Wait ~30 seconds for knowledge base to reload
```

### Update System

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

## Troubleshooting

### Services Won't Start

```bash
# Check what's running
docker-compose ps

# Check specific service logs
docker-compose logs ai-consumer

# Common issues:
# 1. Port already in use
sudo netstat -tulpn | grep :8080

# 2. Resume data file not found
ls -la data/resume-data.json
```

### High OpenAI Costs

```bash
# Check token usage in last 24h
docker-compose logs ai-consumer --since 24h | grep "total_tokens"

# Disable caching temporarily to debug
# (Edit .env: ENABLE_CACHING=false)
docker-compose restart ai-consumer

# Check for repeated questions (should be cached)
docker-compose logs ai-consumer | grep "Cache hit"
```

### Rate Limit Issues

```bash
# Check rate limit violations
docker-compose logs websocket-server-1 | grep "Rate limit"

# Adjust limits in src/websocket-server/.env:
USER_RATE_LIMIT_MAX_REQUESTS=20  # Increase if needed
```

### Knowledge Base Not Working

```bash
# Check if file is mounted
docker exec ai-consumer ls -la /app/data/

# Check loading logs
docker-compose logs ai-consumer | grep "knowledge base"

# Expected output:
# "Loading knowledge base from /app/data/resume-data.json"
# "Knowledge base loaded: X chunks"
```

## Scaling

### For Higher Traffic

1. **Increase WebSocket Servers**:
   ```yaml
   # In docker-compose.backend.yml
   # Add websocket-server-3, websocket-server-4, etc.
   ```

2. **Increase AI Consumer Workers**:
   ```bash
   # In .env
   MAX_WORKERS=100
   ```

3. **Add Redis Cluster** (if needed for high traffic)

## Security Checklist

- [ ] OpenAI API key in `.env` (not in code)
- [ ] Firewall configured (only 80/443 exposed)
- [ ] Cloudflare DDoS protection enabled
- [ ] Rate limiting configured (10 msg/min)
- [ ] Input validation enabled (500 char max)
- [ ] CORS properly configured
- [ ] Logs don't contain sensitive data
- [ ] Regular system updates enabled
- [ ] Monitoring alerts configured

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Verify configuration: `.env` files
3. Test components individually
4. Check GitHub issues (if applicable)
