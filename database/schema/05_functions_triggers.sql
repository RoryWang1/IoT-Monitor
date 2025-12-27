-- IoT Device Monitor - Functions and Triggers Schema
-- Database functions, triggers, and business logic
-- Centralized location for all stored procedures and automated functionality

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at columns
CREATE OR REPLACE TRIGGER update_experiments_updated_at 
    BEFORE UPDATE ON experiments 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_devices_updated_at 
    BEFORE UPDATE ON devices 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_protocol_analysis_updated_at 
    BEFORE UPDATE ON protocol_analysis 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_port_analysis_updated_at 
    BEFORE UPDATE ON port_analysis 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function for device name resolution using reference data
CREATE OR REPLACE FUNCTION resolve_device_info(input_mac_address VARCHAR(17))
RETURNS TABLE (
    resolved_name VARCHAR(255),
    resolved_vendor VARCHAR(255),
    resolved_type VARCHAR(100),
    source VARCHAR(20)
) AS $$
BEGIN
    -- First try to find exact match in known_devices
    RETURN QUERY
    SELECT 
        kd.device_name::VARCHAR(255),
        kd.vendor::VARCHAR(255),
        kd.device_type::VARCHAR(100),
        'known_device'::VARCHAR(20)
    FROM known_devices kd
    WHERE kd.mac_address = input_mac_address;
    
    -- If no exact match found, try vendor pattern matching
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT 
            'Unknown'::VARCHAR(255),
            vp.vendor_name::VARCHAR(255),
            vp.device_category::VARCHAR(100),
            'vendor_pattern'::VARCHAR(20)
        FROM vendor_patterns vp
        WHERE LEFT(input_mac_address, 8) = vp.oui_pattern;
    END IF;
    
    -- If still no match, return unknown
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT 
            'Unknown'::VARCHAR(255),
            'Unknown'::VARCHAR(255),
            'unknown'::VARCHAR(100),
            'none'::VARCHAR(20);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function for IP geolocation lookup using reference data
CREATE OR REPLACE FUNCTION lookup_ip_location(input_ip INET)
RETURNS TABLE (
    country_code CHAR(2),
    country_name VARCHAR(100),
    asn INTEGER,
    asn_name VARCHAR(255)
) AS $$
BEGIN
    -- First try cache lookup
    RETURN QUERY
    SELECT 
        gc.country_code::CHAR(2),
        gc.country_name::VARCHAR(100),
        NULL::INTEGER as asn,
        NULL::VARCHAR(255) as asn_name
    FROM ip_geolocation_cache gc
    WHERE gc.ip_address = input_ip;
    
    -- If not in cache, try reference data range lookup
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT 
            geo.country_code,
            geo.country_name,
            geo.asn,
            geo.asn_name
        FROM ip_geolocation_ref geo
        WHERE input_ip >= geo.start_ip AND input_ip <= geo.end_ip
        ORDER BY (geo.end_ip - geo.start_ip)  -- Prefer more specific ranges
        LIMIT 1;
    END IF;
    
    -- If no match found, return null values
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT 
            NULL::CHAR(2),
            NULL::VARCHAR(100),
            NULL::INTEGER,
            NULL::VARCHAR(255);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function for safe data cleanup (protecting reference tables)
CREATE OR REPLACE FUNCTION safe_clean_iot_data()
RETURNS TEXT AS $$
DECLARE
    deleted_count INTEGER;
    total_deleted INTEGER := 0;
    result_text TEXT := '';
BEGIN
    result_text := 'Safe IoT Data Cleanup - Reference tables protected' || E'\n';
    result_text := result_text || '================================================' || E'\n';
    
    -- Delete from dependent tables first (in correct order)
    DELETE FROM device_activity_timeline;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    total_deleted := total_deleted + deleted_count;
    result_text := result_text || format('Deleted %s records from device_activity_timeline', deleted_count) || E'\n';
    
    DELETE FROM device_traffic_trend;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    total_deleted := total_deleted + deleted_count;
    result_text := result_text || format('Deleted %s records from device_traffic_trend', deleted_count) || E'\n';
    
    DELETE FROM device_topology;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    total_deleted := total_deleted + deleted_count;
    result_text := result_text || format('Deleted %s records from device_topology', deleted_count) || E'\n';
    
    DELETE FROM protocol_analysis;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    total_deleted := total_deleted + deleted_count;
    result_text := result_text || format('Deleted %s records from protocol_analysis', deleted_count) || E'\n';
    
    DELETE FROM port_analysis;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    total_deleted := total_deleted + deleted_count;
    result_text := result_text || format('Deleted %s records from port_analysis', deleted_count) || E'\n';
    
    DELETE FROM network_flow_aggregates;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    total_deleted := total_deleted + deleted_count;
    result_text := result_text || format('Deleted %s records from network_flow_aggregates', deleted_count) || E'\n';
    
    DELETE FROM packet_flows;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    total_deleted := total_deleted + deleted_count;
    result_text := result_text || format('Deleted %s records from packet_flows', deleted_count) || E'\n';
    
    DELETE FROM network_sessions;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    total_deleted := total_deleted + deleted_count;
    result_text := result_text || format('Deleted %s records from network_sessions', deleted_count) || E'\n';
    
    DELETE FROM device_statistics;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    total_deleted := total_deleted + deleted_count;
    result_text := result_text || format('Deleted %s records from device_statistics', deleted_count) || E'\n';
    
    DELETE FROM devices;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    total_deleted := total_deleted + deleted_count;
    result_text := result_text || format('Deleted %s records from devices', deleted_count) || E'\n';
    
    DELETE FROM experiments;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    total_deleted := total_deleted + deleted_count;
    result_text := result_text || format('Deleted %s records from experiments', deleted_count) || E'\n';
    
    result_text := result_text || '================================================' || E'\n';
    result_text := result_text || format('Total deleted: %s records', total_deleted) || E'\n';
    result_text := result_text || 'Reference tables (vendor_patterns, known_devices, ip_geolocation_ref, ip_geolocation_cache) PROTECTED and preserved' || E'\n';
    
    RETURN result_text;
END;
$$ LANGUAGE plpgsql;

-- Function to get experiment statistics
CREATE OR REPLACE FUNCTION get_experiment_stats(exp_id VARCHAR(50))
RETURNS TABLE (
    total_devices INTEGER,
    online_devices INTEGER,
    total_packets BIGINT,
    total_bytes BIGINT,
    total_sessions INTEGER,
    data_time_range INTERVAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(DISTINCT d.device_id)::INTEGER as total_devices,
        COUNT(DISTINCT CASE WHEN d.status = 'online' THEN d.device_id END)::INTEGER as online_devices,
        COALESCE(SUM(ds.total_packets), 0)::BIGINT as total_packets,
        COALESCE(SUM(ds.total_bytes), 0)::BIGINT as total_bytes,
        COALESCE(SUM(ds.total_sessions), 0)::INTEGER as total_sessions,
        (MAX(pf.packet_timestamp) - MIN(pf.packet_timestamp)) as data_time_range
    FROM experiments e
    LEFT JOIN devices d ON e.experiment_id = d.experiment_id
    LEFT JOIN device_statistics ds ON d.device_id = ds.device_id
    LEFT JOIN packet_flows pf ON d.device_id = pf.device_id
    WHERE e.experiment_id = exp_id
    GROUP BY e.experiment_id;
END;
$$ LANGUAGE plpgsql;

-- Function to recalculate device statistics
CREATE OR REPLACE FUNCTION recalculate_device_statistics(target_device_id UUID DEFAULT NULL)
RETURNS INTEGER AS $$
DECLARE
    device_rec RECORD;
    updated_count INTEGER := 0;
BEGIN
    -- If specific device ID provided, only update that device
    -- Otherwise update all devices
    FOR device_rec IN 
        SELECT device_id, experiment_id 
        FROM devices 
        WHERE (target_device_id IS NULL OR device_id = target_device_id)
    LOOP
        -- Update device statistics with fresh calculations
        INSERT INTO device_statistics (
            device_id, 
            experiment_id,
            total_packets, 
            total_bytes, 
            total_sessions,
            avg_packet_size,
            peak_bandwidth,
            connection_count,
            last_updated
        )
        SELECT 
            device_rec.device_id,
            device_rec.experiment_id,
            COUNT(*) as total_packets,
            SUM(packet_size) as total_bytes,
            COUNT(DISTINCT 
                CASE 
                    WHEN src_port IS NOT NULL AND dst_port IS NOT NULL 
                    THEN src_ip::text || ':' || src_port::text || '->' || dst_ip::text || ':' || dst_port::text
                    ELSE NULL 
                END
            ) as total_sessions,
            AVG(packet_size) as avg_packet_size,
            MAX(packet_size) as peak_bandwidth,
            COUNT(DISTINCT dst_ip) as connection_count,
            NOW() as last_updated
        FROM packet_flows
        WHERE device_id = device_rec.device_id
        ON CONFLICT (device_id) 
        DO UPDATE SET
            total_packets = EXCLUDED.total_packets,
            total_bytes = EXCLUDED.total_bytes,
            total_sessions = EXCLUDED.total_sessions,
            avg_packet_size = EXCLUDED.avg_packet_size,
            peak_bandwidth = EXCLUDED.peak_bandwidth,
            connection_count = EXCLUDED.connection_count,
            last_updated = EXCLUDED.last_updated;
        
        updated_count := updated_count + 1;
    END LOOP;
    
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- Function to validate and format MAC address
CREATE OR REPLACE FUNCTION normalize_mac_address(input_mac VARCHAR(17))
RETURNS VARCHAR(17) AS $$
BEGIN
    -- Convert to uppercase and standardize format
    RETURN UPPER(
        REGEXP_REPLACE(
            REGEXP_REPLACE(input_mac, '[^0-9A-Fa-f]', '', 'g'),
            '(.{2})(.{2})(.{2})(.{2})(.{2})(.{2})',
            '\1:\2:\3:\4:\5:\6'
        )
    );
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON FUNCTION update_updated_at_column() IS 'Trigger function to automatically update updated_at timestamps';
COMMENT ON FUNCTION resolve_device_info(VARCHAR) IS 'Resolve device information using known devices and vendor patterns';
COMMENT ON FUNCTION lookup_ip_location(INET) IS 'Lookup IP geolocation from cache and reference data';
COMMENT ON FUNCTION safe_clean_iot_data() IS 'Safe cleanup function that preserves reference data';
COMMENT ON FUNCTION get_experiment_stats(VARCHAR) IS 'Get comprehensive statistics for an experiment';
COMMENT ON FUNCTION recalculate_device_statistics(UUID) IS 'Recalculate device statistics from packet flow data';
COMMENT ON FUNCTION normalize_mac_address(VARCHAR) IS 'Validate and normalize MAC address format'; 