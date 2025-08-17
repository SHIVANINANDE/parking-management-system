"""
Sample data loader for Smart Parking Management System
Run this script to populate the database with sample data for testing
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Add the parent directory to sys.path to import our app
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from app.models.user import User, UserRole, UserStatus
from app.models.vehicle import Vehicle, VehicleType, FuelType
from app.models.parking_lot import ParkingLot, ParkingLotType, AccessType, ParkingLotStatus
from app.models.parking_spot import ParkingSpot, SpotType, SpotStatus, ChargingType
from app.models.reservation import Reservation, ReservationType, ReservationStatus
from app.models.payment import Payment, PaymentType, PaymentMethod, PaymentStatus, Currency
from geoalchemy2 import WKTElement

async def create_sample_users(session: AsyncSession):
    """Create sample users"""
    print("Creating sample users...")
    
    users = [
        User(
            email="admin@smartparking.com",
            username="admin",
            hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewOZE9.T8WGZHsm6",  # password: admin123
            salt="salt123",
            first_name="System",
            last_name="Administrator",
            phone_number="+1234567890",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
            timezone="UTC",
            language="en"
        ),
        User(
            email="john.doe@example.com",
            username="johndoe",
            hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewOZE9.T8WGZHsm6",  # password: password123
            salt="salt456",
            first_name="John",
            last_name="Doe",
            phone_number="+1987654321",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
            timezone="America/New_York",
            language="en"
        ),
        User(
            email="jane.smith@example.com",
            username="janesmith",
            hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewOZE9.T8WGZHsm6",  # password: password123
            salt="salt789",
            first_name="Jane",
            last_name="Smith",
            phone_number="+1555123456",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
            timezone="America/Los_Angeles",
            language="en"
        )
    ]
    
    for user in users:
        session.add(user)
    await session.commit()
    print(f"✓ Created {len(users)} sample users")
    return users

async def create_sample_vehicles(session: AsyncSession, users):
    """Create sample vehicles"""
    print("Creating sample vehicles...")
    
    vehicles = [
        Vehicle(
            owner_id=users[1].id,  # John Doe
            license_plate="ABC123",
            make="Toyota",
            model="Camry",
            year=2022,
            color="White",
            vehicle_type=VehicleType.CAR,
            fuel_type=FuelType.HYBRID,
            length_cm=480,
            width_cm=180,
            height_cm=145,
            weight_kg=1500,
            is_active=True,
            is_verified=True
        ),
        Vehicle(
            owner_id=users[2].id,  # Jane Smith
            license_plate="XYZ789",
            make="Tesla",
            model="Model 3",
            year=2023,
            color="Black",
            vehicle_type=VehicleType.ELECTRIC_CAR,
            fuel_type=FuelType.ELECTRIC,
            length_cm=470,
            width_cm=185,
            height_cm=144,
            weight_kg=1600,
            battery_capacity_kwh=75,
            charging_port_type="Type 2",
            is_active=True,
            is_verified=True
        ),
        Vehicle(
            owner_id=users[1].id,  # John Doe (second vehicle)
            license_plate="DEF456",
            make="Honda",
            model="Civic",
            year=2021,
            color="Blue",
            vehicle_type=VehicleType.CAR,
            fuel_type=FuelType.GASOLINE,
            length_cm=460,
            width_cm=180,
            height_cm=142,
            weight_kg=1300,
            is_active=True,
            is_verified=True
        )
    ]
    
    for vehicle in vehicles:
        session.add(vehicle)
    await session.commit()
    print(f"✓ Created {len(vehicles)} sample vehicles")
    return vehicles

async def create_sample_parking_lots(session: AsyncSession):
    """Create sample parking lots"""
    print("Creating sample parking lots...")
    
    parking_lots = [
        ParkingLot(
            name="Downtown Business District",
            code="DBD001",
            description="Prime location in the heart of downtown with easy access to business district",
            address="123 Main Street, Downtown",
            city="San Francisco",
            state="California",
            country="United States",
            postal_code="94102",
            location=WKTElement('POINT(-122.4194 37.7749)', srid=4326),
            latitude=Decimal('37.7749'),
            longitude=Decimal('-122.4194'),
            total_spots=150,
            available_spots=142,
            reserved_spots=5,
            disabled_spots=8,
            electric_spots=20,
            motorcycle_spots=10,
            parking_lot_type=ParkingLotType.MULTI_LEVEL,
            access_type=AccessType.PUBLIC,
            total_floors=5,
            max_vehicle_height_cm=200,
            base_hourly_rate=Decimal('5.00'),
            daily_rate=Decimal('25.00'),
            monthly_rate=Decimal('200.00'),
            is_24_hours=True,
            has_security=True,
            has_covered_parking=True,
            has_ev_charging=True,
            has_elevators=True,
            has_wheelchair_access=True,
            status=ParkingLotStatus.ACTIVE,
            contact_phone="+14155551234",
            contact_email="info@dbdparking.com"
        ),
        ParkingLot(
            name="Airport Terminal Parking",
            code="ATP001",
            description="Long-term and short-term parking for airport travelers",
            address="San Francisco International Airport, Terminal 1",
            city="San Francisco",
            state="California",
            country="United States",
            postal_code="94128",
            location=WKTElement('POINT(-122.3984 37.6213)', srid=4326),
            latitude=Decimal('37.6213'),
            longitude=Decimal('-122.3984'),
            total_spots=500,
            available_spots=425,
            reserved_spots=15,
            disabled_spots=25,
            electric_spots=50,
            motorcycle_spots=20,
            parking_lot_type=ParkingLotType.OUTDOOR,
            access_type=AccessType.PUBLIC,
            total_floors=1,
            base_hourly_rate=Decimal('3.00'),
            daily_rate=Decimal('20.00'),
            monthly_rate=Decimal('150.00'),
            is_24_hours=True,
            has_security=True,
            has_covered_parking=False,
            has_ev_charging=True,
            has_wheelchair_access=True,
            status=ParkingLotStatus.ACTIVE,
            contact_phone="+16505551234",
            contact_email="parking@sfo.com"
        ),
        ParkingLot(
            name="Shopping Mall Complex",
            code="SMC001",
            description="Covered parking for shopping mall visitors with easy mall access",
            address="456 Shopping Center Drive",
            city="Palo Alto",
            state="California",
            country="United States",
            postal_code="94301",
            location=WKTElement('POINT(-122.1430 37.4419)', srid=4326),
            latitude=Decimal('37.4419'),
            longitude=Decimal('-122.1430'),
            total_spots=300,
            available_spots=245,
            reserved_spots=10,
            disabled_spots=15,
            electric_spots=30,
            motorcycle_spots=15,
            parking_lot_type=ParkingLotType.INDOOR,
            access_type=AccessType.PUBLIC,
            total_floors=3,
            max_vehicle_height_cm=210,
            base_hourly_rate=Decimal('2.00'),
            daily_rate=Decimal('15.00'),
            is_24_hours=False,
            opening_time="06:00",
            closing_time="23:00",
            has_security=True,
            has_covered_parking=True,
            has_ev_charging=True,
            has_restrooms=True,
            has_elevators=True,
            has_wheelchair_access=True,
            status=ParkingLotStatus.ACTIVE,
            contact_phone="+16505552345",
            contact_email="parking@shopmall.com"
        )
    ]
    
    for lot in parking_lots:
        session.add(lot)
    await session.commit()
    print(f"✓ Created {len(parking_lots)} sample parking lots")
    return parking_lots

async def create_sample_parking_spots(session: AsyncSession, parking_lots):
    """Create sample parking spots"""
    print("Creating sample parking spots...")
    
    spots = []
    
    # Create spots for Downtown Business District (DBD001)
    downtown_lot = parking_lots[0]
    
    # Regular spots
    for floor in range(1, 6):  # 5 floors
        for i in range(1, 25):  # 24 spots per floor
            spot = ParkingSpot(
                parking_lot_id=downtown_lot.id,
                spot_number=f"{i:03d}",
                floor=floor,
                section=chr(64 + (i // 12) + 1),  # A, B, C sections
                spot_type=SpotType.REGULAR,
                status=SpotStatus.AVAILABLE,
                length_cm=500,
                width_cm=250,
                has_ev_charging=False,
                charging_type=ChargingType.NONE,
                is_handicapped_accessible=False,
                is_covered=True,
                pricing_multiplier=Decimal('1.00')
            )
            
            # Make some spots electric charging
            if i <= 4:  # First 4 spots on each floor are electric
                spot.spot_type = SpotType.ELECTRIC
                spot.has_ev_charging = True
                spot.charging_type = ChargingType.TYPE_2
                spot.charging_power_kw = Decimal('7.40')
                spot.pricing_multiplier = Decimal('1.20')
            
            # Make some spots handicapped accessible
            elif i <= 6:  # Next 2 spots are handicapped
                spot.spot_type = SpotType.HANDICAPPED
                spot.is_handicapped_accessible = True
                spot.has_wider_access = True
                spot.length_cm = 550
                spot.width_cm = 350
            
            # Simulate some occupied spots
            if i % 8 == 0:  # Every 8th spot is occupied
                spot.status = SpotStatus.OCCUPIED
                spot.occupied_since = datetime.utcnow() - timedelta(hours=2)
            
            spots.append(spot)
    
    # Create spots for Airport Terminal Parking (ATP001)
    airport_lot = parking_lots[1]
    
    for section in ['A', 'B', 'C', 'D', 'E']:
        for row in range(1, 21):  # 20 rows per section
            for spot_num in range(1, 6):  # 5 spots per row
                spot = ParkingSpot(
                    parking_lot_id=airport_lot.id,
                    spot_number=f"{spot_num}",
                    floor=1,
                    section=section,
                    row=str(row),
                    spot_type=SpotType.REGULAR,
                    status=SpotStatus.AVAILABLE,
                    length_cm=520,
                    width_cm=260,
                    has_ev_charging=False,
                    charging_type=ChargingType.NONE,
                    is_covered=False,
                    pricing_multiplier=Decimal('1.00')
                )
                
                # Electric spots in section E
                if section == 'E' and spot_num <= 2:
                    spot.spot_type = SpotType.ELECTRIC
                    spot.has_ev_charging = True
                    spot.charging_type = ChargingType.CCS
                    spot.charging_power_kw = Decimal('50.00')
                    spot.pricing_multiplier = Decimal('1.15')
                
                # Handicapped spots distributed across sections
                elif row <= 2 and spot_num == 1:
                    spot.spot_type = SpotType.HANDICAPPED
                    spot.is_handicapped_accessible = True
                    spot.has_wider_access = True
                    spot.length_cm = 550
                    spot.width_cm = 350
                
                spots.append(spot)
    
    # Add spots in batches to avoid memory issues
    batch_size = 100
    for i in range(0, len(spots), batch_size):
        batch = spots[i:i + batch_size]
        for spot in batch:
            session.add(spot)
        await session.commit()
    
    print(f"✓ Created {len(spots)} sample parking spots")
    return spots

async def create_sample_reservations(session: AsyncSession, users, vehicles, parking_lots, parking_spots):
    """Create sample reservations"""
    print("Creating sample reservations...")
    
    # Get some available spots
    available_spots = [spot for spot in parking_spots if spot.status == SpotStatus.AVAILABLE][:10]
    
    reservations = []
    
    # Current active reservation
    reservations.append(Reservation(
        user_id=users[1].id,  # John Doe
        vehicle_id=vehicles[0].id,  # Toyota Camry
        parking_lot_id=parking_lots[0].id,
        parking_spot_id=available_spots[0].id,
        reservation_number="RES001234567",
        confirmation_code="ABC123",
        reservation_type=ReservationType.IMMEDIATE,
        start_time=datetime.utcnow() - timedelta(hours=1),
        end_time=datetime.utcnow() + timedelta(hours=2),
        actual_arrival_time=datetime.utcnow() - timedelta(hours=1),
        status=ReservationStatus.ACTIVE,
        base_cost=Decimal('15.00'),
        total_cost=Decimal('16.50'),
        tax_amount=Decimal('1.50'),
        is_paid=True,
        requires_ev_charging=False
    ))
    
    # Future scheduled reservation
    reservations.append(Reservation(
        user_id=users[2].id,  # Jane Smith
        vehicle_id=vehicles[1].id,  # Tesla Model 3
        parking_lot_id=parking_lots[0].id,
        parking_spot_id=available_spots[1].id,
        reservation_number="RES001234568",
        confirmation_code="DEF456",
        reservation_type=ReservationType.SCHEDULED,
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, hours=4),
        status=ReservationStatus.CONFIRMED,
        base_cost=Decimal('20.00'),
        total_cost=Decimal('24.00'),
        tax_amount=Decimal('2.00'),
        discount_amount=Decimal('1.00'),
        is_paid=True,
        requires_ev_charging=True
    ))
    
    # Completed reservation
    reservations.append(Reservation(
        user_id=users[1].id,  # John Doe
        vehicle_id=vehicles[2].id,  # Honda Civic
        parking_lot_id=parking_lots[1].id,
        reservation_number="RES001234569",
        confirmation_code="GHI789",
        reservation_type=ReservationType.IMMEDIATE,
        start_time=datetime.utcnow() - timedelta(days=2),
        end_time=datetime.utcnow() - timedelta(days=2) + timedelta(hours=6),
        actual_arrival_time=datetime.utcnow() - timedelta(days=2),
        actual_departure_time=datetime.utcnow() - timedelta(days=2) + timedelta(hours=6),
        status=ReservationStatus.COMPLETED,
        base_cost=Decimal('18.00'),
        total_cost=Decimal('19.80'),
        tax_amount=Decimal('1.80'),
        is_paid=True
    ))
    
    for reservation in reservations:
        session.add(reservation)
    await session.commit()
    print(f"✓ Created {len(reservations)} sample reservations")
    return reservations

async def create_sample_payments(session: AsyncSession, users, reservations):
    """Create sample payments"""
    print("Creating sample payments...")
    
    payments = []
    
    for i, reservation in enumerate(reservations):
        payment = Payment(
            user_id=reservation.user_id,
            reservation_id=reservation.id,
            payment_number=f"PAY{reservation.reservation_number[-6:]}",
            payment_type=PaymentType.RESERVATION,
            payment_method=PaymentMethod.CREDIT_CARD if i % 2 == 0 else PaymentMethod.DIGITAL_WALLET,
            status=PaymentStatus.COMPLETED,
            amount=reservation.total_cost,
            currency=Currency.USD,
            tax_amount=reservation.tax_amount,
            net_amount=reservation.total_cost - Decimal('0.30'),  # Processing fee
            fee_amount=Decimal('0.30'),
            payment_processor="Stripe" if i % 2 == 0 else "PayPal",
            processor_fee=Decimal('0.30'),
            masked_card_number="4242" if i % 2 == 0 else None,
            card_brand="Visa" if i % 2 == 0 else None,
            wallet_type=None if i % 2 == 0 else "Apple Pay",
            processed_at=reservation.created_at + timedelta(seconds=30)
        )
        payments.append(payment)
    
    for payment in payments:
        session.add(payment)
    await session.commit()
    print(f"✓ Created {len(payments)} sample payments")
    return payments

async def main():
    """Main function to load all sample data"""
    print("Loading sample data for Smart Parking Management System...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        try:
            # Create sample data in order
            users = await create_sample_users(session)
            vehicles = await create_sample_vehicles(session, users)
            parking_lots = await create_sample_parking_lots(session)
            parking_spots = await create_sample_parking_spots(session, parking_lots)
            reservations = await create_sample_reservations(session, users, vehicles, parking_lots, parking_spots)
            payments = await create_sample_payments(session, users, reservations)
            
            print("=" * 60)
            print("✅ Sample data loading completed successfully!")
            print("")
            print("Sample data summary:")
            print(f"• Users: {len(users)}")
            print(f"• Vehicles: {len(vehicles)}")
            print(f"• Parking Lots: {len(parking_lots)}")
            print(f"• Parking Spots: {len(parking_spots)}")
            print(f"• Reservations: {len(reservations)}")
            print(f"• Payments: {len(payments)}")
            print("")
            print("Test accounts:")
            print("• Admin: admin@smartparking.com / admin123")
            print("• User 1: john.doe@example.com / password123")
            print("• User 2: jane.smith@example.com / password123")
            
        except Exception as e:
            print(f"❌ Error loading sample data: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(main())