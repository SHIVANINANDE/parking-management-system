"""
Advanced Spatial Algorithms Service for Smart Parking Management

This service implements sophisticated spatial algorithms for:
- A* pathfinding for optimal parking routes
- Quadtree spatial partitioning for efficient location queries
- Geohashing for location encoding and clustering
- Advanced PostGIS operations for geospatial analysis
- OSRM integration for real-world routing
"""

import json
import logging
import math
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import heapq

import numpy as np
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
import geohash2
import h3
import networkx as nx
from rtree import index
from sklearn.cluster import DBSCAN
from geopy.distance import geodesic
import osrm

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_AsText, ST_GeomFromText


logger = logging.getLogger(__name__)


@dataclass
class SpatialPoint:
    """Represents a spatial point with metadata"""
    latitude: float
    longitude: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.longitude, self.latitude)
    
    def distance_to(self, other: 'SpatialPoint') -> float:
        """Calculate distance to another point in meters"""
        return geodesic((self.latitude, self.longitude), 
                       (other.latitude, other.longitude)).meters


@dataclass  
class QuadTreeNode:
    """Node in quadtree spatial index"""
    bounds: Tuple[float, float, float, float]  # min_x, min_y, max_x, max_y
    max_capacity: int = 10
    max_depth: int = 10
    depth: int = 0
    points: List[SpatialPoint] = None
    children: List['QuadTreeNode'] = None
    
    def __post_init__(self):
        if self.points is None:
            self.points = []
        if self.children is None:
            self.children = []


@dataclass
class PathNode:
    """Node for A* pathfinding algorithm"""
    position: Tuple[float, float]
    g_cost: float = float('inf')  # Cost from start
    h_cost: float = 0.0          # Heuristic cost to goal
    f_cost: float = float('inf') # Total cost
    parent: Optional['PathNode'] = None
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost


class QuadTree:
    """Quadtree spatial index for efficient spatial partitioning"""
    
    def __init__(self, bounds: Tuple[float, float, float, float], 
                 max_capacity: int = 10, max_depth: int = 10):
        """
        Initialize quadtree
        
        Args:
            bounds: (min_x, min_y, max_x, max_y) boundary
            max_capacity: Maximum points per node before subdivision
            max_depth: Maximum tree depth
        """
        self.root = QuadTreeNode(bounds, max_capacity, max_depth)
    
    def insert(self, point: SpatialPoint) -> bool:
        """Insert a point into the quadtree"""
        return self._insert_recursive(self.root, point)
    
    def _insert_recursive(self, node: QuadTreeNode, point: SpatialPoint) -> bool:
        """Recursively insert point into quadtree"""
        if not self._point_in_bounds(point, node.bounds):
            return False
        
        if len(node.points) < node.max_capacity or node.depth >= node.max_depth:
            node.points.append(point)
            return True
        
        if not node.children:
            self._subdivide(node)
        
        # Try to insert into children
        for child in node.children:
            if self._insert_recursive(child, point):
                return True
        
        # If no child accepted, add to current node
        node.points.append(point)
        return True
    
    def _subdivide(self, node: QuadTreeNode):
        """Subdivide a node into four children"""
        min_x, min_y, max_x, max_y = node.bounds
        mid_x = (min_x + max_x) / 2
        mid_y = (min_y + max_y) / 2
        
        # Create four children (NE, NW, SE, SW)
        node.children = [
            QuadTreeNode((mid_x, mid_y, max_x, max_y), 
                        node.max_capacity, node.max_depth, node.depth + 1),  # NE
            QuadTreeNode((min_x, mid_y, mid_x, max_y), 
                        node.max_capacity, node.max_depth, node.depth + 1),  # NW
            QuadTreeNode((mid_x, min_y, max_x, mid_y), 
                        node.max_capacity, node.max_depth, node.depth + 1),  # SE
            QuadTreeNode((min_x, min_y, mid_x, mid_y), 
                        node.max_capacity, node.max_depth, node.depth + 1)   # SW
        ]
        
        # Redistribute points to children
        points_to_redistribute = node.points[:]
        node.points = []
        
        for point in points_to_redistribute:
            inserted = False
            for child in node.children:
                if self._insert_recursive(child, point):
                    inserted = True
                    break
            
            if not inserted:
                node.points.append(point)
    
    def _point_in_bounds(self, point: SpatialPoint, bounds: Tuple[float, float, float, float]) -> bool:
        """Check if point is within bounds"""
        min_x, min_y, max_x, max_y = bounds
        return (min_x <= point.longitude <= max_x and 
                min_y <= point.latitude <= max_y)
    
    def query_range(self, bounds: Tuple[float, float, float, float]) -> List[SpatialPoint]:
        """Query points within a rectangular range"""
        result = []
        self._query_range_recursive(self.root, bounds, result)
        return result
    
    def _query_range_recursive(self, node: QuadTreeNode, 
                              query_bounds: Tuple[float, float, float, float], 
                              result: List[SpatialPoint]):
        """Recursively query range"""
        if not self._bounds_intersect(node.bounds, query_bounds):
            return
        
        # Check points in current node
        for point in node.points:
            if self._point_in_bounds(point, query_bounds):
                result.append(point)
        
        # Check children
        for child in node.children:
            self._query_range_recursive(child, query_bounds, result)
    
    def _bounds_intersect(self, bounds1: Tuple[float, float, float, float], 
                         bounds2: Tuple[float, float, float, float]) -> bool:
        """Check if two bounding rectangles intersect"""
        min_x1, min_y1, max_x1, max_y1 = bounds1
        min_x2, min_y2, max_x2, max_y2 = bounds2
        
        return not (max_x1 < min_x2 or max_x2 < min_x1 or 
                   max_y1 < min_y2 or max_y2 < min_y1)
    
    def find_nearest(self, query_point: SpatialPoint, k: int = 1) -> List[SpatialPoint]:
        """Find k nearest points to query point"""
        # Start with large search area and expand if needed
        search_radius = 0.01  # ~1km in degrees
        max_radius = 1.0      # ~100km in degrees
        
        while search_radius <= max_radius:
            bounds = (
                query_point.longitude - search_radius,
                query_point.latitude - search_radius,
                query_point.longitude + search_radius,
                query_point.latitude + search_radius
            )
            
            candidates = self.query_range(bounds)
            
            if len(candidates) >= k:
                # Sort by distance and return k closest
                candidates.sort(key=lambda p: query_point.distance_to(p))
                return candidates[:k]
            
            search_radius *= 2
        
        return []


class AdvancedSpatialService:
    """Advanced spatial algorithms and operations service"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.osrm_client = None
        self._quadtree_cache = {}
        self._spatial_index = None
        self._initialize_osrm()
    
    def _initialize_osrm(self):
        """Initialize OSRM client for routing"""
        try:
            # Initialize OSRM client (requires OSRM server running)
            self.osrm_client = osrm.Client(host='http://router.project-osrm.org')
        except Exception as e:
            logger.warning(f"OSRM client initialization failed: {e}")
            self.osrm_client = None
    
    async def create_spatial_index(self, region_bounds: Tuple[float, float, float, float] = None) -> index.Index:
        """
        Create R-tree spatial index for parking spots
        
        Args:
            region_bounds: Optional bounds to limit indexing area
            
        Returns:
            R-tree spatial index
        """
        if self._spatial_index is not None:
            return self._spatial_index
        
        idx = index.Index()
        
        # Build spatial index from parking spots
        query = """
            SELECT 
                ps.id,
                ST_Y(ST_Transform(ps.location, 4326)) as latitude,
                ST_X(ST_Transform(ps.location, 4326)) as longitude,
                ps.status,
                ps.spot_type
            FROM parking_spots ps
            WHERE ps.location IS NOT NULL
        """
        
        if region_bounds:
            min_lng, min_lat, max_lng, max_lat = region_bounds
            query += f"""
                AND ST_Within(
                    ps.location,
                    ST_MakeEnvelope({min_lng}, {min_lat}, {max_lng}, {max_lat}, 4326)
                )
            """
        
        result = await self.session.execute(text(query))
        
        for row in result:
            # Insert into R-tree: (min_x, min_y, max_x, max_y, object_id)
            idx.insert(
                row.id,
                (row.longitude, row.latitude, row.longitude, row.latitude),
                obj={
                    'id': row.id,
                    'lat': row.latitude,
                    'lng': row.longitude,
                    'status': row.status,
                    'type': row.spot_type
                }
            )
        
        self._spatial_index = idx
        return idx
    
    async def find_nearest_spots_rtree(self, latitude: float, longitude: float, 
                                     k: int = 10, max_distance_km: float = 5.0) -> List[Dict[str, Any]]:
        """
        Find nearest parking spots using R-tree spatial index
        
        Args:
            latitude: Search center latitude
            longitude: Search center longitude
            k: Number of nearest spots to find
            max_distance_km: Maximum search distance in kilometers
            
        Returns:
            List of nearest parking spots with distances
        """
        idx = await self.create_spatial_index()
        
        # Convert max distance to degrees (approximate)
        degree_distance = max_distance_km / 111.0  # ~111km per degree
        
        search_bounds = (
            longitude - degree_distance,
            latitude - degree_distance,
            longitude + degree_distance,
            latitude + degree_distance
        )
        
        # Find candidates using R-tree
        candidates = []
        for spot_id in idx.intersection(search_bounds, objects=True):
            spot_data = spot_id.object
            distance_km = geodesic(
                (latitude, longitude),
                (spot_data['lat'], spot_data['lng'])
            ).kilometers
            
            if distance_km <= max_distance_km:
                candidates.append({
                    'spot_id': spot_data['id'],
                    'latitude': spot_data['lat'],
                    'longitude': spot_data['lng'],
                    'status': spot_data['status'],
                    'spot_type': spot_data['type'],
                    'distance_km': distance_km,
                    'distance_meters': distance_km * 1000
                })
        
        # Sort by distance and return top k
        candidates.sort(key=lambda x: x['distance_km'])
        return candidates[:k]
    
    async def implement_astar_pathfinding(self, start_lat: float, start_lng: float,
                                        goal_lat: float, goal_lng: float,
                                        obstacles: List[Tuple[float, float]] = None) -> List[Tuple[float, float]]:
        """
        Implement A* pathfinding algorithm for optimal parking routes
        
        Args:
            start_lat: Starting latitude
            start_lng: Starting longitude
            goal_lat: Goal latitude
            goal_lng: Goal longitude
            obstacles: List of obstacle coordinates to avoid
            
        Returns:
            List of coordinates representing optimal path
        """
        if obstacles is None:
            obstacles = []
        
        # Create grid-based representation
        grid_resolution = 0.0001  # ~10 meters
        
        start_node = PathNode((start_lng, start_lat))
        goal_node = PathNode((goal_lng, goal_lat))
        
        open_set = [start_node]
        closed_set = set()
        
        start_node.g_cost = 0
        start_node.h_cost = self._heuristic_cost(start_node, goal_node)
        start_node.f_cost = start_node.h_cost
        
        while open_set:
            current_node = heapq.heappop(open_set)
            
            if self._nodes_equal(current_node, goal_node, grid_resolution):
                return self._reconstruct_path(current_node)
            
            closed_set.add(current_node.position)
            
            # Generate neighbors
            neighbors = self._get_neighbors(current_node, grid_resolution)
            
            for neighbor in neighbors:
                if neighbor.position in closed_set:
                    continue
                
                # Check if neighbor is an obstacle
                if self._is_obstacle(neighbor.position, obstacles, grid_resolution):
                    continue
                
                tentative_g_cost = current_node.g_cost + self._distance_between_nodes(current_node, neighbor)
                
                if tentative_g_cost < neighbor.g_cost:
                    neighbor.parent = current_node
                    neighbor.g_cost = tentative_g_cost
                    neighbor.h_cost = self._heuristic_cost(neighbor, goal_node)
                    neighbor.f_cost = neighbor.g_cost + neighbor.h_cost
                    
                    if neighbor not in open_set:
                        heapq.heappush(open_set, neighbor)
        
        return []  # No path found
    
    def _heuristic_cost(self, node1: PathNode, node2: PathNode) -> float:
        """Calculate heuristic cost (Euclidean distance)"""
        dx = node1.position[0] - node2.position[0]
        dy = node1.position[1] - node2.position[1]
        return math.sqrt(dx * dx + dy * dy)
    
    def _distance_between_nodes(self, node1: PathNode, node2: PathNode) -> float:
        """Calculate actual distance between nodes"""
        return geodesic(
            (node1.position[1], node1.position[0]),
            (node2.position[1], node2.position[0])
        ).meters
    
    def _nodes_equal(self, node1: PathNode, node2: PathNode, tolerance: float) -> bool:
        """Check if two nodes are equal within tolerance"""
        return (abs(node1.position[0] - node2.position[0]) < tolerance and
                abs(node1.position[1] - node2.position[1]) < tolerance)
    
    def _get_neighbors(self, node: PathNode, resolution: float) -> List[PathNode]:
        """Get neighboring nodes in 8 directions"""
        neighbors = []
        directions = [
            (-resolution, -resolution), (-resolution, 0), (-resolution, resolution),
            (0, -resolution),                             (0, resolution),
            (resolution, -resolution),  (resolution, 0),  (resolution, resolution)
        ]
        
        for dx, dy in directions:
            new_pos = (node.position[0] + dx, node.position[1] + dy)
            neighbors.append(PathNode(new_pos))
        
        return neighbors
    
    def _is_obstacle(self, position: Tuple[float, float], 
                    obstacles: List[Tuple[float, float]], tolerance: float) -> bool:
        """Check if position is an obstacle"""
        for obstacle in obstacles:
            if (abs(position[0] - obstacle[0]) < tolerance and
                abs(position[1] - obstacle[1]) < tolerance):
                return True
        return False
    
    def _reconstruct_path(self, node: PathNode) -> List[Tuple[float, float]]:
        """Reconstruct path from goal node to start"""
        path = []
        current = node
        
        while current is not None:
            path.append(current.position)
            current = current.parent
        
        return path[::-1]  # Reverse to get start-to-goal path
    
    async def get_osrm_route(self, start_lat: float, start_lng: float,
                           goal_lat: float, goal_lng: float) -> Dict[str, Any]:
        """
        Get real-world route using OSRM
        
        Args:
            start_lat: Starting latitude
            start_lng: Starting longitude
            goal_lat: Goal latitude
            goal_lng: Goal longitude
            
        Returns:
            Route information including geometry, distance, and duration
        """
        if self.osrm_client is None:
            # Fallback to straight-line calculation
            distance = geodesic((start_lat, start_lng), (goal_lat, goal_lng)).meters
            return {
                'distance_meters': distance,
                'duration_seconds': distance / 10,  # Assume 10 m/s average speed
                'geometry': [[start_lng, start_lat], [goal_lng, goal_lat]],
                'route_type': 'straight_line'
            }
        
        try:
            response = self.osrm_client.route(
                coordinates=[[start_lng, start_lat], [goal_lng, goal_lat]],
                profile='driving',
                overview='full',
                geometries='geojson'
            )
            
            if response['code'] == 'Ok' and response['routes']:
                route = response['routes'][0]
                return {
                    'distance_meters': route['distance'],
                    'duration_seconds': route['duration'],
                    'geometry': route['geometry']['coordinates'],
                    'route_type': 'osrm'
                }
        except Exception as e:
            logger.error(f"OSRM route calculation failed: {e}")
        
        # Fallback
        distance = geodesic((start_lat, start_lng), (goal_lat, goal_lng)).meters
        return {
            'distance_meters': distance,
            'duration_seconds': distance / 10,
            'geometry': [[start_lng, start_lat], [goal_lng, goal_lat]],
            'route_type': 'fallback'
        }
    
    def generate_geohash(self, latitude: float, longitude: float, precision: int = 9) -> str:
        """
        Generate geohash for location encoding
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            precision: Geohash precision (default 9 for ~5m accuracy)
            
        Returns:
            Geohash string
        """
        return geohash2.encode(latitude, longitude, precision)
    
    def decode_geohash(self, geohash_str: str) -> Tuple[float, float]:
        """
        Decode geohash to coordinates
        
        Args:
            geohash_str: Geohash string to decode
            
        Returns:
            Tuple of (latitude, longitude)
        """
        return geohash2.decode(geohash_str)
    
    def get_geohash_neighbors(self, geohash_str: str) -> List[str]:
        """
        Get neighboring geohashes
        
        Args:
            geohash_str: Center geohash
            
        Returns:
            List of neighboring geohash strings
        """
        return geohash2.neighbors(geohash_str)
    
    def generate_h3_index(self, latitude: float, longitude: float, resolution: int = 9) -> str:
        """
        Generate H3 hexagonal index for location
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            resolution: H3 resolution (0-15, default 9 for ~100m accuracy)
            
        Returns:
            H3 index string
        """
        return h3.geo_to_h3(latitude, longitude, resolution)
    
    def get_h3_neighbors(self, h3_index: str) -> List[str]:
        """
        Get neighboring H3 hexagons
        
        Args:
            h3_index: Center H3 index
            
        Returns:
            List of neighboring H3 indices
        """
        return h3.hex_ring(h3_index, 1)
    
    async def cluster_parking_spots(self, region_bounds: Tuple[float, float, float, float],
                                  eps_km: float = 0.1, min_samples: int = 3) -> List[Dict[str, Any]]:
        """
        Cluster parking spots using DBSCAN for density analysis
        
        Args:
            region_bounds: (min_lng, min_lat, max_lng, max_lat) boundary
            eps_km: Maximum distance between points in same cluster (km)
            min_samples: Minimum samples required to form cluster
            
        Returns:
            List of cluster information
        """
        min_lng, min_lat, max_lng, max_lat = region_bounds
        
        # Get parking spots in region
        query = text("""
            SELECT 
                ps.id,
                ST_Y(ST_Transform(ps.location, 4326)) as latitude,
                ST_X(ST_Transform(ps.location, 4326)) as longitude,
                ps.status,
                ps.spot_type
            FROM parking_spots ps
            WHERE ps.location IS NOT NULL
            AND ST_Within(
                ps.location,
                ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
            )
        """)
        
        result = await self.session.execute(query, {
            'min_lng': min_lng, 'min_lat': min_lat,
            'max_lng': max_lng, 'max_lat': max_lat
        })
        
        spots = [dict(row._mapping) for row in result]
        
        if len(spots) < min_samples:
            return []
        
        # Prepare coordinates for clustering
        coordinates = [[spot['latitude'], spot['longitude']] for spot in spots]
        
        # Convert eps from km to degrees (approximate)
        eps_degrees = eps_km / 111.0
        
        # Perform DBSCAN clustering
        clustering = DBSCAN(eps=eps_degrees, min_samples=min_samples, metric='euclidean')
        cluster_labels = clustering.fit_predict(coordinates)
        
        # Analyze clusters
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            clusters[label].append(spots[i])
        
        cluster_info = []
        for cluster_id, cluster_spots in clusters.items():
            if cluster_id == -1:  # Noise points
                continue
            
            # Calculate cluster center
            center_lat = sum(spot['latitude'] for spot in cluster_spots) / len(cluster_spots)
            center_lng = sum(spot['longitude'] for spot in cluster_spots) / len(cluster_spots)
            
            # Calculate cluster statistics
            available_spots = sum(1 for spot in cluster_spots if spot['status'] == 'available')
            
            cluster_info.append({
                'cluster_id': int(cluster_id),
                'center_latitude': center_lat,
                'center_longitude': center_lng,
                'total_spots': len(cluster_spots),
                'available_spots': available_spots,
                'occupancy_rate': (len(cluster_spots) - available_spots) / len(cluster_spots),
                'spot_types': list(set(spot['spot_type'] for spot in cluster_spots)),
                'spots': cluster_spots
            })
        
        return cluster_info
    
    async def create_quadtree_index(self, region_bounds: Tuple[float, float, float, float]) -> QuadTree:
        """
        Create quadtree spatial index for region
        
        Args:
            region_bounds: (min_lng, min_lat, max_lng, max_lat) boundary
            
        Returns:
            QuadTree index
        """
        cache_key = f"quadtree_{region_bounds}"
        if cache_key in self._quadtree_cache:
            return self._quadtree_cache[cache_key]
        
        qtree = QuadTree(region_bounds)
        
        min_lng, min_lat, max_lng, max_lat = region_bounds
        
        # Load parking spots into quadtree
        query = text("""
            SELECT 
                ps.id,
                ST_Y(ST_Transform(ps.location, 4326)) as latitude,
                ST_X(ST_Transform(ps.location, 4326)) as longitude,
                ps.status,
                ps.spot_type,
                pl.name as lot_name
            FROM parking_spots ps
            JOIN parking_lots pl ON ps.parking_lot_id = pl.id
            WHERE ps.location IS NOT NULL
            AND ST_Within(
                ps.location,
                ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
            )
        """)
        
        result = await self.session.execute(query, {
            'min_lng': min_lng, 'min_lat': min_lat,
            'max_lng': max_lng, 'max_lat': max_lat
        })
        
        for row in result:
            point = SpatialPoint(
                latitude=row.latitude,
                longitude=row.longitude,
                metadata={
                    'spot_id': row.id,
                    'status': row.status,
                    'spot_type': row.spot_type,
                    'lot_name': row.lot_name
                }
            )
            qtree.insert(point)
        
        self._quadtree_cache[cache_key] = qtree
        return qtree
    
    async def query_quadtree_region(self, region_bounds: Tuple[float, float, float, float],
                                  query_bounds: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        """
        Query quadtree for points in specific bounds
        
        Args:
            region_bounds: Overall quadtree region bounds
            query_bounds: Query region bounds
            
        Returns:
            List of points in query region
        """
        qtree = await self.create_quadtree_index(region_bounds)
        points = qtree.query_range(query_bounds)
        
        return [
            {
                'latitude': point.latitude,
                'longitude': point.longitude,
                'metadata': point.metadata
            }
            for point in points
        ]
    
    async def calculate_polygon_intersections(self, polygon1_wkt: str, polygon2_wkt: str) -> Dict[str, Any]:
        """
        Calculate intersection between two polygons using PostGIS
        
        Args:
            polygon1_wkt: First polygon in WKT format
            polygon2_wkt: Second polygon in WKT format
            
        Returns:
            Intersection analysis results
        """
        query = text("""
            WITH poly1 AS (SELECT ST_GeomFromText(:poly1_wkt, 4326) as geom),
                 poly2 AS (SELECT ST_GeomFromText(:poly2_wkt, 4326) as geom)
            SELECT 
                ST_Intersects(poly1.geom, poly2.geom) as intersects,
                ST_AsText(ST_Intersection(poly1.geom, poly2.geom)) as intersection_wkt,
                ST_Area(ST_Transform(ST_Intersection(poly1.geom, poly2.geom), 3857)) as intersection_area_m2,
                ST_Area(ST_Transform(poly1.geom, 3857)) as poly1_area_m2,
                ST_Area(ST_Transform(poly2.geom, 3857)) as poly2_area_m2
            FROM poly1, poly2
        """)
        
        result = await self.session.execute(query, {
            'poly1_wkt': polygon1_wkt,
            'poly2_wkt': polygon2_wkt
        })
        
        row = result.first()
        if row:
            overlap_percentage = 0.0
            if row.poly1_area_m2 > 0:
                overlap_percentage = (row.intersection_area_m2 / row.poly1_area_m2) * 100
            
            return {
                'intersects': row.intersects,
                'intersection_wkt': row.intersection_wkt,
                'intersection_area_m2': float(row.intersection_area_m2) if row.intersection_area_m2 else 0.0,
                'polygon1_area_m2': float(row.poly1_area_m2) if row.poly1_area_m2 else 0.0,
                'polygon2_area_m2': float(row.poly2_area_m2) if row.poly2_area_m2 else 0.0,
                'overlap_percentage': overlap_percentage
            }
        
        return {
            'intersects': False,
            'intersection_wkt': None,
            'intersection_area_m2': 0.0,
            'polygon1_area_m2': 0.0,
            'polygon2_area_m2': 0.0,
            'overlap_percentage': 0.0
        }
    
    async def optimize_parking_allocation(self, demand_points: List[Tuple[float, float]],
                                        supply_bounds: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """
        Optimize parking allocation using spatial analysis
        
        Args:
            demand_points: List of (lat, lng) points representing demand
            supply_bounds: Bounds containing parking supply
            
        Returns:
            Optimization analysis and recommendations
        """
        # Get available parking spots in supply area
        qtree = await self.create_quadtree_index(supply_bounds)
        
        # Calculate demand density using H3 hexagons
        demand_h3_counts = defaultdict(int)
        for lat, lng in demand_points:
            h3_index = self.generate_h3_index(lat, lng, resolution=8)
            demand_h3_counts[h3_index] += 1
        
        # Analyze supply-demand matching
        allocation_results = []
        
        for h3_index, demand_count in demand_h3_counts.items():
            # Get hexagon center
            center_lat, center_lng = h3.h3_to_geo(h3_index)
            
            # Find nearby parking spots using quadtree
            search_radius = 0.01  # ~1km in degrees
            query_bounds = (
                center_lng - search_radius,
                center_lat - search_radius,
                center_lng + search_radius,
                center_lat + search_radius
            )
            
            nearby_points = qtree.query_range(query_bounds)
            available_spots = [
                p for p in nearby_points 
                if p.metadata.get('status') == 'available'
            ]
            
            supply_demand_ratio = len(available_spots) / max(demand_count, 1)
            
            allocation_results.append({
                'h3_index': h3_index,
                'center_latitude': center_lat,
                'center_longitude': center_lng,
                'demand_count': demand_count,
                'available_supply': len(available_spots),
                'supply_demand_ratio': supply_demand_ratio,
                'is_undersupplied': supply_demand_ratio < 0.8,
                'is_oversupplied': supply_demand_ratio > 2.0
            })
        
        # Generate recommendations
        undersupplied_areas = [r for r in allocation_results if r['is_undersupplied']]
        oversupplied_areas = [r for r in allocation_results if r['is_oversupplied']]
        
        return {
            'total_demand_points': len(demand_points),
            'analyzed_hexagons': len(allocation_results),
            'undersupplied_areas': len(undersupplied_areas),
            'oversupplied_areas': len(oversupplied_areas),
            'allocation_results': allocation_results,
            'recommendations': {
                'expand_supply_in': undersupplied_areas[:5],  # Top 5 undersupplied
                'reduce_supply_in': oversupplied_areas[:5],   # Top 5 oversupplied
                'average_supply_demand_ratio': sum(r['supply_demand_ratio'] for r in allocation_results) / len(allocation_results)
            }
        }
