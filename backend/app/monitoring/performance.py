"""
Performance monitoring decorators and utilities.
"""
import time
import functools
import asyncio
from typing import Optional, Dict, Any, Callable
from contextlib import asynccontextmanager
import structlog
from .monitoring import (
    DATABASE_QUERY_DURATION, 
    REQUEST_DURATION, 
    ERROR_COUNT,
    time_database_query
)
from .alerts import alert_manager

logger = structlog.get_logger(__name__)

class PerformanceMonitor:
    """Context manager and decorator for performance monitoring."""
    
    def __init__(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        self.operation_name = operation_name
        self.tags = tags or {}
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        # Log performance data
        logger.info(
            "Operation completed",
            operation=self.operation_name,
            duration_seconds=duration,
            **self.tags
        )
        
        # Record metrics
        REQUEST_DURATION.labels(
            method="internal",
            endpoint=self.operation_name
        ).observe(duration)
        
        # Check for performance alerts
        asyncio.create_task(
            alert_manager.evaluate_metric(
                f"operation_duration_{self.operation_name}", 
                duration, 
                self.tags
            )
        )
        
        # Log warnings for slow operations
        if duration > 2.0:
            logger.warning(
                "Slow operation detected",
                operation=self.operation_name,
                duration_seconds=duration,
                **self.tags
            )

@asynccontextmanager
async def async_performance_monitor(operation_name: str, tags: Optional[Dict[str, str]] = None):
    """Async context manager for performance monitoring."""
    start_time = time.time()
    tags = tags or {}
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        
        # Log performance data
        logger.info(
            "Async operation completed",
            operation=operation_name,
            duration_seconds=duration,
            **tags
        )
        
        # Record metrics
        REQUEST_DURATION.labels(
            method="async",
            endpoint=operation_name
        ).observe(duration)
        
        # Check for performance alerts
        await alert_manager.evaluate_metric(
            f"async_operation_duration_{operation_name}", 
            duration, 
            tags
        )

def monitor_performance(operation_name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator for monitoring function performance."""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with async_performance_monitor(operation_name, tags):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with PerformanceMonitor(operation_name, tags):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator

def monitor_api_endpoint(endpoint_name: str):
    """Specialized decorator for API endpoint monitoring."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            error_occurred = False
            
            try:
                result = await func(*args, **kwargs)
                
                # Try to extract status code from response
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                
                return result
                
            except Exception as e:
                error_occurred = True
                status_code = 500
                
                # Record error metrics
                ERROR_COUNT.labels(
                    error_type=type(e).__name__,
                    endpoint=endpoint_name
                ).inc()
                
                # Log error
                logger.error(
                    "API endpoint error",
                    endpoint=endpoint_name,
                    error=str(e),
                    error_type=type(e).__name__
                )
                
                raise
                
            finally:
                duration = time.time() - start_time
                
                # Record performance metrics
                REQUEST_DURATION.labels(
                    method="API",
                    endpoint=endpoint_name
                ).observe(duration)
                
                # Log API call
                log_level = "error" if error_occurred else "info"
                getattr(logger, log_level)(
                    "API endpoint called",
                    endpoint=endpoint_name,
                    duration_seconds=duration,
                    status_code=status_code,
                    error_occurred=error_occurred
                )
                
                # Performance alerting
                await alert_manager.evaluate_metric(
                    "api_response_time",
                    duration,
                    {"endpoint": endpoint_name, "status": str(status_code)}
                )
        
        return wrapper
    return decorator

class DatabasePerformanceMonitor:
    """Specialized monitor for database operations."""
    
    @staticmethod
    def monitor_query(query_type: str):
        """Monitor database query performance."""
        return time_database_query(query_type)
    
    @staticmethod
    @asynccontextmanager
    async def monitor_transaction(transaction_name: str):
        """Monitor database transaction performance."""
        start_time = time.time()
        
        try:
            yield
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.error(
                "Database transaction failed",
                transaction=transaction_name,
                duration_seconds=duration,
                error=str(e)
            )
            
            # Record failed transaction metrics
            DATABASE_QUERY_DURATION.labels(
                query_type=f"{transaction_name}_failed"
            ).observe(duration)
            
            raise
            
        else:
            duration = time.time() - start_time
            
            logger.info(
                "Database transaction completed",
                transaction=transaction_name,
                duration_seconds=duration
            )
            
            # Record successful transaction metrics
            DATABASE_QUERY_DURATION.labels(
                query_type=transaction_name
            ).observe(duration)

class MemoryMonitor:
    """Monitor memory usage of operations."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.initial_memory = None
        self.peak_memory = None
    
    def __enter__(self):
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        self.initial_memory = process.memory_info().rss
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        final_memory = process.memory_info().rss
        memory_used = final_memory - self.initial_memory
        
        logger.info(
            "Memory usage tracking",
            operation=self.operation_name,
            initial_memory_mb=self.initial_memory / (1024 * 1024),
            final_memory_mb=final_memory / (1024 * 1024),
            memory_used_mb=memory_used / (1024 * 1024)
        )
        
        # Alert on high memory usage
        if memory_used > 100 * 1024 * 1024:  # 100MB
            logger.warning(
                "High memory usage detected",
                operation=self.operation_name,
                memory_used_mb=memory_used / (1024 * 1024)
            )

def monitor_memory_usage(operation_name: str):
    """Decorator for monitoring memory usage."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with MemoryMonitor(operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator

class CachePerformanceMonitor:
    """Monitor cache hit/miss rates and performance."""
    
    def __init__(self):
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_cache_time = 0.0
    
    def record_cache_hit(self, duration: float, cache_key: str):
        """Record a cache hit."""
        self.cache_hits += 1
        self.total_cache_time += duration
        
        logger.debug(
            "Cache hit",
            cache_key=cache_key,
            duration_seconds=duration
        )
    
    def record_cache_miss(self, cache_key: str):
        """Record a cache miss."""
        self.cache_misses += 1
        
        logger.debug(
            "Cache miss",
            cache_key=cache_key
        )
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_requests = self.cache_hits + self.cache_misses
        if total_requests == 0:
            return 0.0
        return self.cache_hits / total_requests
    
    def get_average_cache_time(self) -> float:
        """Calculate average cache response time."""
        if self.cache_hits == 0:
            return 0.0
        return self.total_cache_time / self.cache_hits

# Global performance monitor instances
cache_monitor = CachePerformanceMonitor()

def monitor_cache_operation(cache_key: str):
    """Decorator for monitoring cache operations."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Determine if this was a cache hit or miss
                if result is not None:
                    cache_monitor.record_cache_hit(duration, cache_key)
                else:
                    cache_monitor.record_cache_miss(cache_key)
                
                return result
                
            except Exception as e:
                cache_monitor.record_cache_miss(cache_key)
                logger.error(
                    "Cache operation failed",
                    cache_key=cache_key,
                    error=str(e)
                )
                raise
        
        return wrapper
    return decorator
