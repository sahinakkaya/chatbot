# Security Guide

This document describes the security measures implemented in the system and best practices for deployment.

## Security Architecture

### Multi-Layer Defense Strategy

```
┌─────────────────────────────────────────────────┐
│ Layer 1: Cloudflare (DDoS Protection)          │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│ Layer 2: Nginx (Load Balancing, Rate Limiting) │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│ Layer 3: WebSocket Server (Input Validation)   │
│  - Rate limiting (10 msg/min per user)         │
│  - Message size limits (500 chars)             │
│  - Input sanitization                          │
│  - Prompt injection detection                  │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│ Layer 4: AI Consumer (RAG, Caching)            │
│  - Knowledge base constraints                  │
│  - Response caching                            │
│  - Token budgets                               │
└─────────────────────────────────────────────────┘
```

## Implemented Security Measures

### 1. Rate Limiting (✓ IMPLEMENTED)

**Per-User Rate Limits** (Redis-based):
- **10 messages per minute** per user
- **100 messages per hour** per user
- Configured in: `src/websocket-server/websocket_server/config.py`

**How it works**:
```python
# Rate limit keys in Redis:
rate_limit:{userid}  # Tracks message count per window
TTL: 60 seconds      # Auto-expires after window
```

**Configuration**:
```bash
# src/websocket-server/.env
USER_RATE_LIMIT_MAX_REQUESTS=10
USER_RATE_LIMIT_WINDOW_SECONDS=60
```

**What it prevents**:
- API abuse and cost exhaustion
- Spam attacks
- Resource exhaustion

### 2. Input Validation & Sanitization (✓ IMPLEMENTED)

**Message Length Limits**:
- Maximum: 500 characters
- Prevents token exhaustion attacks
- Location: `websocket_server/security/input_validator.py`

**Content Sanitization**:
- Removes control characters
- Escapes HTML entities (prevents XSS)
- Normalizes whitespace
- Strips dangerous patterns

**Prompt Injection Detection**:
Detects and blocks patterns like:
- "Ignore previous instructions"
- "You are now..."
- "Forget everything"
- "System:"
- "Disregard all rules"
- Role-playing attempts

**Implementation**:
```python
# Automatic sanitization in message handler
sanitized_content = input_validator.validate_and_sanitize(
    content,
    max_length=500
)
```

### 3. Response Caching (✓ IMPLEMENTED)

**Benefits**:
- Reduces OpenAI API calls (saves money)
- Faster response times
- Reduces load on OpenAI API

**Implementation**:
- Cache key: SHA256 hash of question
- TTL: 24 hours (configurable)
- Storage: Redis
- Location: `ai_consumer/dependencies.py`

**Cost Savings**:
- Cache hit = $0.00 (no API call)
- Cache miss = ~$0.0002-0.0004 per question
- Expected 50-70% cache hit rate for common questions

### 4. RAG (Retrieval-Augmented Generation) (✓ IMPLEMENTED)

**Security Benefits**:
- AI responses constrained to knowledge base
- Prevents hallucination
- Reduces exposure of system prompts
- Limits scope of answers

**How it works**:
```
1. User asks question
2. System searches knowledge base (local, no API)
3. Retrieves top 3 relevant chunks
4. Builds constrained prompt with context
5. AI can ONLY answer from provided context
```

**Configuration**:
```bash
RAG_MAX_CHUNKS=3                  # Number of context chunks
RAG_CONFIDENCE_THRESHOLD=0.3      # Minimum similarity score
```

**Knowledge Base Security**:
- Read-only mount in Docker
- Local embeddings (no external API calls)
- No user data stored in knowledge base

### 5. Token Budget Limits (✓ IMPLEMENTED)

**Current Limits**:
- Max tokens per response: 300 (was 500)
- Timeout: 2 seconds per request
- Max concurrent workers: 50

**Cost Protection**:
```
Daily estimate (worst case):
- 100 questions/day × 300 tokens × $0.002/1K = $0.06/day
- Monthly: ~$1.80

With 70% cache hit:
- 30 API calls/day = $0.018/day
- Monthly: ~$0.54 (well within $5 budget)
```

**Configuration**:
```bash
MAX_TOKENS_PER_RESPONSE=300
MAX_WORKERS=50
```

### 6. Authentication (✓ IMPLEMENTED)

**Token-Based Auth**:
- Random 32-byte tokens generated per user
- Stored in Redis with TTL (1 hour)
- Required for WebSocket connection

**How it works**:
```javascript
// 1. Frontend requests token
POST /token?userid={userid}

// 2. Backend generates token
token = secrets.token_urlsafe(32)
redis.set(f"token:{userid}", token, ttl=3600)

// 3. Frontend connects with token
ws://server/ws?token={token}&userid={userid}
```

**Security**:
- Tokens expire after 1 hour
- Tokens validated on every connection
- Invalid tokens rejected immediately

### 7. Network Isolation (✓ IMPLEMENTED)

**Docker Network Architecture**:
```
Public:
  - Nginx (port 80/8080)

Internal Only (app-network):
  - Kafka (port 29092)
  - Redis (port 6379)
  - WebSocket Servers
  - AI Consumer
  - Message Relay
```

**Benefits**:
- Kafka and Redis not exposed to internet
- Only Nginx accessible from outside
- Services communicate on internal bridge network

### 8. CORS Configuration (✓ IMPLEMENTED)

**Current Settings** (Development):
```python
ALLOW_ORIGINS=["*"]           # Wildcard
ALLOW_CREDENTIALS=False
ALLOW_METHODS=["*"]
ALLOW_HEADERS=["*"]
```

**Production Settings** (Recommended):
```python
ALLOW_ORIGINS=["https://yourdomain.com"]
ALLOW_CREDENTIALS=True
ALLOW_METHODS=["GET", "POST"]
ALLOW_HEADERS=["Content-Type", "Authorization"]
```

**Configuration**:
`src/websocket-server/.env`:
```bash
ALLOW_ORIGINS=["https://yourdomain.com"]
```

## Attack Vectors & Mitigations

### ✅ Mitigated Attacks

| Attack Type | Mitigation | Status |
|-------------|------------|--------|
| Rate Limit Abuse | 10 msg/min limit | ✓ |
| Cost Exhaustion | Token limits + caching | ✓ |
| Prompt Injection | Pattern detection + RAG constraints | ✓ |
| XSS Attacks | Input/output sanitization | ✓ |
| DDoS | Cloudflare + rate limiting | ✓ |
| Token Brute Force | Secure random tokens (256-bit) | ✓ |
| Message Flooding | Size + rate limits | ✓ |
| Data Exfiltration | RAG constraints, no raw KB access | ✓ |
| Replay Attacks | Token expiration (1 hour) | ✓ |

### ⚠️ Partially Mitigated

| Attack Type | Current Status | Recommendation |
|-------------|---------------|----------------|
| IP Spoofing | Relies on X-Forwarded-For | Use Cloudflare (trusted proxy) |
| Credential Stuffing | Anonymous access | Optional: Add CAPTCHA |
| Advanced Prompt Injection | Pattern-based detection | Monitor logs, update patterns |

### 🔴 Not Implemented (Lower Priority for Personal Site)

| Attack Type | Why Not Critical | Optional Solution |
|-------------|------------------|-------------------|
| SQL Injection | No SQL database | N/A |
| CSRF | Stateless WebSocket | Add CSRF tokens if needed |
| Session Hijacking | Short-lived tokens | Use HTTPS only |
| Advanced Bot Detection | Low traffic site | Add hCaptcha if needed |

## Monitoring & Alerts

### Log Monitoring

**Security Events to Monitor**:
```bash
# Rate limit violations
docker-compose logs | grep "Rate limit exceeded"

# Suspicious input patterns
docker-compose logs | grep "Suspicious pattern detected"

# Failed authentication
docker-compose logs | grep "Invalid token"

# High token usage (cost monitoring)
docker-compose logs ai-consumer | grep "total_tokens"
```

### Recommended Alerts

1. **Cost Alert**:
   - OpenAI Dashboard → Set budget limit: $2/month
   - Email alert at 50% usage

2. **Rate Limit Alert**:
   ```bash
   # Check hourly
   if [ $(docker-compose logs --since 1h | grep "Rate limit" | wc -l) -gt 50 ]; then
     echo "High rate limit violations detected"
   fi
   ```

3. **Error Rate Alert**:
   ```bash
   # Monitor error responses
   docker-compose logs nginx --since 1h | grep "429\|500\|503"
   ```

## Cloudflare Configuration (Recommended)

### DNS Setup
1. Add A record: `yourdomain.com` → `your-server-ip`
2. Enable proxy (orange cloud icon)
3. SSL/TLS → Full (not Full Strict)

### Security Rules

1. **Rate Limiting**:
   - Security → WAF → Rate Limiting Rules
   - Rule: 10 requests per minute per IP
   - Action: Block for 1 minute

2. **Bot Fight Mode**:
   - Security → Bots → Enable
   - Challenge automated traffic

3. **Firewall Rules**:
   ```
   (ip.geoip.country ne "US" and ip.geoip.country ne "CA")
   → Challenge
   ```
   (Adjust countries as needed)

4. **DDoS Protection**:
   - Auto-enabled with Cloudflare
   - No configuration needed

## Incident Response

### If You Detect Abuse

1. **Immediate Actions**:
   ```bash
   # Block specific user
   docker exec redis redis-cli SET "block:{userid}" "1" EX 3600

   # Reduce rate limits temporarily
   # Edit .env: USER_RATE_LIMIT_MAX_REQUESTS=5
   docker-compose restart websocket-server-1 websocket-server-2
   ```

2. **Check Damage**:
   ```bash
   # Check today's API costs
   docker-compose logs ai-consumer --since 24h | grep "total_tokens" \
     | awk '{sum+=$NF} END {print "Total tokens:", sum}'
   ```

3. **Long-term Fix**:
   - Update suspicious pattern detection
   - Lower rate limits if needed
   - Add CAPTCHA for high-risk patterns

### If OpenAI Budget Exceeded

1. **Stop Services**:
   ```bash
   docker-compose stop ai-consumer
   ```

2. **Investigate**:
   ```bash
   docker-compose logs ai-consumer | grep "total_tokens" > token_usage.log
   ```

3. **Prevent Future**:
   - Set OpenAI hard limit: $1/month
   - Reduce MAX_TOKENS_PER_RESPONSE
   - Increase CACHE_TTL_SECONDS

## Security Checklist

### Before Deployment
- [ ] OpenAI API key in `.env` file (not code)
- [ ] CORS configured for your domain
- [ ] Cloudflare DNS configured
- [ ] Firewall rules applied (UFW)
- [ ] Docker containers on internal network
- [ ] Resume data doesn't contain secrets
- [ ] Rate limits appropriate for your traffic

### After Deployment
- [ ] Test rate limiting (send 11 messages quickly)
- [ ] Test prompt injection (try "ignore instructions")
- [ ] Test message length limit (send 501 chars)
- [ ] Verify HTTPS works (if using Cloudflare)
- [ ] Check logs for errors
- [ ] Monitor OpenAI usage for 24h
- [ ] Verify caching works (ask same question twice)

### Monthly Maintenance
- [ ] Review logs for suspicious activity
- [ ] Check OpenAI costs
- [ ] Update Docker images
- [ ] Verify backups of resume data
- [ ] Test system still responding correctly
- [ ] Review and rotate secrets if needed

## Additional Hardening (Optional)

### For Higher Security Needs

1. **Add CAPTCHA**:
   - Use hCaptcha (free)
   - Require on first message per session

2. **IP-Based Rate Limiting**:
   - Already implemented in rate_limiter.py
   - Enable in websocket_handler.py

3. **JWT Tokens** (Instead of simple tokens):
   - Add expiration claims
   - Sign with secret key
   - More secure for production

4. **Audit Logging**:
   - Log all questions to separate file
   - Implement log rotation
   - Set up log analysis tools

5. **WAF (Web Application Firewall)**:
   - Cloudflare WAF (paid tier)
   - ModSecurity (open source)

## Reporting Security Issues

If you discover a security vulnerability:
1. **DO NOT** open a public GitHub issue
2. Email: [your-security-email]
3. Include: Description, steps to reproduce, impact
4. Expected response time: 48 hours

## Compliance

This system:
- ✓ Does not store user data persistently
- ✓ Does not use cookies
- ✓ Does not track users across sessions
- ✓ Minimal data sent to OpenAI (questions only)
- ✓ No PII collected

**GDPR Considerations**:
- Questions are cached for 24h (inform users)
- No user accounts or emails collected
- Data not shared with third parties (except OpenAI for processing)

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OpenAI Best Practices](https://platform.openai.com/docs/guides/safety-best-practices)
- [Docker Security](https://docs.docker.com/engine/security/)
- [Cloudflare Security](https://www.cloudflare.com/learning/security/)
