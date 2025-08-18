"""
Monitoring and metrics middleware for the parking management system.
"""
import time
import asyncio
from typing import Callable, Dict, Any
from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import structlog
import psutil
import asyncpg
from sqlalchemy import text
from ..db.database import get_db

logger = structlog.get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections_total',
    'Number of active connections'
)

DATABASE_QUERY_DURATION = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

DATABASE_CONNECTION_POOL = Gauge(
    'database_connection_pool_size',
    'Database connection pool size',
    ['state']  # active, idle, total
)

ERROR_COUNT = Counter(
    'application_errors_total',
    'Total application errors',
    ['error_type', 'endpoint']
)

PARKING_SPOT_OCCUPANCY = Gauge(
    'parking_spot_occupancy',
    'Current parking spot occupancy',
    ['lot_id', 'status']
)

RESERVATION_COUNT = Counter(
    'reservations_total',
    'Total reservations',
    ['status', 'lot_id']
)

PAYMENT_AMOUNT = Histogram(
    'payment_amount_dollars',
    'Payment amounts in dollars',
    ['payment_method', 'status'],
    buckets=[5, 10, 25, 50, 100, 250, 500, 1000]
)

# System metrics
SYSTEM_CPU_USAGE = Gauge('system_cpu_usage_percent', 'System CPU usage percentage')
SYSTEM_MEMORY_USAGE = Gauge('system_memory_usage_percent', 'System memory usage percentage')
SYSTEM_DISK_USAGE = Gauge('system_disk_usage_percent', 'System disk usage percentage')

class MetricsMiddleware:
    """Middleware for collecting application metrics."""
    
    def __init__(self, app):
        self.app = app
        self._start_system_metrics_collection()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        start_time = time.time()
        
        # Track active connections
        ACTIVE_CONNECTIONS.inc()
        
        try:
            response = Response()
            
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    response.status_code = message["status"]
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
            
            # Record metrics
            duration = time.time() - start_time
            method = request.method
            endpoint = self._get_endpoint_name(request)
            status_code = str(response.status_code)
            
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            # Log slow requests
            if duration > 1.0:
                logger.warning(
                    "Slow request detected",
                    method=method,
                    endpoint=endpoint,
                    duration=duration,
                    status_code=status_code
                )
        
        except Exception as e:
            # Record error metrics
            ERROR_COUNT.labels(
                error_type=type(e).__name__,
                endpoint=self._get_endpoint_name(request)
            ).inc()
            
            logger.error(
                "Request processing error",
                error=str(e),
                error_type=type(e).__name__,
                endpoint=self._get_endpoint_name(request)
            )
            raise
        
        finally:
            ACTIVE_CONNECTIONS.dec()
    
    def _get_endpoint_name(self, request: Request) -> str:
        """Extract endpoint name from request."""
        path = request.url.path
        
        # Normalize path parameters
        if "/api/v1/" in path:
            parts = path.split("/")
            normalized_parts = []
            for part in parts:
                if part.isdigit() or (part and part[0].isdigit()):
                    normalized_parts.append("{id}")
                else:
                    normalized_parts.append(part)
            return "/".join(normalized_parts)
        
        return path
    
    def _start_system_metrics_collection(self):
        """Start background task for system metrics collection."""
        asyncio.create_task(self._collect_system_metrics())
    
    async def _collect_system_metrics(self):
        """Collect system metrics periodically."""
        while True:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                SYSTEM_CPU_USAGE.set(cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                SYSTEM_MEMORY_USAGE.set(memory.percent)
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                SYSTEM_DISK_USAGE.set(disk_percent)
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logger.error("Error collecting system metrics", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error

class DatabaseMetricsCollector:
    """Collector for database-specific metrics."""
    
    def __init__(self):
        self.db_session = None
    
    async def collect_db_metrics(self):
        """Collect database metrics."""
        try:
            async for db in get_db():
                self.db_session = db
                break
            
            if self.db_session:
                await self._collect_connection_pool_metrics()
                await self._collect_parking_metrics()
                await self._collect_reservation_metrics()
        
        except Exception as e:
            logger.error("Error collecting database metrics", error=str(e))
    
    async def _collect_connection_pool_metrics(self):
        """Collect connection pool metrics."""
        try:
            # Query connection pool stats
            result = await self.db_session.execute(
                text("SELECT count(*) as total FROM pg_stat_activity")
            )
            total_connections = result.scalar()
            
            result = await self.db_session.execute(
                text("""
                    SELECT count(*) as active 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """)
            )
            active_connections = result.scalar()
            
            result = await self.db_session.execute(
                text("""
                    SELECT count(*) as idle 
                    FROM pg_stat_activity 
                    WHERE state = 'idle'
                """)
            )
            idle_connections = result.scalar()
            
            DATABASE_CONNECTION_POOL.labels(state='total').set(total_connections)
            DATABASE_CONNECTION_POOL.labels(state='active').set(active_connections)
            DATABASE_CONNECTION_POOL.labels(state='idle').set(idle_connections)
        
        except Exception as e:
            logger.error("Error collecting connection pool metrics", error=str(e))
    
    async def _collect_parking_metrics(self):
        """Collect parking-related metrics."""
        try:
            # Parking spot occupancy by lot
            result = await self.db_session.execute(
                text("""
                    SELECT 
                        pl.id as lot_id,
                        ps.status,
                        COUNT(*) as count
                    FROM parking_spots ps
                    JOIN parking_lots pl ON ps.lot_id = pl.id
                    GROUP BY pl.id, ps.status
                """)
            )
            
            for row in result:
                PARKING_SPOT_OCCUPANCY.labels(
                    lot_id=str(row.lot_id),
                    status=row.status
                ).set(row.count)
        
        except Exception as e:
            logger.error("Error collecting parking metrics", error=str(e))
    
    async def _collect_reservation_metrics(self):
        """Collect reservation metrics."""
        try:
            # Reservation counts by status and lot
            result = await self.db_session.execute(
                text("""
                    SELECT 
                        r.lot_id,
                        r.status,
                        COUNT(*) as count
                    FROM reservations r
                    WHERE r.created_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY r.lot_id, r.status
                """)
            )
            
            for row in result:
                RESERVATION_COUNT.labels(
                    status=row.status,
                    lot_id=str(row.lot_id)
                ).inc(row.count)
        
        except Exception as e:
            logger.error("Error collecting reservation metrics", error=str(e))

# Database query timing decorator
def time_database_query(query_type: str):
    """Decorator to time database queries."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                DATABASE_QUERY_DURATION.labels(query_type=query_type).observe(duration)
                
                # Log slow queries
                if duration > 0.5:
                    logger.warning(
                        "Slow database query detected",
                        query_type=query_type,
                        duration=duration,
                        function=func.__name__
                    )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                DATABASE_QUERY_DURATION.labels(query_type=f"{query_type}_error").observe(duration)
                
                logger.error(
                    "Database query error",
                    query_type=query_type,
                    duration=duration,
                    error=str(e),
                    function=func.__name__
                )
                raise
        return wrapper
    return decorator

async def get_metrics():
    """Endpoint to expose Prometheus metrics."""
    # Collect database metrics before exposing
    db_collector = DatabaseMetricsCollector()
    await db_collector.collect_db_metrics()
    
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
