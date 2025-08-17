from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Numeric, Text, JSON, Time
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.db.database import Base
import enum

class ParkingLotStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    TEMPORARILY_CLOSED = "temporarily_closed"

class ParkingLotType(enum.Enum):
    OUTDOOR = "outdoor"
    INDOOR = "indoor"
    UNDERGROUND = "underground"
    MULTI_LEVEL = "multi_level"
    STREET_PARKING = "street_parking"

class AccessType(enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    RESTRICTED = "restricted"
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"

class ParkingLot(Base):
    __tablename__ = "parking_lots"

    id = Column(Integer, primary_key=True, index=True)
    
    # Basic Information
    name = Column(String(200), nullable=False, index=True)
    code = Column(String(20), unique=True, index=True, nullable=True)  # Short code for identification
    description = Column(Text, nullable=True)
    
    # Location and Geography
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=True)
    
    # PostGIS Geometry for precise location
    location = Column(Geometry('POINT', srid=4326), nullable=False, index=True)  # WGS84
    boundary = Column(Geometry('POLYGON', srid=4326), nullable=True)  # Lot boundary
    
    # Geographic coordinates (for easier querying)
    latitude = Column(Numeric(10, 8), nullable=False, index=True)
    longitude = Column(Numeric(11, 8), nullable=False, index=True)
    
    # Capacity and Layout
    total_spots = Column(Integer, nullable=False, default=0)
    available_spots = Column(Integer, nullable=False, default=0)
    reserved_spots = Column(Integer, nullable=False, default=0)
    disabled_spots = Column(Integer, nullable=False, default=0)
    electric_spots = Column(Integer, nullable=False, default=0)
    motorcycle_spots = Column(Integer, nullable=False, default=0)
    
    # Physical Characteristics
    parking_lot_type = Column(Enum(ParkingLotType), nullable=False)
    access_type = Column(Enum(AccessType), default=AccessType.PUBLIC, nullable=False)
    total_floors = Column(Integer, default=1, nullable=False)
    max_vehicle_height_cm = Column(Integer, nullable=True)  # Height restriction in cm
    max_vehicle_weight_kg = Column(Integer, nullable=True)  # Weight restriction in kg
    
    # Pricing
    base_hourly_rate = Column(Numeric(10, 2), nullable=False, default=0.00)
    daily_rate = Column(Numeric(10, 2), nullable=True)
    monthly_rate = Column(Numeric(10, 2), nullable=True)
    pricing_rules = Column(JSON, nullable=True)  # Complex pricing rules as JSON
    
    # Operating Hours
    is_24_hours = Column(Boolean, default=False, nullable=False)
    opening_time = Column(Time, nullable=True)
    closing_time = Column(Time, nullable=True)
    operating_days = Column(JSON, nullable=True)  # Array of operating days
    
    # Features and Amenities
    has_security = Column(Boolean, default=False, nullable=False)
    has_covered_parking = Column(Boolean, default=False, nullable=False)
    has_ev_charging = Column(Boolean, default=False, nullable=False)
    has_valet_service = Column(Boolean, default=False, nullable=False)
    has_car_wash = Column(Boolean, default=False, nullable=False)
    has_restrooms = Column(Boolean, default=False, nullable=False)
    has_elevators = Column(Boolean, default=False, nullable=False)
    has_wheelchair_access = Column(Boolean, default=False, nullable=False)
    
    # Payment and Access
    accepts_cash = Column(Boolean, default=True, nullable=False)
    accepts_card = Column(Boolean, default=True, nullable=False)
    accepts_mobile_payment = Column(Boolean, default=False, nullable=False)
    requires_permit = Column(Boolean, default=False, nullable=False)
    
    # Contact and Management
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    manager_name = Column(String(200), nullable=True)
    operator_company = Column(String(200), nullable=True)
    
    # Status and Operations
    status = Column(Enum(ParkingLotStatus), default=ParkingLotStatus.ACTIVE, nullable=False)
    is_reservation_enabled = Column(Boolean, default=True, nullable=False)
    is_real_time_updates = Column(Boolean, default=True, nullable=False)
    last_occupancy_update = Column(DateTime(timezone=True), nullable=True)
    
    # Additional Information
    website_url = Column(String(500), nullable=True)
    image_urls = Column(JSON, nullable=True)  # Array of image URLs
    amenities = Column(JSON, nullable=True)  # Additional amenities as JSON array
    restrictions = Column(JSON, nullable=True)  # Parking restrictions as JSON
    special_instructions = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    parking_spots = relationship("ParkingSpot", back_populates="parking_lot", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="parking_lot")
    
    def __repr__(self):
        return f"<ParkingLot(id={self.id}, name='{self.name}', city='{self.city}', total_spots={self.total_spots})>"
    
    @property
    def occupancy_rate(self):
        if self.total_spots == 0:
            return 0.0
        occupied = self.total_spots - self.available_spots
        return (occupied / self.total_spots) * 100
    
    @property
    def is_full(self):
        return self.available_spots == 0
    
    @property
    def coordinates(self):
        return {"latitude": float(self.latitude), "longitude": float(self.longitude)}