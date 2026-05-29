"""Gunicorn configuration for production deployment."""

import os
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = max(2, multiprocessing.cpu_count())
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120
graceful_timeout = 30

# Logging
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "enterprise-ka-backend"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (use Nginx/reverse proxy instead in production)
# keyfile = None
# certfile = None
# ca_certs = None
# ciphers = None

# Settings
preload_app = True
forwarded_allow_ips = "*"
secure_scheme_headers = {
    "X-FORWARDED_PROTOCOL": "ssl",
    "X-FORWARDED_PROTO": "https",
    "X-FORWARDED_SSL": "on",
}

# Application
on_starting = None
on_exit = None
when_ready = None
pre_fork = None
post_fork = None
pre_exec = None
post_worker_exit = None
worker_abort = None
