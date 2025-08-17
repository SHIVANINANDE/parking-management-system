"""
Spatial API endpoints for geolocation-based parking operations
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.database import get_async_session
from app.services.spatial_service import SpatialService, GeofenceService


router = APIRouter()


# Pydantic models for request/response
class LocationPoint(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")


class ParkingLotSearchRequest(BaseModel):
    location: LocationPoint
    radius_meters: int = Field(default=1000, ge=100, le=10000, description="Search radius in meters")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of results")


class SpotSearchRequest(BaseModel):
    location: LocationPoint
    radius_meters: int = Field(default=500, ge=50, le=5000, description="Search radius in meters")
    spot_type: Optional[str] = Field(default=None, description="Filter by spot type")
    requires_ev_charging: bool = Field(default=False, description="Requires EV charging")
    limit: int = Field(default=50, ge=1, le=200, description="Maximum number of results")


class OptimalSpotRequest(BaseModel):
    user_location: LocationPoint
    vehicle_id: int
    preferred_lot_id: Optional[int] = None
    max_distance_meters: int = Field(default=1000, ge=100, le=5000)


class GeofenceCheckRequest(BaseModel):
    vehicle_location: LocationPoint
    lot_id: int
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class GeofenceEventRequest(BaseModel):
    event_type: str = Field(..., description="Event type: entry, exit, reservation_start, etc.")
    parking_lot_id: int
    vehicle_location: LocationPoint
    vehicle_id: Optional[int] = None
    user_id: Optional[int] = None
    reservation_id: Optional[int] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    detection_method: str = Field(default="gps", description="Detection method: gps, sensor, manual, qr_code")
    metadata: Optional[Dict[str, Any]] = None


@router.post("/parking-lots/search", response_model=List[Dict[str, Any]])
async def search_parking_lots_nearby(
    request: ParkingLotSearchRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Find parking lots within a specified radius of a location
    """
    spatial_service = SpatialService(session)
    
    try:
        results = await spatial_service.find_parking_lots_within_radius(
            latitude=request.location.latitude,
            longitude=request.location.longitude,
            radius_meters=request.radius_meters,
            limit=request.limit
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spatial search failed: {str(e)}")


@router.post("/parking-spots/search", response_model=List[Dict[str, Any]])
async def search_parking_spots_nearby(
    request: SpotSearchRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Find available parking spots within a specified radius of a location
    """
    spatial_service = SpatialService(session)
    
    try:
        results = await spatial_service.find_available_spots_within_radius(
            latitude=request.location.latitude,
            longitude=request.location.longitude,
            radius_meters=request.radius_meters,
            spot_type=request.spot_type,
            requires_ev_charging=request.requires_ev_charging,
            limit=request.limit
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spot search failed: {str(e)}")


@router.post("/parking-spots/optimal", response_model=List[Dict[str, Any]])
async def find_optimal_parking_spot(
    request: OptimalSpotRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Find optimal parking spot based on vehicle compatibility and distance
    """
    spatial_service = SpatialService(session)
    
    try:
        results = await spatial_service.find_optimal_parking_spot(
            user_latitude=request.user_location.latitude,
            user_longitude=request.user_location.longitude,
            vehicle_id=request.vehicle_id,
            preferred_lot_id=request.preferred_lot_id,
            max_distance_meters=request.max_distance_meters
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimal spot search failed: {str(e)}")


@router.get("/parking-lots/{lot_id}/nearest")
async def get_nearest_parking_lot(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    has_ev_charging: Optional[bool] = Query(default=None),
    min_available_spots: Optional[int] = Query(default=None, ge=0),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Find the nearest parking lot to a location with optional filters
    """
    spatial_service = SpatialService(session)
    
    filters = {}
    if has_ev_charging is not None:
        filters["has_ev_charging"] = has_ev_charging
    if min_available_spots is not None:
        filters["min_available_spots"] = min_available_spots
    
    try:
        result = await spatial_service.find_nearest_parking_lot(
            latitude=latitude,
            longitude=longitude,
            filters=filters if filters else None
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="No parking lot found matching criteria")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Nearest lot search failed: {str(e)}")


@router.get("/analytics/density")
async def get_parking_density(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_meters: int = Query(default=1000, ge=100, le=10000),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get parking density statistics for an area
    """
    spatial_service = SpatialService(session)
    
    try:
        result = await spatial_service.get_parking_density_in_area(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Density analysis failed: {str(e)}")


@router.get("/distance/calculate")
async def calculate_distance(
    lat1: float = Query(..., ge=-90, le=90),
    lng1: float = Query(..., ge=-180, le=180),
    lat2: float = Query(..., ge=-90, le=90),
    lng2: float = Query(..., ge=-180, le=180),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Calculate distance between two GPS coordinates
    """
    spatial_service = SpatialService(session)
    
    try:
        distance = await spatial_service.calculate_distance_between_points(
            lat1=lat1, lng1=lng1, lat2=lat2, lng2=lng2
        )
        return {
            "distance_meters": distance,
            "distance_km": round(distance / 1000, 2),
            "point1": {"latitude": lat1, "longitude": lng1},
            "point2": {"latitude": lat2, "longitude": lng2}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Distance calculation failed: {str(e)}")


@router.get("/parking-spots/{spot_id}/route")
async def get_route_to_spot(
    spot_id: int,
    from_latitude: float = Query(..., ge=-90, le=90),
    from_longitude: float = Query(..., ge=-180, le=180),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get basic route information to a parking spot
    """
    spatial_service = SpatialService(session)
    
    try:
        route = await spatial_service.get_route_to_parking_spot(
            from_lat=from_latitude,
            from_lng=from_longitude,
            to_spot_id=spot_id
        )
        
        if not route:
            raise HTTPException(status_code=404, detail="Parking spot not found")
        
        return route
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Route calculation failed: {str(e)}")


# Geofencing endpoints
@router.post("/geofence/check")
async def check_geofence(
    request: GeofenceCheckRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Check if a vehicle is within a parking lot's geofence
    """
    geofence_service = GeofenceService(session)
    
    try:
        result = await geofence_service.check_vehicle_in_lot(
            vehicle_lat=request.vehicle_location.latitude,
            vehicle_lng=request.vehicle_location.longitude,
            lot_id=request.lot_id,
            confidence_threshold=request.confidence_threshold
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geofence check failed: {str(e)}")


@router.post("/geofence/events")
async def log_geofence_event(
    request: GeofenceEventRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Log a geofence event (entry, exit, etc.)
    """
    geofence_service = GeofenceService(session)
    
    try:
        event_id = await geofence_service.log_geofence_event(
            event_type=request.event_type,
            parking_lot_id=request.parking_lot_id,
            vehicle_lat=request.vehicle_location.latitude,
            vehicle_lng=request.vehicle_location.longitude,
            vehicle_id=request.vehicle_id,
            user_id=request.user_id,
            reservation_id=request.reservation_id,
            confidence_score=request.confidence_score,
            detection_method=request.detection_method,
            metadata=request.metadata
        )
        
        return {
            "event_id": event_id,
            "status": "logged",
            "message": f"Geofence {request.event_type} event logged successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event logging failed: {str(e)}")


@router.get("/geofence/events/unprocessed")
async def get_unprocessed_geofence_events(
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get unprocessed geofence events for background processing
    """
    geofence_service = GeofenceService(session)
    
    try:
        events = await geofence_service.get_unprocessed_events(limit=limit)
        return {
            "events": events,
            "count": len(events)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve events: {str(e)}")


@router.put("/geofence/events/{event_id}/process")
async def mark_event_processed(
    event_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Mark a geofence event as processed
    """
    geofence_service = GeofenceService(session)
    
    try:
        success = await geofence_service.mark_event_processed(event_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return {
            "event_id": event_id,
            "status": "processed",
            "message": "Event marked as processed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process event: {str(e)}")


@router.post("/geofence/polygon/create")
async def create_geofence_polygon(
    center_latitude: float = Query(..., ge=-90, le=90),
    center_longitude: float = Query(..., ge=-180, le=180),
    radius_meters: int = Query(..., ge=10, le=5000),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Create a circular geofence polygon around a point
    """
    spatial_service = SpatialService(session)
    
    try:
        polygon_wkt = await spatial_service.create_geofence_polygon(
            center_lat=center_latitude,
            center_lng=center_longitude,
            radius_meters=radius_meters
        )
        
        return {
            "polygon_wkt": polygon_wkt,
            "center": {"latitude": center_latitude, "longitude": center_longitude},
            "radius_meters": radius_meters,
            "area_square_meters": 3.14159 * (radius_meters ** 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Polygon creation failed: {str(e)}")


@router.post("/polygon/spots")
async def get_spots_in_polygon(
    polygon_wkt: str,
    status_filter: Optional[List[str]] = Query(default=None),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get all parking spots within a polygon boundary
    """
    spatial_service = SpatialService(session)
    
    try:
        spots = await spatial_service.get_spots_in_polygon(
            polygon_wkt=polygon_wkt,
            status_filter=status_filter
        )
        
        return {
            "spots": spots,
            "count": len(spots),
            "polygon_wkt": polygon_wkt
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Polygon search failed: {str(e)}")
