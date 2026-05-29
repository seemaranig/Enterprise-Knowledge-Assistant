# Quick Start Guide - Production Backend

Get the upgraded backend running in minutes!

## 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## 2. Configure Environment

```bash
# Copy the example
cp .env.example .env

# Edit with your settings
nano .env  # or use your editor
```

**Key settings to update**:
- `OLLAMA_MODEL`: Which model to use (default: llama3)
- `OLLAMA_BASE_URL`: Where Ollama is running
- `DEBUG`: Set to False for production
- `LOG_LEVEL`: INFO or WARNING for production

## 3. Start Ollama (if local)

```bash
# In another terminal
ollama serve

# In yet another terminal
ollama pull llama3  # Download the model if not already done
```

## 4. Run the Backend

### Development Mode
```bash
export DEBUG=True
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload
```

Visit: http://localhost:8000/docs

### Production Mode
```bash
export DEBUG=False
export LOG_LEVEL=INFO
gunicorn -c gunicorn_config.py app.main:app
```

## 5. Quick Test

```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs

# Try uploading a PDF
curl -X POST -F "file=@sample.pdf" http://localhost:8000/upload

# Try a query
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?"}'
```

## 6. Docker Deployment

```bash
# Build image
docker build -t enterprise-ka-backend:v1.0.0 .

# Run container
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/vectorstore:/app/vectorstore \
  -v $(pwd)/logs:/app/logs \
  --name backend \
  enterprise-ka-backend:v1.0.0

# Check status
docker logs -f backend

# Stop
docker stop backend
```

## 7. Docker Compose (Full Stack)

```bash
# Start everything (backend + frontend + Ollama)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

## 8. View Logs

```bash
# Live logs
tail -f logs/app.log

# Error logs only
tail -f logs/error.log

# Last 50 lines
tail -50 logs/app.log
```

## 9. Common Issues

### "Connection to Ollama failed"
```bash
# Check Ollama is running
curl http://localhost:11434

# Or update OLLAMA_BASE_URL in .env
export OLLAMA_BASE_URL=http://host.docker.internal:11434  # For Docker
```

### "Vector database not found"
Upload a PDF first via `/upload` endpoint

### "Rate limit exceeded"
```bash
# Disable rate limiting in .env
RATE_LIMIT_ENABLED=False

# Or increase limits
RATE_LIMIT_REQUESTS=1000
```

## 10. Next Steps

1. **Read**: `README_BACKEND.md` for detailed documentation
2. **Deploy**: `DEPLOYMENT_GUIDE.md` for production deployment
3. **Launch**: `PRODUCTION_CHECKLIST.md` before going live
4. **Monitor**: Set up monitoring and alerting

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Health check |
| GET | `/docs` | API documentation (Swagger) |
| POST | `/upload` | Upload PDF |
| POST | `/chat` | Ask question |

## Example cURL Commands

```bash
# Health check
curl http://localhost:8000/health

# Upload PDF
curl -X POST \
  -F "file=@document.pdf" \
  http://localhost:8000/upload

# Ask a question
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize this document",
    "include_sources": true
  }'

# Pretty print JSON response
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the main topic?"}' | jq
```

## Python Example

```python
import requests

api_url = "http://localhost:8000"

# Upload PDF
with open("document.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(f"{api_url}/upload", files=files)
    print(response.json())

# Ask question
response = requests.post(
    f"{api_url}/chat",
    json={"query": "What is this about?"}
)
print(response.json())
```

## Environment Variables

Quick reference:

```bash
# API
DEBUG=False                              # Enable debug mode
LOG_LEVEL=INFO                           # DEBUG, INFO, WARNING, ERROR

# Models
OLLAMA_MODEL=llama3                      # LLM model
OLLAMA_BASE_URL=http://localhost:11434  # Ollama endpoint
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Storage
MAX_UPLOAD_SIZE_MB=50                    # Max file size
CHUNK_SIZE=500                           # Text chunk size
CHUNK_OVERLAP=50                         # Chunk overlap

# Rate Limiting
RATE_LIMIT_ENABLED=True                  # Enable limits
RATE_LIMIT_REQUESTS=100                  # Per period
RATE_LIMIT_PERIOD_SECONDS=60             # Time window

# CORS
ALLOWED_ORIGINS=http://localhost:8501,http://localhost:3000
```

## Performance Tips

1. **Faster responses**: Increase `RETRIEVER_K` in `.env` (get more docs)
2. **Better answers**: Decrease `CHUNK_SIZE` for more granular chunks
3. **More scalable**: Run with gunicorn and 4-8 workers
4. **Better reliability**: Set up monitoring and health checks

## Production Checklist

Before deploying to production:

- [ ] `.env` configured with production values
- [ ] Docker image built and tested
- [ ] Health check passing
- [ ] Rate limiting configured
- [ ] Logging set to WARNING level
- [ ] Error tracking configured (Sentry)
- [ ] Monitoring set up (Prometheus/Grafana)
- [ ] Backup strategy in place
- [ ] SSL/TLS certificates ready
- [ ] Load balancer configured

See `PRODUCTION_CHECKLIST.md` for complete list.

## Getting Help

- **Docs**: `README_BACKEND.md`
- **Deployment**: `DEPLOYMENT_GUIDE.md`
- **API**: http://localhost:8000/docs (Swagger)
- **Logs**: `logs/app.log`

## Monitoring Your Backend

```bash
# Check health
watch -n 5 'curl -s http://localhost:8000/health | jq'

# Monitor logs
tail -f logs/app.log | grep ERROR

# Check resource usage
docker stats backend

# API stats
curl http://localhost:8000/metrics | head -20
```

---

**Ready to deploy?** See `DEPLOYMENT_GUIDE.md` next!
