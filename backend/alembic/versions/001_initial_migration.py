"""Initial migration - Create all core tables

Revision ID: 001
Revises: 
Create Date: 2025-08-17 18:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types
    op.execute("CREATE TYPE userrole AS ENUM ('user', 'admin', 'manager', 'operator')")
    op.execute("CREATE TYPE userstatus AS ENUM ('active', 'inactive', 'suspended', 'pending_verification')")
    op.execute("CREATE TYPE vehicletype AS ENUM ('car', 'motorcycle', 'truck', 'van', 'electric_car', 'electric_motorcycle', 'bicycle', 'scooter')")
    op.execute("CREATE TYPE fueltype AS ENUM ('gasoline', 'diesel', 'electric', 'hybrid', 'plug_in_hybrid', 'cng', 'lpg')")
    op.execute("CREATE TYPE parkinglottype AS ENUM ('outdoor', 'indoor', 'underground', 'multi_level', 'street_parking')")
    op.execute("CREATE TYPE accesstype AS ENUM ('public', 'private', 'restricted', 'residential', 'commercial')")
    op.execute("CREATE TYPE parkinglotstatus AS ENUM ('active', 'inactive', 'maintenance', 'temporarily_closed')")
    op.execute("CREATE TYPE spotstatus AS ENUM ('available', 'occupied', 'reserved', 'out_of_order', 'maintenance')")
    op.execute("CREATE TYPE spottype AS ENUM ('regular', 'compact', 'handicapped', 'electric', 'motorcycle', 'loading_zone', 'vip', 'family')")
    op.execute("CREATE TYPE chargingtype AS ENUM ('none', 'type_1', 'type_2', 'ccs', 'chademo', 'tesla', 'universal')")
    op.execute("CREATE TYPE reservationstatus AS ENUM ('pending', 'confirmed', 'active', 'completed', 'cancelled', 'expired', 'no_show', 'overstayed')")
    op.execute("CREATE TYPE reservationtype AS ENUM ('immediate', 'scheduled', 'recurring')")
    op.execute("CREATE TYPE paymentstatus AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded', 'partially_refunded', 'disputed', 'chargeback')")
    op.execute("CREATE TYPE paymentmethod AS ENUM ('credit_card', 'debit_card', 'digital_wallet', 'bank_transfer', 'cash', 'mobile_payment', 'cryptocurrency', 'account_credit', 'gift_card', 'subscription')")
    op.execute("CREATE TYPE paymenttype AS ENUM ('reservation', 'extension', 'penalty', 'cancellation', 'subscription', 'refund', 'deposit', 'top_up')")
    op.execute("CREATE TYPE currency AS ENUM ('USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'CNY', 'INR')")
    op.execute("CREATE TYPE analyticsperiod AS ENUM ('hourly', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly')")

    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('salt', sa.String(length=100), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('date_of_birth', sa.DateTime(), nullable=True),
        sa.Column('role', sa.Enum('user', 'admin', 'manager', 'operator', name='userrole'), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'suspended', 'pending_verification', name='userstatus'), nullable=False),
        sa.Column('is_email_verified', sa.Boolean(), nullable=False),
        sa.Column('is_phone_verified', sa.Boolean(), nullable=False),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('password_reset_token', sa.String(length=255), nullable=True),
        sa.Column('password_reset_expires', sa.DateTime(), nullable=True),
        sa.Column('email_verification_token', sa.String(length=255), nullable=True),
        sa.Column('profile_picture_url', sa.String(length=500), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('notifications_enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create vehicles table
    op.create_table('vehicles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('license_plate', sa.String(length=20), nullable=False),
        sa.Column('vin', sa.String(length=17), nullable=True),
        sa.Column('make', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('color', sa.String(length=30), nullable=False),
        sa.Column('vehicle_type', sa.Enum('car', 'motorcycle', 'truck', 'van', 'electric_car', 'electric_motorcycle', 'bicycle', 'scooter', name='vehicletype'), nullable=False),
        sa.Column('fuel_type', sa.Enum('gasoline', 'diesel', 'electric', 'hybrid', 'plug_in_hybrid', 'cng', 'lpg', name='fueltype'), nullable=True),
        sa.Column('length_cm', sa.Integer(), nullable=True),
        sa.Column('width_cm', sa.Integer(), nullable=True),
        sa.Column('height_cm', sa.Integer(), nullable=True),
        sa.Column('weight_kg', sa.Integer(), nullable=True),
        sa.Column('battery_capacity_kwh', sa.Integer(), nullable=True),
        sa.Column('charging_port_type', sa.String(length=50), nullable=True),
        sa.Column('registration_number', sa.String(length=50), nullable=True),
        sa.Column('registration_expiry', sa.DateTime(), nullable=True),
        sa.Column('insurance_number', sa.String(length=100), nullable=True),
        sa.Column('insurance_expiry', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('nickname', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vehicles_id'), 'vehicles', ['id'], unique=False)
    op.create_index(op.f('ix_vehicles_license_plate'), 'vehicles', ['license_plate'], unique=True)
    op.create_index(op.f('ix_vehicles_owner_id'), 'vehicles', ['owner_id'], unique=False)

    # Create parking_lots table
    op.create_table('parking_lots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('location', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=False),
        sa.Column('boundary', geoalchemy2.types.Geometry(geometry_type='POLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column('latitude', sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column('longitude', sa.Numeric(precision=11, scale=8), nullable=False),
        sa.Column('total_spots', sa.Integer(), nullable=False),
        sa.Column('available_spots', sa.Integer(), nullable=False),
        sa.Column('reserved_spots', sa.Integer(), nullable=False),
        sa.Column('disabled_spots', sa.Integer(), nullable=False),
        sa.Column('electric_spots', sa.Integer(), nullable=False),
        sa.Column('motorcycle_spots', sa.Integer(), nullable=False),
        sa.Column('parking_lot_type', sa.Enum('outdoor', 'indoor', 'underground', 'multi_level', 'street_parking', name='parkinglottype'), nullable=False),
        sa.Column('access_type', sa.Enum('public', 'private', 'restricted', 'residential', 'commercial', name='accesstype'), nullable=False),
        sa.Column('total_floors', sa.Integer(), nullable=False),
        sa.Column('max_vehicle_height_cm', sa.Integer(), nullable=True),
        sa.Column('max_vehicle_weight_kg', sa.Integer(), nullable=True),
        sa.Column('base_hourly_rate', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('daily_rate', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('monthly_rate', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('pricing_rules', sa.JSON(), nullable=True),
        sa.Column('is_24_hours', sa.Boolean(), nullable=False),
        sa.Column('opening_time', sa.Time(), nullable=True),
        sa.Column('closing_time', sa.Time(), nullable=True),
        sa.Column('operating_days', sa.JSON(), nullable=True),
        sa.Column('has_security', sa.Boolean(), nullable=False),
        sa.Column('has_covered_parking', sa.Boolean(), nullable=False),
        sa.Column('has_ev_charging', sa.Boolean(), nullable=False),
        sa.Column('has_valet_service', sa.Boolean(), nullable=False),
        sa.Column('has_car_wash', sa.Boolean(), nullable=False),
        sa.Column('has_restrooms', sa.Boolean(), nullable=False),
        sa.Column('has_elevators', sa.Boolean(), nullable=False),
        sa.Column('has_wheelchair_access', sa.Boolean(), nullable=False),
        sa.Column('accepts_cash', sa.Boolean(), nullable=False),
        sa.Column('accepts_card', sa.Boolean(), nullable=False),
        sa.Column('accepts_mobile_payment', sa.Boolean(), nullable=False),
        sa.Column('requires_permit', sa.Boolean(), nullable=False),
        sa.Column('contact_phone', sa.String(length=20), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('manager_name', sa.String(length=200), nullable=True),
        sa.Column('operator_company', sa.String(length=200), nullable=True),
        sa.Column('status', sa.Enum('active', 'inactive', 'maintenance', 'temporarily_closed', name='parkinglotstatus'), nullable=False),
        sa.Column('is_reservation_enabled', sa.Boolean(), nullable=False),
        sa.Column('is_real_time_updates', sa.Boolean(), nullable=False),
        sa.Column('last_occupancy_update', sa.DateTime(timezone=True), nullable=True),
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.Column('image_urls', sa.JSON(), nullable=True),
        sa.Column('amenities', sa.JSON(), nullable=True),
        sa.Column('restrictions', sa.JSON(), nullable=True),
        sa.Column('special_instructions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_parking_lots_city'), 'parking_lots', ['city'], unique=False)
    op.create_index(op.f('ix_parking_lots_code'), 'parking_lots', ['code'], unique=True)
    op.create_index(op.f('ix_parking_lots_id'), 'parking_lots', ['id'], unique=False)
    op.create_index(op.f('ix_parking_lots_latitude'), 'parking_lots', ['latitude'], unique=False)
    op.create_index(op.f('ix_parking_lots_location'), 'parking_lots', ['location'], unique=False, postgresql_using='gist')
    op.create_index(op.f('ix_parking_lots_longitude'), 'parking_lots', ['longitude'], unique=False)
    op.create_index(op.f('ix_parking_lots_name'), 'parking_lots', ['name'], unique=False)

    # Create parking_spots table
    op.create_table('parking_spots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parking_lot_id', sa.Integer(), nullable=False),
        sa.Column('spot_number', sa.String(length=20), nullable=False),
        sa.Column('spot_code', sa.String(length=50), nullable=True),
        sa.Column('floor', sa.Integer(), nullable=False),
        sa.Column('section', sa.String(length=10), nullable=True),
        sa.Column('row', sa.String(length=10), nullable=True),
        sa.Column('zone', sa.String(length=50), nullable=True),
        sa.Column('location', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column('spot_boundary', geoalchemy2.types.Geometry(geometry_type='POLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column('latitude', sa.Numeric(precision=10, scale=8), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=11, scale=8), nullable=True),
        sa.Column('spot_type', sa.Enum('regular', 'compact', 'handicapped', 'electric', 'motorcycle', 'loading_zone', 'vip', 'family', name='spottype'), nullable=False),
        sa.Column('status', sa.Enum('available', 'occupied', 'reserved', 'out_of_order', 'maintenance', name='spotstatus'), nullable=False),
        sa.Column('length_cm', sa.Integer(), nullable=True),
        sa.Column('width_cm', sa.Integer(), nullable=True),
        sa.Column('height_cm', sa.Integer(), nullable=True),
        sa.Column('max_vehicle_length_cm', sa.Integer(), nullable=True),
        sa.Column('max_vehicle_width_cm', sa.Integer(), nullable=True),
        sa.Column('max_vehicle_height_cm', sa.Integer(), nullable=True),
        sa.Column('max_vehicle_weight_kg', sa.Integer(), nullable=True),
        sa.Column('has_ev_charging', sa.Boolean(), nullable=False),
        sa.Column('charging_type', sa.Enum('none', 'type_1', 'type_2', 'ccs', 'chademo', 'tesla', 'universal', name='chargingtype'), nullable=False),
        sa.Column('charging_power_kw', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('charging_network', sa.String(length=100), nullable=True),
        sa.Column('charging_station_id', sa.String(length=100), nullable=True),
        sa.Column('is_handicapped_accessible', sa.Boolean(), nullable=False),
        sa.Column('has_wider_access', sa.Boolean(), nullable=False),
        sa.Column('is_covered', sa.Boolean(), nullable=False),
        sa.Column('has_custom_pricing', sa.Boolean(), nullable=False),
        sa.Column('hourly_rate', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('daily_rate', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('pricing_multiplier', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('sensor_id', sa.String(length=100), nullable=True),
        sa.Column('has_sensor', sa.Boolean(), nullable=False),
        sa.Column('last_sensor_update', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sensor_battery_level', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_reservable', sa.Boolean(), nullable=False),
        sa.Column('current_vehicle_id', sa.Integer(), nullable=True),
        sa.Column('occupied_since', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_occupied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_occupancy_time', sa.Integer(), nullable=False),
        sa.Column('maintenance_notes', sa.Text(), nullable=True),
        sa.Column('last_maintenance_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('issue_reported', sa.Boolean(), nullable=False),
        sa.Column('issue_description', sa.Text(), nullable=True),
        sa.Column('issue_reported_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('special_instructions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status_changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['current_vehicle_id'], ['vehicles.id'], ),
        sa.ForeignKeyConstraint(['parking_lot_id'], ['parking_lots.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_parking_spots_id'), 'parking_spots', ['id'], unique=False)
    op.create_index(op.f('ix_parking_spots_location'), 'parking_spots', ['location'], unique=False, postgresql_using='gist')
    op.create_index(op.f('ix_parking_spots_parking_lot_id'), 'parking_spots', ['parking_lot_id'], unique=False)
    op.create_index(op.f('ix_parking_spots_sensor_id'), 'parking_spots', ['sensor_id'], unique=True)
    op.create_index(op.f('ix_parking_spots_spot_number'), 'parking_spots', ['spot_number'], unique=False)
    op.create_index(op.f('ix_parking_spots_status'), 'parking_spots', ['status'], unique=False)

    # Create reservations table
    op.create_table('reservations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('parking_lot_id', sa.Integer(), nullable=False),
        sa.Column('parking_spot_id', sa.Integer(), nullable=True),
        sa.Column('reservation_number', sa.String(length=50), nullable=False),
        sa.Column('confirmation_code', sa.String(length=20), nullable=False),
        sa.Column('reservation_type', sa.Enum('immediate', 'scheduled', 'recurring', name='reservationtype'), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actual_arrival_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_departure_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('grace_period_minutes', sa.Integer(), nullable=False),
        sa.Column('max_extension_hours', sa.Integer(), nullable=False),
        sa.Column('extended_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extension_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'confirmed', 'active', 'completed', 'cancelled', 'expired', 'no_show', 'overstayed', name='reservationstatus'), nullable=False),
        sa.Column('is_recurring', sa.Boolean(), nullable=False),
        sa.Column('parent_reservation_id', sa.Integer(), nullable=True),
        sa.Column('base_cost', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('total_cost', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('extension_cost', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('penalty_cost', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('is_paid', sa.Boolean(), nullable=False),
        sa.Column('payment_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refund_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('requires_ev_charging', sa.Boolean(), nullable=False),
        sa.Column('requires_handicapped_access', sa.Boolean(), nullable=False),
        sa.Column('preferred_spot_type', sa.String(length=50), nullable=True),
        sa.Column('special_requests', sa.Text(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.String(length=200), nullable=True),
        sa.Column('is_refundable', sa.Boolean(), nullable=False),
        sa.Column('cancellation_fee', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('recurrence_pattern', sa.JSON(), nullable=True),
        sa.Column('recurrence_end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_occurrence_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reminder_sent', sa.Boolean(), nullable=False),
        sa.Column('arrival_notification_sent', sa.Boolean(), nullable=False),
        sa.Column('departure_reminder_sent', sa.Boolean(), nullable=False),
        sa.Column('qr_code', sa.String(length=200), nullable=True),
        sa.Column('check_in_method', sa.String(length=50), nullable=True),
        sa.Column('check_out_method', sa.String(length=50), nullable=True),
        sa.Column('license_plate_verified', sa.Boolean(), nullable=False),
        sa.Column('spot_verified', sa.Boolean(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['parent_reservation_id'], ['reservations.id'], ),
        sa.ForeignKeyConstraint(['parking_lot_id'], ['parking_lots.id'], ),
        sa.ForeignKeyConstraint(['parking_spot_id'], ['parking_spots.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reservations_confirmation_code'), 'reservations', ['confirmation_code'], unique=True)
    op.create_index(op.f('ix_reservations_end_time'), 'reservations', ['end_time'], unique=False)
    op.create_index(op.f('ix_reservations_id'), 'reservations', ['id'], unique=False)
    op.create_index(op.f('ix_reservations_parking_lot_id'), 'reservations', ['parking_lot_id'], unique=False)
    op.create_index(op.f('ix_reservations_parking_spot_id'), 'reservations', ['parking_spot_id'], unique=False)
    op.create_index(op.f('ix_reservations_reservation_number'), 'reservations', ['reservation_number'], unique=True)
    op.create_index(op.f('ix_reservations_start_time'), 'reservations', ['start_time'], unique=False)
    op.create_index(op.f('ix_reservations_status'), 'reservations', ['status'], unique=False)
    op.create_index(op.f('ix_reservations_user_id'), 'reservations', ['user_id'], unique=False)
    op.create_index(op.f('ix_reservations_vehicle_id'), 'reservations', ['vehicle_id'], unique=False)

    # Create payments table
    op.create_table('payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reservation_id', sa.Integer(), nullable=True),
        sa.Column('payment_number', sa.String(length=50), nullable=False),
        sa.Column('external_transaction_id', sa.String(length=100), nullable=True),
        sa.Column('receipt_number', sa.String(length=50), nullable=True),
        sa.Column('payment_type', sa.Enum('reservation', 'extension', 'penalty', 'cancellation', 'subscription', 'refund', 'deposit', 'top_up', name='paymenttype'), nullable=False),
        sa.Column('payment_method', sa.Enum('credit_card', 'debit_card', 'digital_wallet', 'bank_transfer', 'cash', 'mobile_payment', 'cryptocurrency', 'account_credit', 'gift_card', 'subscription', name='paymentmethod'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded', 'partially_refunded', 'disputed', 'chargeback', name='paymentstatus'), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.Enum('USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'CNY', 'INR', name='currency'), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('fee_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('net_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('promotion_code', sa.String(length=50), nullable=True),
        sa.Column('promotion_discount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('payment_processor', sa.String(length=50), nullable=True),
        sa.Column('processor_fee', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('processor_transaction_id', sa.String(length=100), nullable=True),
        sa.Column('processor_response', sa.JSON(), nullable=True),
        sa.Column('masked_card_number', sa.String(length=20), nullable=True),
        sa.Column('card_brand', sa.String(length=20), nullable=True),
        sa.Column('card_expiry_month', sa.Integer(), nullable=True),
        sa.Column('card_expiry_year', sa.Integer(), nullable=True),
        sa.Column('billing_address', sa.JSON(), nullable=True),
        sa.Column('wallet_type', sa.String(length=50), nullable=True),
        sa.Column('wallet_transaction_id', sa.String(length=100), nullable=True),
        sa.Column('bank_account_last4', sa.String(length=4), nullable=True),
        sa.Column('bank_routing_number', sa.String(length=20), nullable=True),
        sa.Column('bank_name', sa.String(length=100), nullable=True),
        sa.Column('risk_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('is_flagged', sa.Boolean(), nullable=False),
        sa.Column('fraud_check_result', sa.String(length=50), nullable=True),
        sa.Column('avs_result', sa.String(length=10), nullable=True),
        sa.Column('cvv_result', sa.String(length=10), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('device_fingerprint', sa.String(length=100), nullable=True),
        sa.Column('refund_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('refund_reason', sa.String(length=200), nullable=True),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refund_transaction_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('failure_code', sa.String(length=50), nullable=True),
        sa.Column('dispute_initiated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dispute_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('dispute_reason', sa.String(length=200), nullable=True),
        sa.Column('dispute_evidence_due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('chargeback_id', sa.String(length=100), nullable=True),
        sa.Column('subscription_id', sa.String(length=100), nullable=True),
        sa.Column('billing_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('billing_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['reservation_id'], ['reservations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_external_transaction_id'), 'payments', ['external_transaction_id'], unique=False)
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    op.create_index(op.f('ix_payments_payment_number'), 'payments', ['payment_number'], unique=True)
    op.create_index(op.f('ix_payments_payment_type'), 'payments', ['payment_type'], unique=False)
    op.create_index(op.f('ix_payments_promotion_code'), 'payments', ['promotion_code'], unique=False)
    op.create_index(op.f('ix_payments_reservation_id'), 'payments', ['reservation_id'], unique=False)
    op.create_index(op.f('ix_payments_status'), 'payments', ['status'], unique=False)
    op.create_index(op.f('ix_payments_user_id'), 'payments', ['user_id'], unique=False)

    # Create occupancy_analytics table
    op.create_table('occupancy_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parking_lot_id', sa.Integer(), nullable=False),
        sa.Column('parking_spot_id', sa.Integer(), nullable=True),
        sa.Column('period_type', sa.Enum('hourly', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly', name='analyticsperiod'), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('analysis_date', sa.Date(), nullable=False),
        sa.Column('total_spots', sa.Integer(), nullable=False),
        sa.Column('total_minutes_available', sa.Integer(), nullable=False),
        sa.Column('total_minutes_occupied', sa.Integer(), nullable=False),
        sa.Column('total_minutes_reserved', sa.Integer(), nullable=False),
        sa.Column('occupancy_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('utilization_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('availability_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('peak_occupancy', sa.Integer(), nullable=False),
        sa.Column('peak_occupancy_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('average_occupancy', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('total_arrivals', sa.Integer(), nullable=False),
        sa.Column('total_departures', sa.Integer(), nullable=False),
        sa.Column('total_reservations', sa.Integer(), nullable=False),
        sa.Column('no_show_count', sa.Integer(), nullable=False),
        sa.Column('avg_parking_duration', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('min_parking_duration', sa.Integer(), nullable=False),
        sa.Column('max_parking_duration', sa.Integer(), nullable=False),
        sa.Column('median_parking_duration', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('turnover_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('avg_vacancy_duration', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('regular_spot_occupancy', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('handicapped_spot_occupancy', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('electric_spot_occupancy', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('motorcycle_spot_occupancy', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('morning_peak_occupancy', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('midday_occupancy', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('afternoon_peak_occupancy', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('evening_occupancy', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('overnight_occupancy', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('weekday_avg_occupancy', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('weekend_avg_occupancy', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('weather_condition', sa.String(length=50), nullable=True),
        sa.Column('temperature_avg', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('data_completeness', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('sensor_uptime', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parking_lot_id'], ['parking_lots.id'], ),
        sa.ForeignKeyConstraint(['parking_spot_id'], ['parking_spots.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_occupancy_analytics_analysis_date'), 'occupancy_analytics', ['analysis_date'], unique=False)
    op.create_index(op.f('ix_occupancy_analytics_id'), 'occupancy_analytics', ['id'], unique=False)
    op.create_index(op.f('ix_occupancy_analytics_parking_lot_id'), 'occupancy_analytics', ['parking_lot_id'], unique=False)
    op.create_index(op.f('ix_occupancy_analytics_period_start'), 'occupancy_analytics', ['period_start'], unique=False)
    op.create_index(op.f('ix_occupancy_analytics_period_type'), 'occupancy_analytics', ['period_type'], unique=False)

    # Create revenue_analytics table
    op.create_table('revenue_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parking_lot_id', sa.Integer(), nullable=False),
        sa.Column('period_type', sa.Enum('hourly', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly', name='analyticsperiod'), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('analysis_date', sa.Date(), nullable=False),
        sa.Column('total_revenue', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('parking_revenue', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('penalty_revenue', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('extension_revenue', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('cancellation_revenue', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('cash_revenue', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('card_revenue', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('digital_wallet_revenue', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('mobile_payment_revenue', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_transactions', sa.Integer(), nullable=False),
        sa.Column('successful_transactions', sa.Integer(), nullable=False),
        sa.Column('failed_transactions', sa.Integer(), nullable=False),
        sa.Column('refunded_transactions', sa.Integer(), nullable=False),
        sa.Column('avg_transaction_value', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('min_transaction_value', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('max_transaction_value', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('median_transaction_value', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('processing_fees', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('operational_costs', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('net_revenue', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('avg_hourly_rate', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('avg_daily_rate', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('promotion_usage', sa.Integer(), nullable=False),
        sa.Column('total_refunds', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('refund_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('avg_refund_amount', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('unique_customers', sa.Integer(), nullable=False),
        sa.Column('repeat_customers', sa.Integer(), nullable=False),
        sa.Column('new_customers', sa.Integer(), nullable=False),
        sa.Column('revenue_per_spot', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('revenue_per_hour', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('revenue_per_customer', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('morning_revenue', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('midday_revenue', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('afternoon_revenue', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('evening_revenue', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('overnight_revenue', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('weekday_revenue', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('weekend_revenue', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('subscription_revenue', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('one_time_revenue', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('predicted_revenue', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('forecast_accuracy', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('exchange_rate', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('data_completeness', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parking_lot_id'], ['parking_lots.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_revenue_analytics_analysis_date'), 'revenue_analytics', ['analysis_date'], unique=False)
    op.create_index(op.f('ix_revenue_analytics_id'), 'revenue_analytics', ['id'], unique=False)
    op.create_index(op.f('ix_revenue_analytics_parking_lot_id'), 'revenue_analytics', ['parking_lot_id'], unique=False)
    op.create_index(op.f('ix_revenue_analytics_period_start'), 'revenue_analytics', ['period_start'], unique=False)
    op.create_index(op.f('ix_revenue_analytics_period_type'), 'revenue_analytics', ['period_type'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('revenue_analytics')
    op.drop_table('occupancy_analytics')
    op.drop_table('payments')
    op.drop_table('reservations')
    op.drop_table('parking_spots')
    op.drop_table('parking_lots')
    op.drop_table('vehicles')
    op.drop_table('users')
    
    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS analyticsperiod")
    op.execute("DROP TYPE IF EXISTS currency")
    op.execute("DROP TYPE IF EXISTS paymenttype")
    op.execute("DROP TYPE IF EXISTS paymentmethod")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS reservationtype")
    op.execute("DROP TYPE IF EXISTS reservationstatus")
    op.execute("DROP TYPE IF EXISTS chargingtype")
    op.execute("DROP TYPE IF EXISTS spottype")
    op.execute("DROP TYPE IF EXISTS spotstatus")
    op.execute("DROP TYPE IF EXISTS parkinglotstatus")
    op.execute("DROP TYPE IF EXISTS accesstype")
    op.execute("DROP TYPE IF EXISTS parkinglottype")
    op.execute("DROP TYPE IF EXISTS fueltype")
    op.execute("DROP TYPE IF EXISTS vehicletype")
    op.execute("DROP TYPE IF EXISTS userstatus")
    op.execute("DROP TYPE IF EXISTS userrole")