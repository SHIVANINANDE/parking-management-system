"""
Spatial service for geospatial operations and location-based queries
Enhanced with advanced PostGIS operations and geofencing algorithms
"""
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_, or_
from geoalchemy2 import WKTElement
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_Contains, ST_Buffer, ST_Transform, ST_MakePoint, ST_SetSRID
from decimal import Decimal
import json
import logging

from app.models.parking_lot import ParkingLot, ParkingLotStatus
from app.models.parking_spot import ParkingSpot, SpotStatus, SpotType
from app.models.vehicle import Vehicle

logger = logging.getLogger(__name__)


class SpatialService:
    """Service for handling spatial queries and geolocation operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def find_parking_lots_within_radius(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 1000,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find parking lots within a specified radius of a location
        
        Args:
            latitude: Search location latitude
            longitude: Search location longitude
            radius_meters: Search radius in meters (default 1000)
            limit: Maximum number of results (default 20)
            
        Returns:
            List of parking lots with distance and availability info
        """
        query = text("""
            SELECT * FROM find_parking_lots_within_radius(:lat, :lng, :radius)
            LIMIT :limit
        """)
        
        result = await self.session.execute(
            query,
            {
                "lat": latitude,
                "lng": longitude,
                "radius": radius_meters,
                "limit": limit
            }
        )
        
        return [dict(row._mapping) for row in result]
    
    async def find_available_spots_within_radius(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 500,
        spot_type: Optional[str] = None,
        requires_ev_charging: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find available parking spots within a specified radius
        
        Args:
            latitude: Search location latitude
            longitude: Search location longitude
            radius_meters: Search radius in meters (default 500)
            spot_type: Filter by spot type (optional)
            requires_ev_charging: Filter for EV charging spots
            limit: Maximum number of results (default 50)
            
        Returns:
            List of available parking spots with distance info
        """
        query = text("""
            SELECT * FROM find_available_spots_within_radius(
                :lat, :lng, :radius, :spot_type, :requires_ev_charging
            )
            LIMIT :limit
        """)
        
        result = await self.session.execute(
            query,
            {
                "lat": latitude,
                "lng": longitude,
                "radius": radius_meters,
                "spot_type": spot_type,
                "requires_ev_charging": requires_ev_charging,
                "limit": limit
            }
        )
        
        return [dict(row._mapping) for row in result]
    
    async def find_optimal_parking_spot(
        self,
        user_latitude: float,
        user_longitude: float,
        vehicle_id: int,
        preferred_lot_id: Optional[int] = None,
        max_distance_meters: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Find optimal parking spot based on vehicle compatibility and distance
        
        Args:
            user_latitude: User's current latitude
            user_longitude: User's current longitude
            vehicle_id: Vehicle ID for compatibility checking
            preferred_lot_id: Preferred parking lot ID (optional)
            max_distance_meters: Maximum search distance (default 1000)
            
        Returns:
            List of compatible parking spots ranked by optimization score
        """
        query = text("""
            SELECT * FROM find_optimal_parking_spot(
                :lat, :lng, :vehicle_id, :lot_id, :max_distance
            )
        """)
        
        result = await self.session.execute(
            query,
            {
                "lat": user_latitude,
                "lng": user_longitude,
                "vehicle_id": vehicle_id,
                "lot_id": preferred_lot_id,
                "max_distance": max_distance_meters
            }
        )
        
        return [dict(row._mapping) for row in result]
    
    async def is_point_in_parking_lot(
        self,
        latitude: float,
        longitude: float,
        lot_id: int
    ) -> bool:
        """
        Check if a GPS coordinate is within a parking lot's boundaries
        
        Args:
            latitude: Point latitude to check
            longitude: Point longitude to check
            lot_id: Parking lot ID
            
        Returns:
            True if point is within lot boundaries, False otherwise
        """
        query = text("""
            SELECT is_point_in_parking_lot(:lat, :lng, :lot_id) as is_inside
        """)
        
        result = await self.session.execute(
            query,
            {"lat": latitude, "lng": longitude, "lot_id": lot_id}
        )
        
        row = result.first()
        return row.is_inside if row else False
    
    async def calculate_distance_between_points(
        self,
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float
    ) -> float:
        """
        Calculate distance between two GPS coordinates in meters
        
        Args:
            lat1, lng1: First point coordinates
            lat2, lng2: Second point coordinates
            
        Returns:
            Distance in meters
        """
        query = text("""
            SELECT ST_Distance(
                ST_Transform(ST_SetSRID(ST_MakePoint(:lng1, :lat1), 4326), 3857),
                ST_Transform(ST_SetSRID(ST_MakePoint(:lng2, :lat2), 4326), 3857)
            ) as distance_meters
        """)
        
        result = await self.session.execute(
            query,
            {"lat1": lat1, "lng1": lng1, "lat2": lat2, "lng2": lng2}
        )
        
        row = result.first()
        return float(row.distance_meters) if row else 0.0
    
    async def get_parking_density_in_area(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 1000
    ) -> Dict[str, Any]:
        """
        Get parking density statistics for an area
        
        Args:
            latitude: Center point latitude
            longitude: Center point longitude
            radius_meters: Area radius in meters
            
        Returns:
            Dictionary with density statistics
        """
        query = text("""
            SELECT 
                COUNT(pl.id) as total_lots,
                SUM(pl.total_spots) as total_spots,
                SUM(pl.available_spots) as available_spots,
                AVG(pl.base_hourly_rate) as avg_hourly_rate,
                (SUM(pl.available_spots)::FLOAT / NULLIF(SUM(pl.total_spots), 0)) * 100 as availability_percentage
            FROM parking_lots pl
            WHERE 
                pl.status = 'active'
                AND ST_DWithin(
                    ST_Transform(pl.location, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 3857),
                    :radius
                )
        """)
        
        result = await self.session.execute(
            query,
            {"lat": latitude, "lng": longitude, "radius": radius_meters}
        )
        
        row = result.first()
        if row:
            return {
                "total_lots": row.total_lots or 0,
                "total_spots": row.total_spots or 0,
                "available_spots": row.available_spots or 0,
                "avg_hourly_rate": float(row.avg_hourly_rate) if row.avg_hourly_rate else 0.0,
                "availability_percentage": float(row.availability_percentage) if row.availability_percentage else 0.0
            }
        
        return {
            "total_lots": 0,
            "total_spots": 0,
            "available_spots": 0,
            "avg_hourly_rate": 0.0,
            "availability_percentage": 0.0
        }
    
    async def find_nearest_parking_lot(
        self,
        latitude: float,
        longitude: float,
        filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find the nearest parking lot to a location
        
        Args:
            latitude: Search location latitude
            longitude: Search location longitude
            filters: Optional filters (has_ev_charging, min_available_spots, etc.)
            
        Returns:
            Nearest parking lot info or None if not found
        """
        lots = await self.find_parking_lots_within_radius(
            latitude, longitude, radius_meters=5000, limit=1
        )
        
        if not lots:
            return None
        
        lot = lots[0]
        
        # Apply filters if specified
        if filters:
            if filters.get("has_ev_charging") and not lot.get("has_ev_charging"):
                return None
            if filters.get("min_available_spots", 0) > lot.get("available_spots", 0):
                return None
        
        return lot
    
    async def create_geofence_polygon(
        self,
        center_lat: float,
        center_lng: float,
        radius_meters: int
    ) -> str:
        """
        Create a circular geofence polygon around a point
        
        Args:
            center_lat: Center latitude
            center_lng: Center longitude
            radius_meters: Radius in meters
            
        Returns:
            WKT string of the polygon
        """
        query = text("""
            SELECT ST_AsText(
                ST_Transform(
                    ST_Buffer(
                        ST_Transform(ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 3857),
                        :radius
                    ),
                    4326
                )
            ) as geofence_wkt
        """)
        
        result = await self.session.execute(
            query,
            {"lat": center_lat, "lng": center_lng, "radius": radius_meters}
        )
        
        row = result.first()
        return row.geofence_wkt if row else ""
    
    async def get_spots_in_polygon(
        self,
        polygon_wkt: str,
        status_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all parking spots within a polygon boundary
        
        Args:
            polygon_wkt: Well-Known Text representation of polygon
            status_filter: Optional list of statuses to filter by
            
        Returns:
            List of parking spots within the polygon
        """
        status_condition = ""
        if status_filter:
            status_list = "', '".join(status_filter)
            status_condition = f"AND ps.status IN ('{status_list}')"
        
        query = text(f"""
            SELECT 
                ps.id,
                ps.spot_number,
                ps.spot_type,
                ps.status,
                ps.parking_lot_id,
                ST_Y(ST_Transform(ps.location, 4326)) as latitude,
                ST_X(ST_Transform(ps.location, 4326)) as longitude
            FROM parking_spots ps
            WHERE 
                ps.location IS NOT NULL
                AND ST_Contains(
                    ST_GeomFromText(:polygon_wkt, 4326),
                    ps.location
                )
                {status_condition}
        """)
        
        result = await self.session.execute(
            query,
            {"polygon_wkt": polygon_wkt}
        )
        
        return [dict(row._mapping) for row in result]
    
    async def get_route_to_parking_spot(
        self,
        from_lat: float,
        from_lng: float,
        to_spot_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get basic route information to a parking spot
        
        Args:
            from_lat: Starting latitude
            from_lng: Starting longitude
            to_spot_id: Target parking spot ID
            
        Returns:
            Basic route information (distance, estimated time)
        """
        # Get spot location
        query = text("""
            SELECT 
                ST_Y(ST_Transform(ps.location, 4326)) as spot_lat,
                ST_X(ST_Transform(ps.location, 4326)) as spot_lng,
                pl.name as lot_name,
                ps.spot_number
            FROM parking_spots ps
            JOIN parking_lots pl ON ps.parking_lot_id = pl.id
            WHERE ps.id = :spot_id
        """)
        
        result = await self.session.execute(query, {"spot_id": to_spot_id})
        row = result.first()
        
        if not row:
            return None
        
        # Calculate distance
        distance = await self.calculate_distance_between_points(
            from_lat, from_lng, row.spot_lat, row.spot_lng
        )
        
        # Estimate travel time (assuming average city speed of 25 km/h)
        estimated_time_minutes = (distance / 1000) * (60 / 25)  # Convert to minutes
        
        return {
            "spot_id": to_spot_id,
            "spot_number": row.spot_number,
            "lot_name": row.lot_name,
            "distance_meters": distance,
            "estimated_time_minutes": round(estimated_time_minutes, 1),
            "destination_lat": float(row.spot_lat),
            "destination_lng": float(row.spot_lng)
        }
    
    async def create_buffer_zone(self, center_lat: float, center_lng: float, 
                               radius_meters: int, buffer_meters: int = 50) -> str:
        """
        Create a buffer zone around a point for enhanced geofencing
        
        Args:
            center_lat: Center latitude
            center_lng: Center longitude
            radius_meters: Primary radius in meters
            buffer_meters: Additional buffer in meters
            
        Returns:
            WKT string of buffered polygon
        """
        query = text("""
            SELECT ST_AsText(
                ST_Transform(
                    ST_Buffer(
                        ST_Buffer(
                            ST_Transform(ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 3857),
                            :radius
                        ),
                        :buffer
                    ),
                    4326
                )
            ) as buffered_geofence_wkt
        """)
        
        result = await self.session.execute(
            query,
            {
                "lat": center_lat, 
                "lng": center_lng, 
                "radius": radius_meters,
                "buffer": buffer_meters
            }
        )
        
        row = result.first()
        return row.buffered_geofence_wkt if row else ""
    
    async def find_spots_within_polygon_intersection(self, polygon1_wkt: str, 
                                                   polygon2_wkt: str) -> List[Dict[str, Any]]:
        """
        Find parking spots within intersection of two polygons
        
        Args:
            polygon1_wkt: First polygon in WKT format
            polygon2_wkt: Second polygon in WKT format
            
        Returns:
            List of parking spots in intersection area
        """
        query = text("""
            WITH intersection AS (
                SELECT ST_Intersection(
                    ST_GeomFromText(:poly1_wkt, 4326),
                    ST_GeomFromText(:poly2_wkt, 4326)
                ) as intersect_geom
            )
            SELECT 
                ps.id,
                ps.spot_number,
                ps.spot_type,
                ps.status,
                ps.parking_lot_id,
                pl.name as lot_name,
                ST_Y(ST_Transform(ps.location, 4326)) as latitude,
                ST_X(ST_Transform(ps.location, 4326)) as longitude
            FROM parking_spots ps
            JOIN parking_lots pl ON ps.parking_lot_id = pl.id
            CROSS JOIN intersection
            WHERE 
                ps.location IS NOT NULL
                AND ST_Contains(intersection.intersect_geom, ps.location)
        """)
        
        result = await self.session.execute(
            query,
            {"poly1_wkt": polygon1_wkt, "poly2_wkt": polygon2_wkt}
        )
        
        return [dict(row._mapping) for row in result]
    
    async def calculate_spatial_clustering(self, region_bounds: Tuple[float, float, float, float],
                                         cluster_distance_meters: int = 100) -> List[Dict[str, Any]]:
        """
        Calculate spatial clustering of parking spots using PostGIS
        
        Args:
            region_bounds: (min_lng, min_lat, max_lng, max_lat) boundary
            cluster_distance_meters: Maximum distance for clustering
            
        Returns:
            List of spatial clusters with statistics
        """
        min_lng, min_lat, max_lng, max_lat = region_bounds
        
        query = text("""
            WITH clustered_spots AS (
                SELECT 
                    ps.id,
                    ps.spot_type,
                    ps.status,
                    ST_ClusterDBSCAN(ps.location, eps => :cluster_distance, minpoints => 3) 
                        OVER() AS cluster_id,
                    ST_Y(ST_Transform(ps.location, 4326)) as latitude,
                    ST_X(ST_Transform(ps.location, 4326)) as longitude
                FROM parking_spots ps
                WHERE ps.location IS NOT NULL
                AND ST_Within(
                    ps.location,
                    ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
                )
            )
            SELECT 
                cluster_id,
                COUNT(*) as total_spots,
                COUNT(CASE WHEN status = 'available' THEN 1 END) as available_spots,
                AVG(latitude) as center_latitude,
                AVG(longitude) as center_longitude,
                array_agg(DISTINCT spot_type) as spot_types,
                MIN(latitude) as min_lat,
                MAX(latitude) as max_lat,
                MIN(longitude) as min_lng,
                MAX(longitude) as max_lng
            FROM clustered_spots
            WHERE cluster_id IS NOT NULL
            GROUP BY cluster_id
            ORDER BY total_spots DESC
        """)
        
        result = await self.session.execute(
            query,
            {
                "cluster_distance": cluster_distance_meters,
                "min_lng": min_lng,
                "min_lat": min_lat,
                "max_lng": max_lng,
                "max_lat": max_lat
            }
        )
        
        clusters = []
        for row in result:
            occupancy_rate = 0.0
            if row.total_spots > 0:
                occupancy_rate = ((row.total_spots - row.available_spots) / row.total_spots) * 100
            
            clusters.append({
                "cluster_id": row.cluster_id,
                "total_spots": row.total_spots,
                "available_spots": row.available_spots,
                "occupancy_rate": round(occupancy_rate, 2),
                "center_latitude": float(row.center_latitude),
                "center_longitude": float(row.center_longitude),
                "spot_types": row.spot_types,
                "bounds": {
                    "min_latitude": float(row.min_lat),
                    "max_latitude": float(row.max_lat),
                    "min_longitude": float(row.min_lng),
                    "max_longitude": float(row.max_lng)
                }
            })
        
        return clusters
    
    async def find_optimal_route_with_multiple_stops(self, start_lat: float, start_lng: float,
                                                   stops: List[Tuple[float, float]],
                                                   end_lat: float, end_lng: float) -> Dict[str, Any]:
        """
        Find optimal route through multiple parking lot stops using PostGIS
        
        Args:
            start_lat: Starting latitude
            start_lng: Starting longitude
            stops: List of (lat, lng) stops to visit
            end_lat: Ending latitude
            end_lng: Ending longitude
            
        Returns:
            Optimized route information
        """
        if not stops:
            return await self.get_route_to_parking_spot_by_coords(start_lat, start_lng, end_lat, end_lng)
        
        # Create points for all locations
        all_points = [(start_lat, start_lng)] + stops + [(end_lat, end_lng)]
        
        # Calculate distance matrix
        query = text("""
            WITH points AS (
                SELECT 
                    generate_series(0, :num_points - 1) as point_id,
                    unnest(array[:point_coords]) as coords
            ),
            point_geoms AS (
                SELECT 
                    point_id,
                    ST_SetSRID(ST_MakePoint(
                        split_part(coords, ',', 2)::float,
                        split_part(coords, ',', 1)::float
                    ), 4326) as geom
                FROM points
            )
            SELECT 
                p1.point_id as from_id,
                p2.point_id as to_id,
                ST_Distance(
                    ST_Transform(p1.geom, 3857),
                    ST_Transform(p2.geom, 3857)
                ) as distance_meters
            FROM point_geoms p1
            CROSS JOIN point_geoms p2
            WHERE p1.point_id != p2.point_id
            ORDER BY p1.point_id, p2.point_id
        """)
        
        # Format coordinates for query
        point_coords = [f"{lat},{lng}" for lat, lng in all_points]
        
        result = await self.session.execute(
            query,
            {
                "num_points": len(all_points),
                "point_coords": point_coords
            }
        )
        
        # Build distance matrix
        distances = {}
        for row in result:
            distances[(row.from_id, row.to_id)] = row.distance_meters
        
        # Simple greedy TSP approximation for optimal order
        unvisited = set(range(1, len(all_points) - 1))  # Exclude start and end
        current = 0  # Start point
        route_order = [current]
        total_distance = 0
        
        while unvisited:
            nearest = min(unvisited, key=lambda x: distances.get((current, x), float('inf')))
            total_distance += distances.get((current, nearest), 0)
            route_order.append(nearest)
            unvisited.remove(nearest)
            current = nearest
        
        # Add final leg to end point
        route_order.append(len(all_points) - 1)
        total_distance += distances.get((current, len(all_points) - 1), 0)
        
        # Build route details
        route_legs = []
        for i in range(len(route_order) - 1):
            from_idx = route_order[i]
            to_idx = route_order[i + 1]
            from_point = all_points[from_idx]
            to_point = all_points[to_idx]
            
            route_legs.append({
                "from_latitude": from_point[0],
                "from_longitude": from_point[1],
                "to_latitude": to_point[0],
                "to_longitude": to_point[1],
                "distance_meters": distances.get((from_idx, to_idx), 0),
                "leg_number": i + 1
            })
        
        return {
            "total_distance_meters": total_distance,
            "estimated_time_minutes": round(total_distance / 1000 * 3, 1),  # 3 min per km
            "route_order": route_order,
            "route_legs": route_legs,
            "optimized": True
        }
    
    async def get_route_to_parking_spot_by_coords(self, from_lat: float, from_lng: float,
                                                to_lat: float, to_lng: float) -> Dict[str, Any]:
        """
        Get route between two coordinates
        
        Args:
            from_lat: Starting latitude
            from_lng: Starting longitude
            to_lat: Destination latitude
            to_lng: Destination longitude
            
        Returns:
            Route information
        """
        distance = await self.calculate_distance_between_points(from_lat, from_lng, to_lat, to_lng)
        estimated_time_minutes = (distance / 1000) * (60 / 25)  # 25 km/h average
        
        return {
            "distance_meters": distance,
            "estimated_time_minutes": round(estimated_time_minutes, 1),
            "destination_lat": to_lat,
            "destination_lng": to_lng
        }
    
    async def analyze_spatial_coverage(self, center_lat: float, center_lng: float,
                                     analysis_radius_km: float = 5.0) -> Dict[str, Any]:
        """
        Analyze spatial coverage and distribution of parking infrastructure
        
        Args:
            center_lat: Analysis center latitude
            center_lng: Analysis center longitude
            analysis_radius_km: Analysis radius in kilometers
            
        Returns:
            Spatial coverage analysis
        """
        query = text("""
            WITH analysis_area AS (
                SELECT ST_Buffer(
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 3857),
                    :radius_m
                ) as area_geom
            ),
            coverage_analysis AS (
                SELECT 
                    COUNT(DISTINCT pl.id) as total_lots,
                    COUNT(ps.id) as total_spots,
                    COUNT(CASE WHEN ps.status = 'available' THEN 1 END) as available_spots,
                    AVG(ST_Distance(
                        ST_Transform(ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 3857),
                        ST_Transform(pl.location, 3857)
                    )) as avg_distance_to_center,
                    MIN(ST_Distance(
                        ST_Transform(ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 3857),
                        ST_Transform(pl.location, 3857)
                    )) as min_distance_to_center,
                    MAX(ST_Distance(
                        ST_Transform(ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 3857),
                        ST_Transform(pl.location, 3857)
                    )) as max_distance_to_center,
                    ST_Area(ST_ConvexHull(ST_Collect(pl.location))) / ST_Area(aa.area_geom) * 100 as coverage_percentage
                FROM parking_lots pl
                JOIN parking_spots ps ON ps.parking_lot_id = pl.id
                CROSS JOIN analysis_area aa
                WHERE 
                    pl.status = 'active'
                    AND ST_Within(ST_Transform(pl.location, 3857), aa.area_geom)
            ),
            quadrant_analysis AS (
                SELECT 
                    CASE 
                        WHEN ST_X(ST_Transform(pl.location, 4326)) >= :lng AND ST_Y(ST_Transform(pl.location, 4326)) >= :lat THEN 'NE'
                        WHEN ST_X(ST_Transform(pl.location, 4326)) < :lng AND ST_Y(ST_Transform(pl.location, 4326)) >= :lat THEN 'NW'
                        WHEN ST_X(ST_Transform(pl.location, 4326)) >= :lng AND ST_Y(ST_Transform(pl.location, 4326)) < :lat THEN 'SE'
                        ELSE 'SW'
                    END as quadrant,
                    COUNT(pl.id) as lots_count,
                    SUM(pl.total_spots) as spots_count
                FROM parking_lots pl
                CROSS JOIN analysis_area aa
                WHERE 
                    pl.status = 'active'
                    AND ST_Within(ST_Transform(pl.location, 3857), aa.area_geom)
                GROUP BY quadrant
            )
            SELECT 
                ca.*,
                json_object_agg(qa.quadrant, json_build_object(
                    'lots_count', qa.lots_count,
                    'spots_count', qa.spots_count
                )) as quadrant_distribution
            FROM coverage_analysis ca
            CROSS JOIN quadrant_analysis qa
            GROUP BY ca.total_lots, ca.total_spots, ca.available_spots, 
                     ca.avg_distance_to_center, ca.min_distance_to_center, 
                     ca.max_distance_to_center, ca.coverage_percentage
        """)
        
        result = await self.session.execute(
            query,
            {
                "lat": center_lat,
                "lng": center_lng,
                "radius_m": analysis_radius_km * 1000
            }
        )
        
        row = result.first()
        if row:
            return {
                "analysis_center": {"latitude": center_lat, "longitude": center_lng},
                "analysis_radius_km": analysis_radius_km,
                "total_lots": row.total_lots or 0,
                "total_spots": row.total_spots or 0,
                "available_spots": row.available_spots or 0,
                "occupancy_rate": ((row.total_spots - row.available_spots) / max(row.total_spots, 1)) * 100,
                "coverage_percentage": float(row.coverage_percentage) if row.coverage_percentage else 0.0,
                "distance_stats": {
                    "avg_distance_to_center_m": float(row.avg_distance_to_center) if row.avg_distance_to_center else 0.0,
                    "min_distance_to_center_m": float(row.min_distance_to_center) if row.min_distance_to_center else 0.0,
                    "max_distance_to_center_m": float(row.max_distance_to_center) if row.max_distance_to_center else 0.0
                },
                "quadrant_distribution": row.quadrant_distribution or {}
            }
        
        return {
            "analysis_center": {"latitude": center_lat, "longitude": center_lng},
            "analysis_radius_km": analysis_radius_km,
            "total_lots": 0,
            "total_spots": 0,
            "available_spots": 0,
            "occupancy_rate": 0.0,
            "coverage_percentage": 0.0,
            "distance_stats": {
                "avg_distance_to_center_m": 0.0,
                "min_distance_to_center_m": 0.0,
                "max_distance_to_center_m": 0.0
            },
            "quadrant_distribution": {}
        }


class GeofenceService:
    """Service for handling geofencing operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def check_vehicle_in_lot(
        self,
        vehicle_lat: float,
        vehicle_lng: float,
        lot_id: int,
        confidence_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Check if a vehicle is within a parking lot's geofence
        
        Args:
            vehicle_lat: Vehicle's current latitude
            vehicle_lng: Vehicle's current longitude
            lot_id: Parking lot ID to check
            confidence_threshold: Minimum confidence score for positive detection
            
        Returns:
            Dictionary with detection results
        """
        # Check if point is in lot boundary
        query = text("""
            SELECT 
                is_point_in_parking_lot(:lat, :lng, :lot_id) as is_inside,
                ST_Distance(
                    ST_Transform(pl.location, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 3857)
                ) as distance_to_center
            FROM parking_lots pl
            WHERE pl.id = :lot_id
        """)
        
        result = await self.session.execute(
            query,
            {"lat": vehicle_lat, "lng": vehicle_lng, "lot_id": lot_id}
        )
        
        row = result.first()
        if not row:
            return {"is_inside": False, "confidence": 0.0, "distance_to_center": None}
        
        # Calculate confidence based on distance to center
        distance = float(row.distance_to_center) if row.distance_to_center else 1000
        confidence = max(0.0, min(1.0, 1.0 - (distance / 500)))  # 500m max distance for confidence
        
        return {
            "is_inside": row.is_inside,
            "confidence": confidence,
            "distance_to_center": distance,
            "meets_threshold": confidence >= confidence_threshold
        }
    
    async def log_geofence_event(
        self,
        event_type: str,
        parking_lot_id: int,
        vehicle_lat: float,
        vehicle_lng: float,
        vehicle_id: Optional[int] = None,
        user_id: Optional[int] = None,
        reservation_id: Optional[int] = None,
        confidence_score: Optional[float] = None,
        detection_method: str = "gps",
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log a geofence event
        
        Args:
            event_type: Type of event (entry, exit, etc.)
            parking_lot_id: Parking lot ID
            vehicle_lat: Vehicle latitude
            vehicle_lng: Vehicle longitude
            vehicle_id: Vehicle ID (optional)
            user_id: User ID (optional)
            reservation_id: Reservation ID (optional)
            confidence_score: Detection confidence (optional)
            detection_method: How the event was detected
            metadata: Additional event data
            
        Returns:
            ID of created event record
        """
        query = text("""
            INSERT INTO parking_events (
                event_type, parking_lot_id, parking_spot_id, vehicle_id, user_id, 
                reservation_id, location, event_timestamp, confidence_score, 
                detection_method, metadata, processed
            ) VALUES (
                :event_type, :parking_lot_id, NULL, :vehicle_id, :user_id,
                :reservation_id, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 
                NOW(), :confidence_score, :detection_method, :metadata, FALSE
            ) RETURNING id
        """)
        
        result = await self.session.execute(
            query,
            {
                "event_type": event_type,
                "parking_lot_id": parking_lot_id,
                "vehicle_id": vehicle_id,
                "user_id": user_id,
                "reservation_id": reservation_id,
                "lat": vehicle_lat,
                "lng": vehicle_lng,
                "confidence_score": confidence_score,
                "detection_method": detection_method,
                "metadata": json.dumps(metadata) if metadata else None
            }
        )
        
        row = result.first()
        await self.session.commit()
        
        return row.id if row else None
    
    async def get_unprocessed_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get unprocessed geofence events for background processing
        
        Args:
            limit: Maximum number of events to retrieve
            
        Returns:
            List of unprocessed events
        """
        query = text("""
            SELECT 
                id, event_type, parking_lot_id, parking_spot_id, vehicle_id, 
                user_id, reservation_id, 
                ST_Y(ST_Transform(location, 4326)) as latitude,
                ST_X(ST_Transform(location, 4326)) as longitude,
                event_timestamp, confidence_score, detection_method, metadata
            FROM parking_events
            WHERE processed = FALSE
            ORDER BY event_timestamp ASC
            LIMIT :limit
        """)
        
        result = await self.session.execute(query, {"limit": limit})
        return [dict(row._mapping) for row in result]
    
    async def mark_event_processed(self, event_id: int) -> bool:
        """
        Mark a geofence event as processed
        
        Args:
            event_id: Event ID to mark as processed
            
        Returns:
            True if successful, False otherwise
        """
        query = text("""
            UPDATE parking_events 
            SET processed = TRUE 
            WHERE id = :event_id
        """)
        
        result = await self.session.execute(query, {"event_id": event_id})
        await self.session.commit()
        
        return result.rowcount > 0