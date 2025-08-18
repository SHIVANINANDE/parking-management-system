"""
Health check endpoints for monitoring application status.
"""
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import aioredis
import structlog
from ..db.database import get_db
from ..core.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

class HealthChecker:
    """Comprehensive health checking for all system components."""
    
    def __init__(self):
        self.last_check_time = None
        self.cached_status = None
        self.cache_duration = timedelta(seconds=30)  # Cache health status for 30 seconds
    
    async def get_full_health_status(self, db: Session) -> Dict[str, Any]:
        """Get comprehensive health status with caching."""
        now = datetime.utcnow()
        
        # Return cached status if recent
        if (self.last_check_time and 
            self.cached_status and 
            now - self.last_check_time < self.cache_duration):
            return self.cached_status
        
        # Perform health checks
        status_data = {
            "status": "healthy",
            "timestamp": now.isoformat(),
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "checks": {}
        }
        
        # Run all health checks
        checks = [
            ("database", self._check_database),
            ("redis", self._check_redis),
            ("disk_space", self._check_disk_space),
            ("memory", self._check_memory),
            ("external_services", self._check_external_services),
        ]
        
        overall_healthy = True
        
        for check_name, check_func in checks:
            try:
                if check_name == "database":
                    check_result = await check_func(db)
                else:
                    check_result = await check_func()
                
                status_data["checks"][check_name] = check_result
                
                if not check_result.get("healthy", False):
                    overall_healthy = False
                    
            except Exception as e:
                logger.error(f"Health check failed for {check_name}", error=str(e))
                status_data["checks"][check_name] = {
                    "healthy": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                overall_healthy = False
        
        # Set overall status
        status_data["status"] = "healthy" if overall_healthy else "unhealthy"
        
        # Cache the result
        self.last_check_time = now
        self.cached_status = status_data
        
        return status_data
    
    async def _check_database(self, db: Session) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        start_time = time.time()
        
        try:
            # Test basic connectivity
            result = await db.execute(text("SELECT 1"))
            basic_query_time = time.time() - start_time
            
            # Test connection pool status
            pool_start = time.time()
            pool_result = await db.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
            )
            active_connections = pool_result.scalar()
            pool_query_time = time.time() - pool_start
            
            # Test write capability
            write_start = time.time()
            await db.execute(text("CREATE TEMP TABLE health_check (id int)"))
            await db.execute(text("INSERT INTO health_check VALUES (1)"))
            await db.execute(text("DROP TABLE health_check"))
            write_time = time.time() - write_start
            
            total_time = time.time() - start_time
            
            return {
                "healthy": True,
                "response_time_ms": round(total_time * 1000, 2),
                "details": {
                    "basic_query_time_ms": round(basic_query_time * 1000, 2),
                    "pool_query_time_ms": round(pool_query_time * 1000, 2),
                    "write_test_time_ms": round(write_time * 1000, 2),
                    "active_connections": active_connections,
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance."""
        start_time = time.time()
        
        try:
            # Connect to Redis
            redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test basic operations
            test_key = f"health_check_{int(time.time())}"
            await redis.set(test_key, "test_value", ex=10)
            value = await redis.get(test_key)
            await redis.delete(test_key)
            
            # Get Redis info
            info = await redis.info()
            
            await redis.close()
            
            response_time = time.time() - start_time
            
            return {
                "healthy": True,
                "response_time_ms": round(response_time * 1000, 2),
                "details": {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "N/A"),
                    "redis_version": info.get("redis_version", "N/A"),
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space."""
        try:
            import psutil
            
            disk_usage = psutil.disk_usage('/')
            free_space_gb = disk_usage.free / (1024**3)
            total_space_gb = disk_usage.total / (1024**3)
            used_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Consider unhealthy if less than 1GB free or more than 95% used
            healthy = free_space_gb > 1.0 and used_percent < 95.0
            
            return {
                "healthy": healthy,
                "details": {
                    "free_space_gb": round(free_space_gb, 2),
                    "total_space_gb": round(total_space_gb, 2),
                    "used_percent": round(used_percent, 2),
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            used_percent = memory.percent
            
            # Consider unhealthy if less than 100MB available or more than 95% used
            healthy = available_gb > 0.1 and used_percent < 95.0
            
            return {
                "healthy": healthy,
                "details": {
                    "available_gb": round(available_gb, 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_percent": round(used_percent, 2),
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_external_services(self) -> Dict[str, Any]:
        """Check external service dependencies."""
        try:
            import aiohttp
            
            external_checks = []
            
            # Check if we can reach external APIs (if any)
            # This would include payment processors, mapping services, etc.
            
            # For now, just check if we can resolve DNS
            import socket
            socket.gethostbyname('google.com')
            
            return {
                "healthy": True,
                "details": {
                    "dns_resolution": "working",
                    "external_apis": "not_configured"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Global health checker instance
health_checker = HealthChecker()

@router.get("/")
async def health_check_basic():
    """Basic health check endpoint for load balancers."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@router.get("/detailed")
async def health_check_detailed(db: Session = Depends(get_db)):
    """Detailed health check with all system components."""
    health_status = await health_checker.get_full_health_status(db)
    
    # Return appropriate HTTP status code
    if health_status["status"] == "healthy":
        return health_status
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )

@router.get("/readiness")
async def readiness_check(db: Session = Depends(get_db)):
    """Kubernetes readiness probe endpoint."""
    try:
        # Quick database check
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "error": str(e)}
        )

@router.get("/liveness")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

@router.get("/database")
async def database_health(db: Session = Depends(get_db)):
    """Specific database health check."""
    result = await health_checker._check_database(db)
    
    if result["healthy"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result
        )

@router.get("/redis")
async def redis_health():
    """Specific Redis health check."""
    result = await health_checker._check_redis()
    
    if result["healthy"]:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result
        )
