# Frontend - Enterprise Knowledge Assistant

Production-grade Streamlit frontend for the Enterprise Knowledge Assistant system.

## Features

- ✅ **Production-Ready UI**: Clean, responsive interface
- ✅ **Error Handling**: Graceful error messages and recovery
- ✅ **API Client**: Retry logic, timeout handling, connection management
- ✅ **Session Management**: Persistent chat history and state
- ✅ **Logging**: File-based logging for debugging
- ✅ **Configuration**: Environment-based settings
- ✅ **Health Checks**: Backend connectivity verification
- ✅ **Security**: Input validation, safe file handling
- ✅ **Responsive Design**: Works on desktop and tablet
- ✅ **Docker Optimized**: Multi-stage build, non-root user
- ✅ **Chat History**: Keep track of conversations

## Project Structure

```
frontend/
├── app.py                  # Main Streamlit application
├── config.py              # Configuration management
├── logger.py              # Logging setup
├── api_client.py          # Backend API client with retry logic
├── components.py          # Reusable UI components
├── requirements.txt       # Python dependencies
├── Dockerfile             # Production Docker image
├── .env.example           # Environment variables template
├── .dockerignore          # Docker build optimization
├── .streamlit/
│   └── config.toml        # Streamlit configuration
├── logs/                  # Application logs
└── README_FRONTEND.md     # This file
```

## Setup & Installation

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Backend running (see backend README)

### Local Development

1. **Create environment file**:
```bash
cp .env.example .env
```

2. **Update configuration** (edit `.env`):
```bash
API_URL=http://localhost:8000
API_TIMEOUT=120
MAX_UPLOAD_SIZE_MB=50
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Run the application**:
```bash
streamlit run app.py
```

Visit: http://localhost:8501

### Docker Deployment

```bash
# Build image
docker build -t enterprise-ka-frontend:latest .

# Run container
docker run -p 8501:8501 \
           -e API_URL=http://backend:8000 \
           enterprise-ka-frontend:latest

# Or use Docker Compose
docker-compose up frontend
```

## Usage

### 1. Upload a PDF

- Click the upload button in the sidebar
- Select a PDF file (max size: 50MB by default)
- The file will be processed and indexed

### 2. Ask Questions

- Enter a question in the main area
- Click "Ask" to get an answer
- The system will search through the document and provide an answer with sources

### 3. View History

- Chat history is automatically saved in the session
- Expand previous questions to review answers
- History persists during the session

## Configuration

All settings can be configured via `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_URL` | http://localhost:8000 | Backend API endpoint |
| `API_TIMEOUT` | 120 | Request timeout in seconds |
| `MAX_RETRIES` | 3 | Number of retry attempts |
| `RETRY_DELAY` | 1 | Delay between retries (seconds) |
| `MAX_UPLOAD_SIZE_MB` | 50 | Maximum file upload size |
| `SHOW_ADVANCED_OPTIONS` | False | Show advanced UI options |
| `ENABLE_CHAT_HISTORY` | True | Enable chat history tracking |
| `ENABLE_FEEDBACK` | False | Enable user feedback |
| `LOG_LEVEL` | INFO | Logging level |

## Architecture

```
┌─────────────────────────────────────────┐
│  Web Browser                            │
│  (Streamlit Frontend - Port 8501)       │
└─────────────────────────────────────────┘
            ↓ HTTP/REST
┌─────────────────────────────────────────┐
│  FastAPI Backend (Port 8000)            │
│  - File Upload Processing               │
│  - Query Answering                      │
└─────────────────────────────────────────┘
    ↓                    ↓                  ↓
┌──────────┐    ┌──────────────┐    ┌─────────────┐
│  FAISS   │    │   Ollama     │    │  Logging    │
│ Vector   │    │  (LLM)       │    │  System     │
│Database  │    │              │    │             │
└──────────┘    └──────────────┘    └─────────────┘
```

## Key Components

### `app.py`
Main application file that:
- Sets up the Streamlit page
- Manages session state
- Handles file uploads
- Processes queries
- Displays results

### `api_client.py`
Backend communication with:
- Automatic retries on failure
- Connection error handling
- Timeout management
- Request validation

### `config.py`
Configuration management:
- Environment variable parsing
- Settings validation
- Centralized config access

### `components.py`
Reusable UI components:
- Upload section
- Query section
- Response display
- Error/success messages
- Chat history

### `logger.py`
Logging configuration:
- Console logging
- File logging with timestamps
- Structured error tracking

## Logging

Logs are written to:
- **Console**: Real-time output
- **logs/**: Dated log files (streamlit_YYYYMMDD.log)

View logs:
```bash
# Live logs
tail -f logs/streamlit_*.log

# Last 50 lines
tail -50 logs/streamlit_*.log
```

## Error Handling

The frontend gracefully handles:
- ✅ Backend unavailable
- ✅ Network timeouts
- ✅ Invalid file uploads
- ✅ Query failures
- ✅ API errors
- ✅ Unexpected exceptions

Error messages provide:
- Clear description of the problem
- Troubleshooting steps
- Links to relevant documentation

## Performance

- **Page load**: < 2 seconds
- **File upload**: Depends on backend
- **Query response**: Depends on backend
- **Memory usage**: ~ 200-500 MB
- **Concurrent users**: 10+ recommended

### Performance Tips

1. **Faster uploads**: Use smaller PDFs (< 20MB)
2. **Better responses**: Ask specific questions
3. **Smoother UI**: Clear browser cache
4. **Scalability**: Run multiple instances behind load balancer

## Production Deployment

### Docker Compose (Small Scale)

```bash
docker-compose up -d
```

### Kubernetes (Large Scale)

```bash
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml
```

### Nginx Reverse Proxy

```nginx
upstream streamlit {
    server localhost:8501;
}

server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://streamlit;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

### Issue: "Cannot connect to API"
**Solution**: 
1. Check backend is running: `docker-compose ps`
2. Verify API_URL in `.env`
3. Check firewall settings
4. View backend logs: `docker-compose logs backend`

### Issue: File upload fails
**Solution**:
1. Check file size < MAX_UPLOAD_SIZE_MB
2. Ensure PDF is valid
3. Check backend logs for errors
4. Try with smaller PDF

### Issue: Query times out
**Solution**:
1. Increase API_TIMEOUT in `.env`
2. Check backend is responsive
3. Try with simpler query
4. Check backend resource usage

### Issue: Slow performance
**Solution**:
1. Clear browser cache
2. Restart frontend: `docker-compose restart frontend`
3. Check backend logs for issues
4. Monitor resource usage

### Issue: Out of memory
**Solution**:
1. Restart containers
2. Reduce MAX_UPLOAD_SIZE_MB
3. Clear old logs
4. Monitor with: `docker stats`

## Security Considerations

✅ **Input Validation**: File type and size checked
✅ **Error Handling**: No sensitive info in errors
✅ **Configuration**: Secrets in environment variables
✅ **Non-root Docker**: Runs as appuser
✅ **Health Checks**: Backend connectivity verified
✅ **Timeouts**: Prevent hanging requests

## API Contract

### Backend Expected

The frontend expects the backend API to provide:

**GET /health**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {...}
}
```

**POST /upload**
```json
{
  "message": "PDF uploaded successfully",
  "filename": "document.pdf",
  "chunks_created": 42,
  "total_chunks": 42
}
```

**POST /chat**
```json
{
  "response": "Answer text",
  "sources": ["document.pdf - Page 1"],
  "tokens_used": null
}
```

## Testing

### Manual Testing

1. **Health check**:
   ```bash
   curl http://localhost:8501
   ```

2. **Upload PDF**:
   - Use UI upload button
   - Check for success message

3. **Query**:
   - Enter a question
   - Verify response appears

### Automated Testing

```bash
# Run tests (when available)
pytest tests/ -v
```

## Development

### Install Dev Dependencies

```bash
pip install -r requirements.txt
pip install pytest streamlit-testing-client
```

### Code Structure

- **config.py**: Configuration management
- **logger.py**: Logging setup
- **api_client.py**: API communication
- **components.py**: UI components
- **app.py**: Main application

### Adding New Features

1. Create component in `components.py`
2. Import in `app.py`
3. Add configuration to `config.py`
4. Test locally
5. Update documentation

## Monitoring

### Health Status

```bash
# Check if frontend is running
curl http://localhost:8501

# Check API connectivity (in app logs)
tail -f logs/streamlit_*.log | grep "API\|health"
```

### Resource Usage

```bash
# Docker stats
docker stats frontend

# Process monitoring
ps aux | grep streamlit
```

## Advanced Configuration

### Custom Styling

Edit `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
```

### Session Management

Modify session initialization in `app.py`:
```python
def initialize_session():
    # Add custom state variables
    st.session_state.custom_var = "value"
```

### API Client Configuration

Adjust retry logic in `api_client.py`:
```python
retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504]
)
```

## Support

- **Setup Issues**: See Quick Start
- **API Issues**: Check Backend README
- **UI Issues**: Check browser console for errors
- **Performance**: Check logs and monitor resources

## License

All rights reserved.

## Version Info

- **Frontend Version**: 1.0.0
- **Python**: 3.11
- **Streamlit**: 1.28.1
- **Last Updated**: January 2024
