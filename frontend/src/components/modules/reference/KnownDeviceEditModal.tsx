import React, { useState, useEffect } from 'react';
import { FaTimes } from 'react-icons/fa';
import { KnownDeviceRequest } from '../../../types/reference';

interface KnownDeviceEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: KnownDeviceRequest) => Promise<void>;
  initialData: KnownDeviceRequest | null;
  isLoading?: boolean;
}

const KnownDeviceEditModal: React.FC<KnownDeviceEditModalProps> = ({
  isOpen,
  onClose,
  onSave,
  initialData,
  isLoading = false
}) => {
  const [formData, setFormData] = useState<KnownDeviceRequest>({
    mac_address: '',
    device_name: '',
    device_type: 'unknown',
    vendor: 'Unknown',
    notes: ''
  });
  
  const [errors, setErrors] = useState<{[key: string]: string}>({});

  useEffect(() => {
    if (isOpen) {
      if (initialData) {
        setFormData(initialData);
      } else {
        setFormData({
          mac_address: '',
          device_name: '',
          device_type: 'unknown',
          vendor: 'Unknown',
          notes: ''
        });
      }
      setErrors({});
    }
  }, [isOpen, initialData]);

  const deviceTypes = [
    { value: 'iot', label: 'IoT Device' },
    { value: 'smart_device', label: 'Smart Device' },
    { value: 'mobile', label: 'Mobile Device' },
    { value: 'computer', label: 'Computer' },
    { value: 'router', label: 'Router' },
    { value: 'switch', label: 'Switch' },
    { value: 'access_point', label: 'Access Point' },
    { value: 'camera', label: 'Camera' },
    { value: 'sensor', label: 'Sensor' },
    { value: 'printer', label: 'Printer' },
    { value: 'storage', label: 'Storage' },
    { value: 'entertainment', label: 'Entertainment' },
    { value: 'security', label: 'Security' },
    { value: 'appliance', label: 'Smart Appliance' },
    { value: 'unknown', label: 'Unknown' },
    { value: 'test', label: 'Test Device' }
  ];

  const validateForm = () => {
    const newErrors: {[key: string]: string} = {};

    if (!formData.mac_address.trim()) {
      newErrors.mac_address = 'MAC address is required';
    } else if (!/^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/.test(formData.mac_address.trim())) {
      newErrors.mac_address = 'MAC address must be in format XX:XX:XX:XX:XX:XX';
    }

    if (!formData.device_name.trim()) {
      newErrors.device_name = 'Device name is required';
    } else if (formData.device_name.length > 100) {
      newErrors.device_name = 'Device name must be less than 100 characters';
    }

    if (!formData.vendor.trim()) {
      newErrors.vendor = 'Vendor is required';
    } else if (formData.vendor.length > 100) {
      newErrors.vendor = 'Vendor must be less than 100 characters';
    }

    if (formData.notes && formData.notes.length > 500) {
      newErrors.notes = 'Notes must be less than 500 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field: keyof KnownDeviceRequest, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    try {
      await onSave(formData);
    } catch (error) {
      console.error('Save error:', error);
    }
  };

  const formatMacInput = (value: string) => {
    // Remove any non-hex characters and convert to uppercase
    let cleaned = value.replace(/[^0-9A-Fa-f]/g, '').toUpperCase();
    
    // Limit to 12 characters
    cleaned = cleaned.substring(0, 12);
    
    // Add colons every 2 characters
    const formatted = cleaned.match(/.{1,2}/g)?.join(':') || cleaned;
    
    return formatted;
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      backdropFilter: 'blur(4px)'
    }}>
      {/* Modal Content */}
      <div style={{
        backgroundColor: 'var(--color-bg-secondary)',
        border: '1px solid var(--color-border-primary)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-xl)',
        maxWidth: '500px',
        width: '90%',
        maxHeight: '90vh',
        overflow: 'auto'
      }}>
        {/* Header */}
        <div style={{
          padding: 'var(--spacing-xl)',
          borderBottom: '1px solid var(--color-border-primary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <h3 style={{
            fontSize: 'var(--text-lg)',
            fontWeight: '600',
            color: 'var(--color-text-primary)',
            margin: 0
          }}>
            {initialData ? 'Edit Known Device' : 'Add Known Device'}
          </h3>
          
          <button
            onClick={onClose}
            disabled={isLoading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: 'var(--spacing-sm)',
              border: 'none',
              borderRadius: '50%',
              backgroundColor: 'transparent',
              color: 'var(--color-text-tertiary)',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              opacity: isLoading ? 0.5 : 1
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-bg-tertiary)';
              e.currentTarget.style.color = 'var(--color-text-primary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.color = 'var(--color-text-tertiary)';
            }}
          >
            <FaTimes style={{ width: '1rem', height: '1rem' }} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div style={{ padding: 'var(--spacing-xl)' }}>
            {/* MAC Address */}
            <div style={{ marginBottom: 'var(--spacing-lg)' }}>
              <label style={{
                display: 'block',
                fontSize: 'var(--text-sm)',
                fontWeight: '500',
                color: 'var(--color-text-primary)',
                marginBottom: 'var(--spacing-sm)'
              }}>
                MAC Address *
              </label>
              
              <input
                type="text"
                value={formData.mac_address}
                onChange={(e) => handleInputChange('mac_address', formatMacInput(e.target.value))}
                disabled={!!initialData || isLoading}
                placeholder="XX:XX:XX:XX:XX:XX"
                maxLength={17}
                style={{
                  width: '100%',
                  padding: 'var(--spacing-md)',
                  border: `1px solid ${errors.mac_address ? '#DC2626' : 'var(--color-border-primary)'}`,
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: (!!initialData || isLoading) ? 'var(--color-bg-tertiary)' : 'var(--color-bg-primary)',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-sm)',
                  fontFamily: 'monospace',
                  cursor: (!!initialData || isLoading) ? 'not-allowed' : 'text'
                }}
              />
              
              {errors.mac_address && (
                <p style={{
                  marginTop: 'var(--spacing-xs)',
                  fontSize: 'var(--text-sm)',
                  color: '#DC2626'
                }}>
                  {errors.mac_address}
                </p>
              )}
              
              <p style={{
                marginTop: 'var(--spacing-xs)',
                fontSize: 'var(--text-xs)',
                color: 'var(--color-text-tertiary)'
              }}>
                Device network interface MAC address
              </p>
            </div>

            {/* Device Name */}
            <div style={{ marginBottom: 'var(--spacing-lg)' }}>
              <label style={{
                display: 'block',
                fontSize: 'var(--text-sm)',
                fontWeight: '500',
                color: 'var(--color-text-primary)',
                marginBottom: 'var(--spacing-sm)'
              }}>
                Device Name *
              </label>
              
              <input
                type="text"
                value={formData.device_name}
                onChange={(e) => handleInputChange('device_name', e.target.value)}
                disabled={isLoading}
                placeholder="Enter device name"
                maxLength={100}
                style={{
                  width: '100%',
                  padding: 'var(--spacing-md)',
                  border: `1px solid ${errors.device_name ? '#DC2626' : 'var(--color-border-primary)'}`,
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: isLoading ? 'var(--color-bg-tertiary)' : 'var(--color-bg-primary)',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-sm)',
                  cursor: isLoading ? 'not-allowed' : 'text'
                }}
              />
              
              {errors.device_name && (
                <p style={{
                  marginTop: 'var(--spacing-xs)',
                  fontSize: 'var(--text-sm)',
                  color: '#DC2626'
                }}>
                  {errors.device_name}
                </p>
              )}
            </div>

            {/* Device Type */}
            <div style={{ marginBottom: 'var(--spacing-lg)' }}>
              <label style={{
                display: 'block',
                fontSize: 'var(--text-sm)',
                fontWeight: '500',
                color: 'var(--color-text-primary)',
                marginBottom: 'var(--spacing-sm)'
              }}>
                Device Type
              </label>
              
              <select
                value={formData.device_type}
                onChange={(e) => handleInputChange('device_type', e.target.value)}
                disabled={isLoading}
                style={{
                  width: '100%',
                  padding: 'var(--spacing-md)',
                  border: '1px solid var(--color-border-primary)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: isLoading ? 'var(--color-bg-tertiary)' : 'var(--color-bg-primary)',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-sm)',
                  cursor: isLoading ? 'not-allowed' : 'pointer'
                }}
              >
                {deviceTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Vendor */}
            <div style={{ marginBottom: 'var(--spacing-lg)' }}>
              <label style={{
                display: 'block',
                fontSize: 'var(--text-sm)',
                fontWeight: '500',
                color: 'var(--color-text-primary)',
                marginBottom: 'var(--spacing-sm)'
              }}>
                Vendor *
              </label>
              
              <input
                type="text"
                value={formData.vendor}
                onChange={(e) => handleInputChange('vendor', e.target.value)}
                disabled={isLoading}
                placeholder="Enter vendor name"
                maxLength={100}
                style={{
                  width: '100%',
                  padding: 'var(--spacing-md)',
                  border: `1px solid ${errors.vendor ? '#DC2626' : 'var(--color-border-primary)'}`,
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: isLoading ? 'var(--color-bg-tertiary)' : 'var(--color-bg-primary)',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-sm)',
                  cursor: isLoading ? 'not-allowed' : 'text'
                }}
              />
              
              {errors.vendor && (
                <p style={{
                  marginTop: 'var(--spacing-xs)',
                  fontSize: 'var(--text-sm)',
                  color: '#DC2626'
                }}>
                  {errors.vendor}
                </p>
              )}
            </div>

            {/* Notes */}
            <div style={{ marginBottom: 'var(--spacing-xl)' }}>
              <label style={{
                display: 'block',
                fontSize: 'var(--text-sm)',
                fontWeight: '500',
                color: 'var(--color-text-primary)',
                marginBottom: 'var(--spacing-sm)'
              }}>
                Notes
              </label>
              
              <textarea
                value={formData.notes}
                onChange={(e) => handleInputChange('notes', e.target.value)}
                disabled={isLoading}
                placeholder="Optional notes about this device"
                maxLength={500}
                rows={3}
                style={{
                  width: '100%',
                  padding: 'var(--spacing-md)',
                  border: `1px solid ${errors.notes ? '#DC2626' : 'var(--color-border-primary)'}`,
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: isLoading ? 'var(--color-bg-tertiary)' : 'var(--color-bg-primary)',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-sm)',
                  resize: 'vertical',
                  cursor: isLoading ? 'not-allowed' : 'text'
                }}
              />
              
              {errors.notes && (
                <p style={{
                  marginTop: 'var(--spacing-xs)',
                  fontSize: 'var(--text-sm)',
                  color: '#DC2626'
                }}>
                  {errors.notes}
                </p>
              )}
            </div>
          </div>

          {/* Footer Buttons */}
          <div style={{
            padding: 'var(--spacing-xl)',
            borderTop: '1px solid var(--color-border-primary)',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 'var(--spacing-md)'
          }}>
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="button-responsive"
              style={{
                backgroundColor: 'var(--color-bg-tertiary)',
                color: 'var(--color-text-secondary)',
                border: '1px solid var(--color-border-primary)',
                cursor: 'pointer',
                fontWeight: '500',
                opacity: isLoading ? 0.5 : 1
              }}
            >
              Cancel
            </button>
            
            <button
              type="submit"
              disabled={isLoading}
              className="button-responsive"
              style={{
                backgroundColor: 'var(--color-accent-blue)',
                color: 'var(--color-text-primary)',
                border: 'none',
                cursor: 'pointer',
                fontWeight: '500',
                opacity: isLoading ? 0.5 : 1,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 'var(--spacing-sm)'
              }}
            >
              {isLoading ? (
                <>
                  <div style={{
                    width: '1rem',
                    height: '1rem',
                    border: '2px solid transparent',
                    borderTop: '2px solid currentColor',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                  }}></div>
                  Saving...
                </>
              ) : (
                'Save'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default KnownDeviceEditModal; 