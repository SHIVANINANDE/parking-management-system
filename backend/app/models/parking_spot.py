from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Numeric, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.db.database import Base
import enum

class SpotStatus(enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    OUT_OF_ORDER = "out_of_order"
    MAINTENANCE = "maintenance"

class SpotType(enum.Enum):
    REGULAR = "regular"
    COMPACT = "compact"
    HANDICAPPED = "handicapped"
    ELECTRIC = "electric"
    MOTORCYCLE = "motorcycle"
    LOADING_ZONE = "loading_zone"
    VIP = "vip"
    FAMILY = "family"

class ChargingType(enum.Enum):
    NONE = "none"
    TYPE_1 = "type_1"  # J1772
    TYPE_2 = "type_2"  # Mennekes
    CCS = "ccs"        # Combined Charging System
    CHADEMO = "chademo"
    TESLA = "tesla"
    UNIVERSAL = "universal"

class ParkingSpot(Base):
    __tablename__ = "parking_spots"

    id = Column(Integer, primary_key=True, index=True)
    parking_lot_id = Column(Integer, ForeignKey("parking_lots.id"), nullable=False, index=True)
    
    # Spot Identification
    spot_number = Column(String(20), nullable=False, index=True)
    spot_code = Column(String(50), nullable=True)  # QR code or unique identifier
    
    # Location within parking lot
    floor = Column(Integer, default=1, nullable=False)
    section = Column(String(10), nullable=True)  # A, B, C, etc.
    row = Column(String(10), nullable=True)      # Row identifier
    zone = Column(String(50), nullable=True)     # Special zones like "VIP", "Electric", etc.
    
    # Precise positioning with PostGIS
    location = Column(Geometry('POINT', srid=4326), nullable=True, index=True)
    spot_boundary = Column(Geometry('POLYGON', srid=4326), nullable=True)  # Exact spot boundaries
    
    # Geographic coordinates
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    
    # Spot Characteristics
    spot_type = Column(Enum(SpotType), default=SpotType.REGULAR, nullable=False)
    status = Column(Enum(SpotStatus), default=SpotStatus.AVAILABLE, nullable=False, index=True)
    
    # Physical Dimensions (in centimeters)
    length_cm = Column(Integer, nullable=True, default=500)   # 5 meters default
    width_cm = Column(Integer, nullable=True, default=250)    # 2.5 meters default
    height_cm = Column(Integer, nullable=True)                # For covered spots
    
    # Vehicle Restrictions
    max_vehicle_length_cm = Column(Integer, nullable=True)
    max_vehicle_width_cm = Column(Integer, nullable=True)
    max_vehicle_height_cm = Column(Integer, nullable=True)
    max_vehicle_weight_kg = Column(Integer, nullable=True)
    
    # Electric Vehicle Charging
    has_ev_charging = Column(Boolean, default=False, nullable=False)
    charging_type = Column(Enum(ChargingType), default=ChargingType.NONE, nullable=False)
    charging_power_kw = Column(Numeric(5, 2), nullable=True)  # Charging power in kW
    charging_network = Column(String(100), nullable=True)     # ChargePoint, Tesla, etc.
    charging_station_id = Column(String(100), nullable=True)
    
    # Accessibility
    is_handicapped_accessible = Column(Boolean, default=False, nullable=False)
    has_wider_access = Column(Boolean, default=False, nullable=False)
    is_covered = Column(Boolean, default=False, nullable=False)
    
    # Pricing (can override lot pricing)
    has_custom_pricing = Column(Boolean, default=False, nullable=False)
    hourly_rate = Column(Numeric(10, 2), nullable=True)
    daily_rate = Column(Numeric(10, 2), nullable=True)
    pricing_multiplier = Column(Numeric(3, 2), default=1.00, nullable=False)  # Multiplier for base rates
    
    # Sensor and IoT Integration
    sensor_id = Column(String(100), nullable=True, unique=True)
    has_sensor = Column(Boolean, default=False, nullable=False)
    last_sensor_update = Column(DateTime(timezone=True), nullable=True)
    sensor_battery_level = Column(Integer, nullable=True)  # 0-100 percentage
    
    # Status Management
    is_active = Column(Boolean, default=True, nullable=False)
    is_reservable = Column(Boolean, default=True, nullable=False)
    
    # Occupancy Tracking
    current_vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    occupied_since = Column(DateTime(timezone=True), nullable=True)
    last_occupied_at = Column(DateTime(timezone=True), nullable=True)
    total_occupancy_time = Column(Integer, default=0, nullable=False)  # Total minutes occupied
    
    # Maintenance and Issues
    maintenance_notes = Column(Text, nullable=True)
    last_maintenance_date = Column(DateTime(timezone=True), nullable=True)
    issue_reported = Column(Boolean, default=False, nullable=False)
    issue_description = Column(Text, nullable=True)
    issue_reported_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional Features
    features = Column(JSON, nullable=True)  # Additional features as JSON array
    special_instructions = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    status_changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    parking_lot = relationship("ParkingLot", back_populates="parking_spots")
    current_vehicle = relationship("Vehicle", foreign_keys=[current_vehicle_id])
    reservations = relationship("Reservation", back_populates="parking_spot")
    
    def __repr__(self):
        return f"<ParkingSpot(id={self.id}, number='{self.spot_number}', status='{self.status.value}', type='{self.spot_type.value}')>"
    
    @property
    def full_identifier(self):
        parts = [self.spot_number]
        if self.section:
            parts.insert(0, self.section)
        if self.floor > 1:
            parts.insert(0, f"Floor {self.floor}")
        return "-".join(parts)
    
    @property
    def is_available(self):
        return self.status == SpotStatus.AVAILABLE and self.is_active
    
    @property
    def is_occupied(self):
        return self.status == SpotStatus.OCCUPIED
    
    @property
    def is_electric_compatible(self):
        return self.has_ev_charging or self.spot_type == SpotType.ELECTRIC
    
    @property
    def coordinates(self):
        if self.latitude and self.longitude:
            return {"latitude": float(self.latitude), "longitude": float(self.longitude)}
        return None
    
    @property
    def dimensions(self):
        return {
            "length_cm": self.length_cm,
            "width_cm": self.width_cm,
            "height_cm": self.height_cm
        }
    
    def can_accommodate_vehicle(self, vehicle):
        """Check if this spot can accommodate the given vehicle"""
        # Check vehicle type compatibility
        if vehicle.vehicle_type.value == "motorcycle" and self.spot_type != SpotType.MOTORCYCLE:
            return self.spot_type in [SpotType.REGULAR, SpotType.COMPACT]
        
        if vehicle.requires_charging and not self.is_electric_compatible:
            return False
        
        # Check size restrictions if available
        if (self.max_vehicle_length_cm and vehicle.length_cm and 
            vehicle.length_cm > self.max_vehicle_length_cm):
            return False
            
        if (self.max_vehicle_width_cm and vehicle.width_cm and 
            vehicle.width_cm > self.max_vehicle_width_cm):
            return False
            
        if (self.max_vehicle_height_cm and vehicle.height_cm and 
            vehicle.height_cm > self.max_vehicle_height_cm):
            return False
            
        if (self.max_vehicle_weight_kg and vehicle.weight_kg and 
            vehicle.weight_kg > self.max_vehicle_weight_kg):
            return False
        
        return True