-- IoT Device Monitor - Core Schema
-- Basic tables for experiments and devices

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create experiments table for data isolation
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id VARCHAR(50) PRIMARY KEY,
    experiment_name VARCHAR(255) NOT NULL,
    description TEXT,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'active',
    timezone VARCHAR(50) DEFAULT 'UTC',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_experiment_status CHECK (status IN ('active', 'completed', 'archived', 'draft')),
    CONSTRAINT experiment_name_not_empty CHECK (length(trim(experiment_name)) > 0),
    CONSTRAINT valid_date_range CHECK (end_date IS NULL OR start_date <= end_date),
    CONSTRAINT valid_timezone CHECK (timezone IN ('UTC', 'Europe/London', 'America/New_York', 'Asia/Shanghai', 'Europe/Paris'))
);

-- Create devices table with experiment isolation
CREATE TABLE IF NOT EXISTS devices (
    device_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id VARCHAR(50) NOT NULL REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    device_name VARCHAR(255) NOT NULL,
    mac_address VARCHAR(17) NOT NULL,
    ip_address INET,
    device_type VARCHAR(100) NOT NULL,
    manufacturer VARCHAR(255),
    model VARCHAR(255),
    firmware_version VARCHAR(100),
    status VARCHAR(50) DEFAULT 'unknown',
    last_seen TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Device configuration and metadata
    configuration JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT valid_mac_address CHECK (mac_address ~ '^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'),
    CONSTRAINT valid_status CHECK (status IN ('online', 'offline', 'unknown')),
    CONSTRAINT device_name_not_empty CHECK (length(trim(device_name)) > 0),
    CONSTRAINT unique_mac_per_experiment UNIQUE (experiment_id, mac_address)
);

-- Create device_statistics table for aggregated data
CREATE TABLE IF NOT EXISTS device_statistics (
    device_id UUID PRIMARY KEY REFERENCES devices(device_id) ON DELETE CASCADE,
    experiment_id VARCHAR(50) NOT NULL REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    total_packets BIGINT DEFAULT 0,
    total_bytes BIGINT DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    
    -- Protocol distribution as JSONB
    protocol_distribution JSONB DEFAULT '{}',
    
    -- Port activity as JSONB
    port_activity JSONB DEFAULT '{}',
    
    -- Network topology cache
    network_topology JSONB DEFAULT '{}',
    
    -- Performance metrics
    avg_packet_size DECIMAL(10,2) DEFAULT 0,
    peak_bandwidth BIGINT DEFAULT 0,
    connection_count INTEGER DEFAULT 0,
    
    -- Time tracking
    first_seen TIMESTAMP WITH TIME ZONE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Additional statistics
    uptime_percentage DECIMAL(5,2) DEFAULT 0,
    error_rate DECIMAL(5,2) DEFAULT 0
);

-- Raw packet-level traffic data table
CREATE TABLE IF NOT EXISTS packet_flows (
    flow_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    experiment_id VARCHAR(50) REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    
    -- Real timestamp from PCAP file (UTC timezone for consistency)
    packet_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Ethernet layer information (MAC addresses)
    src_mac VARCHAR(17),
    dst_mac VARCHAR(17),
    
    -- Network layer information
    src_ip INET NOT NULL,
    dst_ip INET NOT NULL,
    src_port INTEGER,
    dst_port INTEGER,
    protocol VARCHAR(20) NOT NULL,
    
    -- Traffic metrics
    packet_size INTEGER NOT NULL DEFAULT 0,
    flow_direction VARCHAR(10) NOT NULL, -- 'inbound', 'outbound', 'internal'
    
    -- Flow identification
    flow_hash VARCHAR(64), -- Hash of src_ip:src_port->dst_ip:dst_port
    
    -- Metadata
    tcp_flags VARCHAR(20),
    payload_size INTEGER DEFAULT 0,
    
    -- Application layer protocol (enhanced protocol detection)
    app_protocol VARCHAR(50),
    
    -- Indexing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Prevent duplicate records in packet_flows
    CONSTRAINT unique_packet_flow_per_device 
    UNIQUE (device_id, packet_timestamp, src_ip, dst_ip, src_port, dst_port, protocol, flow_direction)
);

-- Network sessions table (aggregated flows)
CREATE TABLE IF NOT EXISTS network_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    experiment_id VARCHAR(50) REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    
    -- Session time boundaries
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    
    -- Network endpoints
    local_ip INET NOT NULL,
    remote_ip INET NOT NULL,
    local_port INTEGER,
    remote_port INTEGER,
    protocol VARCHAR(20) NOT NULL,
    
    -- Aggregated metrics
    total_packets INTEGER NOT NULL DEFAULT 0,
    total_bytes BIGINT NOT NULL DEFAULT 0,
    packets_in INTEGER NOT NULL DEFAULT 0,
    packets_out INTEGER NOT NULL DEFAULT 0,
    bytes_in BIGINT NOT NULL DEFAULT 0,
    bytes_out BIGINT NOT NULL DEFAULT 0,
    
    -- Session characteristics
    session_type VARCHAR(20) DEFAULT 'unknown', -- 'short', 'medium', 'long', 'persistent'
    connection_state VARCHAR(20) DEFAULT 'unknown', -- 'established', 'closed', 'timeout'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Basic indexes for core tables
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiments_dates ON experiments(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_experiments_created ON experiments(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_devices_experiment ON devices(experiment_id);
CREATE INDEX IF NOT EXISTS idx_devices_mac_address ON devices(mac_address);
CREATE INDEX IF NOT EXISTS idx_devices_ip_address ON devices(ip_address);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_devices_experiment_status ON devices(experiment_id, status);
CREATE INDEX IF NOT EXISTS idx_devices_metadata ON devices USING GIN(metadata);

CREATE INDEX IF NOT EXISTS idx_device_statistics_experiment ON device_statistics(experiment_id);
CREATE INDEX IF NOT EXISTS idx_device_statistics_updated ON device_statistics(last_updated DESC);
CREATE INDEX IF NOT EXISTS idx_device_statistics_protocol ON device_statistics USING GIN(protocol_distribution);
CREATE INDEX IF NOT EXISTS idx_device_statistics_topology ON device_statistics USING GIN(network_topology);

CREATE INDEX IF NOT EXISTS idx_packet_flows_device_timestamp 
    ON packet_flows(device_id, packet_timestamp);
CREATE INDEX IF NOT EXISTS idx_packet_flows_protocol_timestamp 
    ON packet_flows(protocol, packet_timestamp);
CREATE INDEX IF NOT EXISTS idx_packet_flows_dst_port_timestamp 
    ON packet_flows(dst_port, packet_timestamp);
CREATE INDEX IF NOT EXISTS idx_packet_flows_experiment 
    ON packet_flows(experiment_id, packet_timestamp);
CREATE INDEX IF NOT EXISTS idx_packet_flows_src_mac 
    ON packet_flows(src_mac);
CREATE INDEX IF NOT EXISTS idx_packet_flows_dst_mac 
    ON packet_flows(dst_mac);
CREATE INDEX IF NOT EXISTS idx_packet_flows_app_protocol 
    ON packet_flows(app_protocol);
CREATE INDEX IF NOT EXISTS idx_packet_flows_flow_hash 
    ON packet_flows(flow_hash);

CREATE INDEX IF NOT EXISTS idx_network_sessions_device_time 
    ON network_sessions(device_id, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_network_sessions_protocol_time 
    ON network_sessions(protocol, start_time);
CREATE INDEX IF NOT EXISTS idx_network_sessions_port_time 
    ON network_sessions(remote_port, start_time);

-- Comments for documentation
COMMENT ON TABLE experiments IS 'Core experiments table for data isolation';
COMMENT ON TABLE devices IS 'Device registry with experiment-based isolation';
COMMENT ON TABLE device_statistics IS 'Aggregated device statistics and performance metrics';
COMMENT ON TABLE packet_flows IS 'Raw packet-level traffic data from PCAP analysis';
COMMENT ON TABLE network_sessions IS 'Aggregated network sessions for performance optimization'; 