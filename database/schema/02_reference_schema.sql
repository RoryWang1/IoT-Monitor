-- IoT Device Monitor - Reference Data Schema
-- Device name and vendor mapping tables
-- These tables contain reference data that should be protected from accidental deletion

-- Create vendor_patterns table for MAC address OUI to vendor mapping
CREATE TABLE IF NOT EXISTS vendor_patterns (
    oui_pattern VARCHAR(8) PRIMARY KEY,
    vendor_name VARCHAR(255) NOT NULL,
    device_category VARCHAR(100) NOT NULL DEFAULT 'unknown',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_protected BOOLEAN DEFAULT TRUE,
    
    -- Constraints
    CONSTRAINT valid_oui_pattern CHECK (oui_pattern ~ '^[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}$'),
    CONSTRAINT vendor_name_not_empty CHECK (length(trim(vendor_name)) > 0)
);

-- Create known_devices table for specific device name mapping
CREATE TABLE IF NOT EXISTS known_devices (
    mac_address VARCHAR(17) PRIMARY KEY,
    device_name VARCHAR(255) NOT NULL,
    device_type VARCHAR(100) NOT NULL DEFAULT 'unknown',
    vendor VARCHAR(255) NOT NULL DEFAULT 'Unknown',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_protected BOOLEAN DEFAULT TRUE,
    
    -- Constraints
    CONSTRAINT valid_mac_address CHECK (mac_address ~ '^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'),
    CONSTRAINT device_name_not_empty CHECK (length(trim(device_name)) > 0)
);

-- Create IP geolocation reference table for IP to country mapping
CREATE TABLE IF NOT EXISTS ip_geolocation_ref (
    id SERIAL PRIMARY KEY,
    start_ip INET NOT NULL,
    end_ip INET NOT NULL,
    country_code CHAR(2) NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    asn INTEGER,
    asn_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_protected BOOLEAN DEFAULT TRUE,
    
    -- Constraints
    CONSTRAINT valid_country_code CHECK (country_code ~ '^[A-Z]{2}$'),
    CONSTRAINT country_name_not_empty CHECK (length(trim(country_name)) > 0),
    CONSTRAINT valid_ip_range CHECK (start_ip <= end_ip)
);

-- Create protection trigger function - prevent deletion of protected records
CREATE OR REPLACE FUNCTION protect_reference_data()
RETURNS TRIGGER AS $$
BEGIN
    -- If attempt to delete protected record, prevent deletion
    IF OLD.is_protected = TRUE THEN
        RAISE EXCEPTION 'Cannot delete protected reference data. Table: %, Record: %', 
            TG_TABLE_NAME, 
            CASE 
                WHEN TG_TABLE_NAME = 'vendor_patterns' THEN OLD.oui_pattern
                WHEN TG_TABLE_NAME = 'known_devices' THEN OLD.mac_address
                WHEN TG_TABLE_NAME = 'ip_geolocation_ref' THEN OLD.id::TEXT
                ELSE 'unknown'
            END
            USING HINT = 'Reference data is protected. Use UPDATE to set is_protected=FALSE first if you really need to delete.';
    END IF;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Create protection triggers
CREATE OR REPLACE TRIGGER protect_vendor_patterns_trigger
    BEFORE DELETE ON vendor_patterns
    FOR EACH ROW
    EXECUTE FUNCTION protect_reference_data();

CREATE OR REPLACE TRIGGER protect_known_devices_trigger
    BEFORE DELETE ON known_devices
    FOR EACH ROW
    EXECUTE FUNCTION protect_reference_data();

CREATE OR REPLACE TRIGGER protect_ip_geolocation_ref_trigger
    BEFORE DELETE ON ip_geolocation_ref
    FOR EACH ROW
    EXECUTE FUNCTION protect_reference_data();

-- Note: Reference data protection is handled by row-level triggers above
-- TRUNCATE protection is managed through database user permissions in production

-- Create indexes for optimal query performance
CREATE INDEX IF NOT EXISTS idx_vendor_patterns_vendor ON vendor_patterns(vendor_name);
CREATE INDEX IF NOT EXISTS idx_vendor_patterns_category ON vendor_patterns(device_category);
CREATE INDEX IF NOT EXISTS idx_vendor_patterns_protected ON vendor_patterns(is_protected);

CREATE INDEX IF NOT EXISTS idx_known_devices_name ON known_devices(device_name);
CREATE INDEX IF NOT EXISTS idx_known_devices_type ON known_devices(device_type);
CREATE INDEX IF NOT EXISTS idx_known_devices_vendor ON known_devices(vendor);
CREATE INDEX IF NOT EXISTS idx_known_devices_protected ON known_devices(is_protected);

-- Optimized indexes for IP geolocation queries
CREATE INDEX IF NOT EXISTS idx_ip_geolocation_start_ip ON ip_geolocation_ref USING GIST (start_ip inet_ops);
CREATE INDEX IF NOT EXISTS idx_ip_geolocation_end_ip ON ip_geolocation_ref USING GIST (end_ip inet_ops);
CREATE INDEX IF NOT EXISTS idx_ip_geolocation_range ON ip_geolocation_ref USING GIST (start_ip inet_ops, end_ip inet_ops);
CREATE INDEX IF NOT EXISTS idx_ip_geolocation_country_code ON ip_geolocation_ref(country_code);
CREATE INDEX IF NOT EXISTS idx_ip_geolocation_asn ON ip_geolocation_ref(asn) WHERE asn IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ip_geolocation_protected ON ip_geolocation_ref(is_protected);

-- Comments for documentation
COMMENT ON TABLE vendor_patterns IS 'MAC OUI to vendor mapping for device identification';
COMMENT ON TABLE known_devices IS 'Specific device name mappings for known devices';
COMMENT ON TABLE ip_geolocation_ref IS 'IP address geolocation reference data';
COMMENT ON FUNCTION protect_reference_data() IS 'Trigger function to protect reference data from accidental deletion'; 