-- IoT Device Monitor - Analytics Schema
-- Traffic analysis, protocol distribution, and network topology tables
-- These tables store analyzed and aggregated data for visualization

-- Device activity timeline table
CREATE TABLE IF NOT EXISTS device_activity_timeline (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    experiment_id VARCHAR(50) NOT NULL REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    time_window VARCHAR(10) NOT NULL DEFAULT '1h',
    hour INTEGER NOT NULL DEFAULT 0,
    minute INTEGER NOT NULL DEFAULT 0,
    activity_level DECIMAL(5,2) NOT NULL DEFAULT 0,
    packets INTEGER NOT NULL DEFAULT 0,
    bytes BIGINT NOT NULL DEFAULT 0,
    sessions INTEGER NOT NULL DEFAULT 0,
    pattern VARCHAR(20) DEFAULT 'normal',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_time_window CHECK (time_window IN ('1h', '6h', '12h', '24h', '48h')),
    CONSTRAINT valid_pattern CHECK (pattern IN ('normal', 'peak', 'low', 'anomaly', 'business', 'morning', 'night', 'evening')),
    CONSTRAINT valid_hour CHECK (hour >= 0 AND hour <= 23),
    CONSTRAINT valid_minute CHECK (minute >= 0 AND minute <= 59),
    CONSTRAINT positive_values CHECK (packets >= 0 AND bytes >= 0 AND sessions >= 0),
    CONSTRAINT unique_device_activity_timeline UNIQUE (device_id, experiment_id, time_window, timestamp)
);

-- Device traffic trend table
CREATE TABLE IF NOT EXISTS device_traffic_trend (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    experiment_id VARCHAR(50) NOT NULL REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    time_window VARCHAR(10) NOT NULL DEFAULT '1h',
    packets INTEGER NOT NULL DEFAULT 0,
    bytes BIGINT NOT NULL DEFAULT 0,
    sessions INTEGER NOT NULL DEFAULT 0,
    protocol_data JSONB DEFAULT '{}',
    pattern VARCHAR(20) DEFAULT 'normal',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_time_window CHECK (time_window IN ('1h', '6h', '12h', '24h', '48h')),
    CONSTRAINT valid_pattern CHECK (pattern IN ('normal', 'business', 'evening', 'night', 'weekend', 'low', 'peak', 'burst', 'idle', 'active')),
    CONSTRAINT positive_values CHECK (packets >= 0 AND bytes >= 0 AND sessions >= 0),
    CONSTRAINT unique_device_traffic_trend UNIQUE (device_id, experiment_id, time_window, timestamp)
);

-- Device topology table
CREATE TABLE IF NOT EXISTS device_topology (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    experiment_id VARCHAR(50) NOT NULL REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    time_window VARCHAR(10) NOT NULL DEFAULT '1h',
    topology_data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_time_window CHECK (time_window IN ('1h', '6h', '12h', '24h', '48h')),
    CONSTRAINT unique_device_topology UNIQUE (device_id, experiment_id, time_window)
);

-- Protocol analysis table
CREATE TABLE IF NOT EXISTS protocol_analysis (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    experiment_id VARCHAR(50) NOT NULL REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    time_window VARCHAR(10) NOT NULL DEFAULT '1h',
    protocol VARCHAR(50) NOT NULL,
    packet_count BIGINT NOT NULL DEFAULT 0,
    byte_count BIGINT NOT NULL DEFAULT 0,
    session_count INTEGER NOT NULL DEFAULT 0,
    percentage DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    avg_packet_size DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    formatted_bytes VARCHAR(50) DEFAULT '0 B',
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_time_window CHECK (time_window IN ('1h', '6h', '12h', '24h', '48h')),
    CONSTRAINT positive_values CHECK (packet_count >= 0 AND byte_count >= 0 AND session_count >= 0 AND percentage >= 0),
    CONSTRAINT unique_protocol_analysis UNIQUE (experiment_id, device_id, protocol, time_window)
);

-- Port analysis table
CREATE TABLE IF NOT EXISTS port_analysis (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    experiment_id VARCHAR(50) NOT NULL REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    time_window VARCHAR(10) NOT NULL DEFAULT '1h',
    port_number INTEGER NOT NULL,
    port_type VARCHAR(20) DEFAULT 'unknown',
    protocol VARCHAR(20) NOT NULL,
    packet_count BIGINT NOT NULL DEFAULT 0,
    byte_count BIGINT NOT NULL DEFAULT 0,
    session_count INTEGER NOT NULL DEFAULT 0,
    usage_percentage DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'active',
    service VARCHAR(50) DEFAULT 'Unknown',
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_time_window CHECK (time_window IN ('1h', '6h', '12h', '24h', '48h')),
    CONSTRAINT valid_port CHECK (port_number >= 0 AND port_number <= 65535),
    CONSTRAINT valid_port_type CHECK (port_type IN ('system', 'user', 'dynamic', 'unknown')),
    CONSTRAINT valid_status CHECK (status IN ('open', 'closed', 'filtered', 'active', 'inactive', 'blocked')),
    CONSTRAINT positive_values CHECK (packet_count >= 0 AND byte_count >= 0 AND session_count >= 0 AND usage_percentage >= 0),
    CONSTRAINT unique_port_analysis UNIQUE (experiment_id, device_id, port_number, protocol, time_window)
);

-- Create indexes for analytics tables
CREATE INDEX IF NOT EXISTS idx_device_activity_device_time ON device_activity_timeline(device_id, time_window);
CREATE INDEX IF NOT EXISTS idx_device_activity_experiment ON device_activity_timeline(experiment_id, device_id);
CREATE INDEX IF NOT EXISTS idx_device_activity_timestamp ON device_activity_timeline(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_device_activity_created ON device_activity_timeline(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_device_activity_pattern ON device_activity_timeline(pattern);

CREATE INDEX IF NOT EXISTS idx_device_trend_device_time ON device_traffic_trend(device_id, time_window);
CREATE INDEX IF NOT EXISTS idx_device_trend_experiment ON device_traffic_trend(experiment_id, device_id);
CREATE INDEX IF NOT EXISTS idx_device_trend_timestamp ON device_traffic_trend(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_device_trend_created ON device_traffic_trend(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_device_trend_pattern ON device_traffic_trend(pattern);
CREATE INDEX IF NOT EXISTS idx_device_trend_protocol_data ON device_traffic_trend USING GIN(protocol_data);

CREATE INDEX IF NOT EXISTS idx_device_topology_device_time ON device_topology(device_id, time_window);
CREATE INDEX IF NOT EXISTS idx_device_topology_experiment ON device_topology(experiment_id, device_id);
CREATE INDEX IF NOT EXISTS idx_device_topology_created ON device_topology(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_device_topology_data ON device_topology USING GIN(topology_data);

CREATE INDEX IF NOT EXISTS idx_protocol_analysis_device_time ON protocol_analysis(device_id, time_window);
CREATE INDEX IF NOT EXISTS idx_protocol_analysis_experiment ON protocol_analysis(experiment_id, device_id);
CREATE INDEX IF NOT EXISTS idx_protocol_analysis_protocol ON protocol_analysis(protocol);
CREATE INDEX IF NOT EXISTS idx_protocol_analysis_percentage ON protocol_analysis(percentage DESC);
CREATE INDEX IF NOT EXISTS idx_protocol_analysis_created ON protocol_analysis(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_protocol_analysis_time_range ON protocol_analysis(start_time, end_time);

CREATE INDEX IF NOT EXISTS idx_port_analysis_device_time ON port_analysis(device_id, time_window);
CREATE INDEX IF NOT EXISTS idx_port_analysis_experiment ON port_analysis(experiment_id, device_id);
CREATE INDEX IF NOT EXISTS idx_port_analysis_port ON port_analysis(port_number);
CREATE INDEX IF NOT EXISTS idx_port_analysis_usage ON port_analysis(usage_percentage DESC);
CREATE INDEX IF NOT EXISTS idx_port_analysis_created ON port_analysis(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_port_analysis_status ON port_analysis(status);
CREATE INDEX IF NOT EXISTS idx_port_analysis_time_range ON port_analysis(start_time, end_time);

-- Comments for documentation
COMMENT ON TABLE device_activity_timeline IS 'Time-based device activity patterns and statistics';
COMMENT ON TABLE device_traffic_trend IS 'Traffic trend analysis with pattern recognition';
COMMENT ON TABLE device_topology IS 'Network topology data for device connections visualization';
COMMENT ON TABLE protocol_analysis IS 'Protocol distribution analysis per device and time window';
COMMENT ON TABLE port_analysis IS 'Port usage analysis and service identification'; 