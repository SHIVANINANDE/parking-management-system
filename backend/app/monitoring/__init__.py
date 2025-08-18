"""
Integration of monitoring and observability into the main application.
"""
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import structlog
from .middleware.monitoring import MetricsMiddleware, get_metrics
from .middleware.logging import LoggingMiddleware, configure_logging
from .api.health import router as health_router
from .monitoring.alerts import alert_manager
from .monitoring.business_metrics import business_metrics_collector
from .monitoring.performance import monitor_api_endpoint

# Configure logging first
configure_logging()
logger = structlog.get_logger(__name__)

def setup_monitoring(app: FastAPI):
    """Set up comprehensive monitoring and observability for the application."""
    
    # Add monitoring middleware
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(LoggingMiddleware)
    
    # Add health check endpoints
    app.include_router(health_router)
    
    # Add metrics endpoint
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return await get_metrics()
    
    # Add business metrics endpoint
    @app.get("/api/v1/metrics/business")
    @monitor_api_endpoint("business_metrics")
    async def business_metrics():
        """Business metrics endpoint for monitoring."""
        try:
            # Trigger immediate collection of business metrics
            await business_metrics_collector.collect_real_time_metrics()
            
            # Return basic metrics info
            return {
                "status": "success",
                "message": "Business metrics collected",
                "timestamp": "2025-01-18T00:00:00Z"
            }
        except Exception as e:
            logger.error("Failed to collect business metrics", error=str(e))
            return {
                "status": "error",
                "message": str(e),
                "timestamp": "2025-01-18T00:00:00Z"
            }
    
    # Add alert management endpoints
    @app.get("/api/v1/alerts")
    @monitor_api_endpoint("get_alerts")
    async def get_active_alerts():
        """Get active alerts."""
        try:
            alerts = alert_manager.get_active_alerts()
            return {
                "alerts": [alert.to_dict() for alert in alerts],
                "count": len(alerts)
            }
        except Exception as e:
            logger.error("Failed to get alerts", error=str(e))
            return {"error": str(e)}
    
    @app.post("/api/v1/alerts/{alert_id}/acknowledge")
    @monitor_api_endpoint("acknowledge_alert")
    async def acknowledge_alert(alert_id: str):
        """Acknowledge an alert."""
        try:
            alert_manager.acknowledge_alert(alert_id)
            return {"status": "acknowledged", "alert_id": alert_id}
        except Exception as e:
            logger.error("Failed to acknowledge alert", error=str(e), alert_id=alert_id)
            return {"error": str(e)}
    
    @app.post("/api/v1/alerts/{alert_id}/resolve")
    @monitor_api_endpoint("resolve_alert")
    async def resolve_alert(alert_id: str):
        """Resolve an alert."""
        try:
            alert_manager.resolve_alert(alert_id)
            return {"status": "resolved", "alert_id": alert_id}
        except Exception as e:
            logger.error("Failed to resolve alert", error=str(e), alert_id=alert_id)
            return {"error": str(e)}
    
    # Startup event to initialize monitoring
    @app.on_event("startup")
    async def startup_monitoring():
        """Initialize monitoring components on startup."""
        logger.info("Initializing monitoring and observability components")
        
        try:
            # Start business metrics collection
            await business_metrics_collector.start_collection()
            logger.info("Business metrics collection started")
            
            # Initialize alert manager
            logger.info("Alert manager initialized")
            
        except Exception as e:
            logger.error("Failed to initialize monitoring components", error=str(e))
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_monitoring():
        """Clean up monitoring components on shutdown."""
        logger.info("Shutting down monitoring components")
    
    logger.info("Monitoring and observability setup completed")

# Example of how to use monitoring decorators in your API endpoints
def create_monitored_app() -> FastAPI:
    """Create FastAPI app with full monitoring setup."""
    
    app = FastAPI(
        title="Parking Management System",
        description="Comprehensive parking management with monitoring",
        version="1.0.0"
    )
    
    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup monitoring
    setup_monitoring(app)
    
    return app
