"""Data seeding migration for test scenarios

Revision ID: 005
Revises: 004
Create Date: 2025-08-17 19:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timedelta
from decimal import Decimal

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed database with test data"""
    
    # Get connection for data insertion
    connection = op.get_bind()
    
    # Create test users
    users_data = [
        {
            'email': 'admin@smartparking.com',
            'username': 'admin',
            'hashed_password': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewOZE9.T8WGZHsm6',
            'salt': 'salt123',
            'first_name': 'System',
            'last_name': 'Administrator',
            'phone_number': '+1234567890',
            'role': 'admin',
            'status': 'active',
            'is_email_verified': True,
            'is_phone_verified': False,
            'failed_login_attempts': 0,
            'timezone': 'UTC',
            'language': 'en',
            'notifications_enabled': True
        },
        {
            'email': 'john.doe@example.com',
            'username': 'johndoe',
            'hashed_password': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewOZE9.T8WGZHsm6',
            'salt': 'salt456',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '+1987654321',
            'role': 'user',
            'status': 'active',
            'is_email_verified': True,
            'is_phone_verified': True,
            'failed_login_attempts': 0,
            'timezone': 'America/New_York',
            'language': 'en',
            'notifications_enabled': True
        },
        {
            'email': 'jane.smith@example.com',
            'username': 'janesmith',
            'hashed_password': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewOZE9.T8WGZHsm6',
            'salt': 'salt789',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'phone_number': '+1555123456',
            'role': 'user',
            'status': 'active',
            'is_email_verified': True,
            'is_phone_verified': True,
            'failed_login_attempts': 0,
            'timezone': 'America/Los_Angeles',
            'language': 'en',
            'notifications_enabled': True
        },
        {
            'email': 'manager@smartparking.com',
            'username': 'manager',
            'hashed_password': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewOZE9.T8WGZHsm6',
            'salt': 'salt999',
            'first_name': 'Parking',
            'last_name': 'Manager',
            'phone_number': '+1555987654',
            'role': 'manager',
            'status': 'active',
            'is_email_verified': True,
            'is_phone_verified': True,
            'failed_login_attempts': 0,
            'timezone': 'UTC',
            'language': 'en',
            'notifications_enabled': True
        }
    ]
    
    # Insert users
    for user_data in users_data:
        connection.execute(
            sa.text("""
                INSERT INTO users (
                    email, username, hashed_password, salt, first_name, last_name,
                    phone_number, role, status, is_email_verified, is_phone_verified,
                    failed_login_attempts, timezone, language, notifications_enabled
                ) VALUES (
                    :email, :username, :hashed_password, :salt, :first_name, :last_name,
                    :phone_number, :role, :status, :is_email_verified, :is_phone_verified,
                    :failed_login_attempts, :timezone, :language, :notifications_enabled
                )
            """),
            user_data
        )
    
    # Create test vehicles
    vehicles_data = [
        {
            'owner_id': 2,  # John Doe
            'license_plate': 'ABC123',
            'make': 'Toyota',
            'model': 'Camry',
            'year': 2022,
            'color': 'White',
            'vehicle_type': 'car',
            'fuel_type': 'hybrid',
            'length_cm': 480,
            'width_cm': 180,
            'height_cm': 145,
            'weight_kg': 1500,
            'is_active': True,
            'is_verified': True
        },
        {
            'owner_id': 3,  # Jane Smith
            'license_plate': 'XYZ789',
            'make': 'Tesla',
            'model': 'Model 3',
            'year': 2023,
            'color': 'Black',
            'vehicle_type': 'electric_car',
            'fuel_type': 'electric',
            'length_cm': 470,
            'width_cm': 185,
            'height_cm': 144,
            'weight_kg': 1600,
            'battery_capacity_kwh': 75,
            'charging_port_type': 'Type 2',
            'is_active': True,
            'is_verified': True
        },
        {
            'owner_id': 2,  # John Doe (second vehicle)
            'license_plate': 'DEF456',
            'make': 'Honda',
            'model': 'Civic',
            'year': 2021,
            'color': 'Blue',
            'vehicle_type': 'car',
            'fuel_type': 'gasoline',
            'length_cm': 460,
            'width_cm': 180,
            'height_cm': 142,
            'weight_kg': 1300,
            'is_active': True,
            'is_verified': True
        },
        {
            'owner_id': 4,  # Manager
            'license_plate': 'MGR001',
            'make': 'BMW',
            'model': 'X5',
            'year': 2023,
            'color': 'Silver',
            'vehicle_type': 'car',
            'fuel_type': 'plug_in_hybrid',
            'length_cm': 495,
            'width_cm': 200,
            'height_cm': 175,
            'weight_kg': 2200,
            'battery_capacity_kwh': 30,
            'charging_port_type': 'Type 2',
            'is_active': True,
            'is_verified': True
        }
    ]
    
    # Insert vehicles
    for vehicle_data in vehicles_data:
        connection.execute(
            sa.text("""
                INSERT INTO vehicles (
                    owner_id, license_plate, make, model, year, color, vehicle_type,
                    fuel_type, length_cm, width_cm, height_cm, weight_kg,
                    battery_capacity_kwh, charging_port_type, is_active, is_verified
                ) VALUES (
                    :owner_id, :license_plate, :make, :model, :year, :color, :vehicle_type,
                    :fuel_type, :length_cm, :width_cm, :height_cm, :weight_kg,
                    :battery_capacity_kwh, :charging_port_type, :is_active, :is_verified
                )
            """),
            vehicle_data
        )
    
    # Create test parking lots
    parking_lots_data = [
        {
            'name': 'Downtown Business District',
            'code': 'DBD001',
            'description': 'Prime location in the heart of downtown with easy access to business district',
            'address': '123 Main Street, Downtown',
            'city': 'San Francisco',
            'state': 'California',
            'country': 'United States',
            'postal_code': '94102',
            'location': 'SRID=4326;POINT(-122.4194 37.7749)',
            'latitude': 37.7749,
            'longitude': -122.4194,
            'total_spots': 150,
            'available_spots': 142,
            'reserved_spots': 5,
            'disabled_spots': 8,
            'electric_spots': 20,
            'motorcycle_spots': 10,
            'parking_lot_type': 'multi_level',
            'access_type': 'public',
            'total_floors': 5,
            'max_vehicle_height_cm': 200,
            'base_hourly_rate': 5.00,
            'daily_rate': 25.00,
            'monthly_rate': 200.00,
            'is_24_hours': True,
            'has_security': True,
            'has_covered_parking': True,
            'has_ev_charging': True,
            'has_valet_service': False,
            'has_car_wash': False,
            'has_restrooms': True,
            'has_elevators': True,
            'has_wheelchair_access': True,
            'accepts_cash': True,
            'accepts_card': True,
            'accepts_mobile_payment': True,
            'requires_permit': False,
            'contact_phone': '+14155551234',
            'contact_email': 'info@dbdparking.com',
            'status': 'active',
            'is_reservation_enabled': True,
            'is_real_time_updates': True
        },
        {
            'name': 'Airport Terminal Parking',
            'code': 'ATP001',
            'description': 'Long-term and short-term parking for airport travelers',
            'address': 'San Francisco International Airport, Terminal 1',
            'city': 'San Francisco',
            'state': 'California',
            'country': 'United States',
            'postal_code': '94128',
            'location': 'SRID=4326;POINT(-122.3984 37.6213)',
            'latitude': 37.6213,
            'longitude': -122.3984,
            'total_spots': 500,
            'available_spots': 425,
            'reserved_spots': 15,
            'disabled_spots': 25,
            'electric_spots': 50,
            'motorcycle_spots': 20,
            'parking_lot_type': 'outdoor',
            'access_type': 'public',
            'total_floors': 1,
            'base_hourly_rate': 3.00,
            'daily_rate': 20.00,
            'monthly_rate': 150.00,
            'is_24_hours': True,
            'has_security': True,
            'has_covered_parking': False,
            'has_ev_charging': True,
            'has_valet_service': False,
            'has_car_wash': False,
            'has_restrooms': True,
            'has_elevators': False,
            'has_wheelchair_access': True,
            'accepts_cash': True,
            'accepts_card': True,
            'accepts_mobile_payment': True,
            'requires_permit': False,
            'contact_phone': '+16505551234',
            'contact_email': 'parking@sfo.com',
            'status': 'active',
            'is_reservation_enabled': True,
            'is_real_time_updates': True
        },
        {
            'name': 'Shopping Mall Complex',
            'code': 'SMC001',
            'description': 'Covered parking for shopping mall visitors with easy mall access',
            'address': '456 Shopping Center Drive',
            'city': 'Palo Alto',
            'state': 'California',
            'country': 'United States',
            'postal_code': '94301',
            'location': 'SRID=4326;POINT(-122.1430 37.4419)',
            'latitude': 37.4419,
            'longitude': -122.1430,
            'total_spots': 300,
            'available_spots': 245,
            'reserved_spots': 10,
            'disabled_spots': 15,
            'electric_spots': 30,
            'motorcycle_spots': 15,
            'parking_lot_type': 'indoor',
            'access_type': 'public',
            'total_floors': 3,
            'max_vehicle_height_cm': 210,
            'base_hourly_rate': 2.00,
            'daily_rate': 15.00,
            'is_24_hours': False,
            'opening_time': '06:00:00',
            'closing_time': '23:00:00',
            'has_security': True,
            'has_covered_parking': True,
            'has_ev_charging': True,
            'has_valet_service': False,
            'has_car_wash': False,
            'has_restrooms': True,
            'has_elevators': True,
            'has_wheelchair_access': True,
            'accepts_cash': False,
            'accepts_card': True,
            'accepts_mobile_payment': True,
            'requires_permit': False,
            'contact_phone': '+16505552345',
            'contact_email': 'parking@shopmall.com',
            'status': 'active',
            'is_reservation_enabled': True,
            'is_real_time_updates': True
        }
    ]
    
    # Insert parking lots
    for lot_data in parking_lots_data:
        connection.execute(
            sa.text("""
                INSERT INTO parking_lots (
                    name, code, description, address, city, state, country, postal_code,
                    location, latitude, longitude, total_spots, available_spots, reserved_spots,
                    disabled_spots, electric_spots, motorcycle_spots, parking_lot_type, access_type,
                    total_floors, max_vehicle_height_cm, base_hourly_rate, daily_rate, monthly_rate,
                    is_24_hours, opening_time, closing_time, has_security, has_covered_parking,
                    has_ev_charging, has_valet_service, has_car_wash, has_restrooms, has_elevators,
                    has_wheelchair_access, accepts_cash, accepts_card, accepts_mobile_payment,
                    requires_permit, contact_phone, contact_email, status, is_reservation_enabled,
                    is_real_time_updates
                ) VALUES (
                    :name, :code, :description, :address, :city, :state, :country, :postal_code,
                    ST_GeomFromEWKT(:location), :latitude, :longitude, :total_spots, :available_spots, :reserved_spots,
                    :disabled_spots, :electric_spots, :motorcycle_spots, :parking_lot_type, :access_type,
                    :total_floors, :max_vehicle_height_cm, :base_hourly_rate, :daily_rate, :monthly_rate,
                    :is_24_hours, :opening_time, :closing_time, :has_security, :has_covered_parking,
                    :has_ev_charging, :has_valet_service, :has_car_wash, :has_restrooms, :has_elevators,
                    :has_wheelchair_access, :accepts_cash, :accepts_card, :accepts_mobile_payment,
                    :requires_permit, :contact_phone, :contact_email, :status, :is_reservation_enabled,
                    :is_real_time_updates
                )
            """),
            lot_data
        )
    
    # Create sample parking spots for each lot
    # Downtown Business District - 150 spots across 5 floors
    for floor in range(1, 6):
        for spot_num in range(1, 31):  # 30 spots per floor
            spot_type = 'regular'
            charging_type = 'none'
            has_ev_charging = False
            is_handicapped_accessible = False
            pricing_multiplier = 1.00
            
            # First 4 spots on each floor are electric
            if spot_num <= 4:
                spot_type = 'electric'
                charging_type = 'type_2'
                has_ev_charging = True
                pricing_multiplier = 1.20
            # Next 2 spots are handicapped
            elif spot_num <= 6:
                spot_type = 'handicapped'
                is_handicapped_accessible = True
            
            # Some spots are occupied for testing
            status = 'occupied' if spot_num % 8 == 0 else 'available'
            
            connection.execute(
                sa.text("""
                    INSERT INTO parking_spots (
                        parking_lot_id, spot_number, floor, section, spot_type, status,
                        length_cm, width_cm, height_cm, has_ev_charging, charging_type,
                        is_handicapped_accessible, is_covered, pricing_multiplier, has_sensor, is_active, is_reservable,
                        total_occupancy_time, issue_reported
                    ) VALUES (
                        1, :spot_number, :floor, :section, :spot_type, :status,
                        500, 250, 220, :has_ev_charging, :charging_type,
                        :is_handicapped_accessible, true, :pricing_multiplier, true, true, true,
                        0, false
                    )
                """),
                {
                    'spot_number': f"{spot_num:03d}",
                    'floor': floor,
                    'section': chr(64 + ((spot_num - 1) // 10) + 1),  # A, B, C sections
                    'spot_type': spot_type,
                    'status': status,
                    'has_ev_charging': has_ev_charging,
                    'charging_type': charging_type,
                    'is_handicapped_accessible': is_handicapped_accessible,
                    'pricing_multiplier': pricing_multiplier
                }
            )
    
    # Create sample analytics data
    current_date = datetime.utcnow().date()
    
    # Occupancy analytics for the past week
    for days_back in range(7):
        analysis_date = current_date - timedelta(days=days_back)
        
        connection.execute(
            sa.text("""
                INSERT INTO occupancy_analytics (
                    parking_lot_id, period_type, period_start, period_end, analysis_date,
                    total_spots, total_minutes_available, total_minutes_occupied, total_minutes_reserved,
                    occupancy_rate, utilization_rate, availability_rate, peak_occupancy, average_occupancy,
                    total_arrivals, total_departures, total_reservations, no_show_count,
                    avg_parking_duration, min_parking_duration, max_parking_duration,
                    median_parking_duration, turnover_rate, avg_vacancy_duration,
                    regular_spot_occupancy, handicapped_spot_occupancy, electric_spot_occupancy, motorcycle_spot_occupancy,
                    morning_peak_occupancy, midday_occupancy, afternoon_peak_occupancy, evening_occupancy, overnight_occupancy,
                    weekday_avg_occupancy, weekend_avg_occupancy, data_completeness, sensor_uptime
                ) VALUES (
                    1, 'daily', :period_start, :period_end, :analysis_date,
                    150, 216000, 108000, 21600, 50.00, 60.00, 40.00, 120, 75.50,
                    45, 42, 38, 3, 144.5, 30, 480, 120.0, 0.28, 45.2,
                    52.3, 45.8, 65.2, 30.1, 78.5, 45.2, 82.1, 35.8, 25.4,
                    55.2, 48.7, 98.5, 99.2
                )
            """),
            {
                'period_start': datetime.combine(analysis_date, datetime.min.time()),
                'period_end': datetime.combine(analysis_date, datetime.max.time()),
                'analysis_date': analysis_date
            }
        )
    
    # Revenue analytics for the past week
    for days_back in range(7):
        analysis_date = current_date - timedelta(days=days_back)
        
        connection.execute(
            sa.text("""
                INSERT INTO revenue_analytics (
                    parking_lot_id, period_type, period_start, period_end, analysis_date,
                    total_revenue, parking_revenue, penalty_revenue, extension_revenue, cancellation_revenue,
                    cash_revenue, card_revenue, digital_wallet_revenue, mobile_payment_revenue,
                    total_transactions, successful_transactions, failed_transactions, refunded_transactions,
                    avg_transaction_value, min_transaction_value, max_transaction_value, median_transaction_value,
                    processing_fees, operational_costs, net_revenue, avg_hourly_rate, avg_daily_rate,
                    discount_amount, promotion_usage, total_refunds, refund_rate, avg_refund_amount,
                    unique_customers, repeat_customers, new_customers, revenue_per_spot, revenue_per_hour,
                    revenue_per_customer, morning_revenue, midday_revenue, afternoon_revenue, evening_revenue,
                    overnight_revenue, weekday_revenue, weekend_revenue, subscription_revenue, one_time_revenue,
                    currency, data_completeness
                ) VALUES (
                    1, 'daily', :period_start, :period_end, :analysis_date,
                    1250.50, 1150.75, 45.25, 54.50, 0.00,
                    125.00, 875.25, 150.25, 100.00,
                    58, 56, 2, 1, 21.56, 5.00, 45.75, 18.25,
                    37.52, 125.00, 1087.98, 5.25, 25.50,
                    45.75, 3, 22.50, 1.78, 22.50,
                    42, 15, 27, 8.34, 52.10, 29.77,
                    385.20, 295.75, 425.55, 144.00, 0.00,
                    1050.50, 200.00, 0.00, 1250.50, 'USD', 98.5
                )
            """),
            {
                'period_start': datetime.combine(analysis_date, datetime.min.time()),
                'period_end': datetime.combine(analysis_date, datetime.max.time()),
                'analysis_date': analysis_date
            }
        )


def downgrade() -> None:
    """Remove test data"""
    
    connection = op.get_bind()
    
    # Remove test data in reverse order
    connection.execute(sa.text("DELETE FROM revenue_analytics WHERE parking_lot_id IN (1, 2, 3)"))
    connection.execute(sa.text("DELETE FROM occupancy_analytics WHERE parking_lot_id IN (1, 2, 3)"))
    connection.execute(sa.text("DELETE FROM parking_spots WHERE parking_lot_id IN (1, 2, 3)"))
    connection.execute(sa.text("DELETE FROM parking_lots WHERE code IN ('DBD001', 'ATP001', 'SMC001')"))
    connection.execute(sa.text("DELETE FROM vehicles WHERE license_plate IN ('ABC123', 'XYZ789', 'DEF456', 'MGR001')"))
    connection.execute(sa.text("DELETE FROM users WHERE email IN ('admin@smartparking.com', 'john.doe@example.com', 'jane.smith@example.com', 'manager@smartparking.com')"))
