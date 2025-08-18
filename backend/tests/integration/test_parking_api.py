"""
Integration Tests for Parking API Endpoints
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.parking_lot import ParkingLot
from app.models.parking_spot import ParkingSpot
from app.models.vehicle import Vehicle
from tests.conftest import ParkingLotFactory, VehicleFactory


@pytest.mark.integration
class TestParkingLotAPI:
    """Test parking lot API endpoints."""
    
    async def test_get_parking_lots(self, client: AsyncClient, test_parking_lot: ParkingLot):
        """Test getting all parking lots."""
        response = await client.get("/api/v1/parking-lots/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        lot = data[0]
        assert lot["id"] == test_parking_lot.id
        assert lot["name"] == test_parking_lot.name
        assert lot["address"] == test_parking_lot.address
    
    async def test_get_parking_lot_by_id(self, client: AsyncClient, test_parking_lot: ParkingLot):
        """Test getting parking lot by ID."""
        response = await client.get(f"/api/v1/parking-lots/{test_parking_lot.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_parking_lot.id
        assert data["name"] == test_parking_lot.name
        assert data["total_spots"] == test_parking_lot.total_spots
        assert data["available_spots"] == test_parking_lot.available_spots
    
    async def test_get_parking_lot_not_found(self, client: AsyncClient):
        """Test getting nonexistent parking lot."""
        response = await client.get("/api/v1/parking-lots/nonexistent-id")
        
        assert response.status_code == 404
    
    async def test_search_nearby_parking_lots(self, client: AsyncClient, test_parking_lot: ParkingLot):
        """Test searching for nearby parking lots."""
        params = {
            "latitude": 37.7749,  # Close to test parking lot
            "longitude": -122.4194,
            "radius": 5000  # 5km radius
        }
        
        response = await client.get("/api/v1/parking-lots/nearby", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Check that distances are included
        lot = data[0]
        assert "distance" in lot
        assert lot["distance"] <= params["radius"]
    
    async def test_search_nearby_parking_lots_no_results(self, client: AsyncClient):
        """Test searching for nearby parking lots with no results."""
        params = {
            "latitude": 0.0,  # Middle of ocean
            "longitude": 0.0,
            "radius": 100  # Small radius
        }
        
        response = await client.get("/api/v1/parking-lots/nearby", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    async def test_create_parking_lot_admin(self, client: AsyncClient, test_admin_user: User, admin_auth_headers: dict):
        """Test creating parking lot as admin."""
        lot_data = ParkingLotFactory.build()
        
        response = await client.post("/api/v1/parking-lots/", json=lot_data, headers=admin_auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == lot_data["name"]
        assert data["address"] == lot_data["address"]
        assert data["latitude"] == lot_data["latitude"]
        assert data["longitude"] == lot_data["longitude"]
    
    async def test_create_parking_lot_unauthorized(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test creating parking lot as non-admin (should fail)."""
        lot_data = ParkingLotFactory.build()
        
        response = await client.post("/api/v1/parking-lots/", json=lot_data, headers=auth_headers)
        
        assert response.status_code == 403
    
    async def test_update_parking_lot_admin(self, client: AsyncClient, test_parking_lot: ParkingLot, test_admin_user: User, admin_auth_headers: dict):
        """Test updating parking lot as admin."""
        update_data = {
            "name": "Updated Parking Lot",
            "hourly_rate": 7.5
        }
        
        response = await client.put(f"/api/v1/parking-lots/{test_parking_lot.id}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["hourly_rate"] == update_data["hourly_rate"]
    
    async def test_delete_parking_lot_admin(self, client: AsyncClient, test_parking_lot: ParkingLot, test_admin_user: User, admin_auth_headers: dict):
        """Test deleting parking lot as admin."""
        response = await client.delete(f"/api/v1/parking-lots/{test_parking_lot.id}", headers=admin_auth_headers)
        
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = await client.get(f"/api/v1/parking-lots/{test_parking_lot.id}")
        assert get_response.status_code == 404


@pytest.mark.integration
class TestParkingSpotAPI:
    """Test parking spot API endpoints."""
    
    async def test_get_parking_spots(self, client: AsyncClient, test_parking_spot: ParkingSpot):
        """Test getting parking spots for a lot."""
        response = await client.get(f"/api/v1/parking-lots/{test_parking_spot.parking_lot_id}/spots")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        spot = data[0]
        assert spot["id"] == test_parking_spot.id
        assert spot["spot_number"] == test_parking_spot.spot_number
        assert spot["spot_type"] == test_parking_spot.spot_type
    
    async def test_get_available_spots(self, client: AsyncClient, test_parking_spot: ParkingSpot):
        """Test getting available parking spots."""
        response = await client.get(f"/api/v1/parking-lots/{test_parking_spot.parking_lot_id}/spots/available")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All spots should be available initially
        for spot in data:
            assert spot["is_available"] is True
    
    async def test_get_spots_by_type(self, client: AsyncClient, test_parking_spot: ParkingSpot):
        """Test getting spots by type."""
        params = {"spot_type": "regular"}
        response = await client.get(f"/api/v1/parking-lots/{test_parking_spot.parking_lot_id}/spots", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All returned spots should be of the requested type
        for spot in data:
            assert spot["spot_type"] == "regular"
    
    async def test_create_parking_spot_admin(self, client: AsyncClient, test_parking_lot: ParkingLot, test_admin_user: User, admin_auth_headers: dict):
        """Test creating parking spot as admin."""
        spot_data = {
            "spot_number": "B01",
            "spot_type": "handicap",
            "is_available": True,
            "is_active": True
        }
        
        response = await client.post(f"/api/v1/parking-lots/{test_parking_lot.id}/spots", json=spot_data, headers=admin_auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["spot_number"] == spot_data["spot_number"]
        assert data["spot_type"] == spot_data["spot_type"]
        assert data["parking_lot_id"] == test_parking_lot.id
    
    async def test_update_parking_spot_admin(self, client: AsyncClient, test_parking_spot: ParkingSpot, test_admin_user: User, admin_auth_headers: dict):
        """Test updating parking spot as admin."""
        update_data = {
            "spot_type": "electric",
            "is_active": False
        }
        
        response = await client.put(f"/api/v1/parking-spots/{test_parking_spot.id}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["spot_type"] == update_data["spot_type"]
        assert data["is_active"] == update_data["is_active"]


@pytest.mark.integration
class TestVehicleAPI:
    """Test vehicle API endpoints."""
    
    async def test_get_user_vehicles(self, client: AsyncClient, test_user: User, test_vehicle: Vehicle, auth_headers: dict):
        """Test getting user's vehicles."""
        response = await client.get("/api/v1/vehicles/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        vehicle = data[0]
        assert vehicle["id"] == test_vehicle.id
        assert vehicle["license_plate"] == test_vehicle.license_plate
        assert vehicle["make"] == test_vehicle.make
        assert vehicle["model"] == test_vehicle.model
    
    async def test_get_vehicle_by_id(self, client: AsyncClient, test_user: User, test_vehicle: Vehicle, auth_headers: dict):
        """Test getting vehicle by ID."""
        response = await client.get(f"/api/v1/vehicles/{test_vehicle.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_vehicle.id
        assert data["user_id"] == test_user.id
    
    async def test_get_vehicle_unauthorized(self, client: AsyncClient, test_vehicle: Vehicle):
        """Test getting vehicle without authentication."""
        response = await client.get(f"/api/v1/vehicles/{test_vehicle.id}")
        
        assert response.status_code == 401
    
    async def test_create_vehicle(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test creating a new vehicle."""
        vehicle_data = VehicleFactory.build()
        
        response = await client.post("/api/v1/vehicles/", json=vehicle_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["license_plate"] == vehicle_data["license_plate"]
        assert data["make"] == vehicle_data["make"]
        assert data["model"] == vehicle_data["model"]
        assert data["color"] == vehicle_data["color"]
        assert data["user_id"] == test_user.id
    
    async def test_create_vehicle_duplicate_license_plate(self, client: AsyncClient, test_user: User, test_vehicle: Vehicle, auth_headers: dict):
        """Test creating vehicle with duplicate license plate."""
        vehicle_data = VehicleFactory.build()
        vehicle_data["license_plate"] = test_vehicle.license_plate  # Duplicate
        
        response = await client.post("/api/v1/vehicles/", json=vehicle_data, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "license plate" in data["detail"].lower()
    
    async def test_update_vehicle(self, client: AsyncClient, test_user: User, test_vehicle: Vehicle, auth_headers: dict):
        """Test updating vehicle."""
        update_data = {
            "make": "BMW",
            "model": "X5",
            "color": "Black"
        }
        
        response = await client.put(f"/api/v1/vehicles/{test_vehicle.id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["make"] == update_data["make"]
        assert data["model"] == update_data["model"]
        assert data["color"] == update_data["color"]
    
    async def test_update_vehicle_unauthorized(self, client: AsyncClient, test_vehicle: Vehicle):
        """Test updating vehicle without authentication."""
        update_data = {"make": "BMW"}
        
        response = await client.put(f"/api/v1/vehicles/{test_vehicle.id}", json=update_data)
        
        assert response.status_code == 401
    
    async def test_delete_vehicle(self, client: AsyncClient, test_user: User, test_vehicle: Vehicle, auth_headers: dict):
        """Test deleting vehicle."""
        response = await client.delete(f"/api/v1/vehicles/{test_vehicle.id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = await client.get(f"/api/v1/vehicles/{test_vehicle.id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    async def test_delete_vehicle_with_reservations(self, client: AsyncClient, test_user: User, test_vehicle: Vehicle, test_reservation, auth_headers: dict):
        """Test deleting vehicle that has reservations (should fail)."""
        response = await client.delete(f"/api/v1/vehicles/{test_vehicle.id}", headers=auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "reservations" in data["detail"].lower()


@pytest.mark.integration
class TestParkingAnalyticsAPI:
    """Test parking analytics API endpoints."""
    
    async def test_get_parking_lot_analytics(self, client: AsyncClient, test_parking_lot: ParkingLot, test_admin_user: User, admin_auth_headers: dict):
        """Test getting parking lot analytics."""
        response = await client.get(f"/api/v1/parking-lots/{test_parking_lot.id}/analytics", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required analytics fields
        required_fields = [
            "total_reservations",
            "total_revenue",
            "average_duration",
            "occupancy_rate",
            "peak_hours"
        ]
        
        for field in required_fields:
            assert field in data
    
    async def test_get_parking_lot_analytics_unauthorized(self, client: AsyncClient, test_parking_lot: ParkingLot, test_user: User, auth_headers: dict):
        """Test getting parking lot analytics as non-admin."""
        response = await client.get(f"/api/v1/parking-lots/{test_parking_lot.id}/analytics", headers=auth_headers)
        
        assert response.status_code == 403
    
    async def test_get_system_analytics(self, client: AsyncClient, test_admin_user: User, admin_auth_headers: dict):
        """Test getting system-wide analytics."""
        response = await client.get("/api/v1/analytics/system", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "total_parking_lots",
            "total_parking_spots",
            "total_users",
            "total_reservations",
            "total_revenue",
            "average_utilization"
        ]
        
        for field in required_fields:
            assert field in data
    
    async def test_get_user_analytics(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test getting user's personal analytics."""
        response = await client.get("/api/v1/analytics/user", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "total_reservations",
            "total_spent",
            "average_duration",
            "favorite_locations",
            "parking_patterns"
        ]
        
        for field in required_fields:
            assert field in data
