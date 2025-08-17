"""
Enhanced spatial configuration and utilities for the parking management system
"""
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Spatial constants and configuration
class SpatialConfig:
    """Configuration for spatial operations"""
    
    # Coordinate Systems
    WGS84_SRID = 4326  # World Geodetic System 1984
    WEB_MERCATOR_SRID = 3857  # Web Mercator for distance calculations
    
    # Default search parameters
    DEFAULT_PARKING_LOT_SEARCH_RADIUS = 1000  # meters
    DEFAULT_PARKING_SPOT_SEARCH_RADIUS = 500   # meters
    MAX_SEARCH_RADIUS = 10000  # 10km maximum search radius
    MIN_SEARCH_RADIUS = 50     # 50m minimum search radius
    
    # Geofencing parameters
    DEFAULT_GEOFENCE_CONFIDENCE = 0.8
    GEOFENCE_BUFFER_METERS = 10  # Buffer around exact boundaries
    MIN_GEOFENCE_RADIUS = 10     # meters
    MAX_GEOFENCE_RADIUS = 500    # meters
    
    # Performance optimization
    SPATIAL_INDEX_FILL_FACTOR = 70  # Fill factor for spatial indexes
    SPATIAL_CACHE_TTL = 300  # 5 minutes cache for spatial queries
    BATCH_SIZE_GEOFENCE_EVENTS = 50
    
    # Analytics refresh intervals
    ANALYTICS_REFRESH_INTERVAL = 300  # 5 minutes
    PERFORMANCE_MONITOR_INTERVAL = 900  # 15 minutes
    EVENT_CLEANUP_INTERVAL = 3600  # 1 hour
    EVENT_RETENTION_DAYS = 7
    
    # Distance calculation settings
    AVERAGE_CITY_SPEED_KMH = 25  # for time estimation
    WALKING_SPEED_KMH = 5  # for walking time estimation


class DistanceUnit(Enum):
    """Distance measurement units"""
    METERS = "meters"
    KILOMETERS = "kilometers"
    FEET = "feet"
    MILES = "miles"


class GeofenceEventType(Enum):
    """Types of geofence events"""
    ENTRY = "geofence_entry"
    EXIT = "geofence_exit"
    SPOT_OCCUPIED = "spot_occupied"
    SPOT_VACATED = "spot_vacated"
    RESERVATION_START = "reservation_start"
    RESERVATION_END = "reservation_end"
    VIOLATION_DETECTED = "violation_detected"
    MAINTENANCE_REQUIRED = "maintenance_required"


class DetectionMethod(Enum):
    """Methods for detecting vehicle presence"""
    GPS = "gps"
    SENSOR = "sensor"
    MANUAL = "manual"
    QR_CODE = "qr_code"
    LICENSE_PLATE = "license_plate"
    BLUETOOTH = "bluetooth"
    RFID = "rfid"


@dataclass
class SpatialBounds:
    """Represents a rectangular spatial boundary"""
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float
    
    def contains_point(self, latitude: float, longitude: float) -> bool:
        """Check if a point is within these bounds"""
        return (self.min_latitude <= latitude <= self.max_latitude and
                self.min_longitude <= longitude <= self.max_longitude)
    
    def expand(self, margin_degrees: float):
        """Expand bounds by a margin in degrees"""
        self.min_latitude -= margin_degrees
        self.max_latitude += margin_degrees
        self.min_longitude -= margin_degrees
        self.max_longitude += margin_degrees


@dataclass
class SpatialPoint:
    """Represents a geographic point"""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy_meters: Optional[float] = None
    timestamp: Optional[str] = None
    
    def to_wkt(self) -> str:
        """Convert to Well-Known Text format"""
        if self.altitude is not None:
            return f"POINT Z({self.longitude} {self.latitude} {self.altitude})"
        return f"POINT({self.longitude} {self.latitude})"


class SpatialUtils:
    """Utility functions for spatial operations"""
    
    @staticmethod
    def degrees_to_meters(degrees: float, latitude: float) -> float:
        """
        Convert degrees to meters at a given latitude
        
        Args:
            degrees: Degrees to convert
            latitude: Latitude for calculation (affects longitude conversion)
            
        Returns:
            Distance in meters
        """
        import math
        
        # Earth's radius in meters
        earth_radius = 6378137.0
        
        # Convert latitude degrees to meters (constant)
        lat_meters = degrees * (math.pi / 180.0) * earth_radius
        
        # Convert longitude degrees to meters (varies by latitude)
        lng_meters = degrees * (math.pi / 180.0) * earth_radius * math.cos(math.radians(latitude))
        
        return math.sqrt(lat_meters**2 + lng_meters**2)
    
    @staticmethod
    def meters_to_degrees(meters: float, latitude: float) -> float:
        """
        Convert meters to degrees at a given latitude
        
        Args:
            meters: Meters to convert
            latitude: Latitude for calculation
            
        Returns:
            Distance in degrees
        """
        import math
        
        # Earth's radius in meters
        earth_radius = 6378137.0
        
        # Convert to degrees
        degrees = meters / (earth_radius * math.cos(math.radians(latitude))) * (180.0 / math.pi)
        
        return degrees
    
    @staticmethod
    def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate the great circle distance between two points using Haversine formula
        
        Args:
            lat1, lng1: First point coordinates
            lat2, lng2: Second point coordinates
            
        Returns:
            Distance in meters
        """
        import math
        
        # Earth's radius in meters
        R = 6378137.0
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        # Differences
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        # Haversine formula
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    @staticmethod
    def bearing_between_points(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate the bearing (direction) from point 1 to point 2
        
        Args:
            lat1, lng1: Starting point coordinates
            lat2, lng2: Ending point coordinates
            
        Returns:
            Bearing in degrees (0-360)
        """
        import math
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlng_rad = math.radians(lng2 - lng1)
        
        y = math.sin(dlng_rad) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlng_rad)
        
        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)
        
        return (bearing_deg + 360) % 360
    
    @staticmethod
    def point_in_circle(point_lat: float, point_lng: float, 
                       center_lat: float, center_lng: float, radius_meters: float) -> bool:
        """
        Check if a point is within a circular area
        
        Args:
            point_lat, point_lng: Point to check
            center_lat, center_lng: Circle center
            radius_meters: Circle radius in meters
            
        Returns:
            True if point is within circle
        """
        distance = SpatialUtils.haversine_distance(point_lat, point_lng, center_lat, center_lng)
        return distance <= radius_meters
    
    @staticmethod
    def create_bounding_box(center_lat: float, center_lng: float, radius_meters: float) -> SpatialBounds:
        """
        Create a bounding box around a center point
        
        Args:
            center_lat, center_lng: Center point
            radius_meters: Radius in meters
            
        Returns:
            SpatialBounds object
        """
        # Approximate conversion (good enough for bounding box)
        lat_delta = radius_meters / 111320.0  # meters per degree latitude
        lng_delta = radius_meters / (111320.0 * abs(math.cos(math.radians(center_lat))))
        
        return SpatialBounds(
            min_latitude=center_lat - lat_delta,
            max_latitude=center_lat + lat_delta,
            min_longitude=center_lng - lng_delta,
            max_longitude=center_lng + lng_delta
        )
    
    @staticmethod
    def convert_distance(value: float, from_unit: DistanceUnit, to_unit: DistanceUnit) -> float:
        """
        Convert distance between different units
        
        Args:
            value: Distance value
            from_unit: Source unit
            to_unit: Target unit
            
        Returns:
            Converted distance
        """
        # Convert to meters first
        meters = value
        if from_unit == DistanceUnit.KILOMETERS:
            meters = value * 1000
        elif from_unit == DistanceUnit.FEET:
            meters = value * 0.3048
        elif from_unit == DistanceUnit.MILES:
            meters = value * 1609.344
        
        # Convert from meters to target unit
        if to_unit == DistanceUnit.METERS:
            return meters
        elif to_unit == DistanceUnit.KILOMETERS:
            return meters / 1000
        elif to_unit == DistanceUnit.FEET:
            return meters / 0.3048
        elif to_unit == DistanceUnit.MILES:
            return meters / 1609.344
        
        return meters


class SpatialQueries:
    """Pre-defined spatial SQL queries for common operations"""
    
    # Optimized nearest neighbor query
    NEAREST_LOTS_QUERY = """
        SELECT 
            id, name, available_spots, total_spots, base_hourly_rate,
            ST_Distance(
                ST_Transform(location, 3857),
                ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 3857)
            ) as distance_meters,
            ST_Y(ST_Transform(location, 4326)) as latitude,
            ST_X(ST_Transform(location, 4326)) as longitude
        FROM parking_lots
        WHERE 
            status = 'active'
            AND ST_DWithin(
                ST_Transform(location, 3857),
                ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 3857),
                %s
            )
        ORDER BY location <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        LIMIT %s
    """
    
    # Spatial clustering query
    DENSITY_CLUSTER_QUERY = """
        SELECT 
            ST_ClusterKMeans(location, %s) OVER() as cluster_id,
            id, name, total_spots, available_spots,
            ST_Y(ST_Transform(location, 4326)) as latitude,
            ST_X(ST_Transform(location, 4326)) as longitude
        FROM parking_lots
        WHERE status = 'active'
    """
    
    # Polygon intersection query
    POLYGON_INTERSECTION_QUERY = """
        SELECT 
            ps.id, ps.spot_number, ps.status, ps.spot_type,
            ST_Y(ST_Transform(ps.location, 4326)) as latitude,
            ST_X(ST_Transform(ps.location, 4326)) as longitude
        FROM parking_spots ps
        WHERE 
            ps.location IS NOT NULL
            AND ST_Intersects(ps.location, ST_GeomFromText(%s, 4326))
            AND (%s IS NULL OR ps.status = ANY(%s))
    """


# Spatial configuration singleton
spatial_config = SpatialConfig()
spatial_utils = SpatialUtils()
spatial_queries = SpatialQueries()
