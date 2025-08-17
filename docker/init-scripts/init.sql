-- Enable PostGIS extension and related modules
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgis_sfcgal;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Enable additional extensions for performance monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create database schema
CREATE SCHEMA IF NOT EXISTS parking;

-- Set search path
SET search_path TO parking, public;

-- Create spatial reference systems if not exists
DO $$
BEGIN
    -- Ensure WGS84 (SRID 4326) exists
    IF NOT EXISTS (SELECT 1 FROM spatial_ref_sys WHERE srid = 4326) THEN
        INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, proj4text, srtext) 
        VALUES (4326, 'EPSG', 4326, 
            '+proj=longlat +datum=WGS84 +no_defs', 
            'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]');
    END IF;
    
    -- Ensure Web Mercator (SRID 3857) exists for mapping
    IF NOT EXISTS (SELECT 1 FROM spatial_ref_sys WHERE srid = 3857) THEN
        INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, proj4text, srtext)
        VALUES (3857, 'EPSG', 3857,
            '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs',
            'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]');
    END IF;
END
$$;