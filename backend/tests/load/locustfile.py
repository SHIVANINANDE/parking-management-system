"""
Load Testing for Parking Management System
Using Locust to simulate realistic user behavior and system load
"""
from locust import HttpUser, task, between
import random
import json
from datetime import datetime, timedelta


class ParkingSystemUser(HttpUser):
    """
    Simulates a typical user of the parking management system.
    Performs common operations like searching for parking, making reservations,
    and managing user profile.
    """
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Called when a user starts - handles authentication"""
        self.login()
    
    def login(self):
        """Authenticate user and store tokens"""
        # Create a test user account or use existing credentials
        email = f"loadtest_user_{random.randint(1000, 9999)}@example.com"
        password = "LoadTest123!"
        
        # Register user (in production, you'd have pre-created test accounts)
        user_data = {
            "email": email,
            "password": password,
            "first_name": "Load",
            "last_name": "Test",
            "phone": f"555{random.randint(1000000, 9999999)}"
        }
        
        register_response = self.client.post("/api/v1/auth/register", json=user_data)
        if register_response.status_code in [200, 201]:
            print(f"Created test user: {email}")
        
        # Login
        login_data = {
            "username": email,
            "password": password
        }
        
        response = self.client.post("/api/v1/auth/login", data=login_data)
        if response.status_code == 200:
            tokens = response.json()
            self.access_token = tokens.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.access_token}"}
            print(f"Successfully logged in as {email}")
        else:
            print(f"Login failed for {email}: {response.text}")
            self.headers = {}
    
    @task(3)
    def search_nearby_parking(self):
        """Search for nearby parking lots - most common operation"""
        # Random location (simulate different areas of a city)
        locations = [
            {"lat": 37.7749, "lng": -122.4194},  # San Francisco
            {"lat": 37.7849, "lng": -122.4094},  # Different SF area
            {"lat": 37.7649, "lng": -122.4294},  # Another SF area
        ]
        
        location = random.choice(locations)
        params = {
            "latitude": location["lat"],
            "longitude": location["lng"],
            "radius": random.randint(500, 2000)  # 0.5-2km radius
        }
        
        with self.client.get(
            "/api/v1/parking-lots/nearby", 
            params=params,
            name="search_nearby_parking",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                lots = response.json()
                if lots:
                    response.success()
                    self.current_lots = lots[:5]  # Store top 5 for later use
                else:
                    response.failure("No parking lots found")
            else:
                response.failure(f"Search failed: {response.text}")
    
    @task(2)
    def view_parking_lot_details(self):
        """View details of a specific parking lot"""
        if hasattr(self, 'current_lots') and self.current_lots:
            lot = random.choice(self.current_lots)
            lot_id = lot.get('id')
            
            with self.client.get(
                f"/api/v1/parking-lots/{lot_id}",
                name="view_parking_lot_details",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                    self.selected_lot = response.json()
                else:
                    response.failure(f"Failed to get lot details: {response.text}")
    
    @task(2)
    def view_available_spots(self):
        """Check available spots in a parking lot"""
        if hasattr(self, 'selected_lot') and self.selected_lot:
            lot_id = self.selected_lot.get('id')
            
            with self.client.get(
                f"/api/v1/parking-lots/{lot_id}/spots/available",
                name="view_available_spots",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    spots = response.json()
                    if spots:
                        response.success()
                        self.available_spots = spots[:3]  # Store some spots
                    else:
                        response.failure("No available spots")
                else:
                    response.failure(f"Failed to get spots: {response.text}")
    
    @task(1)
    def create_vehicle(self):
        """Add a new vehicle to user's account"""
        if not hasattr(self, 'headers') or not self.headers:
            return
        
        vehicle_data = {
            "license_plate": f"TEST{random.randint(100, 999)}",
            "make": random.choice(["Toyota", "Honda", "Ford", "BMW"]),
            "model": random.choice(["Camry", "Civic", "Focus", "X3"]),
            "color": random.choice(["Black", "White", "Silver", "Blue"]),
            "vehicle_type": "sedan"
        }
        
        with self.client.post(
            "/api/v1/vehicles/",
            json=vehicle_data,
            headers=self.headers,
            name="create_vehicle",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
                self.user_vehicle = response.json()
            else:
                response.failure(f"Failed to create vehicle: {response.text}")
    
    @task(1)
    def make_reservation(self):
        """Make a parking reservation - core business operation"""
        if not all([
            hasattr(self, 'headers') and self.headers,
            hasattr(self, 'available_spots') and self.available_spots,
            hasattr(self, 'user_vehicle') and self.user_vehicle
        ]):
            return
        
        spot = random.choice(self.available_spots)
        start_time = datetime.utcnow() + timedelta(hours=random.randint(1, 4))
        end_time = start_time + timedelta(hours=random.randint(1, 8))
        
        reservation_data = {
            "parking_spot_id": spot["id"],
            "vehicle_id": self.user_vehicle["id"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        with self.client.post(
            "/api/v1/reservations/",
            json=reservation_data,
            headers=self.headers,
            name="make_reservation",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
                self.user_reservation = response.json()
            else:
                response.failure(f"Failed to create reservation: {response.text}")
    
    @task(1)
    def view_user_reservations(self):
        """View user's current and past reservations"""
        if not hasattr(self, 'headers') or not self.headers:
            return
        
        with self.client.get(
            "/api/v1/reservations/user",
            headers=self.headers,
            name="view_user_reservations",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get reservations: {response.text}")
    
    @task(1)
    def update_profile(self):
        """Update user profile information"""
        if not hasattr(self, 'headers') or not self.headers:
            return
        
        update_data = {
            "phone": f"555{random.randint(1000000, 9999999)}"
        }
        
        with self.client.put(
            "/api/v1/auth/profile",
            json=update_data,
            headers=self.headers,
            name="update_profile",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to update profile: {response.text}")


class AdminUser(HttpUser):
    """
    Simulates admin user behavior - managing parking lots, viewing analytics
    """
    
    wait_time = between(2, 8)  # Admins typically take longer between actions
    weight = 1  # Lower weight - fewer admin users
    
    def on_start(self):
        """Admin login"""
        # Use predefined admin credentials
        login_data = {
            "username": "admin@example.com",
            "password": "AdminPass123!"
        }
        
        response = self.client.post("/api/v1/auth/login", data=login_data)
        if response.status_code == 200:
            tokens = response.json()
            self.access_token = tokens.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.access_token}"}
        else:
            print(f"Admin login failed: {response.text}")
            self.headers = {}
    
    @task(2)
    def view_all_parking_lots(self):
        """View all parking lots in the system"""
        if not hasattr(self, 'headers') or not self.headers:
            return
        
        with self.client.get(
            "/api/v1/parking-lots/",
            headers=self.headers,
            name="admin_view_all_lots",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                self.all_lots = response.json()
            else:
                response.failure(f"Failed to get all lots: {response.text}")
    
    @task(1)
    def view_system_analytics(self):
        """View system-wide analytics"""
        if not hasattr(self, 'headers') or not self.headers:
            return
        
        with self.client.get(
            "/api/v1/analytics/system",
            headers=self.headers,
            name="admin_system_analytics",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get analytics: {response.text}")
    
    @task(1)
    def view_lot_analytics(self):
        """View analytics for a specific parking lot"""
        if not all([
            hasattr(self, 'headers') and self.headers,
            hasattr(self, 'all_lots') and self.all_lots
        ]):
            return
        
        lot = random.choice(self.all_lots)
        lot_id = lot.get('id')
        
        with self.client.get(
            f"/api/v1/parking-lots/{lot_id}/analytics",
            headers=self.headers,
            name="admin_lot_analytics",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get lot analytics: {response.text}")
    
    @task(1)
    def create_parking_lot(self):
        """Create a new parking lot"""
        if not hasattr(self, 'headers') or not self.headers:
            return
        
        lot_data = {
            "name": f"Load Test Lot {random.randint(1000, 9999)}",
            "address": f"{random.randint(100, 999)} Test Street",
            "latitude": 37.7749 + random.uniform(-0.1, 0.1),
            "longitude": -122.4194 + random.uniform(-0.1, 0.1),
            "total_spots": random.randint(50, 200),
            "hourly_rate": round(random.uniform(2.0, 15.0), 2),
            "is_active": True
        }
        
        with self.client.post(
            "/api/v1/parking-lots/",
            json=lot_data,
            headers=self.headers,
            name="admin_create_lot",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Failed to create lot: {response.text}")


class HighVolumeSearchUser(HttpUser):
    """
    Simulates high-frequency search behavior (mobile apps, etc.)
    """
    
    wait_time = between(0.5, 2)  # Very frequent requests
    weight = 2  # More of these users
    
    @task
    def rapid_searches(self):
        """Perform rapid location-based searches"""
        # Simulate moving around the city
        base_lat, base_lng = 37.7749, -122.4194
        lat = base_lat + random.uniform(-0.05, 0.05)
        lng = base_lng + random.uniform(-0.05, 0.05)
        
        params = {
            "latitude": lat,
            "longitude": lng,
            "radius": 1000
        }
        
        self.client.get("/api/v1/parking-lots/nearby", params=params, name="rapid_search")


# Locust configuration for different load testing scenarios
class LoadTestConfig:
    """Configuration for different load testing scenarios"""
    
    # Scenario 1: Normal traffic
    NORMAL_USERS = 50
    NORMAL_SPAWN_RATE = 2
    
    # Scenario 2: Peak traffic (rush hour)
    PEAK_USERS = 200
    PEAK_SPAWN_RATE = 10
    
    # Scenario 3: Stress test
    STRESS_USERS = 500
    STRESS_SPAWN_RATE = 20
    
    # Scenario 4: Spike test
    SPIKE_USERS = 1000
    SPIKE_SPAWN_RATE = 50
