from fastapi import APIRouter
from app.api.api_v1.endpoints import spatial, auth

api_router = APIRouter()

# Include authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Include spatial endpoints
api_router.include_router(spatial.router, prefix="/spatial", tags=["spatial"])

@api_router.get("/")
async def api_status():
    return {
        "message": "API v1 is working",
        "endpoints": {
            "authentication": "/auth",
            "spatial": "/spatial"
        },
        "features": [
            "JWT Authentication",
            "OAuth 2.0 Integration", 
            "Rate Limiting",
            "Security Headers",
            "Spatial Analytics"
        ]
    }