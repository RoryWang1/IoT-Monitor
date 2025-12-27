// Shared types for Reference Data Management

export interface VendorPattern {
  oui_pattern: string;
  vendor_name: string;
  device_category: string;
  created_at?: string;
}

export interface KnownDevice {
  mac_address: string;
  device_name: string;
  device_type: string;
  vendor: string;
  notes?: string;
  created_at?: string;
}

export interface VendorPatternRequest {
  oui_pattern: string;
  vendor_name: string;
  device_category: string;
}

export interface KnownDeviceRequest {
  mac_address: string;
  device_name: string;
  device_type: string;
  vendor: string;
  notes?: string;
}

export const DEVICE_CATEGORIES = [
  'networking',
  'iot',
  'smart_device', 
  'mobile',
  'computer',
  'entertainment',
  'security',
  'unknown'
] as const;

export const DEVICE_TYPES = [
  'smart_device',
  'iot',
  'router',
  'switch',
  'access_point',
  'camera',
  'sensor',
  'smart_speaker',
  'smart_plug',
  'smart_light',
  'smartphone',
  'tablet',
  'laptop',
  'desktop',
  'server',
  'printer',
  'gaming_console',
  'tv',
  'unknown'
] as const;

export type DeviceCategory = typeof DEVICE_CATEGORIES[number];
export type DeviceType = typeof DEVICE_TYPES[number]; 