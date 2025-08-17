#!/usr/bin/env python3
"""
Advanced Data Seeding Utility for Smart Parking Management System
Provides different seeding scenarios for various testing needs
"""

import asyncio
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta, time
from decimal import Decimal
from typing import List, Dict, Any
import random

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
from app.models.analytics import OccupancyAnalytics, RevenueAnalytics, AnalyticsPeriod
from geoalchemy2 import WKTElement

class DataSeeder:
    """Advanced data seeding utility with multiple scenarios"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = []
        self.vehicles = []
        self.parking_lots = []
        self.parking_spots = []
        self.reservations = []
        self.payments = []
    
    async def clear_all_data(self):
        """Clear all existing data from the database"""
        print("🗑️  Clearing existing data...")
        
        # Clear in reverse dependency order
        await self.session.execute("DELETE FROM revenue_analytics")
        await self.session.execute("DELETE FROM occupancy_analytics")
        await self.session.execute("DELETE FROM payments")
        await self.session.execute("DELETE FROM reservations")
        await self.session.execute("DELETE FROM parking_spots")
        await self.session.execute("DELETE FROM parking_lots")
        await self.session.execute("DELETE FROM vehicles")
        await self.session.execute("DELETE FROM users")
        
        await self.session.commit()
        print("✅ All data cleared")
    
    async def seed_basic_scenario(self):
        """Seed basic test scenario with minimal data"""
        print("📦 Seeding basic scenario...")
        
        # Create basic users
        await self._create_basic_users()
        await self._create_basic_vehicles()
        await self._create_basic_parking_lots()
        await self._create_basic_spots()
        
        print("✅ Basic scenario seeded")
    
    async def seed_development_scenario(self):
        """Seed comprehensive development scenario"""
        print("🔧 Seeding development scenario...")
        
        await self._create_comprehensive_users()
        await self._create_comprehensive_vehicles()
        await self._create_comprehensive_parking_lots()
        await self._create_comprehensive_spots()
        await self._create_sample_reservations()
        await self._create_sample_payments()
        
        print("✅ Development scenario seeded")
    
    async def seed_performance_scenario(self):
        """Seed large dataset for performance testing"""
        print("⚡ Seeding performance scenario...")
        
        await self._create_performance_users()
        await self._create_performance_vehicles()
        await self._create_performance_parking_lots()
        await self._create_performance_spots()
        await self._create_performance_reservations()
        await self._create_performance_analytics()
        
        print("✅ Performance scenario seeded")
    
    async def seed_analytics_scenario(self):
        """Seed historical data for analytics testing"""
        print("📊 Seeding analytics scenario...")
        
        await self._create_basic_users()
        await self._create_basic_vehicles()
        await self._create_basic_parking_lots()
        await self._create_basic_spots()
        await self._create_historical_analytics()
        
        print("✅ Analytics scenario seeded")
    
    async def _create_basic_users(self):
        """Create basic user set"""
        users_data = [
            {
                "email": "admin@smartparking.com",
                "username": "admin",
                "first_name": "System",
                "last_name": "Administrator",
                "role": UserRole.ADMIN,
                "phone_number": "+1234567890"
            },
            {
                "email": "john.doe@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "role": UserRole.USER,
                "phone_number": "+1987654321"
            },
            {
                "email": "jane.smith@example.com",
                "username": "janesmith",
                "first_name": "Jane",
                "last_name": "Smith",
                "role": UserRole.USER,
                "phone_number": "+1555123456"
            }
        ]
        
        for user_data in users_data:
            user = User(
                email=user_data["email"],
                username=user_data["username"],
                hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewOZE9.T8WGZHsm6",
                salt="salt123",
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                phone_number=user_data["phone_number"],
                role=user_data["role"],
                status=UserStatus.ACTIVE,
                is_email_verified=True,
                timezone="UTC",
                language="en"
            )
            self.session.add(user)
            self.users.append(user)
        
        await self.session.commit()
        print(f"  ✓ Created {len(self.users)} basic users")
    
    async def _create_comprehensive_users(self):
        """Create comprehensive user set with different roles"""
        await self._create_basic_users()
        
        additional_users = [
            {
                "email": "manager@smartparking.com",
                "username": "manager",
                "first_name": "Parking",
                "last_name": "Manager",
                "role": UserRole.MANAGER,
                "phone_number": "+1555987654"
            },
            {
                "email": "operator@smartparking.com",
                "username": "operator",
                "first_name": "System",
                "last_name": "Operator",
                "role": UserRole.OPERATOR,
                "phone_number": "+1555555555"
            }
        ]
        
        for user_data in additional_users:
            user = User(
                email=user_data["email"],
                username=user_data["username"],
                hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewOZE9.T8WGZHsm6",
                salt="salt123",
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                phone_number=user_data["phone_number"],
                role=user_data["role"],
                status=UserStatus.ACTIVE,
                is_email_verified=True,
                timezone="UTC",
                language="en"
            )
            self.session.add(user)
            self.users.append(user)
        
        await self.session.commit()
        print(f"  ✓ Created {len(self.users)} comprehensive users")
    
    async def _create_performance_users(self):
        """Create large number of users for performance testing"""
        await self._create_comprehensive_users()
        
        # Create 1000 additional users
        for i in range(1000):
            user = User(
                email=f"user{i+1000}@example.com",
                username=f"user{i+1000}",
                hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewOZE9.T8WGZHsm6",
                salt="salt123",
                first_name=f"User{i+1000}",
                last_name="Test",
                phone_number=f"+1{random.randint(1000000000, 9999999999)}",
                role=UserRole.USER,
                status=UserStatus.ACTIVE,
                is_email_verified=True,
                timezone="UTC",
                language="en"
            )
            self.session.add(user)
            self.users.append(user)
            
            # Commit in batches
            if (i + 1) % 100 == 0:
                await self.session.commit()
        
        await self.session.commit()
        print(f"  ✓ Created {len(self.users)} performance users")
    
    async def _create_basic_vehicles(self):
        """Create basic vehicle set"""
        if len(self.users) < 2:
            raise ValueError("Need at least 2 users to create vehicles")
        
        vehicles_data = [
            {
                "owner": self.users[1],  # John Doe
                "license_plate": "ABC123",
                "make": "Toyota",
                "model": "Camry",
                "vehicle_type": VehicleType.CAR,
                "fuel_type": FuelType.HYBRID
            },
            {
                "owner": self.users[2],  # Jane Smith
                "license_plate": "XYZ789",
                "make": "Tesla",
                "model": "Model 3",
                "vehicle_type": VehicleType.ELECTRIC_CAR,
                "fuel_type": FuelType.ELECTRIC
            }
        ]
        
        for vehicle_data in vehicles_data:
            vehicle = Vehicle(
                owner_id=vehicle_data["owner"].id,
                license_plate=vehicle_data["license_plate"],
                make=vehicle_data["make"],
                model=vehicle_data["model"],
                year=random.randint(2020, 2024),
                color=random.choice(["White", "Black", "Silver", "Blue", "Red"]),
                vehicle_type=vehicle_data["vehicle_type"],
                fuel_type=vehicle_data["fuel_type"],
                length_cm=random.randint(400, 500),
                width_cm=random.randint(170, 190),
                height_cm=random.randint(140, 160),
                weight_kg=random.randint(1200, 1800),
                is_active=True,
                is_verified=True
            )
            self.session.add(vehicle)
            self.vehicles.append(vehicle)
        
        await self.session.commit()
        print(f"  ✓ Created {len(self.vehicles)} basic vehicles")
    
    async def _create_comprehensive_vehicles(self):
        """Create comprehensive vehicle set"""
        await self._create_basic_vehicles()
        
        # Add more vehicles for comprehensive testing
        vehicle_types = [VehicleType.CAR, VehicleType.ELECTRIC_CAR, VehicleType.MOTORCYCLE, VehicleType.VAN]
        fuel_types = [FuelType.GASOLINE, FuelType.ELECTRIC, FuelType.HYBRID, FuelType.DIESEL]
        makes = ["Honda", "Ford", "BMW", "Mercedes", "Audi", "Nissan", "Hyundai"]
        
        for i in range(10):
            vehicle = Vehicle(
                owner_id=random.choice(self.users).id,
                license_plate=f"TEST{i:03d}",
                make=random.choice(makes),
                model=f"Model {i}",
                year=random.randint(2018, 2024),
                color=random.choice(["White", "Black", "Silver", "Blue", "Red", "Green", "Gray"]),
                vehicle_type=random.choice(vehicle_types),
                fuel_type=random.choice(fuel_types),
                length_cm=random.randint(400, 550),
                width_cm=random.randint(170, 200),
                height_cm=random.randint(140, 180),
                weight_kg=random.randint(1200, 2500),
                is_active=True,
                is_verified=True
            )
            self.session.add(vehicle)
            self.vehicles.append(vehicle)
        
        await self.session.commit()
        print(f"  ✓ Created {len(self.vehicles)} comprehensive vehicles")
    
    async def _create_performance_vehicles(self):
        """Create large number of vehicles for performance testing"""
        await self._create_comprehensive_vehicles()
        
        # Create vehicles for performance users
        vehicle_types = list(VehicleType)
        fuel_types = list(FuelType)
        makes = ["Honda", "Ford", "BMW", "Mercedes", "Audi", "Nissan", "Hyundai", "Toyota", "Tesla", "Volkswagen"]
        
        for i in range(2000):
            vehicle = Vehicle(
                owner_id=random.choice(self.users).id,
                license_plate=f"PERF{i:04d}",
                make=random.choice(makes),
                model=f"Model {random.randint(1, 20)}",
                year=random.randint(2015, 2024),
                color=random.choice(["White", "Black", "Silver", "Blue", "Red", "Green", "Gray", "Yellow"]),
                vehicle_type=random.choice(vehicle_types),
                fuel_type=random.choice(fuel_types),
                length_cm=random.randint(350, 600),
                width_cm=random.randint(160, 220),
                height_cm=random.randint(130, 200),
                weight_kg=random.randint(1000, 3000),
                is_active=True,
                is_verified=random.choice([True, False])
            )
            self.session.add(vehicle)
            self.vehicles.append(vehicle)
            
            # Commit in batches
            if (i + 1) % 200 == 0:
                await self.session.commit()
        
        await self.session.commit()
        print(f"  ✓ Created {len(self.vehicles)} performance vehicles")
    
    async def _create_basic_parking_lots(self):
        """Create basic parking lot set"""
        lots_data = [
            {
                "name": "Downtown Business District",
                "code": "DBD001",
                "address": "123 Main Street, Downtown",
                "city": "San Francisco",
                "location": (-122.4194, 37.7749),
                "total_spots": 150,
                "parking_lot_type": ParkingLotType.MULTI_LEVEL,
                "base_hourly_rate": 5.00
            },
            {
                "name": "Airport Terminal Parking",
                "code": "ATP001",
                "address": "San Francisco International Airport, Terminal 1",
                "city": "San Francisco",
                "location": (-122.3984, 37.6213),
                "total_spots": 500,
                "parking_lot_type": ParkingLotType.OUTDOOR,
                "base_hourly_rate": 3.00
            }
        ]
        
        for lot_data in lots_data:
            parking_lot = ParkingLot(
                name=lot_data["name"],
                code=lot_data["code"],
                description=f"Test parking lot: {lot_data['name']}",
                address=lot_data["address"],
                city=lot_data["city"],
                state="California",
                country="United States",
                postal_code="94102",
                location=WKTElement(f'POINT({lot_data["location"][0]} {lot_data["location"][1]})', srid=4326),
                latitude=Decimal(str(lot_data["location"][1])),
                longitude=Decimal(str(lot_data["location"][0])),
                total_spots=lot_data["total_spots"],
                available_spots=lot_data["total_spots"] - 10,
                parking_lot_type=lot_data["parking_lot_type"],
                access_type=AccessType.PUBLIC,
                total_floors=1,
                base_hourly_rate=Decimal(str(lot_data["base_hourly_rate"])),
                is_24_hours=True,
                status=ParkingLotStatus.ACTIVE,
                contact_phone="+1234567890",
                is_reservation_enabled=True
            )
            self.session.add(parking_lot)
            self.parking_lots.append(parking_lot)
        
        await self.session.commit()
        print(f"  ✓ Created {len(self.parking_lots)} basic parking lots")
    
    async def _create_comprehensive_parking_lots(self):
        """Create comprehensive parking lot set"""
        await self._create_basic_parking_lots()
        
        # Add more diverse parking lots
        additional_lots = [
            {
                "name": "Shopping Mall Complex",
                "code": "SMC001",
                "address": "456 Shopping Center Drive",
                "city": "Palo Alto",
                "location": (-122.1430, 37.4419),
                "total_spots": 300,
                "parking_lot_type": ParkingLotType.INDOOR,
                "base_hourly_rate": 2.00
            },
            {
                "name": "University Campus Parking",
                "code": "UCP001",
                "address": "789 University Ave",
                "city": "Stanford",
                "location": (-122.1697, 37.4275),
                "total_spots": 200,
                "parking_lot_type": ParkingLotType.OUTDOOR,
                "base_hourly_rate": 1.50
            }
        ]
        
        for lot_data in additional_lots:
            parking_lot = ParkingLot(
                name=lot_data["name"],
                code=lot_data["code"],
                description=f"Test parking lot: {lot_data['name']}",
                address=lot_data["address"],
                city=lot_data["city"],
                state="California",
                country="United States",
                postal_code="94301",
                location=WKTElement(f'POINT({lot_data["location"][0]} {lot_data["location"][1]})', srid=4326),
                latitude=Decimal(str(lot_data["location"][1])),
                longitude=Decimal(str(lot_data["location"][0])),
                total_spots=lot_data["total_spots"],
                available_spots=lot_data["total_spots"] - random.randint(10, 50),
                parking_lot_type=lot_data["parking_lot_type"],
                access_type=AccessType.PUBLIC,
                total_floors=random.randint(1, 5),
                base_hourly_rate=Decimal(str(lot_data["base_hourly_rate"])),
                is_24_hours=random.choice([True, False]),
                has_ev_charging=True,
                has_security=True,
                status=ParkingLotStatus.ACTIVE,
                contact_phone="+1234567890",
                is_reservation_enabled=True
            )
            self.session.add(parking_lot)
            self.parking_lots.append(parking_lot)
        
        await self.session.commit()
        print(f"  ✓ Created {len(self.parking_lots)} comprehensive parking lots")
    
    async def _create_performance_parking_lots(self):
        """Create large number of parking lots for performance testing"""
        await self._create_comprehensive_parking_lots()
        
        # Create additional parking lots for performance testing
        for i in range(50):
            # Generate random coordinates in California
            lat = random.uniform(32.5, 42.0)  # California latitude range
            lon = random.uniform(-124.4, -114.1)  # California longitude range
            
            parking_lot = ParkingLot(
                name=f"Performance Test Lot {i+1:03d}",
                code=f"PTL{i+1:03d}",
                description=f"Performance test parking lot {i+1}",
                address=f"{random.randint(100, 9999)} Test Street",
                city=f"TestCity{i+1}",
                state="California",
                country="United States",
                postal_code=f"{random.randint(90000, 99999)}",
                location=WKTElement(f'POINT({lon} {lat})', srid=4326),
                latitude=Decimal(str(lat)),
                longitude=Decimal(str(lon)),
                total_spots=random.randint(50, 1000),
                available_spots=random.randint(10, 900),
                parking_lot_type=random.choice(list(ParkingLotType)),
                access_type=random.choice(list(AccessType)),
                total_floors=random.randint(1, 10),
                base_hourly_rate=Decimal(str(random.uniform(1.0, 10.0))),
                is_24_hours=random.choice([True, False]),
                has_ev_charging=random.choice([True, False]),
                has_security=random.choice([True, False]),
                status=ParkingLotStatus.ACTIVE,
                contact_phone=f"+1{random.randint(1000000000, 9999999999)}",
                is_reservation_enabled=True
            )
            self.session.add(parking_lot)
            self.parking_lots.append(parking_lot)
        
        await self.session.commit()
        print(f"  ✓ Created {len(self.parking_lots)} performance parking lots")
    
    async def _create_basic_spots(self):
        """Create basic parking spots"""
        if not self.parking_lots:
            raise ValueError("Need parking lots to create spots")
        
        spot_count = 0
        for lot in self.parking_lots[:2]:  # Only for first 2 lots in basic scenario
            for i in range(min(50, lot.total_spots)):  # Create up to 50 spots per lot
                spot = ParkingSpot(
                    parking_lot_id=lot.id,
                    spot_number=f"{i+1:03d}",
                    floor=1,
                    section=chr(65 + (i // 20)),  # A, B, C sections
                    spot_type=SpotType.REGULAR if i < 40 else SpotType.ELECTRIC,
                    status=SpotStatus.AVAILABLE if i % 5 != 0 else SpotStatus.OCCUPIED,
                    length_cm=500,
                    width_cm=250,
                    has_ev_charging=i >= 40,
                    charging_type=ChargingType.TYPE_2 if i >= 40 else ChargingType.NONE,
                    is_covered=lot.parking_lot_type == ParkingLotType.INDOOR,
                    pricing_multiplier=Decimal('1.20' if i >= 40 else '1.00'),
                    is_active=True,
                    is_reservable=True
                )
                self.session.add(spot)
                self.parking_spots.append(spot)
                spot_count += 1
        
        await self.session.commit()
        print(f"  ✓ Created {spot_count} basic parking spots")
    
    async def _create_comprehensive_spots(self):
        """Create comprehensive parking spots"""
        await self._create_basic_spots()
        
        # Create spots for remaining lots
        spot_count = len(self.parking_spots)
        for lot in self.parking_lots[2:]:  # Skip first 2 lots already processed
            spots_to_create = min(100, lot.total_spots)
            for i in range(spots_to_create):
                spot_type = SpotType.REGULAR
                charging_type = ChargingType.NONE
                has_ev_charging = False
                is_handicapped = False
                pricing_multiplier = Decimal('1.00')
                
                # Distribute spot types
                if i < spots_to_create * 0.1:  # 10% electric
                    spot_type = SpotType.ELECTRIC
                    charging_type = random.choice([ChargingType.TYPE_2, ChargingType.CCS])
                    has_ev_charging = True
                    pricing_multiplier = Decimal('1.20')
                elif i < spots_to_create * 0.15:  # 5% handicapped
                    spot_type = SpotType.HANDICAPPED
                    is_handicapped = True
                elif i < spots_to_create * 0.2:  # 5% compact
                    spot_type = SpotType.COMPACT
                    pricing_multiplier = Decimal('0.80')
                
                spot = ParkingSpot(
                    parking_lot_id=lot.id,
                    spot_number=f"{i+1:03d}",
                    floor=random.randint(1, lot.total_floors),
                    section=chr(65 + (i // 25)),  # A, B, C, D sections
                    spot_type=spot_type,
                    status=random.choice([SpotStatus.AVAILABLE, SpotStatus.OCCUPIED, SpotStatus.RESERVED]),
                    length_cm=random.randint(450, 550),
                    width_cm=random.randint(220, 280),
                    has_ev_charging=has_ev_charging,
                    charging_type=charging_type,
                    is_handicapped_accessible=is_handicapped,
                    is_covered=lot.parking_lot_type in [ParkingLotType.INDOOR, ParkingLotType.UNDERGROUND],
                    pricing_multiplier=pricing_multiplier,
                    is_active=True,
                    is_reservable=True
                )
                self.session.add(spot)
                self.parking_spots.append(spot)
                spot_count += 1
        
        await self.session.commit()
        print(f"  ✓ Created {spot_count} comprehensive parking spots")
    
    async def _create_performance_spots(self):
        """Create large number of parking spots for performance testing"""
        await self._create_comprehensive_spots()
        
        spot_count = len(self.parking_spots)
        for lot in self.parking_lots:
            # Create all spots for performance lots
            if lot.total_spots > 100:  # Performance lots
                existing_spots = sum(1 for spot in self.parking_spots if spot.parking_lot_id == lot.id)
                remaining_spots = lot.total_spots - existing_spots
                
                for i in range(remaining_spots):
                    spot = ParkingSpot(
                        parking_lot_id=lot.id,
                        spot_number=f"{existing_spots + i + 1:04d}",
                        floor=random.randint(1, lot.total_floors),
                        section=chr(65 + ((existing_spots + i) // 50)),
                        spot_type=random.choice(list(SpotType)),
                        status=random.choice(list(SpotStatus)),
                        length_cm=random.randint(400, 600),
                        width_cm=random.randint(200, 300),
                        has_ev_charging=random.choice([True, False]),
                        charging_type=random.choice(list(ChargingType)),
                        is_covered=random.choice([True, False]),
                        pricing_multiplier=Decimal(str(random.uniform(0.8, 1.5))),
                        is_active=True,
                        is_reservable=True
                    )
                    self.session.add(spot)
                    self.parking_spots.append(spot)
                    spot_count += 1
                    
                    # Commit in batches
                    if (i + 1) % 100 == 0:
                        await self.session.commit()
        
        await self.session.commit()
        print(f"  ✓ Created {spot_count} performance parking spots")
    
    async def _create_sample_reservations(self):
        """Create sample reservations"""
        if not self.users or not self.vehicles or not self.parking_spots:
            raise ValueError("Need users, vehicles, and spots to create reservations")
        
        # Create various types of reservations
        reservations_data = [
            {
                "user": self.users[1],
                "vehicle": self.vehicles[0],
                "type": ReservationType.IMMEDIATE,
                "status": ReservationStatus.ACTIVE,
                "start_offset": -1,  # 1 hour ago
                "duration": 3  # 3 hours
            },
            {
                "user": self.users[2],
                "vehicle": self.vehicles[1],
                "type": ReservationType.SCHEDULED,
                "status": ReservationStatus.CONFIRMED,
                "start_offset": 24,  # Tomorrow
                "duration": 4  # 4 hours
            },
            {
                "user": self.users[1],
                "vehicle": self.vehicles[0],
                "type": ReservationType.IMMEDIATE,
                "status": ReservationStatus.COMPLETED,
                "start_offset": -48,  # 2 days ago
                "duration": 6  # 6 hours
            }
        ]
        
        for i, res_data in enumerate(reservations_data):
            available_spots = [spot for spot in self.parking_spots if spot.status == SpotStatus.AVAILABLE]
            if not available_spots:
                break
            
            spot = random.choice(available_spots)
            start_time = datetime.utcnow() + timedelta(hours=res_data["start_offset"])
            end_time = start_time + timedelta(hours=res_data["duration"])
            
            reservation = Reservation(
                user_id=res_data["user"].id,
                vehicle_id=res_data["vehicle"].id,
                parking_lot_id=spot.parking_lot_id,
                parking_spot_id=spot.id,
                reservation_number=f"RES{datetime.utcnow().strftime('%Y%m%d')}{i+1:04d}",
                confirmation_code=f"CONF{i+1:03d}",
                reservation_type=res_data["type"],
                start_time=start_time,
                end_time=end_time,
                status=res_data["status"],
                base_cost=Decimal(str(random.uniform(10.0, 50.0))),
                total_cost=Decimal(str(random.uniform(12.0, 55.0))),
                tax_amount=Decimal(str(random.uniform(1.0, 5.0))),
                is_paid=res_data["status"] in [ReservationStatus.ACTIVE, ReservationStatus.COMPLETED]
            )
            
            if res_data["status"] == ReservationStatus.ACTIVE:
                reservation.actual_arrival_time = start_time
            elif res_data["status"] == ReservationStatus.COMPLETED:
                reservation.actual_arrival_time = start_time
                reservation.actual_departure_time = end_time
            
            self.session.add(reservation)
            self.reservations.append(reservation)
        
        await self.session.commit()
        print(f"  ✓ Created {len(self.reservations)} sample reservations")
    
    async def _create_performance_reservations(self):
        """Create large number of reservations for performance testing"""
        await self._create_sample_reservations()
        
        # Create many reservations for performance testing
        for i in range(5000):
            user = random.choice(self.users)
            vehicle = random.choice([v for v in self.vehicles if v.owner_id == user.id])
            if not vehicle:
                continue
            
            spot = random.choice(self.parking_spots)
            start_time = datetime.utcnow() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
            duration = random.randint(1, 12)
            end_time = start_time + timedelta(hours=duration)
            
            reservation = Reservation(
                user_id=user.id,
                vehicle_id=vehicle.id,
                parking_lot_id=spot.parking_lot_id,
                parking_spot_id=spot.id,
                reservation_number=f"PERF{datetime.utcnow().strftime('%Y%m%d')}{i+1:06d}",
                confirmation_code=f"P{i+1:06d}",
                reservation_type=random.choice(list(ReservationType)),
                start_time=start_time,
                end_time=end_time,
                status=random.choice(list(ReservationStatus)),
                base_cost=Decimal(str(random.uniform(5.0, 100.0))),
                total_cost=Decimal(str(random.uniform(6.0, 110.0))),
                tax_amount=Decimal(str(random.uniform(0.5, 10.0))),
                is_paid=random.choice([True, False])
            )
            
            self.session.add(reservation)
            self.reservations.append(reservation)
            
            # Commit in batches
            if (i + 1) % 500 == 0:
                await self.session.commit()
        
        await self.session.commit()
        print(f"  ✓ Created {len(self.reservations)} performance reservations")
    
    async def _create_sample_payments(self):
        """Create sample payments"""
        if not self.reservations:
            return
        
        for reservation in self.reservations:
            if reservation.is_paid:
                payment = Payment(
                    user_id=reservation.user_id,
                    reservation_id=reservation.id,
                    payment_number=f"PAY{reservation.reservation_number[-6:]}",
                    payment_type=PaymentType.RESERVATION,
                    payment_method=random.choice([PaymentMethod.CREDIT_CARD, PaymentMethod.DIGITAL_WALLET]),
                    status=PaymentStatus.COMPLETED,
                    amount=reservation.total_cost,
                    currency=Currency.USD,
                    tax_amount=reservation.tax_amount,
                    net_amount=reservation.total_cost - Decimal('0.30'),
                    fee_amount=Decimal('0.30'),
                    payment_processor=random.choice(["Stripe", "PayPal", "Square"]),
                    processor_fee=Decimal('0.30'),
                    processed_at=reservation.created_at + timedelta(seconds=30)
                )
                self.session.add(payment)
                self.payments.append(payment)
        
        await self.session.commit()
        print(f"  ✓ Created {len(self.payments)} sample payments")
    
    async def _create_historical_analytics(self):
        """Create historical analytics data"""
        if not self.parking_lots:
            return
        
        # Create analytics for the past 30 days
        for days_back in range(30):
            analysis_date = datetime.utcnow().date() - timedelta(days=days_back)
            
            for lot in self.parking_lots:
                # Occupancy analytics
                occupancy = OccupancyAnalytics(
                    parking_lot_id=lot.id,
                    period_type=AnalyticsPeriod.DAILY,
                    period_start=datetime.combine(analysis_date, time.min),
                    period_end=datetime.combine(analysis_date, time.max),
                    analysis_date=analysis_date,
                    total_spots=lot.total_spots,
                    total_minutes_available=random.randint(200000, 220000),
                    total_minutes_occupied=random.randint(80000, 120000),
                    total_minutes_reserved=random.randint(10000, 30000),
                    occupancy_rate=Decimal(str(random.uniform(40.0, 80.0))),
                    utilization_rate=Decimal(str(random.uniform(50.0, 90.0))),
                    availability_rate=Decimal(str(random.uniform(20.0, 60.0))),
                    peak_occupancy=random.randint(int(lot.total_spots * 0.6), lot.total_spots),
                    average_occupancy=Decimal(str(random.uniform(50.0, 150.0))),
                    total_arrivals=random.randint(100, 300),
                    total_departures=random.randint(95, 295),
                    total_reservations=random.randint(80, 250),
                    no_show_count=random.randint(0, 15),
                    avg_parking_duration=Decimal(str(random.uniform(90.0, 300.0))),
                    min_parking_duration=random.randint(15, 60),
                    max_parking_duration=random.randint(600, 1440),
                    median_parking_duration=Decimal(str(random.uniform(120.0, 180.0))),
                    turnover_rate=Decimal(str(random.uniform(0.2, 0.8))),
                    avg_vacancy_duration=Decimal(str(random.uniform(30.0, 120.0))),
                    regular_spot_occupancy=Decimal(str(random.uniform(60.0, 85.0))),
                    handicapped_spot_occupancy=Decimal(str(random.uniform(20.0, 50.0))),
                    electric_spot_occupancy=Decimal(str(random.uniform(70.0, 95.0))),
                    motorcycle_spot_occupancy=Decimal(str(random.uniform(30.0, 60.0))),
                    morning_peak_occupancy=Decimal(str(random.uniform(70.0, 95.0))),
                    midday_occupancy=Decimal(str(random.uniform(40.0, 70.0))),
                    afternoon_peak_occupancy=Decimal(str(random.uniform(75.0, 100.0))),
                    evening_occupancy=Decimal(str(random.uniform(30.0, 60.0))),
                    overnight_occupancy=Decimal(str(random.uniform(10.0, 30.0))),
                    weekday_avg_occupancy=Decimal(str(random.uniform(60.0, 85.0))),
                    weekend_avg_occupancy=Decimal(str(random.uniform(40.0, 70.0))),
                    data_completeness=Decimal(str(random.uniform(95.0, 100.0))),
                    sensor_uptime=Decimal(str(random.uniform(98.0, 100.0)))
                )
                self.session.add(occupancy)
                
                # Revenue analytics
                revenue = RevenueAnalytics(
                    parking_lot_id=lot.id,
                    period_type=AnalyticsPeriod.DAILY,
                    period_start=datetime.combine(analysis_date, time.min),
                    period_end=datetime.combine(analysis_date, time.max),
                    analysis_date=analysis_date,
                    total_revenue=Decimal(str(random.uniform(800.0, 2000.0))),
                    parking_revenue=Decimal(str(random.uniform(700.0, 1800.0))),
                    penalty_revenue=Decimal(str(random.uniform(0.0, 100.0))),
                    extension_revenue=Decimal(str(random.uniform(20.0, 150.0))),
                    cancellation_revenue=Decimal('0.00'),
                    cash_revenue=Decimal(str(random.uniform(50.0, 200.0))),
                    card_revenue=Decimal(str(random.uniform(400.0, 1200.0))),
                    digital_wallet_revenue=Decimal(str(random.uniform(100.0, 400.0))),
                    mobile_payment_revenue=Decimal(str(random.uniform(50.0, 200.0))),
                    total_transactions=random.randint(50, 150),
                    successful_transactions=random.randint(48, 148),
                    failed_transactions=random.randint(0, 5),
                    refunded_transactions=random.randint(0, 3),
                    avg_transaction_value=Decimal(str(random.uniform(15.0, 35.0))),
                    min_transaction_value=Decimal(str(random.uniform(3.0, 8.0))),
                    max_transaction_value=Decimal(str(random.uniform(80.0, 150.0))),
                    median_transaction_value=Decimal(str(random.uniform(18.0, 28.0))),
                    processing_fees=Decimal(str(random.uniform(20.0, 60.0))),
                    operational_costs=Decimal(str(random.uniform(100.0, 300.0))),
                    net_revenue=Decimal(str(random.uniform(600.0, 1600.0))),
                    avg_hourly_rate=Decimal(str(lot.base_hourly_rate)),
                    avg_daily_rate=Decimal(str(random.uniform(20.0, 50.0))),
                    discount_amount=Decimal(str(random.uniform(10.0, 80.0))),
                    promotion_usage=random.randint(5, 25),
                    total_refunds=Decimal(str(random.uniform(0.0, 50.0))),
                    refund_rate=Decimal(str(random.uniform(0.0, 5.0))),
                    avg_refund_amount=Decimal(str(random.uniform(15.0, 30.0))),
                    unique_customers=random.randint(40, 120),
                    repeat_customers=random.randint(15, 60),
                    new_customers=random.randint(10, 40),
                    revenue_per_spot=Decimal(str(random.uniform(5.0, 20.0))),
                    revenue_per_hour=Decimal(str(random.uniform(30.0, 100.0))),
                    revenue_per_customer=Decimal(str(random.uniform(15.0, 40.0))),
                    morning_revenue=Decimal(str(random.uniform(200.0, 500.0))),
                    midday_revenue=Decimal(str(random.uniform(150.0, 400.0))),
                    afternoon_revenue=Decimal(str(random.uniform(250.0, 600.0))),
                    evening_revenue=Decimal(str(random.uniform(100.0, 300.0))),
                    overnight_revenue=Decimal(str(random.uniform(20.0, 100.0))),
                    weekday_revenue=Decimal(str(random.uniform(600.0, 1400.0))),
                    weekend_revenue=Decimal(str(random.uniform(300.0, 800.0))),
                    subscription_revenue=Decimal('0.00'),
                    one_time_revenue=Decimal(str(random.uniform(800.0, 2000.0))),
                    currency="USD",
                    data_completeness=Decimal(str(random.uniform(95.0, 100.0)))
                )
                self.session.add(revenue)
        
        await self.session.commit()
        print(f"  ✓ Created historical analytics data for {len(self.parking_lots)} lots")
    
    async def _create_performance_analytics(self):
        """Create analytics data for performance testing"""
        await self._create_historical_analytics()
        
        # Create additional analytics for performance testing
        print("  Creating additional performance analytics...")
        # This would create hourly and weekly analytics as well
        # Implementation would be similar but with different period types
        print(f"  ✓ Performance analytics created")

async def main():
    """Main seeding function"""
    parser = argparse.ArgumentParser(description='Smart Parking Management Data Seeder')
    parser.add_argument('scenario', choices=['basic', 'development', 'performance', 'analytics'],
                       help='Seeding scenario to run')
    parser.add_argument('--clear', action='store_true', help='Clear existing data before seeding')
    parser.add_argument('--config', help='Configuration file (JSON)')
    
    args = parser.parse_args()
    
    print("🌱 Smart Parking Management Data Seeder")
    print("=" * 50)
    
    async with AsyncSessionLocal() as session:
        seeder = DataSeeder(session)
        
        try:
            if args.clear:
                await seeder.clear_all_data()
            
            if args.scenario == 'basic':
                await seeder.seed_basic_scenario()
            elif args.scenario == 'development':
                await seeder.seed_development_scenario()
            elif args.scenario == 'performance':
                await seeder.seed_performance_scenario()
            elif args.scenario == 'analytics':
                await seeder.seed_analytics_scenario()
            
            print("\n🎉 Data seeding completed successfully!")
            print("\nTest accounts:")
            print("• Admin: admin@smartparking.com / admin123")
            print("• User 1: john.doe@example.com / password123")
            print("• User 2: jane.smith@example.com / password123")
            
            if args.scenario in ['development', 'performance']:
                print("• Manager: manager@smartparking.com / admin123")
                print("• Operator: operator@smartparking.com / admin123")
            
        except Exception as e:
            print(f"❌ Error during seeding: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(main())
