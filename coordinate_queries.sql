-- PostgreSQL queries to view and analyze coordinate data in your locus_assistant database

-- 1. Check table structure for location fields
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'orders'
AND column_name LIKE '%location%'
ORDER BY ordinal_position;

-- 2. Count orders with coordinate data
SELECT
    COUNT(*) as total_orders,
    COUNT(location_latitude) as orders_with_lat,
    COUNT(location_longitude) as orders_with_lng,
    COUNT(CASE WHEN location_latitude IS NOT NULL AND location_longitude IS NOT NULL THEN 1 END) as orders_with_both_coords
FROM orders;

-- 3. View sample orders with coordinates
SELECT
    id,
    location_name,
    location_city,
    location_country_code,
    location_latitude,
    location_longitude,
    date
FROM orders
WHERE location_latitude IS NOT NULL
AND location_longitude IS NOT NULL
ORDER BY date DESC
LIMIT 10;

-- 4. Coordinate data quality check
SELECT
    COUNT(*) as total_coords,
    COUNT(CASE WHEN location_latitude BETWEEN -90 AND 90
               AND location_longitude BETWEEN -180 AND 180
               THEN 1 END) as valid_coords,
    ROUND(MIN(location_latitude)::numeric, 4) as min_lat,
    ROUND(MAX(location_latitude)::numeric, 4) as max_lat,
    ROUND(MIN(location_longitude)::numeric, 4) as min_lng,
    ROUND(MAX(location_longitude)::numeric, 4) as max_lng
FROM orders
WHERE location_latitude IS NOT NULL
AND location_longitude IS NOT NULL;

-- 5. Orders by date with coordinate counts
SELECT
    date,
    COUNT(*) as total_orders,
    COUNT(CASE WHEN location_latitude IS NOT NULL AND location_longitude IS NOT NULL THEN 1 END) as with_coords,
    ROUND(
        COUNT(CASE WHEN location_latitude IS NOT NULL AND location_longitude IS NOT NULL THEN 1 END) * 100.0 / COUNT(*),
        2
    ) as coords_percentage
FROM orders
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY date
ORDER BY date DESC;

-- 6. Location distribution by city with coordinates
SELECT
    location_city,
    location_country_code,
    COUNT(*) as order_count,
    COUNT(CASE WHEN location_latitude IS NOT NULL AND location_longitude IS NOT NULL THEN 1 END) as with_coords,
    ROUND(AVG(location_latitude)::numeric, 6) as avg_lat,
    ROUND(AVG(location_longitude)::numeric, 6) as avg_lng
FROM orders
WHERE location_city IS NOT NULL
GROUP BY location_city, location_country_code
HAVING COUNT(CASE WHEN location_latitude IS NOT NULL AND location_longitude IS NOT NULL THEN 1 END) > 0
ORDER BY order_count DESC
LIMIT 10;

-- 7. Create a map visualization query (coordinates with location names)
SELECT
    id as order_id,
    location_name,
    location_address,
    location_city,
    location_latitude as lat,
    location_longitude as lng,
    order_status,
    date,
    CONCAT(
        'Order: ', COALESCE(location_name, 'N/A'), ' | ',
        'City: ', COALESCE(location_city, 'N/A'), ' | ',
        'Status: ', order_status, ' | ',
        'Date: ', date
    ) as marker_info
FROM orders
WHERE location_latitude IS NOT NULL
AND location_longitude IS NOT NULL
AND location_latitude BETWEEN -90 AND 90
AND location_longitude BETWEEN -180 AND 180
ORDER BY date DESC, id
LIMIT 50;

-- 8. Distance calculation example (distance from Cairo center)
-- Cairo approximate center: 30.0444, 31.2357
SELECT
    id,
    location_name,
    location_city,
    location_latitude,
    location_longitude,
    ROUND(
        6371 * acos(
            cos(radians(30.0444)) * cos(radians(location_latitude)) *
            cos(radians(location_longitude) - radians(31.2357)) +
            sin(radians(30.0444)) * sin(radians(location_latitude))
        )::numeric,
        2
    ) as distance_from_cairo_km
FROM orders
WHERE location_latitude IS NOT NULL
AND location_longitude IS NOT NULL
ORDER BY distance_from_cairo_km
LIMIT 10;