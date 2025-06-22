from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request
import time

# Metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'http_active_requests',
    'Number of active HTTP requests',
    ['method', 'endpoint']
)

DOCUMENT_UPLOAD_COUNT = Counter(
    'document_uploads_total',
    'Total document uploads',
    ['file_type', 'status']
)

QUERY_COUNT = Counter(
    'queries_total',
    'Total queries processed',
    ['status']
)

def setup_monitoring():
    """Setup monitoring metrics"""
    pass

def record_request_metrics(request: Request, status_code: int, duration: float):
    """Record request metrics"""
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

def record_document_upload(file_type: str, status: str):
    """Record document upload metrics"""
    DOCUMENT_UPLOAD_COUNT.labels(
        file_type=file_type,
        status=status
    ).inc()

def record_query(status: str):
    """Record query metrics"""
    QUERY_COUNT.labels(status=status).inc()

def get_metrics():
    """Get Prometheus metrics"""
    return generate_latest() 