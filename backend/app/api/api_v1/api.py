from fastapi import APIRouter

api_router = APIRouter()

@api_router.get("/")
async def api_status():
    return {"message": "API v1 is working"}