#!/bin/bash

# Start script for Smart Parking Management System Frontend

echo "Starting Smart Parking Management System Frontend..."

# Navigate to frontend directory
cd frontend

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "Dependencies not found. Installing..."
    npm install
fi

# Start development server
echo "Starting development server on http://localhost:3000..."
npm run dev