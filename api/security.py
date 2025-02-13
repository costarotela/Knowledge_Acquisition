"""
Security middleware and utilities for API.
"""
from typing import Optional, Dict, List
import time
from datetime import datetime
from fastapi import Request, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import jwt
from redis import Redis
import structlog

logger = structlog.get_logger()

class RateLimiter:
    """Rate limiting implementation."""
    
    def __init__(
        self,
        redis_client: Redis,
        rate_limit: int = 100,  # requests per window
        window: int = 60  # seconds
    ):
        """Initialize rate limiter."""
        self.redis = redis_client
        self.rate_limit = rate_limit
        self.window = window
    
    async def is_rate_limited(self, key: str) -> bool:
        """Check if request should be rate limited."""
        current = int(time.time())
        window_key = f"rate_limit:{key}:{current // self.window}"
        
        try:
            count = self.redis.incr(window_key)
            if count == 1:
                self.redis.expire(window_key, self.window)
            
            return count > self.rate_limit
            
        except Exception as e:
            logger.error("Rate limit error", error=str(e))
            return False

class APIKeyManager:
    """API key management."""
    
    def __init__(self, redis_client: Redis):
        """Initialize API key manager."""
        self.redis = redis_client
    
    async def validate_key(self, api_key: str) -> Optional[Dict]:
        """Validate API key and return associated data."""
        try:
            key_data = self.redis.hgetall(f"api_key:{api_key}")
            if not key_data:
                return None
            
            return {
                "client_id": key_data.get(b"client_id").decode(),
                "roles": key_data.get(b"roles").decode().split(","),
                "rate_limit": int(key_data.get(b"rate_limit", b"100"))
            }
            
        except Exception as e:
            logger.error("API key validation error", error=str(e))
            return None
    
    async def create_key(
        self,
        client_id: str,
        roles: List[str],
        rate_limit: int = 100
    ) -> str:
        """Create new API key."""
        try:
            api_key = jwt.encode(
                {
                    "client_id": client_id,
                    "created_at": datetime.utcnow().isoformat()
                },
                "secret",  # TODO: Use proper secret
                algorithm="HS256"
            )
            
            self.redis.hmset(
                f"api_key:{api_key}",
                {
                    "client_id": client_id,
                    "roles": ",".join(roles),
                    "rate_limit": rate_limit
                }
            )
            
            return api_key
            
        except Exception as e:
            logger.error("API key creation error", error=str(e))
            raise

class AuditLogger:
    """Audit logging for API requests."""
    
    def __init__(self):
        """Initialize audit logger."""
        self.logger = structlog.get_logger("audit")
    
    async def log_request(
        self,
        request: Request,
        client_id: str,
        success: bool,
        error: Optional[str] = None
    ):
        """Log API request."""
        self.logger.info(
            "API request",
            client_id=client_id,
            method=request.method,
            url=str(request.url),
            success=success,
            error=error,
            ip=request.client.host,
            user_agent=request.headers.get("user-agent")
        )

class SecurityConfig(BaseModel):
    """Security configuration."""
    rate_limit: int = 100
    rate_limit_window: int = 60
    audit_logging: bool = True

class SecurityManager:
    """Central security management."""
    
    def __init__(
        self,
        redis_client: Redis,
        config: SecurityConfig
    ):
        """Initialize security manager."""
        self.redis = redis_client
        self.config = config
        
        # Initialize components
        self.rate_limiter = RateLimiter(
            redis_client,
            config.rate_limit,
            config.rate_limit_window
        )
        self.api_key_manager = APIKeyManager(redis_client)
        self.audit_logger = AuditLogger()
        
        # API key header
        self.api_key_header = APIKeyHeader(name="X-API-Key")
    
    async def validate_request(
        self,
        request: Request,
        api_key: str = None
    ) -> Dict:
        """Validate API request."""
        try:
            # Validate API key
            if not api_key:
                api_key = await self.api_key_header(request)
            
            key_data = await self.api_key_manager.validate_key(api_key)
            if not key_data:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid API key"
                )
            
            # Check rate limit
            if await self.rate_limiter.is_rate_limited(key_data["client_id"]):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded"
                )
            
            # Log request
            if self.config.audit_logging:
                await self.audit_logger.log_request(
                    request=request,
                    client_id=key_data["client_id"],
                    success=True
                )
            
            return key_data
            
        except HTTPException:
            # Log failed request
            if self.config.audit_logging:
                await self.audit_logger.log_request(
                    request=request,
                    client_id="unknown",
                    success=False,
                    error="Invalid API key or rate limit exceeded"
                )
            raise
        
        except Exception as e:
            # Log error
            if self.config.audit_logging:
                await self.audit_logger.log_request(
                    request=request,
                    client_id="unknown",
                    success=False,
                    error=str(e)
                )
            
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )
