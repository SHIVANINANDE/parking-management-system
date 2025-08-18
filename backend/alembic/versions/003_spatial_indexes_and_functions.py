"""spatial_indexes_and_functions

Revision ID: 003_spatial_indexes_and_functions
Revises: 002
Create Date: 2024-12-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '003_spatial_indexes_and_functions'
down_revision = '8489f0c5656b'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create advanced spatial indexes and functions for optimal performance
    """
    # Create connection for raw SQL
    connection = op.get_bind()
    
    # 1. Create R-tree spatial indexes for fast nearest neighbor searches
    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_spots_location_rtree ON parking_spots USING GIST (location)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_lots_location_rtree ON parking_lots USING GIST (location)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_lots_boundary_rtree ON parking_lots USING GIST (boundary)"))
    
    # 2. Create geohash columns and indexes for fast spatial lookups
    connection.execute(text("ALTER TABLE parking_spots ADD COLUMN IF NOT EXISTS geohash_6 VARCHAR(6)"))
    connection.execute(text("ALTER TABLE parking_spots ADD COLUMN IF NOT EXISTS geohash_8 VARCHAR(8)"))
    connection.execute(text("ALTER TABLE parking_lots ADD COLUMN IF NOT EXISTS geohash_6 VARCHAR(6)"))
    connection.execute(text("ALTER TABLE parking_lots ADD COLUMN IF NOT EXISTS geohash_8 VARCHAR(8)"))
    
    # Create indexes on geohash columns
    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_spots_geohash_6 ON parking_spots (geohash_6)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_spots_geohash_8 ON parking_spots (geohash_8)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_lots_geohash_6 ON parking_lots (geohash_6)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_lots_geohash_8 ON parking_lots (geohash_8)"))
    
    # 3. Create H3 index columns for hexagonal spatial indexing
    connection.execute(text("ALTER TABLE parking_spots ADD COLUMN IF NOT EXISTS h3_index_6 VARCHAR(15)"))
    connection.execute(text("ALTER TABLE parking_spots ADD COLUMN IF NOT EXISTS h3_index_8 VARCHAR(15)"))
    connection.execute(text("ALTER TABLE parking_lots ADD COLUMN IF NOT EXISTS h3_index_6 VARCHAR(15)"))
    connection.execute(text("ALTER TABLE parking_lots ADD COLUMN IF NOT EXISTS h3_index_8 VARCHAR(15)"))
    
    # Create indexes on H3 columns
    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_spots_h3_6 ON parking_spots (h3_index_6)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_spots_h3_8 ON parking_spots (h3_index_8)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_lots_h3_6 ON parking_lots (h3_index_6)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_lots_h3_8 ON parking_lots (h3_index_8)"))
    
    # 4. Create advanced spatial analysis functions
    connection.execute(text("""
        CREATE OR REPLACE FUNCTION find_nearest_parking_spots(
            search_lat DOUBLE PRECISION,
            search_lng DOUBLE PRECISION,
            max_distance_km DOUBLE PRECISION DEFAULT 5.0,
            limit_count INTEGER DEFAULT 10
        )
        RETURNS TABLE (
            spot_id INTEGER,
            distance_meters DOUBLE PRECISION,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            is_available BOOLEAN,
            spot_type VARCHAR
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT 
                ps.id as spot_id,
                ST_Distance(
                    ps.location::geography,
                    ST_SetSRID(ST_MakePoint(search_lng, search_lat), 4326)::geography
                ) as distance_meters,
                ST_Y(ps.location) as latitude,
                ST_X(ps.location) as longitude,
                ps.is_available,
                ps.spot_type
            FROM parking_spots ps
            WHERE ST_DWithin(
                ps.location::geography,
                ST_SetSRID(ST_MakePoint(search_lng, search_lat), 4326)::geography,
                max_distance_km * 1000
            )
            ORDER BY ps.location <-> ST_SetSRID(ST_MakePoint(search_lng, search_lat), 4326)
            LIMIT limit_count;
        END;
        $$ LANGUAGE plpgsql
    """))
    
    # 5. Create spatial clustering function using PostGIS
    connection.execute(text("""
        CREATE OR REPLACE FUNCTION cluster_parking_spots_in_region(
            min_lng DOUBLE PRECISION,
            min_lat DOUBLE PRECISION,
            max_lng DOUBLE PRECISION,
            max_lat DOUBLE PRECISION,
            cluster_distance_meters DOUBLE PRECISION DEFAULT 100.0
        )
        RETURNS TABLE (
            cluster_id INTEGER,
            spot_id INTEGER,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            is_available BOOLEAN
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT 
                ST_ClusterDBSCAN(ps.location, eps := cluster_distance_meters, minpoints := 2) 
                    OVER () as cluster_id,
                ps.id as spot_id,
                ST_Y(ps.location) as latitude,
                ST_X(ps.location) as longitude,
                ps.is_available
            FROM parking_spots ps
            WHERE ps.location && ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)
            ORDER BY cluster_id NULLS LAST, ps.id;
        END;
        $$ LANGUAGE plpgsql
    """))
    
    # 6. Create performance monitoring view
    connection.execute(text("""
        CREATE OR REPLACE VIEW spatial_performance_stats AS
        SELECT 
            'parking_spots'::TEXT as table_name,
            COUNT(*) as total_records,
            COUNT(CASE WHEN location IS NOT NULL THEN 1 END) as records_with_location,
            ST_Extent(location) as spatial_extent,
            AVG(ST_X(location)) as avg_longitude,
            AVG(ST_Y(location)) as avg_latitude
        FROM parking_spots
        UNION ALL
        SELECT 
            'parking_lots'::TEXT as table_name,
            COUNT(*) as total_records,
            COUNT(CASE WHEN location IS NOT NULL THEN 1 END) as records_with_location,
            ST_Extent(location) as spatial_extent,
            AVG(ST_X(location)) as avg_longitude,
            AVG(ST_Y(location)) as avg_latitude
        FROM parking_lots
    """))


def downgrade():
    """
    Remove spatial indexes and functions
    """
    connection = op.get_bind()
    
    # Drop spatial functions
    connection.execute(text("DROP FUNCTION IF EXISTS find_nearest_parking_spots CASCADE"))
    connection.execute(text("DROP FUNCTION IF EXISTS cluster_parking_spots_in_region CASCADE"))
    connection.execute(text("DROP VIEW IF EXISTS spatial_performance_stats CASCADE"))
    
    # Drop spatial indexes
    connection.execute(text("DROP INDEX IF EXISTS idx_parking_spots_location_rtree"))
    connection.execute(text("DROP INDEX IF EXISTS idx_parking_lots_location_rtree"))
    connection.execute(text("DROP INDEX IF EXISTS idx_parking_lots_boundary_rtree"))
    
    connection.execute(text("DROP INDEX IF EXISTS idx_parking_spots_geohash_6"))
    connection.execute(text("DROP INDEX IF EXISTS idx_parking_spots_geohash_8"))
    connection.execute(text("DROP INDEX IF EXISTS idx_parking_lots_geohash_6"))
    connection.execute(text("DROP INDEX IF EXISTS idx_parking_lots_geohash_8"))
    
    connection.execute(text("DROP INDEX IF EXISTS idx_parking_spots_h3_6"))
    connection.execute(text("DROP INDEX IF EXISTS idx_parking_spots_h3_8"))
    connection.execute(text("DROP INDEX IF EXISTS idx_parking_lots_h3_6"))
    connection.execute(text("DROP INDEX IF EXISTS idx_parking_lots_h3_8"))
    
    # Drop spatial columns
    connection.execute(text("ALTER TABLE parking_spots DROP COLUMN IF EXISTS geohash_6"))
    connection.execute(text("ALTER TABLE parking_spots DROP COLUMN IF EXISTS geohash_8"))
    connection.execute(text("ALTER TABLE parking_spots DROP COLUMN IF EXISTS h3_index_6"))
    connection.execute(text("ALTER TABLE parking_spots DROP COLUMN IF EXISTS h3_index_8"))
    
    connection.execute(text("ALTER TABLE parking_lots DROP COLUMN IF EXISTS geohash_6"))
    connection.execute(text("ALTER TABLE parking_lots DROP COLUMN IF EXISTS geohash_8"))
    connection.execute(text("ALTER TABLE parking_lots DROP COLUMN IF EXISTS h3_index_6"))
    connection.execute(text("ALTER TABLE parking_lots DROP COLUMN IF EXISTS h3_index_8"))
