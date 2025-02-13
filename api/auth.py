"""
Authentication and authorization for API.
"""
from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

from config.schemas import SystemConfig

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthHandler:
    """Handle authentication and authorization."""
    
    def __init__(self, config: SystemConfig):
        """Initialize auth handler."""
        self.secret = config.api.jwt_secret
        self.algorithm = "HS256"
        self.access_token_expire = 30  # minutes
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, username: str) -> str:
        """Create a new access token."""
        expires_delta = timedelta(minutes=self.access_token_expire)
        expires_at = datetime.utcnow() + expires_delta
        
        to_encode = {
            "sub": username,
            "exp": expires_at
        }
        
        return jwt.encode(to_encode, self.secret, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Optional[str]:
        """Decode and validate a token."""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload["sub"]
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
    
    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> str:
        """Get current authenticated user."""
        try:
            token = credentials.credentials
            username = self.decode_token(token)
            return username
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=str(e)
            )

class RoleChecker:
    """Check user roles and permissions."""
    
    def __init__(self, required_roles: list[str]):
        """Initialize role checker."""
        self.required_roles = required_roles
    
    def __call__(self, user: str = Depends(AuthHandler.get_current_user)):
        """Check if user has required roles."""
        # TODO: Implement role checking against user database
        return True
