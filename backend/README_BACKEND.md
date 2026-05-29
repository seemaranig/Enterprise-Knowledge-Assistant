# Backend - Enterprise Knowledge Assistant

Production-grade FastAPI backend for the Enterprise Knowledge Assistant system.

## Features

- ✅ **Production-Ready**: Error handling, logging, rate limiting
- ✅ **Robust Error Handling**: Custom exception classes and handlers
- ✅ **Comprehensive Logging**: Rotating file logs with multiple handlers
- ✅ **Rate Limiting**: Built-in request rate limiting
- ✅ **Input Validation**: Pydantic models for all endpoints
- ✅ **Security**: CORS configuration, safe file handling, path traversal prevention
- ✅ **Vector DB Management**: Smart merging instead of overwriting
- ✅ **Health Checks**: Built-in health endpoint
- ✅ **Environment Configuration**: 12-factor app compliant
- ✅ **Docker Optimized**: Multi-stage builds, non-root user, health checks
- ✅ **API Documentation**: Auto-generated Swagger docs

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration management
│   ├── models.py         # Pydantic request/response models
│   ├── logger.py         # Logging configuration
│   ├── exceptions.py     # Custom exceptions
│   ├── ingest.py         # PDF ingestion logic
│   ├── rag.py           # RAG query logic
│   └── utils.py         # Utility functions
├── data/                 # Uploaded PDFs
├── vectorstore/          # FAISS vector database
├── logs/                # Application logs
├── Dockerfile           # Production Docker image
├── requirements.txt     # Dependencies with pinned versions
├── .env.example         # Environment variables template
├── .dockerignore        # Docker build optimization
└── README.md            # This file
```

## Setup & Installation

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Ollama (with llama3 model)

### Local Development

1. **Create environment file**:
```bash
cp .env.example .env
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Ensure Ollama is running**:
```bash
ollama pull llama3
ollama serve
```

4. **Run the API**:
```bash
# Development mode (with auto-reload)
export DEBUG=True
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
gunicorn --workers 4 \
         --worker-class uvicorn.workers.UvicornWorker \
         --bind 0.0.0.0:8000 \
         app.main:app
```

### Docker Deployment

```bash
# Build image
docker build -t enterprise-ka-backend:latest .

# Run container
docker run -p 8000:8000 \
           -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
           -v $(pwd)/data:/app/data \
           -v $(pwd)/vectorstore:/app/vectorstore \
           -v $(pwd)/logs:/app/logs \
           enterprise-ka-backend:latest

# Or use Docker Compose
docker-compose up backend
```

## API Endpoints

### Health Check
```bash
GET /health
```
Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "api": "healthy",
    "vector_db": "healthy"
  }
}
```

### Upload PDF
```bash
POST /upload
Content-Type: multipart/form-data

# Form data:
file: <PDF file>
```

Response:
```json
{
  "message": "PDF uploaded and processed successfully",
  "filename": "document.pdf",
  "chunks_created": 42,
  "total_chunks": 42
}
```

### Chat/Query
```bash
POST /chat
Content-Type: application/json

{
  "query": "What is this document about?",
  "include_sources": true
}
```

Response:
```json
{
  "response": "This document is about...",
  "sources": ["document.pdf - Page 1", "document.pdf - Page 3"],
  "tokens_used": null
}
```

### Auto-Generated Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Configuration

All settings can be configured via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | False | Enable debug mode |
| `OLLAMA_MODEL` | llama3 | LLM model name |
| `OLLAMA_BASE_URL` | http://localhost:11434 | Ollama API endpoint |
| `EMBEDDING_MODEL` | sentence-transformers/all-MiniLM-L6-v2 | Embedding model |
| `VECTOR_DB_PATH` | vectorstore/faiss_index | Vector database path |
| `MAX_UPLOAD_SIZE_MB` | 50 | Maximum upload size in MB |
| `CHUNK_SIZE` | 500 | PDF chunk size |
| `CHUNK_OVERLAP` | 50 | Chunk overlap for RAG |
| `RETRIEVER_K` | 3 | Number of documents to retrieve |
| `RATE_LIMIT_ENABLED` | True | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | 100 | Requests per period |
| `RATE_LIMIT_PERIOD_SECONDS` | 60 | Rate limit period |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ALLOWED_ORIGINS` | http://localhost:8501,http://localhost:3000 | CORS allowed origins |

## Logging

Logs are written to:
- **Console**: All levels
- **logs/app.log**: Rotating file (10MB max, 5 backups)
- **logs/error.log**: Error level only

Log format:
```
2024-01-15 10:30:45,123 - enterprise_ka - INFO - [uuid] Message
```

## Error Handling

The API returns consistent error responses:

```json
{
  "error": "Error type",
  "detail": "Detailed error message",
  "request_id": "uuid-for-tracking"
}
```

### HTTP Status Codes
- `200`: Success
- `400`: Bad request (validation error)
- `429`: Too many requests (rate limit)
- `500`: Internal server error
- `503`: Service unavailable

## Rate Limiting

- Enabled by default
- 100 requests per 60 seconds per client IP
- Returns `429 Too Many Requests` when exceeded
- Can be disabled via `RATE_LIMIT_ENABLED=False`

## Security Considerations

- ✅ CORS restricted to configured origins
- ✅ File upload validation (PDF only)
- ✅ Path traversal prevention
- ✅ File size limits
- ✅ Non-root Docker user
- ✅ Input validation with Pydantic
- ✅ Safe filename generation
- ✅ Request ID tracking for audit

## Performance

- **Multi-worker deployment**: Gunicorn with 4 workers
- **Vector DB**: FAISS with CPU optimization
- **Embeddings**: Cached across requests
- **Async operations**: FastAPI async support
- **Rate limiting**: In-memory with cleanup

## Monitoring & Debugging

### Health Check
```bash
curl http://localhost:8000/health
```

### View Logs
```bash
# Real-time logs
tail -f logs/app.log

# Error logs
tail -f logs/error.log

# Full logs with timestamps
cat logs/app.log
```

### Request Tracking
All responses include `X-Request-ID` header for tracking:
```bash
curl -i http://localhost:8000/health
# X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

## Production Deployment

### Recommended Setup
1. **Web Server**: Nginx or similar (reverse proxy)
2. **App Server**: Gunicorn with 4-8 workers
3. **Database**: FAISS (file-based) or PostgreSQL + pgvector for scaling
4. **Cache**: Redis for rate limiting (replace in-memory store)
5. **Monitoring**: Prometheus + Grafana
6. **Logging**: ELK stack or similar

### Docker Compose Example
See `docker-compose.yml` in root directory

### Environment for Production
```bash
export DEBUG=False
export LOG_LEVEL=INFO
export RATE_LIMIT_REQUESTS=1000
export MAX_UPLOAD_SIZE_MB=100
# ... other settings
```

## Development

### Running Tests
```bash
pytest tests/ -v
```

### Type Checking
```bash
mypy app/
```

### Linting
```bash
pylint app/
flake8 app/
```

## Troubleshooting

### Issue: "Vector database not found"
**Solution**: Upload a PDF first via `/upload` endpoint

### Issue: "LLM connection failed"
**Solution**: 
1. Check Ollama is running: `ollama serve`
2. Verify `OLLAMA_BASE_URL` is correct
3. Verify model exists: `ollama list`

### Issue: "Rate limit exceeded"
**Solution**:
1. Disable rate limiting in `.env`: `RATE_LIMIT_ENABLED=False`
2. Or increase limits: `RATE_LIMIT_REQUESTS=1000`

### Issue: "PDF processing failed"
**Solution**:
1. Check file is valid PDF
2. Check file size < `MAX_UPLOAD_SIZE_MB`
3. Check disk space for vectorstore

## API Testing

### cURL Examples
```bash
# Health check
curl http://localhost:8000/health

# Upload PDF
curl -X POST -F "file=@document.pdf" http://localhost:8000/upload

# Chat query
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this about?"}'

# With request tracking
curl -i http://localhost:8000/health
```

### Python Example
```python
import requests

# Upload
with open("document.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/upload", files=files)

# Query
response = requests.post("http://localhost:8000/chat", json={
    "query": "What is this document about?"
})

print(response.json())
```

## License

All rights reserved.

## Support

For issues or questions, please contact the development team.
