-- IoT Device Monitor - Geolocation Schema
-- IP geolocation cache and network flow aggregation for geographic analysis
-- Consolidates geolocation features from multiple sources

-- IP geolocation cache table for performance optimization
CREATE TABLE IF NOT EXISTS ip_geolocation_cache (
    id SERIAL PRIMARY KEY,
    ip_address INET UNIQUE NOT NULL,
    country_code VARCHAR(2),
    country_name VARCHAR(100),
    region VARCHAR(100),
    city VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    isp VARCHAR(255),
    organization VARCHAR(255),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_coordinates CHECK (
        latitude IS NULL OR (latitude >= -90 AND latitude <= 90)
    ),
    CONSTRAINT valid_longitude CHECK (
        longitude IS NULL OR (longitude >= -180 AND longitude <= 180)
    )
);

-- Network flow aggregates table for Sankey diagram performance optimization
CREATE TABLE IF NOT EXISTS network_flow_aggregates (
    id SERIAL PRIMARY KEY,
    experiment_id VARCHAR(100) NOT NULL,
    time_window VARCHAR(10) NOT NULL,
    flow_type VARCHAR(50) NOT NULL, -- device-to-location, device-to-device, protocol-to-service
    source_category VARCHAR(100) NOT NULL,
    target_category VARCHAR(100) NOT NULL,
    total_bytes BIGINT DEFAULT 0,
    total_packets BIGINT DEFAULT 0,
    device_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_time_window CHECK (time_window IN ('1h', '6h', '12h', '24h', '48h')),
    CONSTRAINT valid_flow_type CHECK (flow_type IN ('device-to-location', 'device-to-device', 'protocol-to-service', 'location-to-location')),
    CONSTRAINT positive_metrics CHECK (total_bytes >= 0 AND total_packets >= 0 AND device_count >= 0),
    CONSTRAINT unique_flow_aggregate UNIQUE(experiment_id, time_window, flow_type, source_category, target_category)
);

-- Create indexes for geolocation performance
CREATE INDEX IF NOT EXISTS idx_ip_geolocation_ip ON ip_geolocation_cache(ip_address);
CREATE INDEX IF NOT EXISTS idx_ip_geolocation_country ON ip_geolocation_cache(country_code);
CREATE INDEX IF NOT EXISTS idx_ip_geolocation_updated ON ip_geolocation_cache(last_updated);
CREATE INDEX IF NOT EXISTS idx_ip_geolocation_coordinates ON ip_geolocation_cache(latitude, longitude) 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Create indexes for flow aggregates
CREATE INDEX IF NOT EXISTS idx_flow_aggregates_experiment ON network_flow_aggregates(experiment_id);
CREATE INDEX IF NOT EXISTS idx_flow_aggregates_type ON network_flow_aggregates(flow_type);
CREATE INDEX IF NOT EXISTS idx_flow_aggregates_time ON network_flow_aggregates(time_window);
CREATE INDEX IF NOT EXISTS idx_flow_aggregates_source ON network_flow_aggregates(source_category);
CREATE INDEX IF NOT EXISTS idx_flow_aggregates_target ON network_flow_aggregates(target_category);
CREATE INDEX IF NOT EXISTS idx_flow_aggregates_created ON network_flow_aggregates(created_at DESC);

-- Function to clean up expired geolocation cache
CREATE OR REPLACE FUNCTION cleanup_expired_geolocation_cache(retention_days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM ip_geolocation_cache 
    WHERE last_updated < NOW() - INTERVAL '1 day' * retention_days;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update geolocation cache entry
CREATE OR REPLACE FUNCTION upsert_ip_geolocation(
    p_ip_address INET,
    p_country_code VARCHAR(2),
    p_country_name VARCHAR(100),
    p_region VARCHAR(100) DEFAULT NULL,
    p_city VARCHAR(100) DEFAULT NULL,
    p_latitude DECIMAL(10, 8) DEFAULT NULL,
    p_longitude DECIMAL(11, 8) DEFAULT NULL,
    p_isp VARCHAR(255) DEFAULT NULL,
    p_organization VARCHAR(255) DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO ip_geolocation_cache (
        ip_address, country_code, country_name, region, city,
        latitude, longitude, isp, organization, last_updated
    ) VALUES (
        p_ip_address, p_country_code, p_country_name, p_region, p_city,
        p_latitude, p_longitude, p_isp, p_organization, NOW()
    )
    ON CONFLICT (ip_address) 
    DO UPDATE SET
        country_code = EXCLUDED.country_code,
        country_name = EXCLUDED.country_name,
        region = EXCLUDED.region,
        city = EXCLUDED.city,
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        isp = EXCLUDED.isp,
        organization = EXCLUDED.organization,
        last_updated = NOW();
END;
$$ LANGUAGE plpgsql;

-- Function to aggregate network flows for geographic analysis
CREATE OR REPLACE FUNCTION aggregate_network_flows_by_location(
    p_experiment_id VARCHAR(100),
    p_time_window VARCHAR(10) DEFAULT '1h'
)
RETURNS INTEGER AS $$
DECLARE
    affected_rows INTEGER := 0;
BEGIN
    -- Clear existing aggregates for this experiment and time window
    DELETE FROM network_flow_aggregates 
    WHERE experiment_id = p_experiment_id 
      AND time_window = p_time_window
      AND flow_type = 'device-to-location';
    
    -- Aggregate device-to-location flows
    INSERT INTO network_flow_aggregates (
        experiment_id, time_window, flow_type, source_category, target_category,
        total_bytes, total_packets, device_count
    )
    SELECT 
        pf.experiment_id,
        p_time_window,
        'device-to-location',
        d.device_type || ' (' || d.manufacturer || ')' as source_category,
        COALESCE(gc.country_name, 'Unknown Location') as target_category,
        SUM(pf.packet_size) as total_bytes,
        COUNT(*) as total_packets,
        COUNT(DISTINCT pf.device_id) as device_count
    FROM packet_flows pf
    JOIN devices d ON pf.device_id = d.device_id
    LEFT JOIN ip_geolocation_cache gc ON pf.dst_ip = gc.ip_address
    WHERE pf.experiment_id = p_experiment_id
      AND pf.dst_ip IS NOT NULL 
      AND pf.dst_ip != '0.0.0.0'
      AND NOT (pf.dst_ip::text LIKE '192.168.%' OR pf.dst_ip::text LIKE '10.%' OR pf.dst_ip::text LIKE '172.%')
    GROUP BY pf.experiment_id, d.device_type, d.manufacturer, gc.country_name;
    
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    
    RETURN affected_rows;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE ip_geolocation_cache IS 'IP address geolocation information cache for performance optimization';
COMMENT ON TABLE network_flow_aggregates IS 'Pre-aggregated network flow data for geographic visualization';
COMMENT ON FUNCTION cleanup_expired_geolocation_cache(INTEGER) IS 'Remove expired geolocation cache entries';
COMMENT ON FUNCTION upsert_ip_geolocation(INET, VARCHAR, VARCHAR, VARCHAR, VARCHAR, DECIMAL, DECIMAL, VARCHAR, VARCHAR) IS 'Insert or update IP geolocation data';
COMMENT ON FUNCTION aggregate_network_flows_by_location(VARCHAR, VARCHAR) IS 'Aggregate network flows by geographic location for visualization'; 