"""
Security middleware for the application
"""
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import time
import redis
from app.core.config import settings
from app.core.security import SecurityHeaders
import logging

logger = logging.getLogger(__name__)

# Redis client for rate limiting
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        if settings.ENABLE_SECURITY_HEADERS:
            # Add security headers
            for header, value in SecurityHeaders.get_security_headers().items():
                response.headers[header] = value
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limiting middleware"""
    
    def __init__(self, app, calls_per_minute: int = 60, burst_limit: int = 10):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.burst_limit = burst_limit
        self.window_size = 60  # 1 minute window
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/favicon.ico"] or request.url.path.startswith("/static"):
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        if await self._is_rate_limited(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.calls_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + 60)
                }
            )
        
        # Record the request
        await self._record_request(client_ip)
        
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = await self._get_remaining_requests(client_ip)
        response.headers["X-RateLimit-Limit"] = str(self.calls_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers (from load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host
    
    async def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client is rate limited"""
        current_time = int(time.time())
        window_start = current_time - self.window_size
        
        # Clean old entries
        redis_client.zremrangebyscore(f"rate_limit:{client_ip}", 0, window_start)
        
        # Count requests in current window
        request_count = redis_client.zcard(f"rate_limit:{client_ip}")
        
        return request_count >= self.calls_per_minute
    
    async def _record_request(self, client_ip: str):
        """Record a request for rate limiting"""
        current_time = time.time()
        
        # Add request timestamp
        redis_client.zadd(f"rate_limit:{client_ip}", {str(current_time): current_time})
        
        # Set expiry for the key
        redis_client.expire(f"rate_limit:{client_ip}", self.window_size * 2)
    
    async def _get_remaining_requests(self, client_ip: str) -> int:
        """Get remaining requests for client"""
        current_time = int(time.time())
        window_start = current_time - self.window_size
        
        # Clean old entries
        redis_client.zremrangebyscore(f"rate_limit:{client_ip}", 0, window_start)
        
        # Count requests in current window
        request_count = redis_client.zcard(f"rate_limit:{client_ip}")
        
        return max(0, self.calls_per_minute - request_count)

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """IP whitelist middleware for admin endpoints"""
    
    def __init__(self, app, whitelist: list = None):
        super().__init__(app)
        self.whitelist = whitelist or []
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only apply to admin endpoints
        if not request.url.path.startswith("/api/v1/admin"):
            return await call_next(request)
        
        if not self.whitelist:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        
        if client_ip not in self.whitelist:
            logger.warning(f"Blocked admin access from non-whitelisted IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "Access denied from this IP address",
                    "error_code": "IP_NOT_WHITELISTED"
                }
            )
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests for monitoring and security"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host} "
            f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
        )
        
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {response.status_code} "
            f"in {process_time:.4f}s"
        )
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware"""
    
    def __init__(self, app, exempt_paths: list = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/docs", "/redoc", "/openapi.json", "/health",
            "/api/v1/auth/login", "/api/v1/auth/register"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip CSRF check for safe methods and exempt paths
        if (request.method in ["GET", "HEAD", "OPTIONS"] or 
            request.url.path in self.exempt_paths or
            request.url.path.startswith("/static")):
            return await call_next(request)
        
        # Check for CSRF token in headers
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "CSRF token missing",
                    "error_code": "CSRF_TOKEN_MISSING"
                }
            )
        
        # In a real implementation, you would validate the CSRF token
        # against a stored value (session, cookie, etc.)
        # For now, we'll just check if it's present
        
        return await call_next(request)

class BruteForceProtectionMiddleware(BaseHTTPMiddleware):
    """Protection against brute force attacks"""
    
    def __init__(self, app, max_attempts: int = 5, lockout_time: int = 900):
        super().__init__(app)
        self.max_attempts = max_attempts
        self.lockout_time = lockout_time  # 15 minutes
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only apply to login endpoints
        if request.url.path not in ["/api/v1/auth/login", "/api/v1/auth/password-reset"]:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        
        # Check if IP is locked out
        if await self._is_locked_out(client_ip):
            return JSONResponse(
                status_code=status.HTTP_423_LOCKED,
                content={
                    "detail": "Too many failed attempts. Please try again later.",
                    "error_code": "ACCOUNT_LOCKED"
                },
                headers={"Retry-After": str(self.lockout_time)}
            )
        
        response = await call_next(request)
        
        # If login failed, record the attempt
        if response.status_code == 401:
            await self._record_failed_attempt(client_ip)
        elif response.status_code == 200:
            # Clear failed attempts on successful login
            await self._clear_failed_attempts(client_ip)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        return request.client.host
    
    async def _is_locked_out(self, client_ip: str) -> bool:
        """Check if IP is locked out"""
        attempts = redis_client.get(f"brute_force:{client_ip}")
        return attempts and int(attempts) >= self.max_attempts
    
    async def _record_failed_attempt(self, client_ip: str):
        """Record a failed login attempt"""
        key = f"brute_force:{client_ip}"
        current = redis_client.get(key)
        
        if current:
            redis_client.incr(key)
        else:
            redis_client.setex(key, self.lockout_time, 1)
    
    async def _clear_failed_attempts(self, client_ip: str):
        """Clear failed attempts for IP"""
        redis_client.delete(f"brute_force:{client_ip}")
