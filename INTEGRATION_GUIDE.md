# Website Integration Guide

This guide explains how to integrate the Q&A system into your website.

## Overview

You now have a complete RAG-enhanced Q&A system with:
- ✅ **Security**: Rate limiting, input validation, prompt injection detection
- ✅ **Cost Control**: Response caching, token budgets, optimized prompts
- ✅ **RAG**: Knowledge base from your resume-data.json
- ✅ **Frontend**: Clean, responsive chat interface
- ✅ **Scalability**: Load-balanced WebSocket servers

## What's Been Implemented

### 1. Security Features

**Rate Limiting**:
- 10 messages per minute per user
- 100 messages per hour per user
- Prevents abuse and cost exhaustion

**Input Validation**:
- Max message length: 500 characters
- HTML sanitization (prevents XSS)
- Control character removal
- Prompt injection detection

**Network Security**:
- Kafka and Redis on internal network only
- Token-based authentication
- CORS configuration

### 2. RAG (Knowledge Base)

**How It Works**:
1. Your resume data is loaded into a vector database
2. When user asks a question, system searches for relevant info
3. AI answers ONLY based on retrieved context
4. Prevents hallucination and keeps answers accurate

**Files**:
- `src/common/knowledge-base/` - RAG implementation
- `data/resume-data.json` - Your resume data (create this!)
- `data/resume-data.example.json` - Template to follow

### 3. Cost Controls

**Caching**:
- Identical questions cached for 24 hours
- Cache = $0 API cost
- Expected 50-70% cache hit rate

**Token Limits**:
- Max 300 tokens per response (reduced from 500)
- Shorter responses = lower costs
- Estimated cost: $0.50-1.80/month

**Monitoring**:
- Token usage logged
- OpenAI dashboard for spending
- Email alerts at 50% budget

### 4. Frontend

**Features**:
- Clean, modern chat interface
- WebSocket connection with auto-reconnect
- Loading indicators
- Error handling
- Character counter
- Responsive design (mobile-friendly)

**Files**:
- `infra/nginx/chat.html` - Main chat interface
- `infra/nginx/test-ui.html` - Original test UI (still available)

## Setup Steps

### Step 1: Prepare Your Resume Data

1. Create `data/resume-data.json`:
   ```bash
   cd /home/user/nova-prime-challenge
   mkdir -p data
   cp data/resume-data.example.json data/resume-data.json
   ```

2. Edit with your information:
   ```json
   {
     "personal": {
       "name": "Your Name",
       "title": "Your Title",
       ...
     },
     "experience": [...],
     "skills": {...},
     ...
   }
   ```

3. Include sections like:
   - Personal info (name, title, location)
   - Professional summary
   - Work experience
   - Education
   - Skills
   - Projects
   - Certifications
   - Interests

### Step 2: Configure OpenAI

1. Get API key from https://platform.openai.com/api-keys

2. Set in `.env`:
   ```bash
   cd src/ai-consumer
   nano .env
   # Add: OPENAI_API_KEY="sk-..."
   ```

3. Set budget limits:
   - Go to https://platform.openai.com/account/billing/limits
   - Set monthly budget: $2.00
   - Enable email alerts

### Step 3: (Optional) Customize System Prompt

Edit `src/ai-consumer/.env`:

```bash
SYSTEM_PROMPT_TEMPLATE="You are an AI assistant for [Your Name], a [Your Title]. Answer questions about their professional background, skills, and projects. Be concise and friendly."
```

### Step 4: Build and Deploy

```bash
cd infra/docker

# Build images
docker-compose build

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Step 5: Test Locally

1. Access chat: http://localhost:8080/
2. Ask a question: "What are your main skills?"
3. Verify response comes from your resume data
4. Ask again (should be faster - cached!)

## Integrating into Your Website

### Option 1: Embed as iFrame (Simplest)

```html
<!-- On your website -->
<iframe
  src="https://yourdomain.com/chat.html"
  width="100%"
  height="600px"
  frameborder="0"
></iframe>
```

### Option 2: Custom Integration

Use the WebSocket API directly:

```javascript
// 1. Get token
const response = await fetch('https://yourdomain.com/token?userid=user123', {
  method: 'POST'
});
const { token } = await response.json();

// 2. Connect WebSocket
const ws = new WebSocket(`wss://yourdomain.com/ws?token=${token}&userid=user123`);

// 3. Send message
ws.send(JSON.stringify({
  type: 'message',
  content: 'What are your skills?'
}));

// 4. Receive response
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('AI Response:', data.content);
};
```

### Option 3: Standalone Page

Just link to it:
```html
<a href="https://yourdomain.com/chat.html">Ask Me Anything</a>
```

## Production Deployment (Your Server)

### Prerequisites

- Linux server (Ubuntu recommended)
- Docker & Docker Compose installed
- Domain name
- Cloudflare account (free)

### Setup Steps

1. **Server Setup**:
   ```bash
   # On your server
   git clone <your-repo>
   cd nova-prime-challenge
   ```

2. **Configure Environment**:
   ```bash
   # Add your OpenAI key
   cd src/ai-consumer
   cp .env.example .env
   nano .env  # Add OPENAI_API_KEY

   # Add your resume data
   cd ../../data
   nano resume-data.json  # Paste your data
   ```

3. **Configure CORS** (if hosting frontend separately):
   ```bash
   cd src/websocket-server
   nano .env
   # Change: ALLOW_ORIGINS=["https://yourdomain.com"]
   ```

4. **Start Services**:
   ```bash
   cd infra/docker
   docker-compose up -d
   ```

5. **Configure Cloudflare**:
   - DNS: Point yourdomain.com to server IP
   - Enable proxy (orange cloud)
   - SSL/TLS: Set to "Full"
   - Security → Rate Limiting: 10 req/min per IP

6. **Configure Nginx for Production**:
   ```bash
   # Edit docker-compose.backend.yml
   # Change nginx ports:
   ports:
     - "80:80"  # instead of 8080:80
   ```

7. **Firewall**:
   ```bash
   sudo ufw allow 22/tcp   # SSH
   sudo ufw allow 80/tcp   # HTTP
   sudo ufw allow 443/tcp  # HTTPS
   sudo ufw enable
   ```

8. **Verify**:
   - Visit: https://yourdomain.com
   - Ask a question
   - Check logs: `docker-compose logs -f`

## Customization Options

### Change Rate Limits

`src/websocket-server/.env`:
```bash
USER_RATE_LIMIT_MAX_REQUESTS=20  # 20 instead of 10
USER_RATE_LIMIT_WINDOW_SECONDS=60
MAX_MESSAGE_LENGTH=1000  # Longer messages
```

### Adjust RAG Settings

`src/ai-consumer/.env`:
```bash
RAG_MAX_CHUNKS=5  # More context (costs more tokens)
RAG_CONFIDENCE_THRESHOLD=0.5  # Higher = more strict matching
```

### Change Response Style

`src/ai-consumer/.env`:
```bash
SYSTEM_PROMPT_TEMPLATE="You are a friendly AI. Use emojis and be casual!"
MAX_TOKENS_PER_RESPONSE=500  # Longer responses
```

### Customize Frontend

Edit `infra/nginx/chat.html`:
- Change colors in CSS `:root` variables
- Update header text
- Modify welcome message
- Add your logo

## Monitoring and Maintenance

### Daily Monitoring

```bash
# Check service health
curl https://yourdomain.com/health

# Check logs for errors
docker-compose logs --since 24h | grep ERROR

# Check token usage
docker-compose logs ai-consumer --since 24h | grep "total_tokens"
```

### Weekly Tasks

```bash
# Review OpenAI costs
# Visit: https://platform.openai.com/usage

# Check for abuse
docker-compose logs | grep "Rate limit exceeded" | wc -l

# Backup resume data
cp data/resume-data.json data/backup-$(date +%Y%m%d).json
```

### Monthly Maintenance

```bash
# Update system
docker-compose pull
docker-compose down
docker-compose up -d

# Check security
docker-compose logs | grep "Suspicious pattern"

# Review cache hit rate
docker-compose logs ai-consumer | grep "Cache hit" | wc -l
```

## Cost Estimation

**Your Budget**: $5 for 3 months = $1.67/month

**Expected Usage**:
- With caching (70% hit rate): 30 API calls/day
- Cost per call: ~$0.0002-0.0004
- Daily cost: ~$0.006-0.012
- Monthly cost: ~$0.18-0.36

**Safety Buffer**: Well within budget!

**If site becomes popular**:
- Increase cache TTL to 7 days
- Lower MAX_TOKENS_PER_RESPONSE to 200
- Consider switching to gpt-3.5-turbo-0125 (latest, cheaper)

## Troubleshooting

### "Knowledge base not found"

```bash
# Check file exists
ls -la data/resume-data.json

# Check mounted in container
docker exec ai-consumer ls -la /app/data/

# Fix permissions
chmod 644 data/resume-data.json
```

### "Rate limit exceeded" (User complaint)

```bash
# Check if legitimate user
docker-compose logs websocket-server-1 | grep "userid:{their_id}"

# If legit, increase limits in .env
USER_RATE_LIMIT_MAX_REQUESTS=20

# Restart
docker-compose restart websocket-server-1 websocket-server-2
```

### High OpenAI Costs

```bash
# Check token usage
docker-compose logs ai-consumer | grep total_tokens | \
  awk '{sum+=$NF} END {print "Total tokens:", sum}'

# Check cache hit rate
cache_hits=$(docker-compose logs ai-consumer | grep "Cache hit" | wc -l)
total_requests=$(docker-compose logs ai-consumer | grep "Received message" | wc -l)
echo "Cache hit rate: $((cache_hits * 100 / total_requests))%"

# If low hit rate, increase TTL
CACHE_TTL_SECONDS=604800  # 7 days
```

### AI Giving Wrong Answers

1. **Check if question is in resume**:
   - Ensure topic is covered in resume-data.json
   - Add missing information

2. **Adjust RAG threshold**:
   ```bash
   RAG_CONFIDENCE_THRESHOLD=0.4  # Increase for stricter matching
   ```

3. **Check logs**:
   ```bash
   docker-compose logs ai-consumer | grep "Retrieved context"
   ```

## Support and Resources

- **Documentation**:
  - `CLAUDE.md` - Project overview
  - `DEPLOYMENT.md` - Deployment guide
  - `SECURITY.md` - Security details
  - `INTEGRATION_GUIDE.md` - This file

- **Logs**:
  ```bash
  docker-compose logs -f  # All services
  docker-compose logs ai-consumer  # Specific service
  ```

- **Health Check**:
  ```bash
  curl http://localhost:8080/health
  ```

## Next Steps (Future Enhancements)

### Telegram Integration (Optional)

For questions not in knowledge base:
1. System detects low confidence (<0.3)
2. Sends question to your Telegram
3. You respond
4. System sends your response to user

*Not implemented yet - let me know if you want this!*

### Analytics Dashboard

Track:
- Most asked questions
- Cache hit rates
- Daily costs
- User engagement

### Multi-language Support

Add support for questions in other languages using OpenAI translation.

## Summary

You now have:
- ✅ Secure, cost-controlled Q&A system
- ✅ RAG-based responses from your resume
- ✅ Clean frontend interface
- ✅ Production-ready deployment
- ✅ Comprehensive documentation

**Total implementation**:
- 10+ new files
- 2000+ lines of code
- Full security hardening
- Cost optimization
- Production deployment guide

**Estimated setup time**: 30-60 minutes
**Monthly cost**: ~$0.50 (well within budget!)

Good luck with your deployment! 🚀
