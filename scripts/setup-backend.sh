#!/bin/bash

# Setup script for Smart Parking Management System Backend

echo "Setting up Smart Parking Management System Backend..."

# Navigate to backend directory
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please update .env file with your configuration"
fi

echo "Backend setup completed!"
echo ""
echo "Next steps:"
echo "1. Update .env file with your configuration"
echo "2. Start services with: docker-compose -f docker/docker-compose.yml up -d"
echo "3. Run migrations (when ready)"
echo "4. Start backend with: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"