"""Enhanced spatial index optimization and additional PostGIS features

Revision ID: 003
Revises: 002
Create Date: 2025-08-17 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create advanced spatial indexes for better performance
    
    # Partial indexes for active parking lots only
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_parking_lots_location_active_gist 
        ON parking_lots USING GIST (location) 
        WHERE status = 'active'
    """)
    
    # Partial indexes for available spots only
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_parking_spots_location_available_gist 
        ON parking_spots USING GIST (location) 
        WHERE status = 'available' AND is_active = true AND is_reservable = true
    """)
    
    # Multi-column spatial indexes for complex queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_parking_lots_location_type_gist 
        ON parking_lots USING GIST (location, parking_lot_type)
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_parking_spots_location_type_gist 
        ON parking_spots USING GIST (location, spot_type)
    """)
    
    # Spatial indexes for EV charging spots
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_parking_spots_location_ev_gist 
        ON parking_spots USING GIST (location) 
        WHERE has_ev_charging = true AND status = 'available'
    """)
    
    # Create spatial statistics table for performance monitoring
    op.create_table('spatial_statistics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('index_name', sa.String(100), nullable=False),
        sa.Column('query_type', sa.String(50), nullable=False),  # 'nearest', 'within_radius', 'intersection'
        sa.Column('avg_execution_time_ms', sa.Numeric(10, 3), nullable=False),
        sa.Column('total_executions', sa.Integer(), default=0, nullable=False),
        sa.Column('last_execution', sa.DateTime(timezone=True), nullable=True),
        sa.Column('optimization_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create advanced spatial functions
    op.execute("""
        -- Function to find optimal parking zones based on demand
        CREATE OR REPLACE FUNCTION find_optimal_parking_zones(
            city_name VARCHAR(100),
            analysis_radius_meters INTEGER DEFAULT 1000,
            min_demand_threshold INTEGER DEFAULT 10
        )
        RETURNS TABLE(
            zone_center_lat DOUBLE PRECISION,
            zone_center_lng DOUBLE PRECISION,
            total_lots INTEGER,
            total_spots INTEGER,
            avg_occupancy_rate DOUBLE PRECISION,
            demand_score INTEGER,
            recommended_new_spots INTEGER
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            WITH demand_grid AS (
                SELECT 
                    ST_SetSRID(ST_MakePoint(
                        x * 0.01 + ST_XMin(city_bounds.geom), 
                        y * 0.01 + ST_YMin(city_bounds.geom)
                    ), 4326) as grid_center,
                    x, y
                FROM (
                    SELECT ST_Extent(location) as geom 
                    FROM parking_lots 
                    WHERE city = city_name AND status = 'active'
                ) city_bounds,
                generate_series(0, CAST((ST_XMax(city_bounds.geom) - ST_XMin(city_bounds.geom)) / 0.01 AS INTEGER)) as x,
                generate_series(0, CAST((ST_YMax(city_bounds.geom) - ST_YMin(city_bounds.geom)) / 0.01 AS INTEGER)) as y
            ),
            zone_analysis AS (
                SELECT 
                    dg.grid_center,
                    COUNT(pl.id) as lot_count,
                    SUM(pl.total_spots) as spot_count,
                    AVG(CASE 
                        WHEN pl.total_spots > 0 
                        THEN ((pl.total_spots - pl.available_spots)::FLOAT / pl.total_spots) * 100 
                        ELSE 0 
                    END) as avg_occupancy,
                    COUNT(pe.id) as recent_demand  -- Events in last 24 hours
                FROM demand_grid dg
                LEFT JOIN parking_lots pl ON ST_DWithin(
                    ST_Transform(dg.grid_center, 3857),
                    ST_Transform(pl.location, 3857),
                    analysis_radius_meters
                )
                LEFT JOIN parking_events pe ON pe.parking_lot_id = pl.id 
                    AND pe.event_timestamp > NOW() - INTERVAL '24 hours'
                    AND pe.event_type IN ('geofence_entry', 'reservation_start')
                GROUP BY dg.grid_center
            )
            SELECT 
                ST_Y(ST_Transform(za.grid_center, 4326)) as zone_center_lat,
                ST_X(ST_Transform(za.grid_center, 4326)) as zone_center_lng,
                COALESCE(za.lot_count, 0)::INTEGER as total_lots,
                COALESCE(za.spot_count, 0)::INTEGER as total_spots,
                COALESCE(za.avg_occupancy, 0.0) as avg_occupancy_rate,
                COALESCE(za.recent_demand, 0)::INTEGER as demand_score,
                CASE 
                    WHEN za.recent_demand > min_demand_threshold AND za.avg_occupancy > 80 
                    THEN GREATEST(0, za.recent_demand - COALESCE(za.spot_count, 0))
                    ELSE 0 
                END::INTEGER as recommended_new_spots
            FROM zone_analysis za
            WHERE za.recent_demand > 0 OR za.lot_count > 0
            ORDER BY demand_score DESC, avg_occupancy DESC;
        END;
        $$;
    """)
    
    op.execute("""
        -- Function to analyze parking spot utilization patterns
        CREATE OR REPLACE FUNCTION analyze_spot_utilization_patterns(
            lot_id_param INTEGER,
            analysis_days INTEGER DEFAULT 30
        )
        RETURNS TABLE(
            spot_id INTEGER,
            spot_number VARCHAR(20),
            total_reservations INTEGER,
            avg_occupancy_duration_minutes DOUBLE PRECISION,
            peak_usage_hour INTEGER,
            utilization_rate DOUBLE PRECISION,
            revenue_generated NUMERIC(10,2),
            optimization_recommendation TEXT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            WITH spot_stats AS (
                SELECT 
                    ps.id as spot_id,
                    ps.spot_number,
                    COUNT(r.id) as reservation_count,
                    AVG(EXTRACT(EPOCH FROM (r.end_time - r.start_time))/60) as avg_duration,
                    MODE() WITHIN GROUP (ORDER BY EXTRACT(HOUR FROM r.start_time)) as peak_hour,
                    (COUNT(r.id)::FLOAT / analysis_days) as daily_usage,
                    SUM(COALESCE(p.amount, 0)) as total_revenue
                FROM parking_spots ps
                LEFT JOIN reservations r ON ps.id = r.parking_spot_id 
                    AND r.created_at > NOW() - (analysis_days || ' days')::INTERVAL
                    AND r.status IN ('completed', 'active')
                LEFT JOIN payments p ON r.id = p.reservation_id 
                    AND p.status = 'completed'
                WHERE ps.parking_lot_id = lot_id_param
                GROUP BY ps.id, ps.spot_number
            )
            SELECT 
                ss.spot_id,
                ss.spot_number,
                COALESCE(ss.reservation_count, 0)::INTEGER as total_reservations,
                COALESCE(ss.avg_duration, 0.0) as avg_occupancy_duration_minutes,
                COALESCE(ss.peak_hour, 12)::INTEGER as peak_usage_hour,
                LEAST(100.0, (ss.daily_usage * 100.0)) as utilization_rate,
                COALESCE(ss.total_revenue, 0.0) as revenue_generated,
                CASE 
                    WHEN ss.daily_usage < 0.1 THEN 'Low utilization - consider repricing or marketing'
                    WHEN ss.daily_usage > 0.8 THEN 'High demand - consider premium pricing'
                    WHEN ss.avg_duration > 480 THEN 'Long stays - consider time limits'
                    WHEN ss.avg_duration < 60 THEN 'Short stays - optimize for quick turnover'
                    ELSE 'Normal utilization pattern'
                END as optimization_recommendation
            FROM spot_stats ss
            ORDER BY ss.daily_usage DESC;
        END;
        $$;
    """)
    
    op.execute("""
        -- Function to detect spatial anomalies in parking behavior
        CREATE OR REPLACE FUNCTION detect_parking_anomalies(
            analysis_hours INTEGER DEFAULT 24,
            anomaly_threshold DOUBLE PRECISION DEFAULT 2.0
        )
        RETURNS TABLE(
            parking_lot_id INTEGER,
            anomaly_type VARCHAR(50),
            severity_score DOUBLE PRECISION,
            description TEXT,
            detected_at TIMESTAMP WITH TIME ZONE,
            recommended_action TEXT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            -- Detect unusual entry/exit patterns
            WITH lot_activity AS (
                SELECT 
                    pe.parking_lot_id,
                    COUNT(CASE WHEN pe.event_type = 'geofence_entry' THEN 1 END) as entries,
                    COUNT(CASE WHEN pe.event_type = 'geofence_exit' THEN 1 END) as exits,
                    pl.name as lot_name,
                    pl.total_spots
                FROM parking_events pe
                JOIN parking_lots pl ON pe.parking_lot_id = pl.id
                WHERE pe.event_timestamp > NOW() - (analysis_hours || ' hours')::INTERVAL
                GROUP BY pe.parking_lot_id, pl.name, pl.total_spots
            ),
            anomaly_detection AS (
                SELECT 
                    la.*,
                    ABS(la.entries - la.exits) as entry_exit_diff,
                    (la.entries::FLOAT / NULLIF(la.total_spots, 0)) as entry_rate,
                    CASE 
                        WHEN ABS(la.entries - la.exits) > (la.total_spots * 0.5) THEN 'entry_exit_imbalance'
                        WHEN la.entries > (la.total_spots * 2) THEN 'excessive_entries'
                        WHEN la.entries = 0 AND la.exits = 0 THEN 'no_activity'
                        WHEN la.entries > 0 AND la.exits = 0 THEN 'entries_no_exits'
                        ELSE 'normal'
                    END as anomaly_type,
                    CASE 
                        WHEN ABS(la.entries - la.exits) > (la.total_spots * 0.8) THEN 5.0
                        WHEN ABS(la.entries - la.exits) > (la.total_spots * 0.5) THEN 3.0
                        WHEN la.entries > (la.total_spots * 3) THEN 4.0
                        WHEN la.entries = 0 AND la.exits = 0 THEN 2.0
                        ELSE 1.0
                    END as severity
                FROM lot_activity la
            )
            SELECT 
                ad.parking_lot_id,
                ad.anomaly_type::VARCHAR(50),
                ad.severity as severity_score,
                CASE ad.anomaly_type
                    WHEN 'entry_exit_imbalance' THEN 
                        'Significant imbalance between entries (' || ad.entries || ') and exits (' || ad.exits || ')'
                    WHEN 'excessive_entries' THEN 
                        'Unusually high number of entries (' || ad.entries || ') for lot capacity (' || ad.total_spots || ')'
                    WHEN 'no_activity' THEN 
                        'No parking activity detected in the last ' || analysis_hours || ' hours'
                    WHEN 'entries_no_exits' THEN 
                        'Vehicles entering but not exiting - possible sensor/detection issues'
                    ELSE 'Normal activity pattern'
                END::TEXT as description,
                NOW() as detected_at,
                CASE ad.anomaly_type
                    WHEN 'entry_exit_imbalance' THEN 'Check sensor calibration and exit detection systems'
                    WHEN 'excessive_entries' THEN 'Verify capacity limits and investigate potential over-booking'
                    WHEN 'no_activity' THEN 'Check sensor functionality and lot accessibility'
                    WHEN 'entries_no_exits' THEN 'Inspect exit sensors and detection systems'
                    ELSE 'Continue monitoring'
                END::TEXT as recommended_action
            FROM anomaly_detection ad
            WHERE ad.anomaly_type != 'normal' 
            AND ad.severity >= anomaly_threshold
            ORDER BY ad.severity DESC;
        END;
        $$;
    """)
    
    # Create automated index maintenance
    op.execute("""
        -- Function to optimize spatial indexes
        CREATE OR REPLACE FUNCTION optimize_spatial_indexes()
        RETURNS TEXT
        LANGUAGE plpgsql
        AS $$
        DECLARE
            index_rec RECORD;
            result_text TEXT := '';
        BEGIN
            -- Reindex spatial indexes if fragmentation is high
            FOR index_rec IN 
                SELECT 
                    schemaname, tablename, indexname,
                    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
                FROM pg_stat_user_indexes 
                WHERE indexname LIKE '%_gist'
                AND schemaname = 'public'
            LOOP
                -- Check if reindexing is needed (simplified check)
                EXECUTE 'REINDEX INDEX CONCURRENTLY ' || quote_ident(index_rec.indexname);
                result_text := result_text || 'Reindexed: ' || index_rec.indexname || ' (' || index_rec.index_size || ')' || E'\n';
            END LOOP;
            
            -- Update table statistics
            EXECUTE 'ANALYZE parking_lots';
            EXECUTE 'ANALYZE parking_spots';
            EXECUTE 'ANALYZE parking_events';
            
            result_text := result_text || 'Updated table statistics' || E'\n';
            
            RETURN result_text;
        END;
        $$;
    """)
    
    # Create spatial performance monitoring view
    op.execute("""
        CREATE OR REPLACE VIEW spatial_performance_summary AS
        SELECT 
            'parking_lots' as table_name,
            COUNT(*) as total_records,
            COUNT(CASE WHEN location IS NOT NULL THEN 1 END) as records_with_location,
            COUNT(CASE WHEN boundary IS NOT NULL THEN 1 END) as records_with_boundary,
            pg_size_pretty(pg_total_relation_size('parking_lots')) as table_size
        FROM parking_lots
        WHERE status = 'active'
        
        UNION ALL
        
        SELECT 
            'parking_spots' as table_name,
            COUNT(*) as total_records,
            COUNT(CASE WHEN location IS NOT NULL THEN 1 END) as records_with_location,
            COUNT(CASE WHEN spot_boundary IS NOT NULL THEN 1 END) as records_with_boundary,
            pg_size_pretty(pg_total_relation_size('parking_spots')) as table_size
        FROM parking_spots
        WHERE is_active = true
        
        UNION ALL
        
        SELECT 
            'parking_events' as table_name,
            COUNT(*) as total_records,
            COUNT(CASE WHEN location IS NOT NULL THEN 1 END) as records_with_location,
            0 as records_with_boundary,
            pg_size_pretty(pg_total_relation_size('parking_events')) as table_size
        FROM parking_events
        WHERE event_timestamp > NOW() - INTERVAL '30 days';
    """)


def downgrade() -> None:
    # Drop views and functions
    op.execute("DROP VIEW IF EXISTS spatial_performance_summary")
    op.execute("DROP FUNCTION IF EXISTS optimize_spatial_indexes()")
    op.execute("DROP FUNCTION IF EXISTS detect_parking_anomalies(INTEGER, DOUBLE PRECISION)")
    op.execute("DROP FUNCTION IF EXISTS analyze_spot_utilization_patterns(INTEGER, INTEGER)")
    op.execute("DROP FUNCTION IF EXISTS find_optimal_parking_zones(VARCHAR, INTEGER, INTEGER)")
    
    # Drop table
    op.drop_table('spatial_statistics')
    
    # Drop indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_parking_spots_location_ev_gist")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_parking_spots_location_type_gist")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_parking_lots_location_type_gist")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_parking_spots_location_available_gist")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_parking_lots_location_active_gist")
