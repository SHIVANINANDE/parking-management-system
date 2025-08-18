"""
Unit Tests for Parking Lot Model and Services
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parking_lot import ParkingLot
from app.models.parking_spot import ParkingSpot
from app.services.parking_service import ParkingService
from tests.conftest import ParkingLotFactory


@pytest.mark.unit
class TestParkingLotModel:
    """Test ParkingLot model functionality."""
    
    def test_parking_lot_creation(self):
        """Test parking lot model creation."""
        lot_data = ParkingLotFactory.build()
        lot = ParkingLot(**lot_data)
        
        assert lot.name == lot_data["name"]
        assert lot.address == lot_data["address"]
        assert lot.latitude == lot_data["latitude"]
        assert lot.longitude == lot_data["longitude"]
        assert lot.total_spots == lot_data["total_spots"]
        assert lot.hourly_rate == lot_data["hourly_rate"]
        assert lot.is_active == lot_data["is_active"]
    
    def test_parking_lot_occupancy_rate(self):
        """Test occupancy rate calculation."""
        lot = ParkingLot(
            total_spots=100,
            available_spots=75
        )
        
        assert lot.occupancy_rate == 0.25  # 25% occupied
    
    def test_parking_lot_coordinates(self):
        """Test coordinate validation."""
        # Valid coordinates
        lot = ParkingLot(
            name="Test Lot",
            latitude=37.7749,  # San Francisco
            longitude=-122.4194
        )
        
        assert -90 <= lot.latitude <= 90
        assert -180 <= lot.longitude <= 180
    
    def test_parking_lot_availability_update(self):
        """Test updating available spots."""
        lot = ParkingLot(
            total_spots=100,
            available_spots=100
        )
        
        # Reserve a spot
        lot.available_spots -= 1
        assert lot.available_spots == 99
        assert lot.occupancy_rate == 0.01
        
        # Release a spot
        lot.available_spots += 1
        assert lot.available_spots == 100
        assert lot.occupancy_rate == 0.0


@pytest.mark.unit
class TestParkingSpotModel:
    """Test ParkingSpot model functionality."""
    
    def test_parking_spot_creation(self):
        """Test parking spot model creation."""
        spot = ParkingSpot(
            parking_lot_id="lot-123",
            spot_number="A01",
            spot_type="regular",
            is_available=True,
            is_active=True
        )
        
        assert spot.parking_lot_id == "lot-123"
        assert spot.spot_number == "A01"
        assert spot.spot_type == "regular"
        assert spot.is_available is True
        assert spot.is_active is True
    
    def test_spot_types_validation(self):
        """Test spot type validation."""
        valid_types = ["regular", "handicap", "electric", "compact", "motorcycle"]
        
        for spot_type in valid_types:
            spot = ParkingSpot(
                parking_lot_id="lot-123",
                spot_number="A01",
                spot_type=spot_type
            )
            assert spot.spot_type == spot_type
    
    def test_spot_reservation_status(self):
        """Test spot reservation status changes."""
        spot = ParkingSpot(
            parking_lot_id="lot-123",
            spot_number="A01",
            spot_type="regular",
            is_available=True
        )
        
        # Reserve the spot
        spot.is_available = False
        assert spot.is_available is False
        
        # Release the spot
        spot.is_available = True
        assert spot.is_available is True


@pytest.mark.unit
class TestParkingService:
    """Test ParkingService functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock(spec=AsyncSession)
    
    @pytest.fixture
    def parking_service(self, mock_db):
        """Create ParkingService instance with mock db."""
        return ParkingService(mock_db)
    
    async def test_create_parking_lot(self, parking_service, mock_db):
        """Test parking lot creation service."""
        lot_data = ParkingLotFactory.build()
        mock_lot = ParkingLot(**lot_data)
        mock_lot.id = "test-lot-id"
        
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        with patch('app.services.parking_service.ParkingLot') as MockParkingLot:
            MockParkingLot.return_value = mock_lot
            
            result = await parking_service.create_parking_lot(lot_data)
            
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
    
    async def test_get_nearby_parking_lots(self, parking_service, mock_db):
        """Test getting nearby parking lots."""
        latitude = 37.7749
        longitude = -122.4194
        radius = 1000  # meters
        
        mock_lots = [
            ParkingLot(id="lot1", name="Lot 1", latitude=37.7750, longitude=-122.4195),
            ParkingLot(id="lot2", name="Lot 2", latitude=37.7748, longitude=-122.4193)
        ]
        
        with patch('app.services.parking_service.calculate_distance') as mock_distance:
            mock_distance.side_effect = [500, 300]  # distances in meters
            
            mock_db.execute.return_value.scalars.return_value.all.return_value = mock_lots
            
            result = await parking_service.get_nearby_parking_lots(
                latitude, longitude, radius
            )
            
            assert len(result) == 2
            assert all(lot.distance <= radius for lot in result)
    
    async def test_find_available_spot(self, parking_service, mock_db):
        """Test finding available parking spot."""
        lot_id = "test-lot-id"
        spot_type = "regular"
        
        mock_spot = ParkingSpot(
            id="spot-123",
            parking_lot_id=lot_id,
            spot_number="A01",
            spot_type=spot_type,
            is_available=True
        )
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_spot
        
        result = await parking_service.find_available_spot(lot_id, spot_type)
        
        assert result == mock_spot
        assert result.is_available is True
        mock_db.execute.assert_called_once()
    
    async def test_reserve_parking_spot(self, parking_service, mock_db):
        """Test parking spot reservation."""
        spot_id = "spot-123"
        
        mock_spot = ParkingSpot(
            id=spot_id,
            parking_lot_id="lot-123",
            spot_number="A01",
            is_available=True
        )
        
        with patch.object(parking_service, 'get_spot_by_id', return_value=mock_spot):
            mock_db.commit = Mock()
            
            result = await parking_service.reserve_spot(spot_id)
            
            assert result.is_available is False
            mock_db.commit.assert_called_once()
    
    async def test_release_parking_spot(self, parking_service, mock_db):
        """Test parking spot release."""
        spot_id = "spot-123"
        
        mock_spot = ParkingSpot(
            id=spot_id,
            parking_lot_id="lot-123",
            spot_number="A01",
            is_available=False
        )
        
        with patch.object(parking_service, 'get_spot_by_id', return_value=mock_spot):
            mock_db.commit = Mock()
            
            result = await parking_service.release_spot(spot_id)
            
            assert result.is_available is True
            mock_db.commit.assert_called_once()
    
    async def test_calculate_parking_fee(self, parking_service):
        """Test parking fee calculation."""
        from datetime import datetime, timedelta
        
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=3, minutes=30)
        hourly_rate = 5.0
        
        fee = await parking_service.calculate_fee(start_time, end_time, hourly_rate)
        
        # 3.5 hours * $5.00 = $17.50
        expected_fee = 3.5 * 5.0
        assert fee == expected_fee
    
    async def test_get_parking_lot_analytics(self, parking_service, mock_db):
        """Test parking lot analytics."""
        lot_id = "test-lot-id"
        
        mock_analytics = {
            "total_reservations": 150,
            "average_duration": 2.5,
            "peak_hours": [9, 10, 11, 17, 18],
            "revenue": 2500.0,
            "occupancy_rate": 0.75
        }
        
        with patch.object(
            parking_service, 
            'get_lot_analytics', 
            return_value=mock_analytics
        ):
            result = await parking_service.get_lot_analytics(lot_id)
            
            assert result["total_reservations"] == 150
            assert result["average_duration"] == 2.5
            assert result["revenue"] == 2500.0
            assert result["occupancy_rate"] == 0.75


@pytest.mark.unit
class TestSpatialCalculations:
    """Test spatial calculation utilities."""
    
    def test_distance_calculation(self):
        """Test distance calculation between coordinates."""
        from app.utils.spatial import calculate_distance
        
        # San Francisco to Los Angeles (approx 559 km)
        lat1, lon1 = 37.7749, -122.4194  # SF
        lat2, lon2 = 34.0522, -118.2437   # LA
        
        distance = calculate_distance(lat1, lon1, lat2, lon2)
        
        # Should be approximately 559,000 meters
        assert 550000 <= distance <= 570000
    
    def test_distance_calculation_same_point(self):
        """Test distance calculation for same point."""
        from app.utils.spatial import calculate_distance
        
        lat, lon = 37.7749, -122.4194
        distance = calculate_distance(lat, lon, lat, lon)
        
        assert distance == 0.0
    
    def test_point_in_radius(self):
        """Test if point is within radius."""
        from app.utils.spatial import is_within_radius
        
        center_lat, center_lon = 37.7749, -122.4194
        point_lat, point_lon = 37.7750, -122.4195  # Very close point
        radius = 1000  # 1km
        
        result = is_within_radius(
            center_lat, center_lon, 
            point_lat, point_lon, 
            radius
        )
        
        assert result is True
    
    def test_point_outside_radius(self):
        """Test if point is outside radius."""
        from app.utils.spatial import is_within_radius
        
        center_lat, center_lon = 37.7749, -122.4194  # SF
        point_lat, point_lon = 34.0522, -118.2437    # LA
        radius = 1000  # 1km
        
        result = is_within_radius(
            center_lat, center_lon, 
            point_lat, point_lon, 
            radius
        )
        
        assert result is False
