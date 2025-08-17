-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create database schema
CREATE SCHEMA IF NOT EXISTS parking;

-- Set search path
SET search_path TO parking, public;