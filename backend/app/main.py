from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from app.core.config import settings
from app.api.api_v1.api import api_router
from app.services.spatial_background import start_spatial_processor, stop_spatial_processor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Parking Management System...")
    
    # Start spatial background processor
    try:
        # Start background task
        spatial_task = asyncio.create_task(start_spatial_processor())
        logger.info("Spatial background processor started")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down Parking Management System...")
        try:
            await stop_spatial_processor()
            logger.info("Spatial background processor stopped")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Smart Parking Management System API with Advanced Spatial Extensions",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": "Smart Parking Management System API",
        "features": [
            "PostGIS Spatial Extensions",
            "Real-time Geofencing",
            "Spatial Analytics",
            "R-tree Optimized Queries",
            "Advanced Location Services"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "spatial_extensions": "enabled",
        "postgis": "active"
    }