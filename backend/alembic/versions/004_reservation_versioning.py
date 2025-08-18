"""
Enhanced reservation system with versioning and concurrency control

Revision ID: 004_reservation_versioning
Revises: 003_spatial_indexes_and_functions
Create Date: 2025-08-18 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '004_reservation_versioning'
down_revision = '003_spatial_indexes_and_functions'
branch_labels = None
depends_on = None

def upgrade():
    """Add versioning and concurrency control features"""
    
    # Add version column to reservations for optimistic concurrency control
    op.add_column('reservations', sa.Column('version', sa.Integer, nullable=False, default=1))
    
    # Add version column to parking_spots
    op.add_column('parking_spots', sa.Column('version', sa.Integer, nullable=False, default=1))
    
    # Add request tracking table for reservation queue management
    op.create_table(
        'reservation_requests',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('request_id', sa.String(36), unique=True, nullable=False, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('vehicle_id', sa.Integer, sa.ForeignKey('vehicles.id'), nullable=False),
        sa.Column('parking_lot_id', sa.Integer, sa.ForeignKey('parking_lots.id'), nullable=False),
        sa.Column('preferred_spot_id', sa.Integer, sa.ForeignKey('parking_spots.id'), nullable=True),
        
        # Request details
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False, default='normal'),
        sa.Column('requires_ev_charging', sa.Boolean, default=False),
        sa.Column('requires_handicapped_access', sa.Boolean, default=False),
        sa.Column('special_requests', sa.Text, nullable=True),
        
        # Queue management
        sa.Column('status', sa.String(20), nullable=False, default='queued', index=True),
        sa.Column('queue_position', sa.Integer, nullable=True),
        sa.Column('max_wait_time_seconds', sa.Integer, default=300),
        
        # Results
        sa.Column('reservation_id', sa.Integer, sa.ForeignKey('reservations.id'), nullable=True),
        sa.Column('assigned_spot_id', sa.Integer, sa.ForeignKey('parking_spots.id'), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        
        # Timing
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_time_ms', sa.Integer, nullable=True),
        
        # Metadata
        sa.Column('correlation_id', sa.String(36), nullable=True, index=True),
        sa.Column('metadata', sa.JSON, nullable=True)
    )
    
    # Create event store table for event sourcing
    op.create_table(
        'event_store',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('event_id', sa.String(36), unique=True, nullable=False, index=True),
        sa.Column('event_type', sa.String(50), nullable=False, index=True),
        sa.Column('aggregate_type', sa.String(50), nullable=False, index=True),
        sa.Column('aggregate_id', sa.String(50), nullable=False, index=True),
        sa.Column('version', sa.Integer, nullable=False),
        
        # Event data
        sa.Column('event_data', sa.JSON, nullable=False),
        sa.Column('metadata', sa.JSON, nullable=False),
        
        # Event properties
        sa.Column('priority', sa.String(20), default='normal'),
        sa.Column('correlation_id', sa.String(36), nullable=True, index=True),
        sa.Column('causation_id', sa.String(36), nullable=True),
        
        # Timing
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        # Composite index for aggregate events ordering
        sa.Index('idx_event_store_aggregate', 'aggregate_type', 'aggregate_id', 'version')
    )
    
    # Create notification preferences table
    op.create_table(
        'notification_preferences',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, unique=True),
        
        # Channel preferences
        sa.Column('email_enabled', sa.Boolean, default=True),
        sa.Column('sms_enabled', sa.Boolean, default=False),
        sa.Column('push_enabled', sa.Boolean, default=True),
        sa.Column('websocket_enabled', sa.Boolean, default=True),
        
        # Event type preferences (JSON with event_type -> enabled mapping)
        sa.Column('event_preferences', sa.JSON, nullable=True),
        
        # Contact information
        sa.Column('phone_number', sa.String(20), nullable=True),
        sa.Column('push_token', sa.String(500), nullable=True),
        
        # Timing preferences
        sa.Column('quiet_hours_start', sa.Time, nullable=True),
        sa.Column('quiet_hours_end', sa.Time, nullable=True),
        sa.Column('timezone', sa.String(50), default='UTC'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create system alerts table for capacity and performance monitoring
    op.create_table(
        'system_alerts',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('alert_id', sa.String(36), unique=True, nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False, index=True),
        sa.Column('severity', sa.String(20), nullable=False, index=True),  # low, medium, high, critical
        
        # Alert details
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('alert_data', sa.JSON, nullable=True),
        
        # Targeting
        sa.Column('parking_lot_id', sa.Integer, sa.ForeignKey('parking_lots.id'), nullable=True, index=True),
        sa.Column('affected_resource_type', sa.String(50), nullable=True),
        sa.Column('affected_resource_id', sa.String(50), nullable=True),
        
        # Status and resolution
        sa.Column('status', sa.String(20), default='active', index=True),  # active, acknowledged, resolved
        sa.Column('acknowledged_by', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text, nullable=True),
        
        # Timing
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Add indexes for performance optimization
    
    # Reservation version index for concurrency control
    op.create_index(
        'idx_reservations_version',
        'reservations',
        ['id', 'version']
    )
    
    # Spot version index
    op.create_index(
        'idx_parking_spots_version', 
        'parking_spots',
        ['id', 'version']
    )
    
    # Reservation request status and priority index
    op.create_index(
        'idx_reservation_requests_status_priority',
        'reservation_requests',
        ['status', 'priority', 'created_at']
    )
    
    # Event store performance indexes
    op.create_index(
        'idx_event_store_type_timestamp',
        'event_store',
        ['event_type', 'timestamp']
    )
    
    op.create_index(
        'idx_event_store_correlation',
        'event_store',
        ['correlation_id', 'timestamp']
    )
    
    # System alerts active status index
    op.create_index(
        'idx_system_alerts_active',
        'system_alerts',
        ['status', 'severity', 'triggered_at']
    )
    
    # Add triggers for automatic version incrementing
    
    # Reservation version trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION increment_reservation_version()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                NEW.version = OLD.version + 1;
                NEW.updated_at = NOW();
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER reservation_version_trigger
        BEFORE UPDATE ON reservations
        FOR EACH ROW
        EXECUTE FUNCTION increment_reservation_version();
    """)
    
    # Parking spot version trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION increment_spot_version()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                NEW.version = OLD.version + 1;
                NEW.updated_at = NOW();
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER spot_version_trigger
        BEFORE UPDATE ON parking_spots
        FOR EACH ROW
        EXECUTE FUNCTION increment_spot_version();
    """)
    
    # Create function for optimistic concurrency check
    op.execute("""
        CREATE OR REPLACE FUNCTION check_reservation_version(
            p_reservation_id INTEGER,
            p_expected_version INTEGER
        ) RETURNS BOOLEAN AS $$
        DECLARE
            current_version INTEGER;
        BEGIN
            SELECT version INTO current_version
            FROM reservations
            WHERE id = p_reservation_id;
            
            RETURN current_version = p_expected_version;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE OR REPLACE FUNCTION check_spot_version(
            p_spot_id INTEGER,
            p_expected_version INTEGER
        ) RETURNS BOOLEAN AS $$
        DECLARE
            current_version INTEGER;
        BEGIN
            SELECT version INTO current_version
            FROM parking_spots
            WHERE id = p_spot_id;
            
            RETURN current_version = p_expected_version;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create function to prevent double booking with row-level locking
    op.execute("""
        CREATE OR REPLACE FUNCTION reserve_spot_atomic(
            p_spot_id INTEGER,
            p_reservation_id INTEGER,
            p_start_time TIMESTAMP WITH TIME ZONE,
            p_end_time TIMESTAMP WITH TIME ZONE
        ) RETURNS BOOLEAN AS $$
        DECLARE
            conflict_count INTEGER;
            spot_available BOOLEAN;
        BEGIN
            -- Lock the spot row
            SELECT 
                status = 'available' AND is_active = true AND is_reservable = true
            INTO spot_available
            FROM parking_spots
            WHERE id = p_spot_id
            FOR UPDATE;
            
            IF NOT spot_available THEN
                RETURN FALSE;
            END IF;
            
            -- Check for time conflicts
            SELECT COUNT(*) INTO conflict_count
            FROM reservations
            WHERE parking_spot_id = p_spot_id
            AND status IN ('confirmed', 'active', 'pending')
            AND (
                (start_time <= p_start_time AND end_time > p_start_time) OR
                (start_time < p_end_time AND end_time >= p_end_time) OR
                (start_time >= p_start_time AND end_time <= p_end_time)
            );
            
            IF conflict_count > 0 THEN
                RETURN FALSE;
            END IF;
            
            -- Reserve the spot
            UPDATE parking_spots
            SET status = 'reserved',
                status_changed_at = NOW()
            WHERE id = p_spot_id;
            
            RETURN TRUE;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create materialized view for real-time capacity monitoring
    op.execute("""
        CREATE MATERIALIZED VIEW parking_lot_capacity AS
        SELECT 
            pl.id as parking_lot_id,
            pl.name as lot_name,
            COUNT(ps.id) as total_spots,
            COUNT(CASE WHEN ps.status = 'available' THEN 1 END) as available_spots,
            COUNT(CASE WHEN ps.status = 'occupied' THEN 1 END) as occupied_spots,
            COUNT(CASE WHEN ps.status = 'reserved' THEN 1 END) as reserved_spots,
            COUNT(CASE WHEN ps.status = 'out_of_order' THEN 1 END) as out_of_order_spots,
            ROUND(
                (COUNT(CASE WHEN ps.status IN ('occupied', 'reserved') THEN 1 END)::NUMERIC / 
                 NULLIF(COUNT(ps.id), 0)) * 100, 2
            ) as capacity_percentage,
            NOW() as last_updated
        FROM parking_lots pl
        LEFT JOIN parking_spots ps ON pl.id = ps.parking_lot_id 
            AND ps.is_active = true
        GROUP BY pl.id, pl.name;
    """)
    
    # Create unique index on materialized view
    op.create_unique_index(
        'idx_parking_lot_capacity_unique',
        'parking_lot_capacity',
        ['parking_lot_id']
    )
    
    # Create function to refresh capacity view
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_parking_lot_capacity()
        RETURNS VOID AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY parking_lot_capacity;
        END;
        $$ LANGUAGE plpgsql;
    """)

def downgrade():
    """Remove versioning and concurrency control features"""
    
    # Drop materialized view
    op.execute("DROP MATERIALIZED VIEW IF EXISTS parking_lot_capacity CASCADE")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS refresh_parking_lot_capacity()")
    op.execute("DROP FUNCTION IF EXISTS reserve_spot_atomic(INTEGER, INTEGER, TIMESTAMP WITH TIME ZONE, TIMESTAMP WITH TIME ZONE)")
    op.execute("DROP FUNCTION IF EXISTS check_spot_version(INTEGER, INTEGER)")
    op.execute("DROP FUNCTION IF EXISTS check_reservation_version(INTEGER, INTEGER)")
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS spot_version_trigger ON parking_spots")
    op.execute("DROP TRIGGER IF EXISTS reservation_version_trigger ON reservations")
    
    # Drop trigger functions
    op.execute("DROP FUNCTION IF EXISTS increment_spot_version()")
    op.execute("DROP FUNCTION IF EXISTS increment_reservation_version()")
    
    # Drop indexes
    op.drop_index('idx_system_alerts_active', 'system_alerts')
    op.drop_index('idx_event_store_correlation', 'event_store')
    op.drop_index('idx_event_store_type_timestamp', 'event_store')
    op.drop_index('idx_reservation_requests_status_priority', 'reservation_requests')
    op.drop_index('idx_parking_spots_version', 'parking_spots')
    op.drop_index('idx_reservations_version', 'reservations')
    
    # Drop tables
    op.drop_table('system_alerts')
    op.drop_table('notification_preferences')
    op.drop_table('event_store')
    op.drop_table('reservation_requests')
    
    # Remove version columns
    op.drop_column('parking_spots', 'version')
    op.drop_column('reservations', 'version')
