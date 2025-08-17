"""Enhanced schema with additional indexes and constraints

Revision ID: 004
Revises: 003
Create Date: 2025-08-17 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema with additional indexes and constraints"""
    
    # Add composite indexes for better query performance
    op.create_index('ix_parking_spots_lot_status_type', 'parking_spots', 
                   ['parking_lot_id', 'status', 'spot_type'], unique=False)
    
    op.create_index('ix_reservations_user_status_dates', 'reservations', 
                   ['user_id', 'status', 'start_time', 'end_time'], unique=False)
    
    op.create_index('ix_payments_user_status_method', 'payments', 
                   ['user_id', 'status', 'payment_method'], unique=False)
    
    op.create_index('ix_users_role_status', 'users', 
                   ['role', 'status'], unique=False)
    
    op.create_index('ix_vehicles_owner_active', 'vehicles', 
                   ['owner_id', 'is_active'], unique=False)
    
    # Add partial indexes for better performance on filtered queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_spots_available 
        ON parking_spots (parking_lot_id, spot_type) 
        WHERE status = 'available'
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_reservations_active 
        ON reservations (parking_lot_id, start_time, end_time) 
        WHERE status IN ('confirmed', 'active')
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_payments_pending 
        ON payments (created_at, payment_method) 
        WHERE status = 'pending'
    """)
    
    # Add check constraints for data integrity
    op.create_check_constraint(
        'ck_parking_lots_coordinates_valid',
        'parking_lots',
        'latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180'
    )
    
    op.create_check_constraint(
        'ck_parking_lots_spots_consistency',
        'parking_lots',
        'available_spots + reserved_spots <= total_spots'
    )
    
    op.create_check_constraint(
        'ck_parking_spots_dimensions_positive',
        'parking_spots',
        'length_cm > 0 AND width_cm > 0 AND height_cm > 0'
    )
    
    op.create_check_constraint(
        'ck_reservations_time_logical',
        'reservations',
        'end_time > start_time'
    )
    
    op.create_check_constraint(
        'ck_payments_amounts_positive',
        'payments',
        'amount >= 0 AND tax_amount >= 0 AND fee_amount >= 0'
    )
    
    # Add triggers for automatic timestamp updates
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Apply update triggers to all tables with updated_at columns
    tables_with_updated_at = [
        'users', 'vehicles', 'parking_lots', 'parking_spots', 
        'reservations', 'payments', 'occupancy_analytics', 'revenue_analytics'
    ]
    
    for table in tables_with_updated_at:
        op.execute(f"""
            DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
            CREATE TRIGGER update_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)
    
    # Add function for parking spot status updates
    op.execute("""
        CREATE OR REPLACE FUNCTION update_parking_lot_occupancy()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Update parking lot occupancy counts when spot status changes
            IF TG_OP = 'UPDATE' AND OLD.status != NEW.status THEN
                -- Handle status change
                UPDATE parking_lots SET
                    available_spots = (
                        SELECT COUNT(*) FROM parking_spots 
                        WHERE parking_lot_id = NEW.parking_lot_id 
                        AND status = 'available'
                    ),
                    reserved_spots = (
                        SELECT COUNT(*) FROM parking_spots 
                        WHERE parking_lot_id = NEW.parking_lot_id 
                        AND status = 'reserved'
                    ),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.parking_lot_id;
            END IF;
            
            RETURN COALESCE(NEW, OLD);
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        DROP TRIGGER IF EXISTS update_parking_lot_occupancy_trigger ON parking_spots;
        CREATE TRIGGER update_parking_lot_occupancy_trigger
            AFTER UPDATE OF status ON parking_spots
            FOR EACH ROW
            EXECUTE FUNCTION update_parking_lot_occupancy();
    """)
    
    # Add function for reservation status updates
    op.execute("""
        CREATE OR REPLACE FUNCTION handle_reservation_status_change()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Update parking spot status based on reservation status
            IF TG_OP = 'UPDATE' AND OLD.status != NEW.status THEN
                CASE NEW.status
                    WHEN 'confirmed' THEN
                        -- Reserve the spot
                        UPDATE parking_spots SET 
                            status = 'reserved',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = NEW.parking_spot_id;
                    
                    WHEN 'active' THEN
                        -- Mark spot as occupied
                        UPDATE parking_spots SET 
                            status = 'occupied',
                            current_vehicle_id = NEW.vehicle_id,
                            occupied_since = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = NEW.parking_spot_id;
                    
                    WHEN 'completed', 'cancelled', 'expired', 'no_show' THEN
                        -- Free up the spot
                        UPDATE parking_spots SET 
                            status = 'available',
                            current_vehicle_id = NULL,
                            occupied_since = NULL,
                            last_occupied_at = CASE 
                                WHEN OLD.status = 'active' THEN CURRENT_TIMESTAMP 
                                ELSE last_occupied_at 
                            END,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = NEW.parking_spot_id;
                END CASE;
            END IF;
            
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        DROP TRIGGER IF EXISTS handle_reservation_status_change_trigger ON reservations;
        CREATE TRIGGER handle_reservation_status_change_trigger
            AFTER UPDATE OF status ON reservations
            FOR EACH ROW
            EXECUTE FUNCTION handle_reservation_status_change();
    """)


def downgrade() -> None:
    """Downgrade database schema"""
    
    # Remove triggers
    tables_with_updated_at = [
        'users', 'vehicles', 'parking_lots', 'parking_spots', 
        'reservations', 'payments', 'occupancy_analytics', 'revenue_analytics'
    ]
    
    for table in tables_with_updated_at:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};")
    
    op.execute("DROP TRIGGER IF EXISTS update_parking_lot_occupancy_trigger ON parking_spots;")
    op.execute("DROP TRIGGER IF EXISTS handle_reservation_status_change_trigger ON reservations;")
    
    # Remove functions
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    op.execute("DROP FUNCTION IF EXISTS update_parking_lot_occupancy();")
    op.execute("DROP FUNCTION IF EXISTS handle_reservation_status_change();")
    
    # Remove check constraints
    op.drop_constraint('ck_payments_amounts_positive', 'payments')
    op.drop_constraint('ck_reservations_time_logical', 'reservations')
    op.drop_constraint('ck_parking_spots_dimensions_positive', 'parking_spots')
    op.drop_constraint('ck_parking_lots_spots_consistency', 'parking_lots')
    op.drop_constraint('ck_parking_lots_coordinates_valid', 'parking_lots')
    
    # Remove partial indexes
    op.execute("DROP INDEX IF EXISTS ix_payments_pending;")
    op.execute("DROP INDEX IF EXISTS ix_reservations_active;")
    op.execute("DROP INDEX IF EXISTS ix_parking_spots_available;")
    
    # Remove composite indexes
    op.drop_index('ix_vehicles_owner_active', table_name='vehicles')
    op.drop_index('ix_users_role_status', table_name='users')
    op.drop_index('ix_payments_user_status_method', table_name='payments')
    op.drop_index('ix_reservations_user_status_dates', table_name='reservations')
    op.drop_index('ix_parking_spots_lot_status_type', table_name='parking_spots')
