#!/usr/bin/env python3
"""
Simple database setup for benchmarking
Creates basic tables if they don't exist
"""

import asyncio
import asyncpg
import os

async def setup_test_database():
    """Setup test database with basic schema"""
    
    # Database connection parameters
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'password',
        'database': 'postgres'  # Connect to default database first
    }
    
    try:
        # Connect to PostgreSQL
        conn = await asyncpg.connect(**db_config)
        
        # Create test database if it doesn't exist
        try:
            await conn.execute("CREATE DATABASE parking_test")
            print("✅ Created parking_test database")
        except asyncpg.DuplicateDatabaseError:
            print("ℹ️  parking_test database already exists")
        except Exception as e:
            print(f"Database creation: {e}")
        
        await conn.close()
        
        # Connect to test database
        db_config['database'] = 'parking_test'
        conn = await asyncpg.connect(**db_config)
        
        # Enable PostGIS extension
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            print("✅ PostGIS extension enabled")
        except Exception as e:
            print(f"PostGIS setup: {e}")
        
        # Create basic tables
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                phone_number VARCHAR(20),
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS parking_lots (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                description TEXT,
                location GEOMETRY(POINT, 4326),
                address TEXT NOT NULL,
                total_spots INTEGER NOT NULL,
                available_spots INTEGER NOT NULL,
                hourly_rate DECIMAL(10,2) NOT NULL,
                daily_rate DECIMAL(10,2),
                amenities JSONB,
                operating_hours JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS parking_spots (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                parking_lot_id UUID REFERENCES parking_lots(id),
                spot_number VARCHAR(20) NOT NULL,
                spot_type VARCHAR(20) NOT NULL,
                is_available BOOLEAN DEFAULT TRUE,
                width DECIMAL(5,2),
                length DECIMAL(5,2),
                location_coordinates JSONB
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id),
                parking_lot_id UUID REFERENCES parking_lots(id),
                spot_id UUID REFERENCES parking_spots(id),
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                total_cost DECIMAL(10,2) NOT NULL,
                status VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_parking_lots_location ON parking_lots USING GIST (location)",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)",
            "CREATE INDEX IF NOT EXISTS idx_reservations_user_id ON reservations (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_reservations_spot_id ON reservations (spot_id)",
            "CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations (status)",
            "CREATE INDEX IF NOT EXISTS idx_parking_spots_lot_id ON parking_spots (parking_lot_id)",
            "CREATE INDEX IF NOT EXISTS idx_parking_spots_available ON parking_spots (is_available)"
        ]
        
        for index_sql in indexes:
            try:
                await conn.execute(index_sql)
            except Exception as e:
                print(f"Index creation: {e}")
        
        await conn.close()
        print("✅ Database schema setup complete")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        print("Please ensure PostgreSQL is running on localhost:5432")
        print("Default credentials: postgres/password")
        return False

if __name__ == "__main__":
    asyncio.run(setup_test_database())
