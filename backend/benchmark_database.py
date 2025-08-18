#!/usr/bin/env python3
"""
Database Performance Benchmarking Script
Measures actual query performance with real data
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select, func
import asyncpg
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.models.parking_lot import ParkingLot
from app.models.parking_spot import ParkingSpot
from app.models.reservation import Reservation
from app.models.user import User
from app.core.config import settings

class DatabaseBenchmark:
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.results = {}
        
    async def setup(self):
        """Initialize database connection"""
        try:
            # Use environment variable or default
            database_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:password@localhost:5432/parking_test')
            
            self.engine = create_async_engine(
                database_url,
                pool_size=10,
                max_overflow=20,
                echo=False
            )
            
            self.session_factory = sessionmaker(
                self.engine, 
                class_=AsyncSession, 
                expire_on_commit=False
            )
            
            print("✅ Database connection established")
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print("Please ensure PostgreSQL is running and DATABASE_URL is correct")
            return False
        
        return True
    
    async def create_test_data(self):
        """Create test data for benchmarking"""
        print("🔄 Creating test data...")
        
        async with self.session_factory() as session:
            try:
                # Create test users
                users_query = text("""
                    INSERT INTO users (id, email, password_hash, full_name, phone_number, is_verified)
                    SELECT 
                        gen_random_uuid(),
                        'user' || generate_series || '@test.com',
                        '$2b$12$dummy_hash_for_testing',
                        'Test User ' || generate_series,
                        '+1555' || LPAD(generate_series::text, 7, '0'),
                        true
                    FROM generate_series(1, 1000)
                    ON CONFLICT (email) DO NOTHING;
                """)
                await session.execute(users_query)
                
                # Create test parking lots with spatial data
                lots_query = text("""
                    INSERT INTO parking_lots (id, name, description, location, address, total_spots, available_spots, hourly_rate, daily_rate, amenities, operating_hours)
                    SELECT 
                        gen_random_uuid(),
                        'Test Parking Lot ' || generate_series,
                        'Test parking facility ' || generate_series,
                        ST_Point(
                            -122.4194 + (random() - 0.5) * 0.1,  -- San Francisco area
                            37.7749 + (random() - 0.5) * 0.1
                        ),
                        generate_series || ' Test Street, San Francisco, CA',
                        100 + (generate_series % 400),
                        50 + (generate_series % 200),
                        10.0 + (generate_series % 20),
                        60.0 + (generate_series % 100),
                        '["covered", "security"]'::jsonb,
                        '{"monday": {"open": "06:00", "close": "22:00"}}'::jsonb
                    FROM generate_series(1, 100)
                    ON CONFLICT DO NOTHING;
                """)
                await session.execute(lots_query)
                
                # Create parking spots
                spots_query = text("""
                    INSERT INTO parking_spots (id, parking_lot_id, spot_number, spot_type, is_available, width, length)
                    SELECT 
                        gen_random_uuid(),
                        pl.id,
                        'SPOT-' || row_number() OVER (PARTITION BY pl.id),
                        CASE (random() * 4)::int 
                            WHEN 0 THEN 'standard'
                            WHEN 1 THEN 'compact'
                            WHEN 2 THEN 'accessible'
                            ELSE 'ev_charging'
                        END,
                        random() > 0.3,  -- 70% available
                        2.5 + random(),
                        5.0 + random()
                    FROM parking_lots pl
                    CROSS JOIN generate_series(1, 50)
                    ON CONFLICT DO NOTHING;
                """)
                await session.execute(spots_query)
                
                # Create test reservations
                reservations_query = text("""
                    INSERT INTO reservations (id, user_id, parking_lot_id, spot_id, start_time, end_time, total_cost, status)
                    SELECT 
                        gen_random_uuid(),
                        u.id,
                        ps.parking_lot_id,
                        ps.id,
                        NOW() + (generate_series || ' hours')::interval,
                        NOW() + (generate_series + 2 || ' hours')::interval,
                        25.0 + (generate_series % 50),
                        CASE (generate_series % 4)
                            WHEN 0 THEN 'pending'
                            WHEN 1 THEN 'confirmed'
                            WHEN 2 THEN 'active'
                            ELSE 'completed'
                        END
                    FROM users u
                    CROSS JOIN parking_spots ps
                    CROSS JOIN generate_series(1, 3)
                    WHERE generate_series <= 1000
                    ON CONFLICT DO NOTHING;
                """)
                await session.execute(reservations_query)
                
                await session.commit()
                print("✅ Test data created successfully")
                
            except Exception as e:
                print(f"❌ Error creating test data: {e}")
                await session.rollback()
    
    async def benchmark_query(self, name: str, query: str, iterations: int = 100) -> Dict[str, Any]:
        """Benchmark a specific query"""
        print(f"🔄 Benchmarking: {name}")
        
        latencies = []
        errors = 0
        
        async with self.session_factory() as session:
            for i in range(iterations):
                try:
                    start_time = time.perf_counter()
                    result = await session.execute(text(query))
                    await result.fetchall()  # Fetch all results
                    end_time = time.perf_counter()
                    
                    latency_ms = (end_time - start_time) * 1000
                    latencies.append(latency_ms)
                    
                except Exception as e:
                    errors += 1
                    if errors <= 3:  # Log first few errors
                        print(f"  ⚠️  Query error: {e}")
        
        if not latencies:
            return {
                "name": name,
                "error": "All queries failed",
                "errors": errors
            }
        
        # Calculate statistics
        stats = {
            "name": name,
            "iterations": len(latencies),
            "errors": errors,
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "mean_ms": statistics.mean(latencies),
            "median_ms": statistics.median(latencies),
            "p95_ms": self.percentile(latencies, 95),
            "p99_ms": self.percentile(latencies, 99),
            "throughput_qps": len(latencies) / (sum(latencies) / 1000) if latencies else 0
        }
        
        return stats
    
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
        """Run all database benchmarks"""
        print("🚀 Starting database benchmarks...\n")
        
        # Test queries based on your actual application
        queries = {
            "Simple User Lookup": """
                SELECT id, email, full_name FROM users WHERE email = 'user500@test.com'
            """,
            
            "Parking Lot Search (No Spatial)": """
                SELECT id, name, total_spots, available_spots, hourly_rate 
                FROM parking_lots 
                WHERE available_spots > 10 
                ORDER BY hourly_rate 
                LIMIT 20
            """,
            
            "Spatial Search (5km radius)": """
                SELECT pl.id, pl.name, pl.available_spots,
                       ST_Distance(pl.location, ST_Point(-122.4194, 37.7749)) as distance
                FROM parking_lots pl
                WHERE ST_DWithin(pl.location, ST_Point(-122.4194, 37.7749), 5000)
                ORDER BY distance
                LIMIT 20
            """,
            
            "Available Spots Check": """
                SELECT ps.id, ps.spot_number, ps.spot_type
                FROM parking_spots ps
                WHERE ps.parking_lot_id = (SELECT id FROM parking_lots LIMIT 1)
                AND ps.is_available = true
                AND ps.id NOT IN (
                    SELECT spot_id FROM reservations 
                    WHERE status IN ('confirmed', 'active')
                    AND start_time <= NOW() + interval '2 hours'
                    AND end_time >= NOW()
                )
                LIMIT 10
            """,
            
            "User Reservations": """
                SELECT r.id, r.start_time, r.end_time, r.total_cost, r.status,
                       pl.name as parking_lot_name, ps.spot_number
                FROM reservations r
                JOIN parking_lots pl ON r.parking_lot_id = pl.id
                JOIN parking_spots ps ON r.spot_id = ps.id
                WHERE r.user_id = (SELECT id FROM users LIMIT 1)
                ORDER BY r.start_time DESC
                LIMIT 10
            """,
            
            "Complex Analytics Query": """
                SELECT 
                    pl.name,
                    COUNT(r.id) as total_reservations,
                    AVG(r.total_cost) as avg_cost,
                    SUM(CASE WHEN r.status = 'completed' THEN r.total_cost ELSE 0 END) as revenue
                FROM parking_lots pl
                LEFT JOIN reservations r ON pl.id = r.parking_lot_id
                WHERE r.start_time >= NOW() - interval '30 days'
                GROUP BY pl.id, pl.name
                HAVING COUNT(r.id) > 0
                ORDER BY revenue DESC
                LIMIT 10
            """,
            
            "Reservation Conflict Check": """
                SELECT COUNT(*) as conflicts
                FROM reservations
                WHERE spot_id = (SELECT id FROM parking_spots LIMIT 1)
                AND status IN ('confirmed', 'active')
                AND start_time <= NOW() + interval '3 hours'
                AND end_time >= NOW() + interval '1 hour'
            """
        }
        
        # Run benchmarks
        results = []
        for name, query in queries.items():
            result = await self.benchmark_query(name, query, iterations=50)
            results.append(result)
            self.print_result(result)
            print()
        
        # Summary
        self.print_summary(results)
        return results
    
    def print_result(self, result: Dict[str, Any]):
        """Print benchmark result"""
        if "error" in result:
            print(f"❌ {result['name']}: {result['error']}")
            return
        
        print(f"📊 {result['name']}:")
        print(f"   Iterations: {result['iterations']}")
        print(f"   Errors: {result['errors']}")
        print(f"   Mean: {result['mean_ms']:.2f}ms")
        print(f"   Median: {result['median_ms']:.2f}ms")
        print(f"   P95: {result['p95_ms']:.2f}ms")
        print(f"   P99: {result['p99_ms']:.2f}ms")
        print(f"   Throughput: {result['throughput_qps']:.0f} queries/sec")
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print benchmark summary"""
        print("=" * 60)
        print("📋 BENCHMARK SUMMARY")
        print("=" * 60)
        
        valid_results = [r for r in results if "error" not in r]
        
        if not valid_results:
            print("❌ No successful benchmarks")
            return
        
        # Overall statistics
        all_medians = [r['median_ms'] for r in valid_results]
        all_throughputs = [r['throughput_qps'] for r in valid_results]
        
        print(f"Total Queries Tested: {len(results)}")
        print(f"Successful: {len(valid_results)}")
        print(f"Failed: {len(results) - len(valid_results)}")
        print()
        print(f"Overall Median Latency: {statistics.median(all_medians):.2f}ms")
        print(f"Average Throughput: {statistics.mean(all_throughputs):.0f} queries/sec")
        print()
        
        # Top performers
        print("🏆 Top Performing Queries:")
        sorted_by_speed = sorted(valid_results, key=lambda x: x['median_ms'])
        for i, result in enumerate(sorted_by_speed[:3]):
            print(f"  {i+1}. {result['name']}: {result['median_ms']:.2f}ms")
        
        print()
        print("🐌 Slowest Queries:")
        for i, result in enumerate(reversed(sorted_by_speed[-3:])):
            print(f"  {i+1}. {result['name']}: {result['median_ms']:.2f}ms")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.engine:
            await self.engine.dispose()

async def main():
    """Main benchmark function"""
    benchmark = DatabaseBenchmark()
    
    try:
        # Setup
        if not await benchmark.setup():
            return
        
        # Create test data
        await benchmark.create_test_data()
        
        # Run benchmarks
        results = await benchmark.run_benchmarks()
        
        print("\n🎯 Use these ACTUAL metrics in your resume/documentation!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Benchmark interrupted by user")
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
    finally:
        await benchmark.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
