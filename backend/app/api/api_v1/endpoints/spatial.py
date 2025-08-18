"""
Spatial API endpoints for geolocation-based parking operations
Enhanced with advanced spatial algorithms and PostGIS operations
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging

from app.db.database import get_db
from app.services.spatial_service import SpatialService, GeofenceService
from app.services.advanced_spatial_service import AdvancedSpatialService

logger = logging.getLogger(__name__)
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


class OptimalRouteRequest(BaseModel):
    start_location: LocationPoint
    destination_location: LocationPoint
    waypoints: Optional[List[LocationPoint]] = Field(default=None, description="Optional waypoints")
    route_type: str = Field(default="fastest", description="Route optimization type: fastest, shortest, scenic")
    avoid_tolls: bool = Field(default=False, description="Avoid toll roads")
    vehicle_type: str = Field(default="car", description="Vehicle type for routing")
    obstacles: Optional[List[List[float]]] = Field(default=None, description="Obstacle coordinates [[lat,lng],...]")


class SpatialClusteringRequest(BaseModel):
    region_bounds: List[float] = Field(..., description="[min_lng, min_lat, max_lng, max_lat]")
    cluster_distance_km: float = Field(default=0.1, ge=0.01, le=10.0, description="Clustering distance in km")
    min_samples: int = Field(default=3, ge=2, le=20, description="Minimum samples per cluster")


class GeohashRequest(BaseModel):
    location: LocationPoint
    precision: int = Field(default=9, ge=1, le=12, description="Geohash precision level")


class H3IndexRequest(BaseModel):
    location: LocationPoint
    resolution: int = Field(default=9, ge=0, le=15, description="H3 resolution level")


class PolygonIntersectionRequest(BaseModel):
    polygon1_wkt: str = Field(..., description="First polygon in WKT format")
    polygon2_wkt: str = Field(..., description="Second polygon in WKT format")


class SpatialAnalysisRequest(BaseModel):
    center_location: LocationPoint
    analysis_radius_km: float = Field(default=5.0, ge=0.1, le=50.0, description="Analysis radius in km")
    include_coverage: bool = Field(default=True, description="Include spatial coverage analysis")
    include_clustering: bool = Field(default=True, description="Include clustering analysis")


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


# Advanced Spatial Endpoints

@router.post("/advanced/nearest-rtree", response_model=List[Dict[str, Any]])
async def find_nearest_spots_with_rtree(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    k: int = Query(default=10, ge=1, le=100),
    max_distance_km: float = Query(default=5.0, ge=0.1, le=50.0),
    session: AsyncSession = Depends(get_db)
):
    """
    Find nearest parking spots using R-tree spatial index for optimal performance
    """
    advanced_service = AdvancedSpatialService(session)
    
    try:
        results = await advanced_service.find_nearest_spots_rtree(
            latitude=latitude,
            longitude=longitude,
            k=k,
            max_distance_km=max_distance_km
        )
        return results
    except Exception as e:
        logger.error(f"R-tree nearest search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Advanced nearest search failed: {str(e)}")


@router.post("/advanced/astar-pathfinding")
async def calculate_astar_path(
    request: OptimalRouteRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Calculate optimal path using A* pathfinding algorithm
    """
    advanced_service = AdvancedSpatialService(session)
    
    try:
        obstacle_coords = []
        if request.obstacles:
            obstacle_coords = [(lat, lng) for lat, lng in request.obstacles]
        
        path = await advanced_service.implement_astar_pathfinding(
            start_lat=request.start_location.latitude,
            start_lng=request.start_location.longitude,
            goal_lat=request.destination_location.latitude,
            goal_lng=request.destination_location.longitude,
            obstacles=obstacle_coords
        )
        
        if not path:
            raise HTTPException(status_code=404, detail="No path found between start and destination")
        
        # Calculate path statistics
        total_distance = 0
        for i in range(len(path) - 1):
            # Simple distance calculation for path segments
            dx = path[i+1][0] - path[i][0]
            dy = path[i+1][1] - path[i][1]
            total_distance += (dx*dx + dy*dy) ** 0.5
        
        return {
            "path": [{"longitude": lng, "latitude": lat} for lng, lat in path],
            "total_waypoints": len(path),
            "estimated_distance_degrees": total_distance,
            "algorithm": "A*",
            "obstacles_avoided": len(obstacle_coords)
        }
    except Exception as e:
        logger.error(f"A* pathfinding failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pathfinding failed: {str(e)}")


@router.post("/advanced/osrm-route")
async def get_osrm_route(
    request: OptimalRouteRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Get real-world route using OSRM (Open Source Routing Machine)
    """
    advanced_service = AdvancedSpatialService(session)
    
    try:
        route = await advanced_service.get_osrm_route(
            start_lat=request.start_location.latitude,
            start_lng=request.start_location.longitude,
            goal_lat=request.destination_location.latitude,
            goal_lng=request.destination_location.longitude
        )
        
        return {
            "route": route,
            "start": {
                "latitude": request.start_location.latitude,
                "longitude": request.start_location.longitude
            },
            "destination": {
                "latitude": request.destination_location.latitude,
                "longitude": request.destination_location.longitude
            },
            "route_type": request.route_type
        }
    except Exception as e:
        logger.error(f"OSRM routing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Route calculation failed: {str(e)}")


@router.post("/advanced/spatial-clustering")
async def perform_spatial_clustering(
    request: SpatialClusteringRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Perform spatial clustering analysis using DBSCAN algorithm
    """
    advanced_service = AdvancedSpatialService(session)
    
    try:
        if len(request.region_bounds) != 4:
            raise HTTPException(status_code=400, detail="region_bounds must contain exactly 4 values")
        
        clusters = await advanced_service.cluster_parking_spots(
            region_bounds=tuple(request.region_bounds),
            eps_km=request.cluster_distance_km,
            min_samples=request.min_samples
        )
        
        return {
            "clusters": clusters,
            "total_clusters": len(clusters),
            "region_bounds": request.region_bounds,
            "clustering_parameters": {
                "cluster_distance_km": request.cluster_distance_km,
                "min_samples": request.min_samples
            }
        }
    except Exception as e:
        logger.error(f"Spatial clustering failed: {e}")
        raise HTTPException(status_code=500, detail=f"Clustering analysis failed: {str(e)}")


@router.post("/advanced/geohash")
async def generate_geohash(
    request: GeohashRequest,
    neighbors: bool = Query(default=False, description="Include neighboring geohashes"),
    session: AsyncSession = Depends(get_db)
):
    """
    Generate geohash for location encoding and spatial indexing
    """
    advanced_service = AdvancedSpatialService(session)
    
    try:
        geohash = advanced_service.generate_geohash(
            latitude=request.location.latitude,
            longitude=request.location.longitude,
            precision=request.precision
        )
        
        result = {
            "geohash": geohash,
            "latitude": request.location.latitude,
            "longitude": request.location.longitude,
            "precision": request.precision
        }
        
        if neighbors:
            neighbor_hashes = advanced_service.get_geohash_neighbors(geohash)
            neighbor_coords = []
            
            for neighbor in neighbor_hashes:
                lat, lng = advanced_service.decode_geohash(neighbor)
                neighbor_coords.append({
                    "geohash": neighbor,
                    "latitude": lat,
                    "longitude": lng
                })
            
            result["neighbors"] = neighbor_coords
        
        return result
    except Exception as e:
        logger.error(f"Geohash generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Geohash generation failed: {str(e)}")


@router.post("/advanced/h3-index")
async def generate_h3_index(
    request: H3IndexRequest,
    neighbors: bool = Query(default=False, description="Include neighboring H3 hexagons"),
    session: AsyncSession = Depends(get_db)
):
    """
    Generate H3 hexagonal index for location
    """
    advanced_service = AdvancedSpatialService(session)
    
    try:
        h3_index = advanced_service.generate_h3_index(
            latitude=request.location.latitude,
            longitude=request.location.longitude,
            resolution=request.resolution
        )
        
        result = {
            "h3_index": h3_index,
            "latitude": request.location.latitude,
            "longitude": request.location.longitude,
            "resolution": request.resolution
        }
        
        if neighbors:
            neighbor_indices = advanced_service.get_h3_neighbors(h3_index)
            result["neighbors"] = neighbor_indices
        
        return result
    except Exception as e:
        logger.error(f"H3 index generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"H3 index generation failed: {str(e)}")


@router.post("/advanced/polygon-intersection")
async def calculate_polygon_intersection(
    request: PolygonIntersectionRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Calculate intersection between two polygons using advanced PostGIS operations
    """
    advanced_service = AdvancedSpatialService(session)
    
    try:
        intersection = await advanced_service.calculate_polygon_intersections(
            polygon1_wkt=request.polygon1_wkt,
            polygon2_wkt=request.polygon2_wkt
        )
        
        return intersection
    except Exception as e:
        logger.error(f"Polygon intersection calculation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Intersection calculation failed: {str(e)}")


@router.post("/advanced/quadtree-query")
async def query_quadtree_spatial_index(
    region_bounds: List[float] = Query(..., description="[min_lng, min_lat, max_lng, max_lat] for quadtree region"),
    query_bounds: List[float] = Query(..., description="[min_lng, min_lat, max_lng, max_lat] for query area"),
    session: AsyncSession = Depends(get_db)
):
    """
    Query spatial data using quadtree spatial partitioning
    """
    advanced_service = AdvancedSpatialService(session)
    
    try:
        if len(region_bounds) != 4 or len(query_bounds) != 4:
            raise HTTPException(status_code=400, detail="Bounds must contain exactly 4 values each")
        
        results = await advanced_service.query_quadtree_region(
            region_bounds=tuple(region_bounds),
            query_bounds=tuple(query_bounds)
        )
        
        return {
            "results": results,
            "total_points": len(results),
            "region_bounds": region_bounds,
            "query_bounds": query_bounds,
            "spatial_index": "quadtree"
        }
    except Exception as e:
        logger.error(f"Quadtree query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quadtree query failed: {str(e)}")


@router.post("/advanced/parking-allocation-optimization")
async def optimize_parking_allocation(
    demand_points: List[List[float]] = Query(..., description="List of [lat,lng] demand points"),
    supply_bounds: List[float] = Query(..., description="[min_lng, min_lat, max_lng, max_lat] supply area"),
    session: AsyncSession = Depends(get_db)
):
    """
    Optimize parking allocation using advanced spatial analysis
    """
    advanced_service = AdvancedSpatialService(session)
    
    try:
        if len(supply_bounds) != 4:
            raise HTTPException(status_code=400, detail="supply_bounds must contain exactly 4 values")
        
        demand_coords = [(lat, lng) for lat, lng in demand_points]
        
        optimization = await advanced_service.optimize_parking_allocation(
            demand_points=demand_coords,
            supply_bounds=tuple(supply_bounds)
        )
        
        return optimization
    except Exception as e:
        logger.error(f"Parking allocation optimization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Allocation optimization failed: {str(e)}")


# Enhanced PostGIS Operations

@router.post("/postgis/spatial-clustering")
async def perform_postgis_clustering(
    region_bounds: List[float] = Query(..., description="[min_lng, min_lat, max_lng, max_lat]"),
    cluster_distance_meters: int = Query(default=100, ge=10, le=1000),
    session: AsyncSession = Depends(get_db)
):
    """
    Perform spatial clustering using PostGIS ST_ClusterDBSCAN
    """
    spatial_service = SpatialService(session)
    
    try:
        if len(region_bounds) != 4:
            raise HTTPException(status_code=400, detail="region_bounds must contain exactly 4 values")
        
        clusters = await spatial_service.calculate_spatial_clustering(
            region_bounds=tuple(region_bounds),
            cluster_distance_meters=cluster_distance_meters
        )
        
        return {
            "clusters": clusters,
            "total_clusters": len(clusters),
            "clustering_method": "PostGIS ST_ClusterDBSCAN",
            "cluster_distance_meters": cluster_distance_meters
        }
    except Exception as e:
        logger.error(f"PostGIS clustering failed: {e}")
        raise HTTPException(status_code=500, detail=f"PostGIS clustering failed: {str(e)}")


@router.post("/postgis/coverage-analysis")
async def analyze_spatial_coverage(
    request: SpatialAnalysisRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Analyze spatial coverage and distribution using PostGIS
    """
    spatial_service = SpatialService(session)
    
    try:
        coverage = await spatial_service.analyze_spatial_coverage(
            center_lat=request.center_location.latitude,
            center_lng=request.center_location.longitude,
            analysis_radius_km=request.analysis_radius_km
        )
        
        result = {
            "coverage_analysis": coverage,
            "analysis_parameters": {
                "center": {
                    "latitude": request.center_location.latitude,
                    "longitude": request.center_location.longitude
                },
                "radius_km": request.analysis_radius_km
            }
        }
        
        if request.include_clustering:
            # Add clustering analysis
            analysis_bounds = [
                request.center_location.longitude - request.analysis_radius_km/111.0,
                request.center_location.latitude - request.analysis_radius_km/111.0,
                request.center_location.longitude + request.analysis_radius_km/111.0,
                request.center_location.latitude + request.analysis_radius_km/111.0
            ]
            
            clusters = await spatial_service.calculate_spatial_clustering(
                region_bounds=tuple(analysis_bounds),
                cluster_distance_meters=200
            )
            
            result["cluster_analysis"] = {
                "clusters": clusters,
                "total_clusters": len(clusters)
            }
        
        return result
    except Exception as e:
        logger.error(f"Spatial coverage analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Coverage analysis failed: {str(e)}")


@router.post("/postgis/polygon-intersect-spots")
async def find_spots_in_polygon_intersection(
    polygon1_wkt: str = Query(..., description="First polygon in WKT format"),
    polygon2_wkt: str = Query(..., description="Second polygon in WKT format"),
    session: AsyncSession = Depends(get_db)
):
    """
    Find parking spots within intersection of two polygons
    """
    spatial_service = SpatialService(session)
    
    try:
        spots = await spatial_service.find_spots_within_polygon_intersection(
            polygon1_wkt=polygon1_wkt,
            polygon2_wkt=polygon2_wkt
        )
        
        return {
            "spots": spots,
            "total_spots": len(spots),
            "polygon1_wkt": polygon1_wkt,
            "polygon2_wkt": polygon2_wkt,
            "method": "PostGIS ST_Intersection"
        }
    except Exception as e:
        logger.error(f"Polygon intersection spots search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Intersection spots search failed: {str(e)}")


@router.post("/postgis/multi-stop-route")
async def calculate_multi_stop_route(
    start_location: LocationPoint,
    destination_location: LocationPoint,
    stops: List[LocationPoint],
    session: AsyncSession = Depends(get_db)
):
    """
    Calculate optimal route through multiple stops using PostGIS
    """
    spatial_service = SpatialService(session)
    
    try:
        stop_coords = [(stop.latitude, stop.longitude) for stop in stops]
        
        route = await spatial_service.find_optimal_route_with_multiple_stops(
            start_lat=start_location.latitude,
            start_lng=start_location.longitude,
            stops=stop_coords,
            end_lat=destination_location.latitude,
            end_lng=destination_location.longitude
        )
        
        return route
    except Exception as e:
        logger.error(f"Multi-stop route calculation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Multi-stop route failed: {str(e)}")


# Background Processing

@router.post("/processing/spatial-index-rebuild")
async def rebuild_spatial_indexes(
    background_tasks: BackgroundTasks,
    region_bounds: Optional[List[float]] = Query(default=None, description="Optional region bounds"),
    session: AsyncSession = Depends(get_db)
):
    """
    Rebuild spatial indexes in background for improved performance
    """
    async def rebuild_indexes():
        try:
            advanced_service = AdvancedSpatialService(session)
            bounds = tuple(region_bounds) if region_bounds and len(region_bounds) == 4 else None
            await advanced_service.create_spatial_index(bounds)
            logger.info("Spatial indexes rebuilt successfully")
        except Exception as e:
            logger.error(f"Spatial index rebuild failed: {e}")
    
    background_tasks.add_task(rebuild_indexes)
    
    return {
        "status": "accepted",
        "message": "Spatial index rebuild started in background",
        "region_bounds": region_bounds
    }
async def search_parking_lots_nearby(
    request: ParkingLotSearchRequest,
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
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
