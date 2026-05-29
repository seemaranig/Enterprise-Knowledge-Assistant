# Frontend Documentation Index

Welcome to the production-grade Streamlit frontend! This guide will help you navigate the documentation.

## Start Here 👈

### 🚀 First Time Setup?
👉 Read: [QUICK_START.md](./QUICK_START.md)
- Get running in 5 minutes
- Basic commands
- Common issues
- Configuration options

### 📚 Want Full Details?
👉 Read: [README_FRONTEND.md](./README_FRONTEND.md)
- Project structure
- Features overview
- Configuration reference
- Troubleshooting guide
- Security details

### 🎨 Want to Customize?
👉 Check: [.streamlit/config.toml](./.streamlit/config.toml)
- Theme colors
- Server settings
- Logger configuration

### ⚙️ Want to Extend?
👉 Read source code:
- `app.py` - Main application
- `api_client.py` - Backend communication
- `components.py` - UI components
- `config.py` - Configuration

## Documentation Map

```
QUICK_START.md (5 min)
    ↓
    Run frontend locally
    ↓
README_FRONTEND.md (detailed)
    ↓
    Understand architecture
    ↓
Deploy with Docker Compose
    ↓
Production deployment!
```

## File Reference

| File | Purpose | Read When |
|------|---------|-----------|
| [QUICK_START.md](./QUICK_START.md) | Get up and running fast | Setting up locally |
| [README_FRONTEND.md](./README_FRONTEND.md) | Complete documentation | Need detailed info |
| [UPGRADE_SUMMARY.md](./UPGRADE_SUMMARY.md) | What changed | Curious about improvements |
| [INDEX.md](./INDEX.md) | Navigation guide | You are here! |
| [.env.example](./.env.example) | Configuration template | Setting up config |
| [.streamlit/config.toml](./.streamlit/config.toml) | Streamlit settings | Customizing UI |

## Quick Links

### Application
- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **Backend Docs**: http://localhost:8000/docs

### Documentation
- **Quick Start**: [QUICK_START.md](./QUICK_START.md)
- **Full Docs**: [README_FRONTEND.md](./README_FRONTEND.md)
- **Upgrade Info**: [UPGRADE_SUMMARY.md](./UPGRADE_SUMMARY.md)

### Source Files
- Main App: `app.py`
- API Client: `api_client.py`
- UI Components: `components.py`
- Configuration: `config.py`
- Logging: `logger.py`

## Common Tasks

### I want to...

**...run locally**
```bash
cp .env.example .env
pip install -r requirements.txt
streamlit run app.py
```
→ See [QUICK_START.md](./QUICK_START.md#4-run-the-frontend)

**...run with Docker**
```bash
docker build -t ka-frontend:v1 .
docker run -p 8501:8501 --env-file .env ka-frontend:v1
```
→ See [QUICK_START.md](./QUICK_START.md#4-run-the-frontend)

**...run full stack**
```bash
docker-compose up -d
```
→ See root `docker-compose.yml`

**...configure API connection**
Edit `.env`:
```bash
API_URL=http://localhost:8000
API_TIMEOUT=120
```
→ See [QUICK_START.md](./QUICK_START.md#2-configure-environment)

**...troubleshoot issues**
```bash
tail -f logs/streamlit_*.log
curl http://localhost:8000/health
```
→ See [README_FRONTEND.md](./README_FRONTEND.md#troubleshooting)

**...customize appearance**
Edit `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
```
→ See [README_FRONTEND.md](./README_FRONTEND.md#advanced-configuration)

**...add new features**
→ See [README_FRONTEND.md](./README_FRONTEND.md#development)

**...deploy to production**
→ See root project docs

## Key Features

✅ **Production Ready**: Error handling, logging, configuration
✅ **Easy to Use**: Simple, intuitive interface
✅ **Reliable**: Retry logic, timeout handling
✅ **Observable**: Comprehensive logging
✅ **Flexible**: Fully configurable
✅ **Secure**: Input validation, error sanitization
✅ **Scalable**: Works locally and in containers
✅ **Well Documented**: 3 guide documents

## Architecture

```
┌─────────────────────────────────────────┐
│  Web Browser                            │
│  Streamlit Frontend (Port 8501)         │
│  ├─ User Interface                      │
│  ├─ Session State Management            │
│  └─ API Client                          │
└─────────────────────────────────────────┘
            ↓ HTTP/REST with Retry
┌─────────────────────────────────────────┐
│  FastAPI Backend (Port 8000)            │
│  ├─ PDF Upload                          │
│  ├─ Query Processing                    │
│  └─ Health Checks                       │
└─────────────────────────────────────────┘
```

## Component Overview

### Main Application (`app.py`)
- Page setup and configuration
- Session initialization
- API health checks
- File upload handling
- Query processing
- Response display

### API Client (`api_client.py`)
- Backend communication
- Automatic retries
- Connection error handling
- Timeout management
- Request validation
- Response parsing

### UI Components (`components.py`)
- Upload section
- Query input
- Response display
- Status indicators
- Error/success messages
- Chat history
- Troubleshooting tips

### Configuration (`config.py`)
- Environment variable parsing
- Settings validation
- Feature flags
- Centralized access

### Logging (`logger.py`)
- Console output
- File logging
- Daily rotation
- Timestamp formatting

## Version Info

- **Frontend Version**: 1.0.0
- **Streamlit**: 1.28.1
- **Python**: 3.11
- **Last Updated**: January 2024

## Support & Help

### Documentation
- API Docs: http://localhost:8000/docs
- Streamlit Docs: https://docs.streamlit.io
- Backend README: `../backend/README_BACKEND.md`

### Troubleshooting
- Check logs: `tail -f logs/streamlit_*.log`
- Check backend: `curl http://localhost:8000/health`
- Check config: `cat .env`

### Debug Mode
Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
streamlit run app.py
```

### Reset to Defaults
```bash
cp .env.example .env
python -c "from config import get_config; print(get_config())"
```

## Next Steps

1. **Today**: Read [QUICK_START.md](./QUICK_START.md) and get it running
2. **Tomorrow**: Read [README_FRONTEND.md](./README_FRONTEND.md) for details
3. **This Week**: Deploy using Docker Compose
4. **Later**: Customize and extend for your needs

## Useful Commands

```bash
# Setup
cp .env.example .env
pip install -r requirements.txt

# Run
streamlit run app.py
docker-compose up frontend

# Monitor
tail -f logs/streamlit_*.log
docker stats frontend

# Debug
curl http://localhost:8501
curl http://localhost:8000/health | jq

# Docker
docker build -t ka-frontend:v1 .
docker run -p 8501:8501 ka-frontend:v1
docker logs -f container_name
```

## FAQ

**Q: How do I change the API URL?**
A: Edit `.env` and set `API_URL=your_backend_url`

**Q: How do I enable chat history?**
A: It's on by default. Set `ENABLE_CHAT_HISTORY=True` in `.env`

**Q: How do I increase upload size?**
A: Edit `.env` and set `MAX_UPLOAD_SIZE_MB=100`

**Q: How do I see debug logs?**
A: Set `LOG_LEVEL=DEBUG` in `.env` or environment

**Q: Can I run multiple instances?**
A: Yes, use Docker and a load balancer

**Q: How do I customize the theme?**
A: Edit `.streamlit/config.toml`

## Production Checklist

Before deploying to production:

- [ ] Read [README_FRONTEND.md](./README_FRONTEND.md)
- [ ] Configure `.env` with production settings
- [ ] Test with actual backend
- [ ] Check logs and monitoring
- [ ] Setup reverse proxy (Nginx, etc.)
- [ ] Configure SSL/TLS certificates
- [ ] Plan for scaling
- [ ] Setup backup strategy
- [ ] Configure alerts

## Deployment Platforms

- **Local**: `streamlit run app.py`
- **Docker**: `docker build -t ka-frontend:v1 .`
- **Docker Compose**: `docker-compose up frontend`
- **Kubernetes**: Use k8s manifests (see backend docs)
- **Cloud**: AWS ECS, GCP Cloud Run, Azure Container Instances

## Getting Help

- 📖 **Read docs**: [README_FRONTEND.md](./README_FRONTEND.md)
- 🚀 **Quick start**: [QUICK_START.md](./QUICK_START.md)
- 🔍 **Check logs**: `logs/streamlit_*.log`
- ❓ **FAQ**: See above
- 💬 **Backend**: Check `../backend/` docs

---

**Ready to get started?** → [QUICK_START.md](./QUICK_START.md)

**Want full details?** → [README_FRONTEND.md](./README_FRONTEND.md)

**Curious about changes?** → [UPGRADE_SUMMARY.md](./UPGRADE_SUMMARY.md)
