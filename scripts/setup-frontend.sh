#!/bin/bash

# Setup script for Smart Parking Management System Frontend

echo "Setting up Smart Parking Management System Frontend..."

# Navigate to frontend directory
cd frontend

# Install dependencies
echo "Installing Node.js dependencies..."
npm install

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please update .env file with your configuration"
fi

# Run type check
echo "Running TypeScript type check..."
npm run type-check

# Run linting
echo "Running ESLint..."
npm run lint

echo "Frontend setup completed!"
echo ""
echo "Next steps:"
echo "1. Update .env file with your configuration"
echo "2. Start development server with: cd frontend && npm run dev"
echo "3. Open http://localhost:3000 in your browser"