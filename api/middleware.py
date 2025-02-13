"""
Middleware for API request processing.
"""
from typing import Callable
from fastapi import Request, Response
import time
import structlog
from prometheus_client import Counter, Histogram

from .security import SecurityManager

logger = structlog.get_logger()

# Metrics
REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total count of API requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"]
)

class MetricsMiddleware:
    """Collect metrics about API requests."""
    
    def __init__(self, app):
        """Initialize middleware."""
        self.app = app
    
    async def __call__(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request and collect metrics."""
        method = request.method
        path = request.url.path
        
        # Track request latency
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Record metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status=response.status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=path
            ).observe(time.time() - start_time)
            
            return response
            
        except Exception as e:
            # Record error metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status=500
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=path
            ).observe(time.time() - start_time)
            
            raise

class LoggingMiddleware:
    """Log API requests and responses."""
    
    def __init__(self, app):
        """Initialize middleware."""
        self.app = app
    
    async def __call__(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process and log request."""
        # Log request
        logger.info(
            "API request",
            method=request.method,
            url=str(request.url),
            client_host=request.client.host
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Log response
            logger.info(
                "API response",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code
            )
            
            return response
            
        except Exception as e:
            # Log error
            logger.error(
                "API error",
                method=request.method,
                url=str(request.url),
                error=str(e)
            )
            raise

class SecurityMiddleware:
    """Apply security checks to requests."""
    
    def __init__(self, app, security_manager: SecurityManager):
        """Initialize middleware."""
        self.app = app
        self.security_manager = security_manager
    
    async def __call__(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request with security checks."""
        # Skip security for certain endpoints
        if self._should_skip_security(request):
            return await call_next(request)
        
        try:
            # Validate request
            key_data = await self.security_manager.validate_request(request)
            
            # Add client info to request state
            request.state.client_id = key_data["client_id"]
            request.state.roles = key_data["roles"]
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(
                "Security check failed",
                method=request.method,
                url=str(request.url),
                error=str(e)
            )
            raise
    
    def _should_skip_security(self, request: Request) -> bool:
        """Check if security should be skipped."""
        # Skip for health check and metrics
        skip_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        return request.url.path in skip_paths

class CompressionMiddleware:
    """Compress API responses."""
    
    def __init__(self, app):
        """Initialize middleware."""
        self.app = app
    
    async def __call__(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request with compression."""
        response = await call_next(request)
        
        # Check if response should be compressed
        if self._should_compress(request, response):
            # TODO: Implement compression
            pass
        
        return response
    
    def _should_compress(
        self,
        request: Request,
        response: Response
    ) -> bool:
        """Check if response should be compressed."""
        # Check content type
        content_type = response.headers.get("content-type", "")
        compressible_types = [
            "application/json",
            "text/plain",
            "text/html"
        ]
        
        return any(
            t in content_type.lower()
            for t in compressible_types
        )

class CacheMiddleware:
    """Cache API responses."""
    
    def __init__(self, app):
        """Initialize middleware."""
        self.app = app
    
    async def __call__(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request with caching."""
        # Check if response is cached
        cache_key = self._get_cache_key(request)
        
        # TODO: Implement caching
        
        return await call_next(request)
    
    def _get_cache_key(self, request: Request) -> str:
        """Generate cache key for request."""
        return f"{request.method}:{request.url}"

def setup_middleware(app, security_manager: SecurityManager):
    """Setup all middleware."""
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        SecurityMiddleware,
        security_manager=security_manager
    )
    app.add_middleware(CompressionMiddleware)
    app.add_middleware(CacheMiddleware)
