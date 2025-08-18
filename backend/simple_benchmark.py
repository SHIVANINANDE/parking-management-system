#!/usr/bin/env python3
"""
Simple benchmark without PostGIS dependencies
Tests basic SQL performance
"""

import asyncio
import time
import statistics
import asyncpg
from typing import List, Dict, Any

class SimpleDatabaseBenchmark:
    def __init__(self):
        self.conn = None
        
    async def setup(self):
        """Setup database connection"""
        try:
            self.conn = await asyncpg.connect(
                host='localhost',
                port=5432, 
                user='postgres',
                password='password',
                database='postgres'  # Use default database
            )
            print("✅ Database connected")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("Starting Docker PostgreSQL...")
            return await self.setup_docker_postgres()
    
    async def setup_docker_postgres(self):
        """Setup PostgreSQL using Docker"""
        import subprocess
        
        try:
            # Check if PostgreSQL container is running
            result = subprocess.run(['docker', 'ps', '-q', '-f', 'name=postgres'], 
                                  capture_output=True, text=True)
            
            if not result.stdout.strip():
                print("🐳 Starting PostgreSQL in Docker...")
                subprocess.run([
                    'docker', 'run', '--name', 'postgres', '-d',
                    '-e', 'POSTGRES_PASSWORD=password',
                    '-p', '5432:5432',
                    'postgres:14'
                ], check=True)
                
                # Wait for PostgreSQL to start
                await asyncio.sleep(10)
            
            # Try connecting again
            self.conn = await asyncpg.connect(
                host='localhost',
                port=5432,
                user='postgres', 
                password='password',
                database='postgres'
            )
            print("✅ PostgreSQL Docker container connected")
            return True
            
        except Exception as e:
            print(f"❌ Docker setup failed: {e}")
            return False
    
    async def create_test_tables(self):
        """Create simple test tables"""
        print("🔄 Creating test tables...")
        
        # Create test tables
        await self.conn.execute("""
            DROP TABLE IF EXISTS test_reservations CASCADE;
            DROP TABLE IF EXISTS test_parking_spots CASCADE;
            DROP TABLE IF EXISTS test_parking_lots CASCADE;
            DROP TABLE IF EXISTS test_users CASCADE;
        """)
        
        await self.conn.execute("""
            CREATE TABLE test_users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                full_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await self.conn.execute("""
            CREATE TABLE test_parking_lots (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                latitude DECIMAL(10, 8),
                longitude DECIMAL(11, 8),
                total_spots INTEGER NOT NULL,
                available_spots INTEGER NOT NULL,
                hourly_rate DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await self.conn.execute("""
            CREATE TABLE test_parking_spots (
                id SERIAL PRIMARY KEY,
                parking_lot_id INTEGER REFERENCES test_parking_lots(id),
                spot_number VARCHAR(20),
                is_available BOOLEAN DEFAULT TRUE
            )
        """)
        
        await self.conn.execute("""
            CREATE TABLE test_reservations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES test_users(id),
                parking_lot_id INTEGER REFERENCES test_parking_lots(id),
                spot_id INTEGER REFERENCES test_parking_spots(id),
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                total_cost DECIMAL(10,2),
                status VARCHAR(20),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Create indexes
        await self.conn.execute("CREATE INDEX idx_users_email ON test_users(email)")
        await self.conn.execute("CREATE INDEX idx_lots_location ON test_parking_lots(latitude, longitude)")
        await self.conn.execute("CREATE INDEX idx_spots_lot ON test_parking_spots(parking_lot_id)")
        await self.conn.execute("CREATE INDEX idx_reservations_user ON test_reservations(user_id)")
        await self.conn.execute("CREATE INDEX idx_reservations_status ON test_reservations(status)")
        
        print("✅ Test tables created")
    
    async def populate_test_data(self):
        """Populate with test data"""
        print("🔄 Populating test data...")
        
        # Insert users
        await self.conn.execute("""
            INSERT INTO test_users (email, full_name)
            SELECT 
                'user' || generate_series || '@test.com',
                'Test User ' || generate_series
            FROM generate_series(1, 5000)
        """)
        
        # Insert parking lots (San Francisco area coordinates)
        await self.conn.execute("""
            INSERT INTO test_parking_lots (name, latitude, longitude, total_spots, available_spots, hourly_rate)
            SELECT 
                'Parking Lot ' || generate_series,
                37.7749 + (random() - 0.5) * 0.1,
                -122.4194 + (random() - 0.5) * 0.1,
                50 + (generate_series % 200),
                25 + (generate_series % 100), 
                10.0 + (generate_series % 25)
            FROM generate_series(1, 500)
        """)
        
        # Insert parking spots
        await self.conn.execute("""
            INSERT INTO test_parking_spots (parking_lot_id, spot_number, is_available)
            SELECT 
                pl.id,
                'SPOT-' || row_number() OVER (PARTITION BY pl.id),
                random() > 0.3
            FROM test_parking_lots pl
            CROSS JOIN generate_series(1, 20)
        """)
        
        # Insert reservations  
        await self.conn.execute("""
            INSERT INTO test_reservations (user_id, parking_lot_id, spot_id, start_time, end_time, total_cost, status)
            SELECT 
                (1 + random() * 4999)::int,
                ps.parking_lot_id,
                ps.id,
                NOW() + (generate_series || ' hours')::interval,
                NOW() + (generate_series + 2 || ' hours')::interval,
                15.0 + (generate_series % 50),
                CASE (generate_series % 4)
                    WHEN 0 THEN 'pending'
                    WHEN 1 THEN 'confirmed' 
                    WHEN 2 THEN 'active'
                    ELSE 'completed'
                END
            FROM test_parking_spots ps
            CROSS JOIN generate_series(1, 2)
            WHERE generate_series <= 10000
        """)
        
        print("✅ Test data populated")
    
    async def benchmark_query(self, name: str, query: str, iterations: int = 100):
        """Benchmark a query"""
        print(f"🔄 Testing: {name}")
        
        latencies = []
        
        for i in range(iterations):
            start_time = time.perf_counter()
            try:
                await self.conn.fetch(query)
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000
                latencies.append(latency_ms)
            except Exception as e:
                print(f"  ❌ Query failed: {e}")
                return None
        
        # Calculate stats
        return {
            'name': name,
            'min_ms': min(latencies),
            'max_ms': max(latencies), 
            'mean_ms': statistics.mean(latencies),
            'median_ms': statistics.median(latencies),
            'p95_ms': self.percentile(latencies, 95),
            'p99_ms': self.percentile(latencies, 99),
            'throughput_qps': len(latencies) / (sum(latencies) / 1000)
        }
    
    def percentile(self, data: List[float], p: float) -> float:
        """Calculate percentile"""
        data_sorted = sorted(data)
        k = (len(data_sorted) - 1) * (p / 100)
        f = int(k)
        c = k - f
        if f == len(data_sorted) - 1:
            return data_sorted[f]
        return data_sorted[f] * (1 - c) + data_sorted[f + 1] * c
    
    async def run_benchmarks(self):
        """Run all benchmarks"""
        print("🚀 Running database benchmarks...\n")
        
        queries = {
            "Simple SELECT": "SELECT id, email FROM test_users LIMIT 10",
            
            "User Lookup by Email": "SELECT * FROM test_users WHERE email = 'user2500@test.com'",
            
            "Parking Lot Search": """
                SELECT id, name, available_spots, hourly_rate 
                FROM test_parking_lots 
                WHERE available_spots > 20 
                ORDER BY hourly_rate 
                LIMIT 20
            """,
            
            "Location-based Search": """
                SELECT id, name, latitude, longitude,
                       SQRT(POW(latitude - 37.7749, 2) + POW(longitude + 122.4194, 2)) as distance
                FROM test_parking_lots
                WHERE SQRT(POW(latitude - 37.7749, 2) + POW(longitude + 122.4194, 2)) < 0.05
                ORDER BY distance
                LIMIT 20
            """,
            
            "Available Spots": """
                SELECT ps.id, ps.spot_number 
                FROM test_parking_spots ps
                WHERE ps.parking_lot_id = 1 
                AND ps.is_available = true
                LIMIT 10
            """,
            
            "User Reservations with JOIN": """
                SELECT r.id, r.start_time, r.total_cost, pl.name
                FROM test_reservations r
                JOIN test_parking_lots pl ON r.parking_lot_id = pl.id
                WHERE r.user_id = 100
                ORDER BY r.start_time DESC
                LIMIT 10
            """,
            
            "Complex Analytics": """
                SELECT 
                    pl.name,
                    COUNT(r.id) as reservations,
                    AVG(r.total_cost) as avg_cost,
                    SUM(CASE WHEN r.status = 'completed' THEN r.total_cost ELSE 0 END) as revenue
                FROM test_parking_lots pl
                LEFT JOIN test_reservations r ON pl.id = r.parking_lot_id
                GROUP BY pl.id, pl.name
                HAVING COUNT(r.id) > 5
                ORDER BY revenue DESC
                LIMIT 10
            """,
            
            "Reservation Conflicts": """
                SELECT COUNT(*) 
                FROM test_reservations 
                WHERE spot_id = 100
                AND status IN ('confirmed', 'active')
                AND start_time <= NOW() + interval '2 hours'
                AND end_time >= NOW()
            """
        }
        
        results = []
        for name, query in queries.items():
            result = await self.benchmark_query(name, query, iterations=50)
            if result:
                results.append(result)
                self.print_result(result)
                print()
        
        self.print_summary(results)
        return results
    
    def print_result(self, result):
        """Print single result"""
        print(f"📊 {result['name']}:")
        print(f"   Mean: {result['mean_ms']:.2f}ms")
        print(f"   Median: {result['median_ms']:.2f}ms") 
        print(f"   P95: {result['p95_ms']:.2f}ms")
        print(f"   P99: {result['p99_ms']:.2f}ms")
        print(f"   Throughput: {result['throughput_qps']:.0f} queries/sec")
    
    def print_summary(self, results):
        """Print benchmark summary"""
        print("=" * 60)
        print("📋 ACTUAL DATABASE PERFORMANCE RESULTS")
        print("=" * 60)
        
        if not results:
            print("❌ No successful benchmarks")
            return
        
        # Calculate overall stats
        all_medians = [r['median_ms'] for r in results]
        all_throughputs = [r['throughput_qps'] for r in results]
        
        print(f"Queries Tested: {len(results)}")
        print(f"Overall Median Latency: {statistics.median(all_medians):.2f}ms")
        print(f"Average Throughput: {statistics.mean(all_throughputs):.0f} queries/sec")
        print()
        
        # Best performing queries
        print("🏆 FASTEST QUERIES:")
        sorted_results = sorted(results, key=lambda x: x['median_ms'])
        for i, result in enumerate(sorted_results[:3]):
            print(f"  {i+1}. {result['name']}: {result['median_ms']:.2f}ms ({result['throughput_qps']:.0f} qps)")
        
        print()
        print("📊 FOR YOUR RESUME:")
        median_latency = statistics.median(all_medians)
        avg_throughput = statistics.mean(all_throughputs)
        print(f"• Database Performance: {avg_throughput:.0f}+ queries/sec with {median_latency:.1f}ms median latency")
        print(f"• Complex Queries: {sorted_results[-1]['throughput_qps']:.0f}+ qps for analytics workloads")
        print(f"• Simple Lookups: {sorted_results[0]['throughput_qps']:.0f}+ qps for basic operations")
    
    async def cleanup(self):
        """Cleanup"""
        if self.conn:
            await self.conn.close()

async def main():
    benchmark = SimpleDatabaseBenchmark()
    
    try:
        if not await benchmark.setup():
            return
        
        await benchmark.create_test_tables()
        await benchmark.populate_test_data()
        await benchmark.run_benchmarks()
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
    finally:
        await benchmark.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
