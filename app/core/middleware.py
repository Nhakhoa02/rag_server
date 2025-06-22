from fastapi import Request
import structlog
import time
from typing import Callable
import uuid

logger = structlog.get_logger()

class RequestLoggingMiddleware:
    """Middleware for logging HTTP requests"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Log request start
        logger.info("Request started",
                   request_id=request_id,
                   method=scope["method"],
                   path=scope["path"],
                   client=scope.get("client", ("unknown", 0))[0])
        
        # Create custom send function to capture response
        async def custom_send(message):
            if message["type"] == "http.response.start":
                # Log response
                duration = time.time() - start_time
                logger.info("Request completed",
                           request_id=request_id,
                           status_code=message["status"],
                           duration=duration)
            
            await send(message)
        
        await self.app(scope, receive, custom_send) 