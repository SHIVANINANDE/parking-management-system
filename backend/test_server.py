"""
Minimal FastAPI server to test event system implementation
"""
from fastapi import FastAPI
import uvicorn

# Test basic FastAPI functionality
app = FastAPI(
    title="Parking Management System - Test Server",
    description="Testing event system implementation"
)

@app.get("/")
async def root():
    return {
        "message": "Smart Parking Management System API",
        "status": "testing", 
        "step": "Step 5: Real-time Event System",
        "features": [
            "Event Streaming Architecture",
            "CQRS Pattern", 
            "Kafka Integration",
            "WebSocket Support",
            "Concurrent Reservations",
            "Event Sourcing",
            "Redis Distributed Locking",
            "Optimistic Concurrency Control"
        ]
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "test_mode": True}

# Test importing our event system components
@app.get("/test-imports")
async def test_imports():
    """Test if all our event system components can be imported"""
    try:
        # Test basic imports first
        from app.services.event_service import Event, EventStore, EventBus
        from app.services.cqrs_service import Command, Query, CreateReservationCommand
        from app.services.reservation_service import ConcurrentReservationManager, DistributedLock
        from app.services.event_handlers import NotificationService, SystemEventHandler
        
        return {
            "imports": "success",
            "event_service": "✓ Event, EventStore, EventBus imported",
            "cqrs_service": "✓ Command, Query, CreateReservationCommand imported", 
            "reservation_service": "✓ ConcurrentReservationManager, DistributedLock imported",
            "event_handlers": "✓ NotificationService, SystemEventHandler imported",
            "status": "All event system components imported successfully"
        }
    except Exception as e:
        return {
            "imports": "failed",
            "error": str(e),
            "status": "Import error encountered"
        }

if __name__ == "__main__":
    uvicorn.run("test_server:app", host="0.0.0.0", port=8000, reload=True)
