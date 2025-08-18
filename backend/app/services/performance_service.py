"""
Performance Optimization Service - Step 6: Analytics & Optimization
Implements Bloom filters, Redis caching, connection pooling, and query optimization.
"""

import asyncio
import logging
import hashlib
import struct
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timedelta
import json
import pickle
from contextlib import asynccontextmanager

import redis.asyncio as redis
import numpy as np
from bitarray import bitarray

from sqlalchemy import create_engine, text, Index
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db, engine
from app.models.parking_spot import ParkingSpot
from app.models.parking_lot import ParkingLot
from app.models.reservation import Reservation

logger = logging.getLogger(__name__)

class BloomFilter:
    """
    High-performance Bloom filter for quick availability checks.
    Used to rapidly filter out unavailable parking spots before database queries.
    """
    
    def __init__(self, capacity: int = 10000, error_rate: float = 0.1):
        """
        Initialize Bloom filter with specified capacity and error rate.
        
        Args:
            capacity: Expected number of elements
            error_rate: Desired false positive rate
        """
        self.capacity = capacity
        self.error_rate = error_rate
        
        # Calculate optimal parameters
        self.bit_size = self._calculate_bit_size(capacity, error_rate)
        self.hash_count = self._calculate_hash_count(self.bit_size, capacity)
        
        # Initialize bit array
        self.bit_array = bitarray(self.bit_size)
        self.bit_array.setall(0)
        
        # Track statistics
        self.element_count = 0
        self.false_positive_count = 0
        self.total_queries = 0
        
        logger.info(f"Initialized Bloom filter: {self.bit_size} bits, {self.hash_count} hash functions")
    
    def _calculate_bit_size(self, capacity: int, error_rate: float) -> int:
        """Calculate optimal bit array size."""
        import math
        bit_size = -(capacity * math.log(error_rate)) / (math.log(2) ** 2)
        return int(bit_size)
    
    def _calculate_hash_count(self, bit_size: int, capacity: int) -> int:
        """Calculate optimal number of hash functions."""
        import math
        hash_count = (bit_size / capacity) * math.log(2)
        return max(1, int(hash_count))
    
    def _hash_functions(self, item: str) -> List[int]:
        """Generate multiple hash values for an item."""
        hashes = []
        
        # Primary hash using SHA-256
        primary_hash = hashlib.sha256(item.encode()).digest()
        
        # Generate multiple hashes using different portions of the primary hash
        for i in range(self.hash_count):
            # Use different 4-byte chunks of the hash
            start_idx = (i * 4) % len(primary_hash)
            chunk = primary_hash[start_idx:start_idx + 4]
            
            # Pad if necessary
            if len(chunk) < 4:
                chunk += primary_hash[:4 - len(chunk)]
            
            # Convert to integer and modulo with bit size
            hash_value = struct.unpack('I', chunk)[0] % self.bit_size
            hashes.append(hash_value)
        
        return hashes
    
    def add(self, item: str) -> None:
        """Add an item to the Bloom filter."""
        if self.element_count >= self.capacity:
            logger.warning("Bloom filter approaching capacity, consider resizing")
        
        for hash_value in self._hash_functions(item):
            self.bit_array[hash_value] = 1
        
        self.element_count += 1
    
    def add_batch(self, items: List[str]) -> None:
        """Add multiple items efficiently."""
        for item in items:
            self.add(item)
    
    def might_contain(self, item: str) -> bool:
        """
        Check if item might be in the set.
        Returns True if item might be present, False if definitely not present.
        """
        self.total_queries += 1
        
        for hash_value in self._hash_functions(item):
            if not self.bit_array[hash_value]:
                return False
        
        return True
    
    def bulk_check(self, items: List[str]) -> Dict[str, bool]:
        """Check multiple items efficiently."""
        results = {}
        for item in items:
            results[item] = self.might_contain(item)
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get Bloom filter statistics."""
        load_factor = self.element_count / self.capacity if self.capacity > 0 else 0
        estimated_false_positive_rate = (1 - np.exp(-self.hash_count * load_factor)) ** self.hash_count
        
        return {
            'capacity': self.capacity,
            'element_count': self.element_count,
            'bit_size': self.bit_size,
            'hash_count': self.hash_count,
            'load_factor': load_factor,
            'estimated_false_positive_rate': estimated_false_positive_rate,
            'total_queries': self.total_queries,
            'memory_usage_mb': self.bit_array.buffer_info()[1] * self.bit_array.itemsize / (1024 * 1024)
        }
    
    def clear(self) -> None:
        """Clear the Bloom filter."""
        self.bit_array.setall(0)
        self.element_count = 0
        self.total_queries = 0
        self.false_positive_count = 0
    
    def serialize(self) -> bytes:
        """Serialize Bloom filter for storage."""
        data = {
            'capacity': self.capacity,
            'error_rate': self.error_rate,
            'bit_size': self.bit_size,
            'hash_count': self.hash_count,
            'element_count': self.element_count,
            'bit_array': self.bit_array.tobytes()
        }
        return pickle.dumps(data)
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'BloomFilter':
        """Deserialize Bloom filter from storage."""
        obj_data = pickle.loads(data)
        
        bloom_filter = cls(obj_data['capacity'], obj_data['error_rate'])
        bloom_filter.bit_size = obj_data['bit_size']
        bloom_filter.hash_count = obj_data['hash_count']
        bloom_filter.element_count = obj_data['element_count']
        
        # Restore bit array
        bloom_filter.bit_array = bitarray()
        bloom_filter.bit_array.frombytes(obj_data['bit_array'])
        
        return bloom_filter

class RedisCache:
    """
    Advanced Redis caching with intelligent cache warming and invalidation.
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'invalidations': 0
        }
        
    async def get(self, key: str, decode_json: bool = True) -> Optional[Any]:
        """Get value from cache with statistics tracking."""
        try:
            value = await self.redis_client.get(key)
            if value is not None:
                self.cache_stats['hits'] += 1
                if decode_json:
                    return json.loads(value)
                return value
            else:
                self.cache_stats['misses'] += 1
                return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self.cache_stats['misses'] += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600, encode_json: bool = True) -> bool:
        """Set value in cache with TTL."""
        try:
            if encode_json:
                value = json.dumps(value, default=str)
            
            await self.redis_client.setex(key, ttl, value)
            self.cache_stats['sets'] += 1
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def get_or_set(self, key: str, factory_func, ttl: int = 3600, *args, **kwargs) -> Any:
        """Get from cache or compute and set if not exists."""
        # Try to get from cache first
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value
        
        # Compute value
        if asyncio.iscoroutinefunction(factory_func):
            computed_value = await factory_func(*args, **kwargs)
        else:
            computed_value = factory_func(*args, **kwargs)
        
        # Store in cache
        await self.set(key, computed_value, ttl)
        
        return computed_value
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted_count = await self.redis_client.delete(*keys)
                self.cache_stats['invalidations'] += deleted_count
                return deleted_count
            return 0
        except Exception as e:
            logger.error(f"Cache invalidation error for pattern {pattern}: {e}")
            return 0
    
    async def warm_cache(self, parking_lot_id: str) -> None:
        """Warm cache with frequently accessed data."""
        logger.info(f"Warming cache for parking lot {parking_lot_id}")
        
        try:
            # Warm parking lot info
            await self._warm_parking_lot_info(parking_lot_id)
            
            # Warm current availability
            await self._warm_availability_info(parking_lot_id)
            
            # Warm recent analytics
            await self._warm_analytics_data(parking_lot_id)
            
        except Exception as e:
            logger.error(f"Cache warming error for {parking_lot_id}: {e}")
    
    async def _warm_parking_lot_info(self, parking_lot_id: str) -> None:
        """Warm parking lot basic information."""
        cache_key = f"parking_lot_info:{parking_lot_id}"
        
        async with get_db() as db:
            query = text("""
                SELECT 
                    id, name, location, total_spots, hourly_rate,
                    ST_AsGeoJSON(location_point)::json as location_geojson
                FROM parking_lots 
                WHERE id = :parking_lot_id
            """)
            
            result = db.execute(query, {'parking_lot_id': parking_lot_id})
            parking_lot_data = result.fetchone()
            
            if parking_lot_data:
                await self.set(cache_key, dict(parking_lot_data), ttl=7200)  # 2 hours
    
    async def _warm_availability_info(self, parking_lot_id: str) -> None:
        """Warm current availability information."""
        cache_key = f"availability:{parking_lot_id}"
        
        async with get_db() as db:
            query = text("""
                SELECT 
                    pl.total_spots,
                    COUNT(r.id) as occupied_spots,
                    (pl.total_spots - COUNT(r.id)) as available_spots,
                    (COUNT(r.id) * 100.0 / pl.total_spots) as occupancy_rate
                FROM parking_lots pl
                LEFT JOIN reservations r ON r.parking_lot_id = pl.id 
                    AND r.status = 'confirmed'
                    AND NOW() BETWEEN r.start_time AND r.end_time
                WHERE pl.id = :parking_lot_id
                GROUP BY pl.id, pl.total_spots
            """)
            
            result = db.execute(query, {'parking_lot_id': parking_lot_id})
            availability_data = result.fetchone()
            
            if availability_data:
                await self.set(cache_key, dict(availability_data), ttl=300)  # 5 minutes
    
    async def _warm_analytics_data(self, parking_lot_id: str) -> None:
        """Warm recent analytics data."""
        cache_key = f"recent_analytics:{parking_lot_id}"
        
        # Get last 24 hours of hourly data
        async with get_db() as db:
            query = text("""
                SELECT 
                    DATE_TRUNC('hour', r.start_time) as hour_slot,
                    COUNT(*) as reservations,
                    AVG(EXTRACT(EPOCH FROM (r.end_time - r.start_time))/3600) as avg_duration_hours
                FROM reservations r
                WHERE r.parking_lot_id = :parking_lot_id
                AND r.start_time >= NOW() - INTERVAL '24 hours'
                AND r.status = 'confirmed'
                GROUP BY DATE_TRUNC('hour', r.start_time)
                ORDER BY hour_slot DESC
                LIMIT 24
            """)
            
            result = db.execute(query, {'parking_lot_id': parking_lot_id})
            analytics_data = [dict(row) for row in result.fetchall()]
            
            await self.set(cache_key, analytics_data, ttl=1800)  # 30 minutes
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        # Get Redis info
        redis_info = await self.redis_client.info()
        
        return {
            'cache_stats': self.cache_stats,
            'hit_rate_percentage': hit_rate,
            'redis_memory_usage': redis_info.get('used_memory_human', 'N/A'),
            'redis_connected_clients': redis_info.get('connected_clients', 0),
            'redis_commands_processed': redis_info.get('total_commands_processed', 0)
        }

class DatabaseOptimizer:
    """
    Database query optimization and connection pooling manager.
    """
    
    def __init__(self):
        self.connection_pool = None
        self.query_cache = {}
        self.slow_query_threshold = 1.0  # seconds
        self.query_stats = defaultdict(list)
        
    def setup_connection_pool(self, database_url: str, pool_size: int = 20, max_overflow: int = 30):
        """Setup optimized database connection pool."""
        
        self.connection_pool = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections every hour
            echo=False,
            future=True
        )
        
        logger.info(f"Database connection pool initialized: {pool_size} base connections, {max_overflow} overflow")
    
    @asynccontextmanager
    async def get_optimized_session(self):
        """Get database session with connection pooling."""
        async with get_db() as session:
            yield session
    
    async def create_spatial_indexes(self, db: Session) -> None:
        """Create optimized spatial indexes for better query performance."""
        
        indexes_to_create = [
            # Spatial index on parking lot locations
            "CREATE INDEX IF NOT EXISTS idx_parking_lots_location_gist ON parking_lots USING GIST (location_point);",
            
            # Composite index for reservation queries
            "CREATE INDEX IF NOT EXISTS idx_reservations_lot_time ON reservations (parking_lot_id, start_time, end_time);",
            
            # Index for status-based queries
            "CREATE INDEX IF NOT EXISTS idx_reservations_status_time ON reservations (status, start_time) WHERE status = 'confirmed';",
            
            # Partial index for active reservations
            "CREATE INDEX IF NOT EXISTS idx_active_reservations ON reservations (parking_lot_id, start_time, end_time) WHERE status = 'confirmed';",
            
            # Index for analytics queries
            "CREATE INDEX IF NOT EXISTS idx_reservations_analytics ON reservations (parking_lot_id, start_time, status) WHERE status = 'confirmed';",
            
            # Covering index for availability checks
            "CREATE INDEX IF NOT EXISTS idx_availability_check ON reservations (parking_lot_id, status) INCLUDE (start_time, end_time);",
            
            # Index for user reservations
            "CREATE INDEX IF NOT EXISTS idx_user_reservations ON reservations (user_id, status, start_time);",
            
            # GIN index for flexible spot searches
            "CREATE INDEX IF NOT EXISTS idx_parking_spots_features ON parking_spots USING GIN (features);",
        ]
        
        for index_sql in indexes_to_create:
            try:
                db.execute(text(index_sql))
                logger.info(f"Created index: {index_sql.split('ON')[1].split('(')[0].strip()}")
            except Exception as e:
                logger.warning(f"Index creation failed: {e}")
        
        db.commit()
    
    async def optimize_spatial_queries(self, db: Session) -> None:
        """Optimize spatial query performance."""
        
        # Update statistics for spatial columns
        spatial_optimization_queries = [
            "ANALYZE parking_lots;",
            "ANALYZE parking_spots;",
            "ANALYZE reservations;",
            
            # Create statistics on spatial columns
            "CREATE STATISTICS IF NOT EXISTS parking_lots_location_stats ON location_point FROM parking_lots;",
            
            # Optimize PostGIS settings
            "SET work_mem = '256MB';",
            "SET random_page_cost = 1.1;",
            "SET effective_cache_size = '4GB';",
        ]
        
        for query in spatial_optimization_queries:
            try:
                db.execute(text(query))
            except Exception as e:
                logger.warning(f"Spatial optimization query failed: {e}")
        
        db.commit()
    
    async def analyze_query_performance(self, query: str, params: Dict = None) -> Dict[str, Any]:
        """Analyze query performance using EXPLAIN ANALYZE."""
        
        try:
            # Get query plan
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            
            async with self.get_optimized_session() as db:
                result = db.execute(text(explain_query), params or {})
                plan_data = result.fetchone()[0]
            
            execution_time = plan_data[0]['Execution Time']
            planning_time = plan_data[0]['Planning Time']
            
            # Track slow queries
            if execution_time > self.slow_query_threshold * 1000:  # Convert to ms
                logger.warning(f"Slow query detected: {execution_time:.2f}ms - {query[:100]}...")
            
            return {
                'execution_time_ms': execution_time,
                'planning_time_ms': planning_time,
                'total_time_ms': execution_time + planning_time,
                'query_plan': plan_data[0],
                'performance_rating': self._rate_query_performance(execution_time)
            }
            
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return {}
    
    def _rate_query_performance(self, execution_time_ms: float) -> str:
        """Rate query performance based on execution time."""
        if execution_time_ms < 10:
            return "excellent"
        elif execution_time_ms < 100:
            return "good"
        elif execution_time_ms < 1000:
            return "acceptable"
        else:
            return "needs_optimization"
    
    async def get_database_statistics(self, db: Session) -> Dict[str, Any]:
        """Get comprehensive database performance statistics."""
        
        stats_queries = {
            'table_sizes': """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
            """,
            
            'index_usage': """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC;
            """,
            
            'slow_queries': """
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    rows
                FROM pg_stat_statements
                WHERE mean_time > 100
                ORDER BY mean_time DESC
                LIMIT 10;
            """,
            
            'connection_stats': """
                SELECT 
                    state,
                    COUNT(*) as connection_count
                FROM pg_stat_activity
                GROUP BY state;
            """
        }
        
        statistics = {}
        
        for stat_name, query in stats_queries.items():
            try:
                result = db.execute(text(query))
                statistics[stat_name] = [dict(row) for row in result.fetchall()]
            except Exception as e:
                logger.warning(f"Failed to get {stat_name}: {e}")
                statistics[stat_name] = []
        
        return statistics

class PerformanceOptimizationService:
    """
    Main service coordinating all performance optimization components.
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.redis_cache = RedisCache(redis_client)
        self.db_optimizer = DatabaseOptimizer()
        
        # Bloom filters for different purposes
        self.availability_bloom = BloomFilter(capacity=50000, error_rate=0.01)
        self.user_bloom = BloomFilter(capacity=100000, error_rate=0.01)
        
        # Performance metrics
        self.performance_metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'bloom_filter_hits': 0,
            'database_queries': 0,
            'average_response_time': 0.0
        }
    
    async def initialize(self) -> None:
        """Initialize performance optimization components."""
        
        logger.info("Initializing performance optimization service")
        
        # Setup database connection pool
        self.db_optimizer.setup_connection_pool(str(settings.DATABASE_URL))
        
        # Create database indexes
        async with get_db() as db:
            await self.db_optimizer.create_spatial_indexes(db)
            await self.db_optimizer.optimize_spatial_queries(db)
        
        # Warm Bloom filters
        await self._initialize_bloom_filters()
        
        # Warm cache
        await self._warm_initial_cache()
        
        logger.info("Performance optimization service initialized successfully")
    
    async def _initialize_bloom_filters(self) -> None:
        """Initialize Bloom filters with current data."""
        
        logger.info("Initializing Bloom filters")
        
        try:
            async with get_db() as db:
                # Load occupied parking spots into availability Bloom filter
                occupied_query = text("""
                    SELECT DISTINCT CONCAT(parking_lot_id, ':', spot_number)
                    FROM reservations r
                    JOIN parking_spots ps ON ps.parking_lot_id = r.parking_lot_id
                    WHERE r.status = 'confirmed'
                    AND NOW() BETWEEN r.start_time AND r.end_time
                """)
                
                result = db.execute(occupied_query)
                occupied_spots = [row[0] for row in result.fetchall()]
                
                if occupied_spots:
                    self.availability_bloom.add_batch(occupied_spots)
                    logger.info(f"Loaded {len(occupied_spots)} occupied spots into availability Bloom filter")
                
                # Load active users into user Bloom filter
                users_query = text("""
                    SELECT DISTINCT user_id::text
                    FROM reservations
                    WHERE status = 'confirmed'
                    AND start_time >= NOW() - INTERVAL '30 days'
                """)
                
                result = db.execute(users_query)
                active_users = [row[0] for row in result.fetchall()]
                
                if active_users:
                    self.user_bloom.add_batch(active_users)
                    logger.info(f"Loaded {len(active_users)} active users into user Bloom filter")
                    
        except Exception as e:
            logger.error(f"Failed to initialize Bloom filters: {e}")
    
    async def _warm_initial_cache(self) -> None:
        """Warm cache with frequently accessed data."""
        
        logger.info("Warming initial cache")
        
        try:
            async with get_db() as db:
                # Get all parking lot IDs
                result = db.execute(text("SELECT id FROM parking_lots"))
                parking_lot_ids = [row[0] for row in result.fetchall()]
                
                # Warm cache for each parking lot
                for lot_id in parking_lot_ids[:10]:  # Limit to first 10 for initial warming
                    await self.redis_cache.warm_cache(lot_id)
                    
        except Exception as e:
            logger.error(f"Failed to warm initial cache: {e}")
    
    async def check_availability_optimized(self, parking_lot_id: str, 
                                         start_time: datetime, 
                                         end_time: datetime) -> Dict[str, Any]:
        """
        Optimized availability check using Bloom filters and caching.
        """
        
        self.performance_metrics['total_requests'] += 1
        start_request_time = datetime.now()
        
        # Check cache first
        cache_key = f"availability:{parking_lot_id}:{start_time.isoformat()}:{end_time.isoformat()}"
        cached_result = await self.redis_cache.get(cache_key)
        
        if cached_result:
            self.performance_metrics['cache_hits'] += 1
            self._update_response_time(start_request_time)
            return cached_result
        
        # Use Bloom filter for quick negative check
        time_slot_key = f"{parking_lot_id}:{start_time.hour}"
        if self.availability_bloom.might_contain(time_slot_key):
            # Might be occupied, need to check database
            availability_data = await self._check_availability_database(parking_lot_id, start_time, end_time)
        else:
            # Definitely not in occupied set, likely available
            self.performance_metrics['bloom_filter_hits'] += 1
            availability_data = await self._get_parking_lot_info(parking_lot_id)
            availability_data['available_spots'] = availability_data.get('total_spots', 0)
            availability_data['occupied_spots'] = 0
            availability_data['occupancy_rate'] = 0.0
        
        # Cache result
        await self.redis_cache.set(cache_key, availability_data, ttl=300)  # 5 minutes
        
        self._update_response_time(start_request_time)
        return availability_data
    
    async def _check_availability_database(self, parking_lot_id: str, 
                                         start_time: datetime, 
                                         end_time: datetime) -> Dict[str, Any]:
        """Check availability in database with optimized query."""
        
        self.performance_metrics['database_queries'] += 1
        
        async with self.db_optimizer.get_optimized_session() as db:
            # Optimized query using indexes
            query = text("""
                WITH occupied_spots AS (
                    SELECT COUNT(*) as occupied_count
                    FROM reservations r
                    WHERE r.parking_lot_id = :parking_lot_id
                    AND r.status = 'confirmed'
                    AND (
                        (r.start_time <= :start_time AND r.end_time > :start_time) OR
                        (r.start_time < :end_time AND r.end_time >= :end_time) OR
                        (r.start_time >= :start_time AND r.end_time <= :end_time)
                    )
                )
                SELECT 
                    pl.id,
                    pl.name,
                    pl.total_spots,
                    COALESCE(os.occupied_count, 0) as occupied_spots,
                    (pl.total_spots - COALESCE(os.occupied_count, 0)) as available_spots,
                    CASE 
                        WHEN pl.total_spots > 0 THEN 
                            (COALESCE(os.occupied_count, 0) * 100.0 / pl.total_spots)
                        ELSE 0 
                    END as occupancy_rate
                FROM parking_lots pl
                CROSS JOIN occupied_spots os
                WHERE pl.id = :parking_lot_id
            """)
            
            result = db.execute(query, {
                'parking_lot_id': parking_lot_id,
                'start_time': start_time,
                'end_time': end_time
            })
            
            row = result.fetchone()
            if row:
                return dict(row)
            else:
                return {}
    
    async def _get_parking_lot_info(self, parking_lot_id: str) -> Dict[str, Any]:
        """Get basic parking lot information from cache or database."""
        
        cache_key = f"parking_lot_info:{parking_lot_id}"
        cached_info = await self.redis_cache.get(cache_key)
        
        if cached_info:
            return cached_info
        
        async with self.db_optimizer.get_optimized_session() as db:
            query = text("""
                SELECT id, name, total_spots, hourly_rate
                FROM parking_lots
                WHERE id = :parking_lot_id
            """)
            
            result = db.execute(query, {'parking_lot_id': parking_lot_id})
            row = result.fetchone()
            
            if row:
                info = dict(row)
                await self.redis_cache.set(cache_key, info, ttl=3600)
                return info
            
            return {}
    
    def _update_response_time(self, start_time: datetime) -> None:
        """Update average response time metric."""
        
        response_time = (datetime.now() - start_time).total_seconds()
        
        # Simple moving average
        alpha = 0.1
        if self.performance_metrics['average_response_time'] == 0:
            self.performance_metrics['average_response_time'] = response_time
        else:
            self.performance_metrics['average_response_time'] = (
                alpha * response_time + 
                (1 - alpha) * self.performance_metrics['average_response_time']
            )
    
    async def invalidate_cache_for_reservation(self, parking_lot_id: str, 
                                             reservation_data: Dict[str, Any]) -> None:
        """Invalidate relevant cache entries when a reservation is made."""
        
        # Invalidate availability cache
        await self.redis_cache.invalidate_pattern(f"availability:{parking_lot_id}:*")
        
        # Update Bloom filter
        start_time = reservation_data.get('start_time')
        if start_time:
            time_slot_key = f"{parking_lot_id}:{start_time.hour}"
            self.availability_bloom.add(time_slot_key)
        
        # Invalidate analytics cache
        await self.redis_cache.invalidate_pattern(f"recent_analytics:{parking_lot_id}")
        
        logger.info(f"Cache invalidated for parking lot {parking_lot_id} due to new reservation")
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        
        # Get individual component metrics
        cache_stats = await self.redis_cache.get_statistics()
        availability_bloom_stats = self.availability_bloom.get_statistics()
        user_bloom_stats = self.user_bloom.get_statistics()
        
        async with get_db() as db:
            db_stats = await self.db_optimizer.get_database_statistics(db)
        
        return {
            'service_metrics': self.performance_metrics,
            'cache_performance': cache_stats,
            'bloom_filters': {
                'availability_filter': availability_bloom_stats,
                'user_filter': user_bloom_stats
            },
            'database_performance': db_stats,
            'recommendations': await self._generate_performance_recommendations()
        }
    
    async def _generate_performance_recommendations(self) -> List[Dict[str, str]]:
        """Generate performance optimization recommendations."""
        
        recommendations = []
        
        # Check cache hit rate
        cache_stats = await self.redis_cache.get_statistics()
        hit_rate = cache_stats.get('hit_rate_percentage', 0)
        
        if hit_rate < 80:
            recommendations.append({
                'type': 'cache_optimization',
                'issue': f'Low cache hit rate: {hit_rate:.1f}%',
                'recommendation': 'Consider increasing cache TTL values or implementing cache warming',
                'priority': 'medium'
            })
        
        # Check Bloom filter efficiency
        bloom_stats = self.availability_bloom.get_statistics()
        if bloom_stats['load_factor'] > 0.8:
            recommendations.append({
                'type': 'bloom_filter_optimization',
                'issue': f'High Bloom filter load factor: {bloom_stats["load_factor"]:.2f}',
                'recommendation': 'Consider increasing Bloom filter capacity or implementing rotation',
                'priority': 'low'
            })
        
        # Check response time
        avg_response_time = self.performance_metrics['average_response_time']
        if avg_response_time > 0.5:
            recommendations.append({
                'type': 'response_time_optimization',
                'issue': f'High average response time: {avg_response_time:.3f}s',
                'recommendation': 'Investigate slow queries and consider additional caching',
                'priority': 'high'
            })
        
        return recommendations
    
    async def cleanup_expired_data(self) -> None:
        """Clean up expired data from Bloom filters and caches."""
        
        logger.info("Starting performance optimization cleanup")
        
        # Reset Bloom filters periodically to prevent false positive buildup
        current_time = datetime.now()
        
        # Reset availability Bloom filter and reload with current data
        self.availability_bloom.clear()
        await self._initialize_bloom_filters()
        
        # Clean up old cache entries (Redis handles TTL automatically)
        
        logger.info("Performance optimization cleanup completed")

# Initialize global performance optimization service
_performance_service: Optional[PerformanceOptimizationService] = None

async def get_performance_service() -> PerformanceOptimizationService:
    """Get global performance optimization service instance."""
    global _performance_service
    
    if _performance_service is None:
        # Initialize Redis client for performance service
        redis_client = redis.from_url(
            str(settings.REDIS_URL),
            encoding="utf-8",
            decode_responses=True
        )
        
        _performance_service = PerformanceOptimizationService(redis_client)
        await _performance_service.initialize()
    
    return _performance_service
