-- IoT Device Monitor - Views and Advanced Indexes Schema
-- Database views and specialized indexes for query optimization
-- Views provide convenient access to commonly used data combinations

-- Device resolution view (combining known devices and vendor patterns)
CREATE OR REPLACE VIEW device_resolution AS
SELECT 
    d.device_id,
    d.mac_address,
    d.ip_address,
    d.experiment_id,
    COALESCE(kd.device_name, 'Unknown') as resolved_device_name,
    COALESCE(kd.device_type, d.device_type) as resolved_device_type,
    COALESCE(kd.vendor, vp.vendor_name, d.manufacturer, 'Unknown') as resolved_vendor,
    kd.mac_address IS NOT NULL as has_known_device_mapping,
    vp.oui_pattern IS NOT NULL as has_vendor_pattern_mapping,
    d.device_name as original_device_name,
    d.manufacturer as original_manufacturer,
    d.status,
    d.last_seen
FROM devices d
LEFT JOIN known_devices kd ON d.mac_address = kd.mac_address
LEFT JOIN vendor_patterns vp ON LEFT(d.mac_address, 8) = vp.oui_pattern;

-- Active devices view
CREATE OR REPLACE VIEW active_devices AS
SELECT 
    d.device_id,
    d.experiment_id,
    d.device_name,
    d.device_type,
    d.mac_address,
    d.ip_address,
    d.manufacturer,
    d.status,
    d.last_seen,
    ds.total_packets,
    ds.total_bytes,
    ds.total_sessions,
    ds.avg_packet_size,
    ds.connection_count
FROM devices d
LEFT JOIN device_statistics ds ON d.device_id = ds.device_id
WHERE d.status = 'online'
ORDER BY d.experiment_id, d.device_name;

-- Recent traffic view
CREATE OR REPLACE VIEW recent_traffic AS
SELECT 
    dtt.device_id,
    dtt.experiment_id,
    d.device_name,
    d.mac_address,
    dtt.timestamp,
    dtt.time_window,
    dtt.packets,
    dtt.bytes,
    dtt.sessions,
    dtt.pattern,
    dtt.protocol_data
FROM device_traffic_trend dtt
JOIN devices d ON dtt.device_id = d.device_id
WHERE dtt.timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
ORDER BY dtt.experiment_id, dtt.timestamp DESC;

-- Experiment overview view
CREATE OR REPLACE VIEW experiment_overview AS
SELECT 
    e.experiment_id,
    e.experiment_name,
    e.status,
    e.start_date,
    e.end_date,
    COUNT(DISTINCT d.device_id) as device_count,
    COUNT(DISTINCT CASE WHEN d.status = 'online' THEN d.device_id END) as online_devices,
    COALESCE(SUM(ds.total_packets), 0) as total_packets,
    COALESCE(SUM(ds.total_bytes), 0) as total_bytes,
    COALESCE(SUM(ds.total_sessions), 0) as total_sessions,
    MIN(pf.packet_timestamp) as earliest_data,
    MAX(pf.packet_timestamp) as latest_data,
    e.created_at,
    e.updated_at
FROM experiments e
LEFT JOIN devices d ON e.experiment_id = d.experiment_id
LEFT JOIN device_statistics ds ON d.device_id = ds.device_id AND ds.experiment_id = e.experiment_id
LEFT JOIN packet_flows pf ON d.device_id = pf.device_id
GROUP BY e.experiment_id, e.experiment_name, e.status, e.start_date, e.end_date, e.created_at, e.updated_at
ORDER BY e.created_at DESC;

-- Experiment device statistics view
CREATE OR REPLACE VIEW experiment_device_stats AS
SELECT 
    d.experiment_id,
    d.device_id,
    d.device_name,
    d.device_type,
    d.mac_address,
    d.ip_address,
    d.manufacturer,
    d.status,
    ds.total_packets,
    ds.total_bytes,
    ds.total_sessions,
    ds.avg_packet_size,
    ds.peak_bandwidth,
    ds.connection_count,
    ds.last_updated as stats_updated,
    d.last_seen
FROM devices d
LEFT JOIN device_statistics ds ON d.device_id = ds.device_id AND ds.experiment_id = d.experiment_id
ORDER BY d.experiment_id, d.device_name;

-- Geolocation statistics view for experiments
CREATE OR REPLACE VIEW experiment_location_stats AS
SELECT 
    pf.experiment_id,
    gc.country_name,
    gc.country_code,
    COUNT(DISTINCT pf.dst_ip) as unique_ips,
    SUM(pf.packet_size) as total_bytes,
    COUNT(*) as total_packets,
    COUNT(DISTINCT pf.device_id) as device_count
FROM packet_flows pf
JOIN ip_geolocation_cache gc ON pf.dst_ip = gc.ip_address
WHERE pf.dst_ip IS NOT NULL 
AND pf.dst_ip != '0.0.0.0'
AND NOT (pf.dst_ip::text LIKE '192.168.%' OR pf.dst_ip::text LIKE '10.%' OR pf.dst_ip::text LIKE '172.%')
GROUP BY pf.experiment_id, gc.country_name, gc.country_code
ORDER BY pf.experiment_id, total_bytes DESC;

-- Protocol distribution summary view
CREATE OR REPLACE VIEW protocol_distribution_summary AS
SELECT 
    pa.experiment_id,
    pa.protocol,
    COUNT(DISTINCT pa.device_id) as device_count,
    SUM(pa.packet_count) as total_packets,
    SUM(pa.byte_count) as total_bytes,
    AVG(pa.percentage) as avg_percentage,
    MAX(pa.percentage) as max_percentage,
    pa.time_window
FROM protocol_analysis pa
GROUP BY pa.experiment_id, pa.protocol, pa.time_window
ORDER BY pa.experiment_id, total_bytes DESC;

-- Port usage summary view
CREATE OR REPLACE VIEW port_usage_summary AS
SELECT 
    pa.experiment_id,
    pa.port_number,
    pa.protocol,
    pa.service,
    COUNT(DISTINCT pa.device_id) as device_count,
    SUM(pa.packet_count) as total_packets,
    SUM(pa.byte_count) as total_bytes,
    AVG(pa.usage_percentage) as avg_usage_percentage,
    pa.time_window,
    STRING_AGG(DISTINCT pa.status, ', ') as status_list
FROM port_analysis pa
GROUP BY pa.experiment_id, pa.port_number, pa.protocol, pa.service, pa.time_window
ORDER BY pa.experiment_id, total_bytes DESC;

-- Device activity patterns view
CREATE OR REPLACE VIEW device_activity_patterns AS
SELECT 
    dat.device_id,
    dat.experiment_id,
    d.device_name,
    dat.time_window,
    dat.pattern,
    COUNT(*) as pattern_occurrences,
    AVG(dat.activity_level) as avg_activity_level,
    SUM(dat.packets) as total_packets,
    SUM(dat.bytes) as total_bytes,
    MIN(dat.timestamp) as first_occurrence,
    MAX(dat.timestamp) as last_occurrence
FROM device_activity_timeline dat
JOIN devices d ON dat.device_id = d.device_id
GROUP BY dat.device_id, dat.experiment_id, d.device_name, dat.time_window, dat.pattern
ORDER BY dat.experiment_id, d.device_name, pattern_occurrences DESC;

-- Network topology summary view
CREATE OR REPLACE VIEW network_topology_summary AS
SELECT 
    dt.experiment_id,
    dt.time_window,
    COUNT(DISTINCT dt.device_id) as devices_with_topology,
    COUNT(*) as topology_entries,
    AVG(JSONB_ARRAY_LENGTH(dt.topology_data->'connections')) as avg_connections_per_device,
    MAX(dt.created_at) as latest_update
FROM device_topology dt
WHERE dt.topology_data ? 'connections'
GROUP BY dt.experiment_id, dt.time_window
ORDER BY dt.experiment_id, devices_with_topology DESC;

-- Advanced composite indexes for complex queries
CREATE INDEX IF NOT EXISTS idx_packet_flows_device_protocol_time 
    ON packet_flows(device_id, protocol, packet_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_packet_flows_experiment_direction_time 
    ON packet_flows(experiment_id, flow_direction, packet_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_devices_experiment_type_status 
    ON devices(experiment_id, device_type, status);

CREATE INDEX IF NOT EXISTS idx_protocol_analysis_experiment_protocol_time 
    ON protocol_analysis(experiment_id, protocol, time_window, percentage DESC);

CREATE INDEX IF NOT EXISTS idx_port_analysis_experiment_port_usage 
    ON port_analysis(experiment_id, port_number, usage_percentage DESC);

CREATE INDEX IF NOT EXISTS idx_device_activity_experiment_pattern_time 
    ON device_activity_timeline(experiment_id, pattern, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_device_traffic_experiment_pattern_time 
    ON device_traffic_trend(experiment_id, pattern, timestamp DESC);

-- Specialized indexes for geolocation queries
CREATE INDEX IF NOT EXISTS idx_packet_flows_dst_ip_public 
    ON packet_flows(dst_ip) 
    WHERE dst_ip IS NOT NULL 
      AND dst_ip != '0.0.0.0'
      AND NOT (dst_ip::text LIKE '192.168.%' OR dst_ip::text LIKE '10.%' OR dst_ip::text LIKE '172.%');

-- Partial indexes for active data
CREATE INDEX IF NOT EXISTS idx_devices_active_experiment 
    ON devices(experiment_id, last_seen DESC) 
    WHERE status = 'online';

CREATE INDEX IF NOT EXISTS idx_experiments_active_dates 
    ON experiments(start_date, end_date) 
    WHERE status = 'active';

-- Comments for documentation
COMMENT ON VIEW device_resolution IS 'Comprehensive device information with resolved names and vendors';
COMMENT ON VIEW active_devices IS 'Currently active devices with their statistics';
COMMENT ON VIEW recent_traffic IS 'Recent traffic activity across all devices';
COMMENT ON VIEW experiment_overview IS 'Summary statistics for all experiments';
COMMENT ON VIEW experiment_device_stats IS 'Device statistics grouped by experiment';
COMMENT ON VIEW experiment_location_stats IS 'Geographic distribution of traffic by experiment';
COMMENT ON VIEW protocol_distribution_summary IS 'Protocol usage summary across experiments';
COMMENT ON VIEW port_usage_summary IS 'Port usage patterns across experiments';
COMMENT ON VIEW device_activity_patterns IS 'Device activity pattern analysis';
COMMENT ON VIEW network_topology_summary IS 'Network topology analysis summary'; 