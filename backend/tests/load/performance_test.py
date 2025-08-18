"""
Performance Testing Utilities and Custom Load Testing Scenarios
"""
import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict, Any
from datetime import datetime, timedelta
import json


class PerformanceMetrics:
    """Collect and analyze performance metrics"""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.error_count = 0
        self.success_count = 0
        self.start_time = time.time()
    
    def record_response(self, response_time: float, success: bool):
        """Record a response time and success/failure"""
        self.response_times.append(response_time)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.response_times:
            return {}
        
        total_requests = len(self.response_times)
        elapsed_time = time.time() - self.start_time
        
        return {
            "total_requests": total_requests,
            "success_rate": (self.success_count / total_requests) * 100,
            "error_rate": (self.error_count / total_requests) * 100,
            "requests_per_second": total_requests / elapsed_time,
            "avg_response_time": statistics.mean(self.response_times),
            "median_response_time": statistics.median(self.response_times),
            "min_response_time": min(self.response_times),
            "max_response_time": max(self.response_times),
            "p95_response_time": self._percentile(self.response_times, 95),
            "p99_response_time": self._percentile(self.response_times, 99),
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]


class APILoadTester:
    """Custom API load tester for specific scenarios"""
    
    def __init__(self, base_url: str, auth_token: str = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.session = None
        self.metrics = PerformanceMetrics()
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request and record metrics"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.get('headers', {})
        
        if self.auth_token:
            headers['Authorization'] = f"Bearer {self.auth_token}"
        
        start_time = time.time()
        success = False
        response_data = {}
        
        try:
            async with self.session.request(method, url, headers=headers, **kwargs) as response:
                response_time = time.time() - start_time
                success = 200 <= response.status < 300
                
                try:
                    response_data = await response.json()
                except:
                    response_data = {"text": await response.text()}
                
                self.metrics.record_response(response_time, success)
                
                return {
                    "status": response.status,
                    "response_time": response_time,
                    "success": success,
                    "data": response_data
                }
        
        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.record_response(response_time, False)
            
            return {
                "status": 0,
                "response_time": response_time,
                "success": False,
                "error": str(e)
            }


async def test_parking_search_performance(concurrent_users: int = 50, duration_seconds: int = 60):
    """Test parking search endpoint performance"""
    
    async def search_worker(worker_id: int, results: List[Dict]):
        """Individual worker for search testing"""
        async with APILoadTester("http://localhost:8000") as tester:
            end_time = time.time() + duration_seconds
            worker_results = []
            
            while time.time() < end_time:
                # Random search parameters
                import random
                params = {
                    "latitude": 37.7749 + random.uniform(-0.1, 0.1),
                    "longitude": -122.4194 + random.uniform(-0.1, 0.1),
                    "radius": random.randint(500, 2000)
                }
                
                result = await tester.make_request(
                    "GET", 
                    "/api/v1/parking-lots/nearby",
                    params=params
                )
                
                worker_results.append({
                    "worker_id": worker_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    **result
                })
                
                # Small delay to simulate realistic usage
                await asyncio.sleep(0.1)
            
            results.extend(worker_results)
    
    # Run concurrent workers
    results = []
    tasks = [
        search_worker(i, results) 
        for i in range(concurrent_users)
    ]
    
    print(f"Starting parking search performance test...")
    print(f"Concurrent users: {concurrent_users}")
    print(f"Duration: {duration_seconds} seconds")
    
    start_time = time.time()
    await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Analyze results
    success_count = sum(1 for r in results if r.get('success', False))
    total_requests = len(results)
    avg_response_time = statistics.mean([r['response_time'] for r in results])
    
    print(f"\n=== Parking Search Performance Results ===")
    print(f"Total requests: {total_requests}")
    print(f"Successful requests: {success_count}")
    print(f"Success rate: {(success_count/total_requests)*100:.2f}%")
    print(f"Average response time: {avg_response_time:.3f}s")
    print(f"Requests per second: {total_requests/total_time:.2f}")
    
    return results


async def test_reservation_flow_performance():
    """Test the complete reservation flow performance"""
    
    async with APILoadTester("http://localhost:8000") as tester:
        # 1. Register user
        user_data = {
            "email": f"perftest_{int(time.time())}@example.com",
            "password": "PerfTest123!",
            "first_name": "Perf",
            "last_name": "Test",
            "phone": "5551234567"
        }
        
        print("1. Registering user...")
        register_result = await tester.make_request("POST", "/api/v1/auth/register", json=user_data)
        print(f"   Registration: {register_result['response_time']:.3f}s")
        
        # 2. Login
        print("2. Logging in...")
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        login_result = await tester.make_request("POST", "/api/v1/auth/login", data=login_data)
        print(f"   Login: {login_result['response_time']:.3f}s")
        
        if not login_result['success']:
            print("Login failed, cannot continue")
            return
        
        # Update auth token
        token = login_result['data'].get('access_token')
        tester.auth_token = token
        
        # 3. Search for parking
        print("3. Searching for parking...")
        search_params = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "radius": 1000
        }
        search_result = await tester.make_request("GET", "/api/v1/parking-lots/nearby", params=search_params)
        print(f"   Search: {search_result['response_time']:.3f}s")
        
        if not search_result['success'] or not search_result['data']:
            print("No parking lots found, cannot continue")
            return
        
        lot = search_result['data'][0]
        
        # 4. Get available spots
        print("4. Getting available spots...")
        spots_result = await tester.make_request("GET", f"/api/v1/parking-lots/{lot['id']}/spots/available")
        print(f"   Get spots: {spots_result['response_time']:.3f}s")
        
        if not spots_result['success'] or not spots_result['data']:
            print("No available spots, cannot continue")
            return
        
        spot = spots_result['data'][0]
        
        # 5. Create vehicle
        print("5. Creating vehicle...")
        vehicle_data = {
            "license_plate": f"PERF{int(time.time() % 10000)}",
            "make": "Toyota",
            "model": "Camry",
            "color": "Blue",
            "vehicle_type": "sedan"
        }
        vehicle_result = await tester.make_request("POST", "/api/v1/vehicles/", json=vehicle_data)
        print(f"   Create vehicle: {vehicle_result['response_time']:.3f}s")
        
        if not vehicle_result['success']:
            print("Vehicle creation failed, cannot continue")
            return
        
        vehicle = vehicle_result['data']
        
        # 6. Make reservation
        print("6. Making reservation...")
        start_time = datetime.utcnow() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        reservation_data = {
            "parking_spot_id": spot["id"],
            "vehicle_id": vehicle["id"],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        reservation_result = await tester.make_request("POST", "/api/v1/reservations/", json=reservation_data)
        print(f"   Make reservation: {reservation_result['response_time']:.3f}s")
        
        # Summary
        total_time = sum([
            register_result['response_time'],
            login_result['response_time'],
            search_result['response_time'],
            spots_result['response_time'],
            vehicle_result['response_time'],
            reservation_result['response_time']
        ])
        
        print(f"\n=== Complete Reservation Flow Performance ===")
        print(f"Total flow time: {total_time:.3f}s")
        print(f"All operations successful: {all([
            register_result['success'],
            login_result['success'],
            search_result['success'],
            spots_result['success'],
            vehicle_result['success'],
            reservation_result['success']
        ])}")


async def test_database_performance():
    """Test database query performance under load"""
    
    async def db_query_worker(worker_id: int, query_type: str, results: List[Dict]):
        """Worker for database query testing"""
        async with APILoadTester("http://localhost:8000") as tester:
            worker_results = []
            
            for i in range(100):  # 100 queries per worker
                if query_type == "search":
                    # Search queries
                    import random
                    params = {
                        "latitude": 37.7749 + random.uniform(-0.1, 0.1),
                        "longitude": -122.4194 + random.uniform(-0.1, 0.1),
                        "radius": random.randint(500, 2000)
                    }
                    result = await tester.make_request("GET", "/api/v1/parking-lots/nearby", params=params)
                
                elif query_type == "lots":
                    # Get all parking lots
                    result = await tester.make_request("GET", "/api/v1/parking-lots/")
                
                elif query_type == "analytics":
                    # Analytics queries (more complex)
                    result = await tester.make_request("GET", "/api/v1/analytics/system")
                
                worker_results.append({
                    "worker_id": worker_id,
                    "query_type": query_type,
                    "response_time": result['response_time'],
                    "success": result['success']
                })
            
            results.extend(worker_results)
    
    # Test different query types concurrently
    results = []
    tasks = []
    
    # 10 workers for each query type
    for query_type in ["search", "lots", "analytics"]:
        for worker_id in range(10):
            tasks.append(db_query_worker(worker_id, query_type, results))
    
    print("Starting database performance test...")
    start_time = time.time()
    await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Analyze by query type
    for query_type in ["search", "lots", "analytics"]:
        type_results = [r for r in results if r['query_type'] == query_type]
        if type_results:
            avg_time = statistics.mean([r['response_time'] for r in type_results])
            success_rate = (sum(1 for r in type_results if r['success']) / len(type_results)) * 100
            
            print(f"\n{query_type.upper()} queries:")
            print(f"  Average response time: {avg_time:.3f}s")
            print(f"  Success rate: {success_rate:.1f}%")
            print(f"  Total queries: {len(type_results)}")


if __name__ == "__main__":
    import asyncio
    
    print("Running performance tests...")
    
    # Run tests
    asyncio.run(test_parking_search_performance(concurrent_users=20, duration_seconds=30))
    print("\n" + "="*50 + "\n")
    
    asyncio.run(test_reservation_flow_performance())
    print("\n" + "="*50 + "\n")
    
    asyncio.run(test_database_performance())
