# Frontend Quick Start

Get the upgraded Streamlit frontend running in minutes!

## 1. Install Dependencies

```bash
cd frontend
pip install -r requirements.txt
```

## 2. Configure Environment

```bash
# Copy the example
cp .env.example .env

# Edit with your settings (optional)
nano .env  # or use your editor
```

**Key settings**:
- `API_URL`: Where the backend is running (default: http://localhost:8000)
- `API_TIMEOUT`: Request timeout in seconds (default: 120)
- `MAX_UPLOAD_SIZE_MB`: Max file size (default: 50)

## 3. Ensure Backend is Running

```bash
# In another terminal
cd backend
docker-compose up backend
# OR
uvicorn app.main:app --reload
```

## 4. Run the Frontend

### Development Mode
```bash
streamlit run app.py
```

Visit: http://localhost:8501

### Production Mode (Docker)
```bash
docker build -t enterprise-ka-frontend:v1.0.0 .
docker run -p 8501:8501 \
  --env-file .env \
  enterprise-ka-frontend:v1.0.0
```

## 5. Quick Test

1. **Check API Connection**
   - Look at the sidebar for API status
   - If red ❌: Backend is not running
   - If green ✅: Everything is connected

2. **Upload a PDF**
   - Click upload button in sidebar
   - Select a PDF file
   - Click "📤 Upload"
   - Wait for success message

3. **Ask a Question**
   - Type a question about the document
   - Click "🔍 Ask"
   - View the answer

## 6. Docker Compose (Full Stack)

```bash
# Start everything (frontend + backend + Ollama)
cd ..
docker-compose up -d

# View logs
docker-compose logs -f frontend

# Check status
docker-compose ps

# Stop
docker-compose down
```

## 7. View Logs

```bash
# Live logs
tail -f logs/streamlit_*.log

# Today's logs
ls -la logs/

# Search for errors
grep ERROR logs/streamlit_*.log
```

## 8. Common Issues

### "Cannot connect to API"
```bash
# Check backend is running
docker-compose ps

# Start backend
docker-compose up backend
```

### "API_URL not configured"
```bash
# Create .env file
cp .env.example .env
```

### "Connection refused"
```bash
# Update API_URL in .env
# For Docker: API_URL=http://backend:8000
# For local: API_URL=http://localhost:8000
```

### "File upload fails"
```bash
# Check file is PDF
# Check file size < 50MB (or configured limit)
# Check backend logs
docker-compose logs backend
```

## 9. Configuration Options

Quick reference for `.env`:

```bash
# API Connection
API_URL=http://localhost:8000
API_TIMEOUT=120
MAX_RETRIES=3

# Features
ENABLE_CHAT_HISTORY=True
SHOW_ADVANCED_OPTIONS=False

# Upload
MAX_UPLOAD_SIZE_MB=50
```

## 10. Features to Try

### 💬 Chat History
- Previous questions are saved
- Click to expand and review
- History persists during session

### 🔄 Health Check
- Click "Check Connection" in sidebar
- Shows API status
- Troubleshooting tips if disconnected

### 📚 Source Citations
- Every answer shows source documents
- See which pages the answer came from
- Up to 5 sources displayed

### ⚡ Performance
- Fast uploads (unless backend is slow)
- Quick response times
- Works on desktop and tablet

## 11. Next Steps

1. **Read**: `README_FRONTEND.md` for detailed documentation
2. **Deploy**: Use Docker Compose for multi-container deployment
3. **Monitor**: Check logs for any issues
4. **Customize**: Modify `.streamlit/config.toml` for branding

## 12. API Testing

### Using the UI
```
1. Open http://localhost:8501
2. Upload PDF
3. Ask question
4. View answer
```

### Using cURL
```bash
# Check frontend health (Streamlit)
curl http://localhost:8501

# Check backend health
curl http://localhost:8000/health
```

### Using Python
```python
import requests

# Check connection
response = requests.get("http://localhost:8000/health")
print(response.json())
```

## 13. Environment Variables

All options configurable via `.env`:

```bash
# Backend API
API_URL=http://localhost:8000              # API endpoint
API_TIMEOUT=120                            # Timeout in seconds
MAX_RETRIES=3                              # Retry attempts
RETRY_DELAY=1                              # Delay between retries

# File Upload
MAX_UPLOAD_SIZE_MB=50                      # Max file size

# UI/UX
SHOW_ADVANCED_OPTIONS=False                # Show advanced UI
ENABLE_CHAT_HISTORY=True                   # Keep history
ENABLE_FEEDBACK=False                      # User feedback

# Logging
LOG_LEVEL=INFO                             # DEBUG, INFO, WARNING, ERROR
```

## 14. Production Checklist

Before deploying to production:

- [ ] `.env` configured with correct API_URL
- [ ] Backend deployed and running
- [ ] Docker image built and tested
- [ ] Port 8501 is accessible
- [ ] CORS configured on backend
- [ ] SSL certificates ready (optional)
- [ ] Load balancer configured (if scaling)
- [ ] Monitoring setup
- [ ] Logs being collected
- [ ] Rollback plan ready

## 15. Monitoring

```bash
# Check if running
docker-compose ps | grep frontend

# View logs
docker-compose logs frontend

# Check connectivity
curl -s http://localhost:8501 | head -20

# Monitor resources
docker stats frontend

# Check API health
curl http://localhost:8000/health | jq
```

## 16. Troubleshooting Commands

```bash
# Restart frontend
docker-compose restart frontend

# Full restart
docker-compose down
docker-compose up frontend

# Clear cache and restart
docker system prune -a
docker-compose up --build frontend

# Check logs for errors
grep -i error logs/streamlit_*.log

# Find the latest log file
ls -t logs/ | head -1
```

## 17. Performance Tips

1. **Fast uploads**: Keep PDFs under 20MB
2. **Quick responses**: Ask specific questions
3. **Smooth UI**: Clear browser cache
4. **Better performance**: Close other tabs
5. **Scalability**: Run multiple instances

## 18. Getting Help

**Issue:** Frontend won't start
**Solution:** Check Python version (3.11+), run `pip install -r requirements.txt`

**Issue:** Can't connect to backend
**Solution:** Check API_URL in `.env`, ensure backend is running

**Issue:** File upload slow
**Solution:** Try smaller PDF, check network speed

**Issue:** Response takes too long
**Solution:** Increase API_TIMEOUT, check backend logs

## 19. Useful Commands

```bash
# Install dependencies fresh
pip install --upgrade pip
pip install -r requirements.txt

# Run with specific log level
export LOG_LEVEL=DEBUG
streamlit run app.py

# Run on different port
streamlit run app.py -- --server.port 8502

# Check version
streamlit --version
```

## 20. Next: Production Deployment

Ready to deploy to production?

→ See root `docker-compose.yml` for full stack
→ See backend `DEPLOYMENT_GUIDE.md` for infrastructure setup
→ See `README_FRONTEND.md` for detailed documentation

---

**All set!** Your frontend is ready. Open http://localhost:8501 and start using it!
