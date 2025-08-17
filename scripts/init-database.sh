#!/bin/bash

# Database initialization script for Smart Parking Management System

echo "Initializing Smart Parking Management System Database..."

# Navigate to backend directory
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run setup-backend.sh first."
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install additional requirements if needed
echo "Installing/updating dependencies..."
pip install -r requirements.txt

# Check if PostgreSQL is running
echo "Checking PostgreSQL connection..."
python -c "
import asyncpg
import asyncio
from app.core.config import settings

async def check_connection():
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL.replace('+asyncpg', ''))
        await conn.close()
        print('✓ PostgreSQL connection successful')
        return True
    except Exception as e:
        print(f'✗ PostgreSQL connection failed: {e}')
        return False

result = asyncio.run(check_connection())
exit(0 if result else 1)
"

if [ $? -ne 0 ]; then
    echo "Please start PostgreSQL service first."
    echo "Run: docker-compose -f docker/docker-compose.yml up -d postgres"
    exit 1
fi

# Run database migrations
echo "Running Alembic migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✓ Database migrations completed successfully"
else
    echo "✗ Database migrations failed"
    exit 1
fi

echo ""
echo "Database initialization completed!"
echo ""
echo "Next steps:"
echo "1. Start all services: ./scripts/start-services.sh"
echo "2. Load sample data: python scripts/load_sample_data.py"
echo "3. Start backend API: cd backend && uvicorn app.main:app --reload"