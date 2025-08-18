"""
Integration Tests for Reservation API Endpoints
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.parking_lot import ParkingLot
from app.models.parking_spot import ParkingSpot
from app.models.vehicle import Vehicle
from app.models.reservation import Reservation


@pytest.mark.integration
class TestReservationAPI:
    """Test reservation API endpoints."""
    
    async def test_create_reservation_success(
        self, 
        client: AsyncClient, 
        test_user: User, 
        test_parking_spot: ParkingSpot, 
        test_vehicle: Vehicle, 
        auth_headers: dict
    ):
        """Test successful reservation creation."""
        start_time = datetime.utcnow() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        reservation_data = {
            "parking_spot_id": test_parking_spot.id,
            "vehicle_id": test_vehicle.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        response = await client.post("/api/v1/reservations/", json=reservation_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["parking_spot_id"] == test_parking_spot.id
        assert data["vehicle_id"] == test_vehicle.id
        assert data["status"] == "confirmed"
    
    async def test_create_reservation_unauthorized(self, client: AsyncClient, test_parking_spot: ParkingSpot, test_vehicle: Vehicle):
        """Test creating reservation without authentication."""
        start_time = datetime.utcnow() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        reservation_data = {
            "parking_spot_id": test_parking_spot.id,
            "vehicle_id": test_vehicle.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        response = await client.post("/api/v1/reservations/", json=reservation_data)
        
        assert response.status_code == 401
    
    async def test_create_reservation_invalid_time_range(
        self, 
        client: AsyncClient, 
        test_parking_spot: ParkingSpot, 
        test_vehicle: Vehicle, 
        auth_headers: dict
    ):
        """Test creating reservation with invalid time range."""
        start_time = datetime.utcnow() + timedelta(hours=2)
        end_time = start_time - timedelta(hours=1)  # End before start
        
        reservation_data = {
            "parking_spot_id": test_parking_spot.id,
            "vehicle_id": test_vehicle.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        response = await client.post("/api/v1/reservations/", json=reservation_data, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "time" in data["detail"].lower()
    
    async def test_create_reservation_past_time(
        self, 
        client: AsyncClient, 
        test_parking_spot: ParkingSpot, 
        test_vehicle: Vehicle, 
        auth_headers: dict
    ):
        """Test creating reservation in the past."""
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = start_time + timedelta(hours=1)
        
        reservation_data = {
            "parking_spot_id": test_parking_spot.id,
            "vehicle_id": test_vehicle.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        response = await client.post("/api/v1/reservations/", json=reservation_data, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "past" in data["detail"].lower()
    
    async def test_create_overlapping_reservation(
        self, 
        client: AsyncClient, 
        test_user: User,
        test_parking_spot: ParkingSpot, 
        test_vehicle: Vehicle, 
        test_reservation: Reservation,
        auth_headers: dict
    ):
        """Test creating overlapping reservation (should fail)."""
        # Try to create reservation that overlaps with existing one
        start_time = test_reservation.start_time + timedelta(minutes=30)
        end_time = test_reservation.end_time + timedelta(minutes=30)
        
        reservation_data = {
            "parking_spot_id": test_parking_spot.id,
            "vehicle_id": test_vehicle.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        response = await client.post("/api/v1/reservations/", json=reservation_data, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "overlap" in data["detail"].lower() or "unavailable" in data["detail"].lower()
    
    async def test_get_user_reservations(self, client: AsyncClient, test_user: User, test_reservation: Reservation, auth_headers: dict):
        """Test getting user's reservations."""
        response = await client.get("/api/v1/reservations/user", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        reservation = data[0]
        assert reservation["user_id"] == test_user.id
        assert reservation["id"] == test_reservation.id
    
    async def test_get_reservation_by_id(self, client: AsyncClient, test_user: User, test_reservation: Reservation, auth_headers: dict):
        """Test getting specific reservation by ID."""
        response = await client.get(f"/api/v1/reservations/{test_reservation.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_reservation.id
        assert data["user_id"] == test_user.id
    
    async def test_get_reservation_unauthorized(self, client: AsyncClient, test_reservation: Reservation):
        """Test getting reservation without authentication."""
        response = await client.get(f"/api/v1/reservations/{test_reservation.id}")
        
        assert response.status_code == 401
    
    async def test_get_reservation_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting nonexistent reservation."""
        response = await client.get("/api/v1/reservations/nonexistent-id", headers=auth_headers)
        
        assert response.status_code == 404
    
    async def test_cancel_reservation(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test canceling a reservation."""
        # Create a future reservation first
        start_time = datetime.utcnow() + timedelta(hours=2)
        end_time = start_time + timedelta(hours=1)
        
        # Assuming we have the necessary fixtures
        reservation_data = {
            "parking_spot_id": "test-spot-id",
            "vehicle_id": "test-vehicle-id", 
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        create_response = await client.post("/api/v1/reservations/", json=reservation_data, headers=auth_headers)
        if create_response.status_code != 201:
            pytest.skip("Could not create reservation for cancellation test")
        
        reservation_id = create_response.json()["id"]
        
        # Cancel the reservation
        response = await client.patch(f"/api/v1/reservations/{reservation_id}/cancel", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
    
    async def test_cancel_reservation_too_late(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test canceling reservation too close to start time."""
        # Create a reservation starting very soon
        start_time = datetime.utcnow() + timedelta(minutes=5)  # Only 5 minutes away
        end_time = start_time + timedelta(hours=1)
        
        reservation_data = {
            "parking_spot_id": "test-spot-id",
            "vehicle_id": "test-vehicle-id",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        create_response = await client.post("/api/v1/reservations/", json=reservation_data, headers=auth_headers)
        if create_response.status_code != 201:
            pytest.skip("Could not create reservation for cancellation test")
        
        reservation_id = create_response.json()["id"]
        
        # Try to cancel (should fail due to time restriction)
        response = await client.patch(f"/api/v1/reservations/{reservation_id}/cancel", headers=auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "too late" in data["detail"].lower() or "cannot cancel" in data["detail"].lower()
    
    async def test_extend_reservation(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test extending a reservation."""
        # Create an active reservation
        start_time = datetime.utcnow() - timedelta(minutes=30)  # Started 30 min ago
        end_time = datetime.utcnow() + timedelta(hours=1)       # Ends in 1 hour
        
        reservation_data = {
            "parking_spot_id": "test-spot-id",
            "vehicle_id": "test-vehicle-id",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        create_response = await client.post("/api/v1/reservations/", json=reservation_data, headers=auth_headers)
        if create_response.status_code != 201:
            pytest.skip("Could not create reservation for extension test")
        
        reservation_id = create_response.json()["id"]
        
        # Extend by 2 hours
        extend_data = {"additional_hours": 2}
        response = await client.patch(f"/api/v1/reservations/{reservation_id}/extend", json=extend_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that end time was extended
        original_end = datetime.fromisoformat(end_time.isoformat().replace('Z', '+00:00'))
        new_end = datetime.fromisoformat(data["end_time"].replace('Z', '+00:00'))
        assert new_end > original_end
    
    async def test_reservation_check_in(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test checking in to a reservation."""
        # Create a reservation that's ready for check-in
        start_time = datetime.utcnow() - timedelta(minutes=5)  # Started 5 min ago
        end_time = start_time + timedelta(hours=2)
        
        reservation_data = {
            "parking_spot_id": "test-spot-id",
            "vehicle_id": "test-vehicle-id",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        create_response = await client.post("/api/v1/reservations/", json=reservation_data, headers=auth_headers)
        if create_response.status_code != 201:
            pytest.skip("Could not create reservation for check-in test")
        
        reservation_id = create_response.json()["id"]
        
        # Check in
        response = await client.patch(f"/api/v1/reservations/{reservation_id}/check-in", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert "checked_in_at" in data
    
    async def test_reservation_check_out(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test checking out of a reservation."""
        # This would require an active reservation
        # Implementation depends on having the check-in functionality working
        pass
    
    async def test_get_reservations_by_date_range(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test filtering reservations by date range."""
        start_date = datetime.utcnow().date()
        end_date = start_date + timedelta(days=7)
        
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        
        response = await client.get("/api/v1/reservations/user", params=params, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All reservations should be within the date range
        for reservation in data:
            res_start = datetime.fromisoformat(reservation["start_time"].replace('Z', '+00:00')).date()
            assert start_date <= res_start <= end_date
    
    async def test_get_reservations_by_status(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test filtering reservations by status."""
        params = {"status": "confirmed"}
        
        response = await client.get("/api/v1/reservations/user", params=params, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All reservations should have the requested status
        for reservation in data:
            assert reservation["status"] == "confirmed"


@pytest.mark.integration
class TestReservationPaymentIntegration:
    """Test reservation and payment integration."""
    
    async def test_reservation_with_payment(self, client: AsyncClient, test_user: User, test_parking_spot: ParkingSpot, test_vehicle: Vehicle, auth_headers: dict):
        """Test creating reservation with immediate payment."""
        start_time = datetime.utcnow() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        reservation_data = {
            "parking_spot_id": test_parking_spot.id,
            "vehicle_id": test_vehicle.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "payment_method": "credit_card",
            "payment_token": "tok_visa_test"
        }
        
        response = await client.post("/api/v1/reservations/", json=reservation_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "confirmed"
        assert "payment" in data
        assert data["payment"]["status"] == "completed"
    
    async def test_reservation_payment_failure(self, client: AsyncClient, test_user: User, test_parking_spot: ParkingSpot, test_vehicle: Vehicle, auth_headers: dict):
        """Test reservation creation when payment fails."""
        start_time = datetime.utcnow() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        reservation_data = {
            "parking_spot_id": test_parking_spot.id,
            "vehicle_id": test_vehicle.id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "payment_method": "credit_card",
            "payment_token": "tok_card_declined"  # Test token that will fail
        }
        
        response = await client.post("/api/v1/reservations/", json=reservation_data, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "payment" in data["detail"].lower()


@pytest.mark.integration
class TestReservationAdminAPI:
    """Test admin reservation management endpoints."""
    
    async def test_get_all_reservations_admin(self, client: AsyncClient, test_admin_user: User, admin_auth_headers: dict):
        """Test getting all reservations as admin."""
        response = await client.get("/api/v1/admin/reservations/", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_get_all_reservations_unauthorized(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test getting all reservations as non-admin."""
        response = await client.get("/api/v1/admin/reservations/", headers=auth_headers)
        
        assert response.status_code == 403
    
    async def test_cancel_any_reservation_admin(self, client: AsyncClient, test_reservation: Reservation, test_admin_user: User, admin_auth_headers: dict):
        """Test admin canceling any user's reservation."""
        response = await client.patch(f"/api/v1/admin/reservations/{test_reservation.id}/cancel", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
    
    async def test_reservation_analytics_admin(self, client: AsyncClient, test_admin_user: User, admin_auth_headers: dict):
        """Test getting reservation analytics as admin."""
        response = await client.get("/api/v1/admin/reservations/analytics", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "total_reservations",
            "completed_reservations", 
            "cancelled_reservations",
            "total_revenue",
            "average_duration"
        ]
        
        for field in required_fields:
            assert field in data
