from fastapi import APIRouter
from app.api.api_v1.endpoints import spatial

api_router = APIRouter()

# Include spatial endpoints
api_router.include_router(spatial.router, prefix="/spatial", tags=["spatial"])

@api_router.get("/")
async def api_status():
    return {"message": "API v1 is working"}