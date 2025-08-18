"""
Logging configuration and structured logging setup.
"""
import os
import sys
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger
import structlog
from structlog.stdlib import LoggerFactory

# Configure structlog
def configure_logging():
    """Configure structured logging with JSON output for ELK stack."""
    
    # Determine log level from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Configure structlog processors
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        add_service_context,
        add_trace_info,
    ]
    
    if os.getenv("ENVIRONMENT") == "development":
        # Pretty printing for development
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True)
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # JSON output for production (ELK stack)
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    # Configure standard library logging
    formatter = jsonlogger.JsonFormatter(
        '%(levelname)s %(name)s %(asctime)s %(message)s',
        timestamp=True
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level))
    
    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)

def add_service_context(logger, method_name, event_dict):
    """Add service context to all log entries."""
    event_dict.update({
        "service": "parking-management-api",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "host": os.getenv("HOSTNAME", "localhost"),
    })
    return event_dict

def add_trace_info(logger, method_name, event_dict):
    """Add tracing information if available."""
    # Add correlation ID if present in context
    # This would integrate with distributed tracing
    correlation_id = getattr(logger, '_correlation_id', None)
    if correlation_id:
        event_dict['correlation_id'] = correlation_id
    
    return event_dict

class LoggingMiddleware:
    """Middleware for request/response logging."""
    
    def __init__(self, app):
        self.app = app
        self.logger = structlog.get_logger(__name__)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = datetime.utcnow()
        request_id = self._generate_request_id()
        
        # Bind request ID to logger
        bound_logger = self.logger.bind(request_id=request_id)
        
        # Log request
        bound_logger.info(
            "Request started",
            method=scope["method"],
            path=scope["path"],
            query_string=scope.get("query_string", b"").decode(),
            client=scope.get("client"),
            headers=self._format_headers(scope.get("headers", [])),
        )
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                duration = (datetime.utcnow() - start_time).total_seconds()
                status_code = message["status"]
                
                # Log response
                log_level = "error" if status_code >= 500 else "warning" if status_code >= 400 else "info"
                getattr(bound_logger, log_level)(
                    "Request completed",
                    status_code=status_code,
                    duration_seconds=duration,
                    response_headers=self._format_headers(message.get("headers", [])),
                )
            
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            bound_logger.error(
                "Request failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=duration,
                traceback=traceback.format_exc(),
            )
            raise
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        import uuid
        return str(uuid.uuid4())
    
    def _format_headers(self, headers) -> Dict[str, str]:
        """Format headers for logging (excluding sensitive data)."""
        formatted = {}
        sensitive_headers = {"authorization", "cookie", "x-api-key"}
        
        for header_tuple in headers:
            if len(header_tuple) == 2:
                name, value = header_tuple
                name = name.decode() if isinstance(name, bytes) else name
                value = value.decode() if isinstance(value, bytes) else value
                
                if name.lower() in sensitive_headers:
                    formatted[name] = "[REDACTED]"
                else:
                    formatted[name] = value
        
        return formatted

class DatabaseLogHandler:
    """Handler for logging database operations."""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    def log_query(self, query: str, params: Optional[Dict] = None, duration: Optional[float] = None):
        """Log database query with performance info."""
        log_data = {
            "query": self._sanitize_query(query),
            "operation": "database_query"
        }
        
        if params:
            log_data["params"] = self._sanitize_params(params)
        
        if duration is not None:
            log_data["duration_seconds"] = duration
            
            # Log slow queries as warnings
            if duration > 1.0:
                self.logger.warning("Slow database query detected", **log_data)
            else:
                self.logger.info("Database query executed", **log_data)
        else:
            self.logger.info("Database query prepared", **log_data)
    
    def log_connection_event(self, event: str, details: Optional[Dict] = None):
        """Log database connection events."""
        log_data = {
            "operation": "database_connection",
            "event": event
        }
        
        if details:
            log_data.update(details)
        
        self.logger.info("Database connection event", **log_data)
    
    def _sanitize_query(self, query: str) -> str:
        """Sanitize query for logging (remove sensitive data)."""
        # Remove potential password or sensitive data patterns
        import re
        
        # Replace potential password values
        query = re.sub(r"password\s*=\s*'[^']*'", "password='[REDACTED]'", query, flags=re.IGNORECASE)
        query = re.sub(r"password\s*=\s*\"[^\"]*\"", "password=\"[REDACTED]\"", query, flags=re.IGNORECASE)
        
        return query
    
    def _sanitize_params(self, params: Dict) -> Dict:
        """Sanitize query parameters for logging."""
        sanitized = {}
        sensitive_fields = {"password", "token", "secret", "key", "auth"}
        
        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = str(value)[:100]  # Truncate long values
        
        return sanitized

class ErrorTracker:
    """Centralized error tracking and alerting."""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        self.error_counts = {}
    
    def track_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Track error occurrence with context."""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Count error occurrences
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        log_data = {
            "error_type": error_type,
            "error_message": error_message,
            "error_count": self.error_counts[error_type],
            "traceback": traceback.format_exc(),
            "operation": "error_tracking"
        }
        
        if context:
            log_data["context"] = context
        
        # Determine severity based on error type
        if isinstance(error, (ConnectionError, TimeoutError)):
            self.logger.critical("Critical infrastructure error", **log_data)
        elif isinstance(error, (ValueError, TypeError)):
            self.logger.error("Application logic error", **log_data)
        else:
            self.logger.error("Unhandled error", **log_data)
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of error counts."""
        return self.error_counts.copy()

class PerformanceTracker:
    """Track application performance metrics."""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    def track_operation(self, operation: str, duration: float, **kwargs):
        """Track operation performance."""
        log_data = {
            "operation": "performance_tracking",
            "operation_name": operation,
            "duration_seconds": duration,
        }
        log_data.update(kwargs)
        
        # Determine log level based on duration
        if duration > 5.0:
            self.logger.warning("Slow operation detected", **log_data)
        elif duration > 2.0:
            self.logger.info("Moderate operation duration", **log_data)
        else:
            self.logger.debug("Operation completed", **log_data)
    
    def track_api_performance(self, endpoint: str, method: str, status_code: int, 
                            duration: float, **kwargs):
        """Track API endpoint performance."""
        log_data = {
            "operation": "api_performance",
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration_seconds": duration,
        }
        log_data.update(kwargs)
        
        # Performance thresholds
        slow_threshold = 1.0
        very_slow_threshold = 3.0
        
        if duration > very_slow_threshold:
            self.logger.warning("Very slow API response", **log_data)
        elif duration > slow_threshold:
            self.logger.info("Slow API response", **log_data)
        else:
            self.logger.debug("API response", **log_data)

# Global instances
error_tracker = ErrorTracker()
performance_tracker = PerformanceTracker()
db_log_handler = DatabaseLogHandler()

# Initialize logging configuration
configure_logging()
