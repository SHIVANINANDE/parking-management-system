"""
Authentication dependencies for FastAPI endpoints
"""
from typing import Optional, Generator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_async_session
from app.models.user import User, UserStatus
from app.core.security import verify_token
import redis
from app.core.config import settings

# Security scheme
security = HTTPBearer()

# Redis client for token blacklist
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class TokenBlacklist:
    """Manage token blacklist using Redis"""
    
    @staticmethod
    async def add_token(token: str, expires_in: int = None):
        """Add token to blacklist"""
        if expires_in is None:
            expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        redis_client.setex(f"blacklist:{token}", expires_in, "1")
    
    @staticmethod
    async def is_blacklisted(token: str) -> bool:
        """Check if token is blacklisted"""
        return redis_client.exists(f"blacklist:{token}")

async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Extract and validate token from request"""
    token = credentials.credentials
    
    # Check if token is blacklisted
    if await TokenBlacklist.is_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    user_id = verify_token(token, "access")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token

async def get_current_user(
    token: str = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_async_session)
) -> User:
    """Get current user from token"""
    user_id = verify_token(token, "access")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified"
        )
    
    return current_user

async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_async_session)
) -> Optional[User]:
    """Get current user if token is provided, otherwise return None"""
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        
        user_id = verify_token(token, "access")
        if user_id is None:
            return None
        
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        
        if user and user.status == UserStatus.ACTIVE and user.is_email_verified:
            return user
    except (ValueError, AttributeError):
        pass
    
    return None

def require_roles(*allowed_roles: str):
    """Decorator to require specific roles"""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role.value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker

def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role"""
    return require_roles("admin")(current_user)

def require_manager_or_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require manager or admin role"""
    return require_roles("admin", "manager")(current_user)

def require_operator_or_above(current_user: User = Depends(get_current_active_user)) -> User:
    """Require operator, manager, or admin role"""
    return require_roles("admin", "manager", "operator")(current_user)

async def verify_refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Verify refresh token"""
    token = credentials.credentials
    
    # Check if token is blacklisted
    if await TokenBlacklist.is_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = verify_token(token, "refresh")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id

class RateLimitDependency:
    """Rate limiting dependency"""
    
    def __init__(self, calls: int = 10, period: int = 60):
        self.calls = calls
        self.period = period
    
    async def __call__(self, request: Request):
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"
        
        current = redis_client.get(key)
        if current is None:
            redis_client.setex(key, self.period, 1)
        else:
            current = int(current)
            if current >= self.calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
            redis_client.incr(key)

# Rate limiting instances
rate_limit_standard = RateLimitDependency(calls=60, period=60)  # 60 calls per minute
rate_limit_strict = RateLimitDependency(calls=10, period=60)    # 10 calls per minute
rate_limit_auth = RateLimitDependency(calls=5, period=300)      # 5 calls per 5 minutes
