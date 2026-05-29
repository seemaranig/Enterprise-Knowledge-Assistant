# Production Deployment Guide

## Overview

This guide covers production-level deployment of the Enterprise Knowledge Assistant backend on various platforms.

## Pre-Deployment Checklist

- [ ] All environment variables configured in `.env`
- [ ] Ollama service running and accessible
- [ ] Docker image built and tested
- [ ] SSL/TLS certificates obtained
- [ ] Database backups configured
- [ ] Monitoring and alerting setup
- [ ] Logging aggregation configured
- [ ] Rate limiting adjusted for your needs

## Deployment Architectures

### 1. Docker Compose (Small Scale)

**Best for**: Small teams, staging environments, POC

```bash
cd /path/to/project

# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### 2. Kubernetes (Large Scale)

**Best for**: High availability, auto-scaling, enterprise deployments

**Prerequisites**:
- Kubernetes cluster (EKS, GKE, AKS, or self-managed)
- kubectl configured
- Docker image pushed to registry

**Deployment steps**:

```bash
# Create namespace
kubectl create namespace enterprise-ka

# Create secret for environment variables
kubectl create secret generic backend-env \
  --from-env-file=.env \
  -n enterprise-ka

# Deploy
kubectl apply -f k8s/backend-deployment.yaml -n enterprise-ka
kubectl apply -f k8s/backend-service.yaml -n enterprise-ka

# Monitor
kubectl get pods -n enterprise-ka
kubectl logs -f deployment/backend -n enterprise-ka
```

**k8s/backend-deployment.yaml** example:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: enterprise-ka-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: your-registry/enterprise-ka-backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: backend-env
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        volumeMounts:
        - name: data
          mountPath: /app/data
        - name: vectorstore
          mountPath: /app/vectorstore
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: backend-data-pvc
      - name: vectorstore
        persistentVolumeClaim:
          claimName: backend-vectorstore-pvc
```

### 3. VM Deployment (AWS EC2, DigitalOcean, etc.)

**Best for**: Medium scale, cost-effective, traditional infrastructure

**Setup**:

```bash
# 1. SSH into instance
ssh -i key.pem ubuntu@your-server.com

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# 3. Create app directory
mkdir -p /opt/enterprise-ka
cd /opt/enterprise-ka

# 4. Clone/copy code
git clone <repo> .
# OR
scp -r backend ubuntu@your-server.com:/opt/enterprise-ka/

# 5. Build and run
docker build -t enterprise-ka-backend:latest backend/
docker run -d \
  --name backend \
  -p 80:8000 \
  --env-file backend/.env \
  -v /opt/enterprise-ka/data:/app/data \
  -v /opt/enterprise-ka/vectorstore:/app/vectorstore \
  enterprise-ka-backend:latest

# 6. Setup Nginx reverse proxy
sudo apt install nginx
sudo systemctl start nginx
```

**Nginx config**:
```nginx
upstream backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 4. Heroku Deployment

**Best for**: Quick deployments, low maintenance

```bash
# Create Procfile
echo "web: gunicorn -c gunicorn_config.py app.main:app" > Procfile

# Create runtime.txt
echo "python-3.11.0" > runtime.txt

# Deploy
heroku login
heroku create your-app-name
heroku config:set DEBUG=False
heroku config:set OLLAMA_BASE_URL=<external-ollama-url>
git push heroku main

# View logs
heroku logs -t
```

## Security Configuration

### 1. Environment Variables

Create `.env.production`:
```bash
DEBUG=False
LOG_LEVEL=WARNING
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=1000
MAX_UPLOAD_SIZE_MB=100
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
```

### 2. SSL/TLS Certificates

**Using Let's Encrypt**:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d yourdomain.com
```

**Nginx SSL config**:
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # ... rest of config
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### 3. Rate Limiting

Adjust in `.env`:
```bash
RATE_LIMIT_REQUESTS=1000      # Per period
RATE_LIMIT_PERIOD_SECONDS=60  # Time window
```

For high-traffic deployments, use Redis:
- Update `main.py` to use Redis backend instead of in-memory store
- Deploy Redis instance separately

### 4. API Key Authentication (Optional)

Add to `main.py`:
```python
from fastapi import Header, HTTPException

@app.post("/chat")
async def chat(request: ChatRequest, authorization: str = Header(None)):
    if not authorization or not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    # ... rest of logic
```

## Monitoring & Observability

### 1. Prometheus Metrics

Add to `requirements.txt`:
```
prometheus-client==0.19.0
```

Add to `main.py`:
```python
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client import REGISTRY

chat_requests = Counter('chat_requests_total', 'Total chat requests')
upload_requests = Counter('upload_requests_total', 'Total upload requests')
chat_latency = Histogram('chat_latency_seconds', 'Chat request latency')

@app.get("/metrics")
async def metrics():
    return generate_latest(REGISTRY)
```

### 2. Logging Aggregation

**ELK Stack** (Elasticsearch, Logstash, Kibana):

Install Filebeat on VM:
```bash
curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.0.0-linux-x86_64.tar.gz
tar xzf filebeat-*.tar.gz
cd filebeat-*
./filebeat -e
```

**CloudWatch** (AWS):
```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
```

### 3. Error Tracking

Use **Sentry**:
```bash
pip install sentry-sdk
```

Add to `main.py`:
```python
import sentry_sdk
sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=0.1,
    environment="production"
)
```

## Scaling Considerations

### 1. Horizontal Scaling

- Deploy multiple backend instances
- Use load balancer (Nginx, HAProxy, AWS ALB)
- Use Redis for shared rate limiting
- Share FAISS vector database via network storage

### 2. Vector Database Scaling

For large deployments:
```bash
# PostgreSQL + pgvector
pip install pgvector psycopg[binary]

# Or use cloud services
# - Pinecone
# - Weaviate
# - Milvus
```

### 3. LLM Scaling

- Deploy multiple Ollama instances
- Use load balancer
- Consider managed LLM APIs (OpenAI, Anthropic)

## Performance Tuning

### 1. Worker Configuration

Adjust in `gunicorn_config.py`:
```python
# CPU-bound: 2-4 * CPU cores
# I/O-bound: 8-32 * CPU cores
workers = multiprocessing.cpu_count() * 4
```

### 2. Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_embeddings_cached(model_name):
    return HuggingFaceEmbeddings(model_name=model_name)
```

### 3. Database Optimization

- Index FAISS vectors appropriately
- Regular maintenance/cleanup of old vectors
- Consider vector quantization for large datasets

## Disaster Recovery

### 1. Backup Strategy

```bash
# Backup vectorstore
rsync -av vectorstore/ backup-server:/backups/vectorstore/

# Backup data
rsync -av data/ backup-server:/backups/data/

# Backup configuration
rsync -av .env backup-server:/backups/
```

### 2. Restore Procedure

```bash
# Restore from backup
rsync -av backup-server:/backups/vectorstore/ vectorstore/
rsync -av backup-server:/backups/data/ data/

# Restart service
docker-compose restart backend
```

### 3. Health Monitoring

```bash
# Check API health
curl -f http://localhost:8000/health || alert_on_failure

# Monitor disk space
df -h / | grep -v "^Filesystem" | awk '{if ($5+0 > 90) print "Disk usage high: " $0}'

# Monitor service
systemctl status backend || alert_on_failure
```

## Troubleshooting

### Issue: High Memory Usage

**Solution**:
```bash
# Limit worker memory
gunicorn --limit-memory-hard 1000000000  # 1GB

# Or in gunicorn_config.py
limit_memory_hard = 1000000000
```

### Issue: Slow Responses

**Solution**:
1. Check FAISS vector DB size
2. Increase worker count
3. Enable caching
4. Monitor resource usage

### Issue: Connection Timeouts

**Solution**:
1. Increase timeout in load balancer
2. Increase timeout in gunicorn: `timeout = 240`
3. Check network connectivity to Ollama

## Rollback Procedure

```bash
# Docker Compose
docker-compose down
git checkout previous-version
docker-compose build
docker-compose up -d

# Kubernetes
kubectl set image deployment/backend backend=your-registry/backend:previous-tag -n enterprise-ka

# Verify
kubectl rollout status deployment/backend -n enterprise-ka
```

## Maintenance Tasks

### Daily
- Monitor logs for errors
- Check disk space
- Verify health check passes

### Weekly
- Review performance metrics
- Update logs archive
- Check for security updates

### Monthly
- Performance audit
- Vector database optimization
- Dependency updates
- Disaster recovery drill

## Support & Alerts

Set up alerts for:
- Service down (HTTP 502/503)
- High error rate (> 5% 5xx errors)
- Slow response times (p99 > 5s)
- High memory usage (> 80%)
- Disk usage (> 85%)

## Additional Resources

- [FastAPI Deployment Docs](https://fastapi.tiangolo.com/deployment/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
