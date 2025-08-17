"""PostGIS Spatial Extensions Setup

Revision ID: 002
Revises: 001
Create Date: 2025-08-17 19:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS extensions (should already be enabled in init script)
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_sfcgal")
    op.execute("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder")
    
    # Create spatial reference systems if not exists
    op.execute("""
        DO $$
        BEGIN
            -- Ensure WGS84 (SRID 4326) exists
            IF NOT EXISTS (SELECT 1 FROM spatial_ref_sys WHERE srid = 4326) THEN
                INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, proj4text, srtext) 
                VALUES (4326, 'EPSG', 4326, 
                    '+proj=longlat +datum=WGS84 +no_defs', 
                    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]');
            END IF;
            
            -- Ensure Web Mercator (SRID 3857) exists for mapping
            IF NOT EXISTS (SELECT 1 FROM spatial_ref_sys WHERE srid = 3857) THEN
                INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, proj4text, srtext)
                VALUES (3857, 'EPSG', 3857,
                    '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs',
                    'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]');
            END IF;
        END
        $$;
    """)
    
    # Create advanced spatial indexes with GiST (Generalized Search Tree)
    print("Creating spatial indexes...")
    
    # Parking lots spatial indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_parking_lots_location_gist ON parking_lots USING GIST (location)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_parking_lots_boundary_gist ON parking_lots USING GIST (boundary)")
    
    # Compound spatial index for location + status queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_parking_lots_location_status_gist 
        ON parking_lots USING GIST (location, status) 
        WHERE status = 'active'
    """)
    
    # Parking spots spatial indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_parking_spots_location_gist ON parking_spots USING GIST (location)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_parking_spots_boundary_gist ON parking_spots USING GIST (spot_boundary)")
    
    # Compound spatial index for spots with availability
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_parking_spots_location_available_gist 
        ON parking_spots USING GIST (location, status) 
        WHERE status = 'available' AND is_active = true
    """)
    
    # R-tree style index for nearest neighbor queries (using GiST with distance operator)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_parking_lots_location_distance_gist 
        ON parking_lots USING GIST (location gist_geometry_ops_nd)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_parking_spots_location_distance_gist 
        ON parking_spots USING GIST (location gist_geometry_ops_nd)
    """)
    
    # Create spatial functions for common operations
    op.execute("""
        -- Function to find parking lots within radius (in meters)
        CREATE OR REPLACE FUNCTION find_parking_lots_within_radius(
            search_lat DOUBLE PRECISION,
            search_lng DOUBLE PRECISION,
            radius_meters INTEGER DEFAULT 1000
        )
        RETURNS TABLE(
            id INTEGER,
            name VARCHAR(200),
            distance_meters DOUBLE PRECISION,
            available_spots INTEGER,
            total_spots INTEGER,
            hourly_rate NUMERIC(10,2),
            location_lat DOUBLE PRECISION,
            location_lng DOUBLE PRECISION
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            SELECT 
                pl.id,
                pl.name,
                ST_Distance(
                    ST_Transform(pl.location, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(search_lng, search_lat), 4326), 3857)
                ) as distance_meters,
                pl.available_spots,
                pl.total_spots,
                pl.base_hourly_rate,
                ST_Y(ST_Transform(pl.location, 4326)) as location_lat,
                ST_X(ST_Transform(pl.location, 4326)) as location_lng
            FROM parking_lots pl
            WHERE 
                pl.status = 'active'
                AND ST_DWithin(
                    ST_Transform(pl.location, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(search_lng, search_lat), 4326), 3857),
                    radius_meters
                )
            ORDER BY distance_meters ASC;
        END;
        $$;
    """)
    
    op.execute("""
        -- Function to find available parking spots within radius
        CREATE OR REPLACE FUNCTION find_available_spots_within_radius(
            search_lat DOUBLE PRECISION,
            search_lng DOUBLE PRECISION,
            radius_meters INTEGER DEFAULT 500,
            spot_type_filter VARCHAR(50) DEFAULT NULL,
            requires_ev_charging BOOLEAN DEFAULT FALSE
        )
        RETURNS TABLE(
            id INTEGER,
            parking_lot_id INTEGER,
            spot_number VARCHAR(20),
            spot_type VARCHAR(50),
            distance_meters DOUBLE PRECISION,
            has_ev_charging BOOLEAN,
            charging_type VARCHAR(50),
            hourly_rate NUMERIC(10,2),
            location_lat DOUBLE PRECISION,
            location_lng DOUBLE PRECISION
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            SELECT 
                ps.id,
                ps.parking_lot_id,
                ps.spot_number,
                ps.spot_type::VARCHAR(50),
                ST_Distance(
                    ST_Transform(ps.location, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(search_lng, search_lat), 4326), 3857)
                ) as distance_meters,
                ps.has_ev_charging,
                ps.charging_type::VARCHAR(50),
                COALESCE(ps.hourly_rate, pl.base_hourly_rate * ps.pricing_multiplier) as hourly_rate,
                ST_Y(ST_Transform(ps.location, 4326)) as location_lat,
                ST_X(ST_Transform(ps.location, 4326)) as location_lng
            FROM parking_spots ps
            JOIN parking_lots pl ON ps.parking_lot_id = pl.id
            WHERE 
                ps.status = 'available'
                AND ps.is_active = true
                AND ps.is_reservable = true
                AND pl.status = 'active'
                AND (spot_type_filter IS NULL OR ps.spot_type::TEXT = spot_type_filter)
                AND (requires_ev_charging = FALSE OR ps.has_ev_charging = TRUE)
                AND ST_DWithin(
                    ST_Transform(ps.location, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(search_lng, search_lat), 4326), 3857),
                    radius_meters
                )
            ORDER BY distance_meters ASC;
        END;
        $$;
    """)
    
    op.execute("""
        -- Function to check if a point is within parking lot boundaries
        CREATE OR REPLACE FUNCTION is_point_in_parking_lot(
            check_lat DOUBLE PRECISION,
            check_lng DOUBLE PRECISION,
            lot_id INTEGER
        )
        RETURNS BOOLEAN
        LANGUAGE plpgsql
        AS $$
        DECLARE
            lot_boundary GEOMETRY;
        BEGIN
            SELECT boundary INTO lot_boundary 
            FROM parking_lots 
            WHERE id = lot_id;
            
            IF lot_boundary IS NULL THEN
                -- If no boundary defined, use a 50-meter buffer around the location
                SELECT ST_Buffer(
                    ST_Transform(location, 3857), 
                    50  -- 50 meter buffer
                ) INTO lot_boundary
                FROM parking_lots 
                WHERE id = lot_id;
                
                -- Transform back to WGS84 for comparison
                lot_boundary := ST_Transform(lot_boundary, 4326);
            END IF;
            
            RETURN ST_Contains(
                lot_boundary,
                ST_SetSRID(ST_MakePoint(check_lng, check_lat), 4326)
            );
        END;
        $$;
    """)
    
    op.execute("""
        -- Function to calculate optimal parking spot assignment
        CREATE OR REPLACE FUNCTION find_optimal_parking_spot(
            user_lat DOUBLE PRECISION,
            user_lng DOUBLE PRECISION,
            vehicle_id_param INTEGER,
            preferred_lot_id INTEGER DEFAULT NULL,
            max_distance_meters INTEGER DEFAULT 1000
        )
        RETURNS TABLE(
            spot_id INTEGER,
            parking_lot_id INTEGER,
            spot_number VARCHAR(20),
            distance_meters DOUBLE PRECISION,
            compatibility_score INTEGER,
            estimated_cost NUMERIC(10,2)
        )
        LANGUAGE plpgsql
        AS $$
        DECLARE
            vehicle_rec RECORD;
        BEGIN
            -- Get vehicle information
            SELECT vehicle_type, fuel_type, length_cm, width_cm, height_cm, weight_kg
            INTO vehicle_rec
            FROM vehicles
            WHERE id = vehicle_id_param;
            
            RETURN QUERY
            SELECT 
                ps.id as spot_id,
                ps.parking_lot_id,
                ps.spot_number,
                ST_Distance(
                    ST_Transform(ps.location, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(user_lng, user_lat), 4326), 3857)
                ) as distance_meters,
                (
                    CASE 
                        -- Perfect match for electric vehicles
                        WHEN vehicle_rec.fuel_type IN ('electric', 'plug_in_hybrid') AND ps.has_ev_charging THEN 100
                        -- Good match for handicapped spots (if needed)
                        WHEN ps.spot_type = 'handicapped' AND ps.is_handicapped_accessible THEN 90
                        -- Standard compatibility
                        WHEN ps.spot_type = 'regular' THEN 80
                        -- Compact spot penalty for larger vehicles
                        WHEN ps.spot_type = 'compact' AND vehicle_rec.length_cm > 450 THEN 60
                        -- Motorcycle spots for motorcycles
                        WHEN ps.spot_type = 'motorcycle' AND vehicle_rec.vehicle_type = 'motorcycle' THEN 95
                        ELSE 70
                    END
                ) as compatibility_score,
                COALESCE(ps.hourly_rate, pl.base_hourly_rate * ps.pricing_multiplier) as estimated_cost
            FROM parking_spots ps
            JOIN parking_lots pl ON ps.parking_lot_id = pl.id
            WHERE 
                ps.status = 'available'
                AND ps.is_active = true
                AND ps.is_reservable = true
                AND pl.status = 'active'
                AND (preferred_lot_id IS NULL OR pl.id = preferred_lot_id)
                -- Size compatibility checks
                AND (ps.max_vehicle_length_cm IS NULL OR vehicle_rec.length_cm IS NULL OR ps.max_vehicle_length_cm >= vehicle_rec.length_cm)
                AND (ps.max_vehicle_width_cm IS NULL OR vehicle_rec.width_cm IS NULL OR ps.max_vehicle_width_cm >= vehicle_rec.width_cm)
                AND (ps.max_vehicle_height_cm IS NULL OR vehicle_rec.height_cm IS NULL OR ps.max_vehicle_height_cm >= vehicle_rec.height_cm)
                AND (ps.max_vehicle_weight_kg IS NULL OR vehicle_rec.weight_kg IS NULL OR ps.max_vehicle_weight_kg >= vehicle_rec.weight_kg)
                AND ST_DWithin(
                    ST_Transform(ps.location, 3857),
                    ST_Transform(ST_SetSRID(ST_MakePoint(user_lng, user_lat), 4326), 3857),
                    max_distance_meters
                )
            ORDER BY 
                compatibility_score DESC,
                distance_meters ASC,
                estimated_cost ASC
            LIMIT 10;
        END;
        $$;
    """)
    
    # Create geofencing triggers
    op.execute("""
        -- Function to handle geofence entry/exit events
        CREATE OR REPLACE FUNCTION handle_geofence_event()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            -- This would be called by external systems when GPS/sensor data indicates
            -- a vehicle has entered or exited a parking lot boundary
            
            IF TG_OP = 'INSERT' THEN
                -- Log the geofence event
                INSERT INTO parking_events (
                    event_type,
                    parking_lot_id,
                    vehicle_id,
                    location,
                    event_timestamp,
                    metadata
                ) VALUES (
                    'geofence_entry',
                    NEW.parking_lot_id,
                    NEW.vehicle_id,
                    NEW.location,
                    NOW(),
                    json_build_object(
                        'automatic_detection', true,
                        'confidence_score', NEW.confidence_score
                    )
                );
                
                RETURN NEW;
            END IF;
            
            RETURN NULL;
        END;
        $$;
    """)
    
    # Create table for parking events (for geofencing)
    op.create_table('parking_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),  # entry, exit, reservation_start, etc.
        sa.Column('parking_lot_id', sa.Integer(), nullable=False),
        sa.Column('parking_spot_id', sa.Integer(), nullable=True),
        sa.Column('vehicle_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('reservation_id', sa.Integer(), nullable=True),
        sa.Column('location', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('confidence_score', sa.Numeric(5,2), nullable=True),  # For automatic detection
        sa.Column('detection_method', sa.String(50), nullable=True),  # 'gps', 'sensor', 'manual', 'qr_code'
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('processed', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parking_lot_id'], ['parking_lots.id']),
        sa.ForeignKeyConstraint(['parking_spot_id'], ['parking_spots.id']),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['reservation_id'], ['reservations.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for parking events
    op.create_index('idx_parking_events_timestamp', 'parking_events', ['event_timestamp'])
    op.create_index('idx_parking_events_type', 'parking_events', ['event_type'])
    op.create_index('idx_parking_events_location_gist', 'parking_events', ['location'], postgresql_using='gist')
    op.create_index('idx_parking_events_processed', 'parking_events', ['processed'])
    
    # Create materialized view for spatial analytics
    op.execute("""
        CREATE MATERIALIZED VIEW parking_density_grid AS
        WITH grid AS (
            SELECT 
                ST_SetSRID(ST_MakePoint(
                    x * 0.001 + ST_XMin(bbox.geom), 
                    y * 0.001 + ST_YMin(bbox.geom)
                ), 4326) as center,
                x, y
            FROM (
                SELECT ST_Extent(location) as geom 
                FROM parking_lots 
                WHERE status = 'active'
            ) bbox,
            generate_series(0, CAST(ST_XMax(bbox.geom) - ST_XMin(bbox.geom) / 0.001 AS INTEGER)) as x,
            generate_series(0, CAST(ST_YMax(bbox.geom) - ST_YMin(bbox.geom) / 0.001 AS INTEGER)) as y
        )
        SELECT 
            x, y,
            center,
            COUNT(pl.id) as parking_lots_count,
            SUM(pl.total_spots) as total_spots,
            SUM(pl.available_spots) as available_spots,
            AVG(pl.base_hourly_rate) as avg_hourly_rate
        FROM grid g
        LEFT JOIN parking_lots pl ON ST_DWithin(
            ST_Transform(g.center, 3857),
            ST_Transform(pl.location, 3857),
            500  -- 500 meter radius
        )
        WHERE pl.status = 'active' OR pl.status IS NULL
        GROUP BY x, y, center;
    """)
    
    # Create index on materialized view
    op.execute("CREATE INDEX idx_parking_density_grid_center_gist ON parking_density_grid USING GIST (center)")
    
    # Create function to refresh spatial analytics
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_spatial_analytics()
        RETURNS VOID
        LANGUAGE plpgsql
        AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY parking_density_grid;
        END;
        $$;
    """)


def downgrade() -> None:
    # Drop materialized view
    op.execute("DROP MATERIALIZED VIEW IF EXISTS parking_density_grid")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS refresh_spatial_analytics()")
    op.execute("DROP FUNCTION IF EXISTS handle_geofence_event()")
    op.execute("DROP FUNCTION IF EXISTS find_optimal_parking_spot(DOUBLE PRECISION, DOUBLE PRECISION, INTEGER, INTEGER, INTEGER)")
    op.execute("DROP FUNCTION IF EXISTS is_point_in_parking_lot(DOUBLE PRECISION, DOUBLE PRECISION, INTEGER)")
    op.execute("DROP FUNCTION IF EXISTS find_available_spots_within_radius(DOUBLE PRECISION, DOUBLE PRECISION, INTEGER, VARCHAR, BOOLEAN)")
    op.execute("DROP FUNCTION IF EXISTS find_parking_lots_within_radius(DOUBLE PRECISION, DOUBLE PRECISION, INTEGER)")
    
    # Drop table
    op.drop_table('parking_events')
    
    # Drop spatial indexes
    op.execute("DROP INDEX IF EXISTS idx_parking_density_grid_center_gist")
    op.execute("DROP INDEX IF EXISTS idx_parking_events_processed")
    op.execute("DROP INDEX IF EXISTS idx_parking_events_location_gist")
    op.execute("DROP INDEX IF EXISTS idx_parking_events_type")
    op.execute("DROP INDEX IF EXISTS idx_parking_events_timestamp")
    op.execute("DROP INDEX IF EXISTS idx_parking_spots_location_distance_gist")
    op.execute("DROP INDEX IF EXISTS idx_parking_lots_location_distance_gist")
    op.execute("DROP INDEX IF EXISTS idx_parking_spots_location_available_gist")
    op.execute("DROP INDEX IF EXISTS idx_parking_lots_location_status_gist")
    op.execute("DROP INDEX IF EXISTS idx_parking_spots_boundary_gist")
    op.execute("DROP INDEX IF EXISTS idx_parking_spots_location_gist")
    op.execute("DROP INDEX IF EXISTS idx_parking_lots_boundary_gist")
    op.execute("DROP INDEX IF EXISTS idx_parking_lots_location_gist")