from fastapi import APIRouter
from app.api.api_v1.endpoints import spatial, auth, events, analytics

api_router = APIRouter()

# Include authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Include spatial endpoints
api_router.include_router(spatial.router, prefix="/spatial", tags=["spatial"])

# Include event system endpoints
api_router.include_router(events.router, prefix="/events", tags=["events"])

# Include analytics and optimization endpoints
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

@api_router.get("/")
async def api_status():
    return {
        "message": "API v1 is working",
        "endpoints": {
            "authentication": "/auth",
            "spatial": "/spatial",
            "events": "/events",
            "analytics": "/analytics"
        },
        "features": [
            "JWT Authentication",
            "OAuth 2.0 Integration", 
            "Rate Limiting",
            "Security Headers",
            "Spatial Analytics",
            "Real-time Event Streaming",
            "CQRS Pattern",
            "Concurrent Reservations",
            "WebSocket Support",
            "ML-based Demand Prediction",
            "Performance Optimization",
            "Sliding Window Analytics",
            "Bloom Filter Optimization",
            "Advanced Caching"
        ]
    }