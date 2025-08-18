-- Development database initialization script
-- This script is executed after the main database setup

-- Create development-specific functions and test data

-- Enable additional logging for development
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 0;
SELECT pg_reload_conf();

-- Create development user with extended permissions
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'dev_user') THEN
        CREATE ROLE dev_user WITH LOGIN PASSWORD 'dev_password';
        GRANT CONNECT ON DATABASE parking_db TO dev_user;
        GRANT USAGE ON SCHEMA public TO dev_user;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO dev_user;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO dev_user;
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO dev_user;
    END IF;
END
$$;

-- Create test parking lots for development
INSERT INTO parking_lots (name, address, total_spots, hourly_rate, location, amenities, created_at) 
VALUES 
    (
        'Dev Test Lot 1',
        '123 Test Street, Dev City, DC 12345',
        50,
        5.00,
        ST_GeomFromText('POINT(-77.0369 38.9072)', 4326), -- Washington DC
        '["security", "ev_charging", "covered"]'::jsonb,
        NOW()
    ),
    (
        'Dev Test Lot 2', 
        '456 Development Ave, Test Town, TT 67890',
        100,
        8.00,
        ST_GeomFromText('POINT(-74.0060 40.7128)', 4326), -- New York
        '["security", "wheelchair_accessible", "valet"]'::jsonb,
        NOW()
    )
ON CONFLICT (name) DO NOTHING;

-- Create test parking spots
WITH lot_ids AS (
    SELECT id, name FROM parking_lots WHERE name LIKE 'Dev Test Lot%'
)
INSERT INTO parking_spots (lot_id, spot_number, spot_type, is_available, location, created_at)
SELECT 
    l.id,
    'A' || generate_series(1, 25),
    CASE 
        WHEN generate_series(1, 25) % 5 = 0 THEN 'handicap'::spot_type
        WHEN generate_series(1, 25) % 3 = 0 THEN 'electric'::spot_type
        ELSE 'regular'::spot_type
    END,
    true,
    ST_GeomFromText('POINT(' || 
        (-77.0369 + (random() - 0.5) * 0.01) || ' ' || 
        (38.9072 + (random() - 0.5) * 0.01) || ')', 4326),
    NOW()
FROM lot_ids l
WHERE l.name = 'Dev Test Lot 1'
ON CONFLICT (lot_id, spot_number) DO NOTHING;

-- Add spots for second lot
WITH lot_ids AS (
    SELECT id, name FROM parking_lots WHERE name LIKE 'Dev Test Lot%'
)
INSERT INTO parking_spots (lot_id, spot_number, spot_type, is_available, location, created_at)
SELECT 
    l.id,
    'B' || generate_series(1, 50),
    CASE 
        WHEN generate_series(1, 50) % 7 = 0 THEN 'handicap'::spot_type
        WHEN generate_series(1, 50) % 4 = 0 THEN 'electric'::spot_type
        ELSE 'regular'::spot_type
    END,
    true,
    ST_GeomFromText('POINT(' || 
        (-74.0060 + (random() - 0.5) * 0.01) || ' ' || 
        (40.7128 + (random() - 0.5) * 0.01) || ')', 4326),
    NOW()
FROM lot_ids l
WHERE l.name = 'Dev Test Lot 2'
ON CONFLICT (lot_id, spot_number) DO NOTHING;

-- Create development test user
INSERT INTO users (
    email, 
    username, 
    hashed_password, 
    full_name, 
    phone_number, 
    is_active, 
    is_verified,
    created_at
) VALUES (
    'dev@test.com',
    'devuser',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- password: secret
    'Development User',
    '+1234567890',
    true,
    true,
    NOW()
) ON CONFLICT (email) DO NOTHING;

-- Create test vehicle for dev user
WITH dev_user AS (
    SELECT id FROM users WHERE email = 'dev@test.com'
)
INSERT INTO vehicles (
    user_id,
    license_plate,
    make,
    model,
    year,
    color,
    vehicle_type,
    created_at
)
SELECT 
    u.id,
    'DEV-123',
    'Tesla',
    'Model 3',
    2023,
    'white',
    'electric'::vehicle_type,
    NOW()
FROM dev_user u
ON CONFLICT (license_plate) DO NOTHING;

-- Create development indexes for performance testing
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dev_reservations_created_at 
ON reservations (created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dev_parking_spots_location 
ON parking_spots USING GIST (location);

-- Development-specific views for testing
CREATE OR REPLACE VIEW dev_parking_overview AS
SELECT 
    pl.name as lot_name,
    pl.address,
    COUNT(ps.id) as total_spots,
    COUNT(ps.id) FILTER (WHERE ps.is_available = true) as available_spots,
    COUNT(r.id) as active_reservations,
    pl.hourly_rate,
    pl.amenities
FROM parking_lots pl
LEFT JOIN parking_spots ps ON pl.id = ps.lot_id
LEFT JOIN reservations r ON ps.id = r.spot_id 
    AND r.status = 'active' 
    AND r.start_time <= NOW() 
    AND r.end_time >= NOW()
WHERE pl.name LIKE 'Dev Test Lot%'
GROUP BY pl.id, pl.name, pl.address, pl.hourly_rate, pl.amenities;

-- Grant permissions on development views
GRANT SELECT ON dev_parking_overview TO dev_user;

-- Development logging function
CREATE OR REPLACE FUNCTION log_dev_action(action_type TEXT, details JSONB DEFAULT '{}')
RETURNS VOID AS $$
BEGIN
    INSERT INTO system_logs (level, message, details, created_at)
    VALUES ('INFO', 'DEV_ACTION: ' || action_type, details, NOW());
    
    RAISE NOTICE 'Development action logged: %', action_type;
END;
$$ LANGUAGE plpgsql;

-- Create some sample reservations for testing
WITH dev_user AS (SELECT id FROM users WHERE email = 'dev@test.com'),
     dev_vehicle AS (SELECT id FROM vehicles WHERE license_plate = 'DEV-123'),
     test_spot AS (
         SELECT ps.id 
         FROM parking_spots ps 
         JOIN parking_lots pl ON ps.lot_id = pl.id 
         WHERE pl.name = 'Dev Test Lot 1' 
         AND ps.spot_number = 'A1'
     )
INSERT INTO reservations (
    user_id,
    spot_id, 
    vehicle_id,
    start_time,
    end_time,
    total_amount,
    status,
    created_at
)
SELECT 
    u.id,
    s.id,
    v.id,
    NOW() + INTERVAL '1 hour',
    NOW() + INTERVAL '3 hours',
    10.00,
    'confirmed'::reservation_status,
    NOW()
FROM dev_user u, dev_vehicle v, test_spot s
ON CONFLICT DO NOTHING;

COMMIT;
