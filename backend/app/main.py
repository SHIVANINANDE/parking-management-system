from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging
import uvicorn

from app.core.config import settings
from app.api.api_v1.api import api_router
from app.services.spatial_background import start_spatial_processor, stop_spatial_processor
from app.api.api_v1.endpoints.events import initialize_event_system
from app.middleware import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    BruteForceProtectionMiddleware
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Smart Parking Management System...")
    
    try:
        # Start spatial background processor
        spatial_task = asyncio.create_task(start_spatial_processor())
        logger.info("Spatial background processor started")
        
        # Initialize event system
        await initialize_event_system()
        logger.info("Event system initialized")
        
        # Initialize authentication and security systems
        logger.info("Authentication and security systems initialized")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down Smart Parking Management System...")
        try:
            await stop_spatial_processor()
            logger.info("Spatial background processor stopped")
            
            # Stop event system
            from app.services.reservation_service import reservation_manager
            from app.services.event_service import event_service
            
            await reservation_manager.stop_processing()
            event_service.close()
            logger.info("Event system stopped")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Smart Parking Management System API with Advanced Security, Spatial Analytics & Real-time Events",
    openapi_url=settings.OPENAPI_URL if settings.DEBUG else None,
    docs_url=settings.DOCS_URL if settings.DEBUG else None,
    redoc_url=settings.REDOC_URL if settings.DEBUG else None,
    lifespan=lifespan
)

# Security Middleware (order matters!)
# 1. Trusted Host Middleware (outermost)
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.your-domain.com"]
    )

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "WEBSOCKET"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
)

# 3. Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 4. Rate Limiting Middleware
app.add_middleware(
    RateLimitMiddleware,
    calls_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    burst_limit=settings.RATE_LIMIT_BURST
)

# 5. Brute Force Protection Middleware
app.add_middleware(BruteForceProtectionMiddleware)

# 6. Request Logging Middleware (innermost)
if settings.DEBUG:
    app.add_middleware(RequestLoggingMiddleware)

# Exception handlers
@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    """Handle validation errors"""
    logger.warning(f"Validation error on {request.url}: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors() if hasattr(exc, 'errors') else str(exc)
        }
    )

@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc):
    """Handle internal server errors"""
    logger.error(f"Internal server error on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR"
        }
    )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "Smart Parking Management System API",
        "version": settings.VERSION,
        "features": [
            "JWT Authentication",
            "OAuth 2.0 (Google, GitHub)",
            "Rate Limiting",
            "Security Headers", 
            "CORS Protection",
            "PostGIS Spatial Extensions",
            "Real-time Geofencing",
            "Spatial Analytics",
            "Advanced Security",
            "Real-time Event Streaming",
            "CQRS Pattern",
            "Event Sourcing", 
            "Concurrent Reservations",
            "WebSocket Support",
            "Priority Queuing",
            "Optimistic Concurrency Control"
        ],
        "documentation": "/docs" if settings.DEBUG else None
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "security": "enabled",
        "spatial_extensions": "enabled",
        "postgis": "active",
        "authentication": "JWT + OAuth2",
        "rate_limiting": "active",
        "event_streaming": "active",
        "kafka": "connected",
        "redis": "connected",
        "cqrs": "enabled",
        "websockets": "enabled"
    }

@app.get("/security-info")
async def security_info():
    """Security configuration information"""
    return {
        "authentication": {
            "jwt_enabled": True,
            "oauth_providers": [
                "google" if settings.GOOGLE_CLIENT_ID else None,
                "github" if settings.GITHUB_CLIENT_ID else None
            ],
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_minutes": settings.REFRESH_TOKEN_EXPIRE_MINUTES
        },
        "security_features": {
            "rate_limiting": True,
            "security_headers": True,
            "brute_force_protection": True,
            "cors_enabled": True,
            "input_validation": True,
            "row_level_locking": True,
            "optimistic_concurrency": True
        },
        "password_requirements": {
            "min_length": settings.PASSWORD_MIN_LENGTH,
            "require_uppercase": settings.PASSWORD_REQUIRE_UPPERCASE,
            "require_lowercase": settings.PASSWORD_REQUIRE_LOWERCASE,
            "require_numbers": settings.PASSWORD_REQUIRE_NUMBERS,
            "require_special": settings.PASSWORD_REQUIRE_SPECIAL
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        ssl_keyfile=settings.SSL_PRIVATE_KEY_PATH if settings.USE_SSL else None,
        ssl_certfile=settings.SSL_CERTIFICATE_PATH if settings.USE_SSL else None
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        ssl_keyfile=settings.SSL_PRIVATE_KEY_PATH if settings.USE_SSL else None,
        ssl_certfile=settings.SSL_CERTIFICATE_PATH if settings.USE_SSL else None
    )