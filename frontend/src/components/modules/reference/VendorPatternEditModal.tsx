import React, { useState, useEffect } from 'react';
import { FaTimes } from 'react-icons/fa';
import { VendorPatternRequest } from '../../../types/reference';

interface VendorPatternEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: VendorPatternRequest) => Promise<void>;
  initialData: VendorPatternRequest | null;
  isLoading?: boolean;
}

const VendorPatternEditModal: React.FC<VendorPatternEditModalProps> = ({
  isOpen,
  onClose,
  onSave,
  initialData,
  isLoading = false
}) => {
  const [formData, setFormData] = useState<VendorPatternRequest>({
    oui_pattern: '',
    vendor_name: '',
    device_category: 'unknown'
  });
  
  const [errors, setErrors] = useState<{[key: string]: string}>({});

  useEffect(() => {
    if (isOpen) {
      if (initialData) {
        setFormData(initialData);
      } else {
        setFormData({
          oui_pattern: '',
          vendor_name: '',
          device_category: 'unknown'
        });
      }
      setErrors({});
    }
  }, [isOpen, initialData]);

  const deviceCategories = [
    { value: 'iot', label: 'IoT Device' },
    { value: 'smart_device', label: 'Smart Device' },
    { value: 'mobile', label: 'Mobile Device' },
    { value: 'computer', label: 'Computer' },
    { value: 'router', label: 'Router' },
    { value: 'switch', label: 'Switch' },
    { value: 'access_point', label: 'Access Point' },
    { value: 'camera', label: 'Camera' },
    { value: 'sensor', label: 'Sensor' },
    { value: 'entertainment', label: 'Entertainment' },
    { value: 'security', label: 'Security' },
    { value: 'unknown', label: 'Unknown' }
  ];

  const validateForm = () => {
    const newErrors: {[key: string]: string} = {};

    if (!formData.oui_pattern.trim()) {
      newErrors.oui_pattern = 'OUI pattern is required';
    } else if (!/^[0-9A-Fa-f:]{8}$/.test(formData.oui_pattern.trim())) {
      newErrors.oui_pattern = 'OUI pattern must be in format XX:XX:XX (8 characters)';
    }

    if (!formData.vendor_name.trim()) {
      newErrors.vendor_name = 'Vendor name is required';
    } else if (formData.vendor_name.length > 100) {
      newErrors.vendor_name = 'Vendor name must be less than 100 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field: keyof VendorPatternRequest, value: string) => {
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

  const formatOuiInput = (value: string) => {
    // Remove any non-hex characters and convert to uppercase
    let cleaned = value.replace(/[^0-9A-Fa-f]/g, '').toUpperCase();
    
    // Limit to 6 characters
    cleaned = cleaned.substring(0, 6);
    
    // Add colons every 2 characters
    if (cleaned.length >= 3) {
      cleaned = cleaned.substring(0, 2) + ':' + cleaned.substring(2, 4) + ':' + cleaned.substring(4, 6);
    } else if (cleaned.length >= 2) {
      cleaned = cleaned.substring(0, 2) + ':' + cleaned.substring(2);
    }
    
    return cleaned;
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
            {initialData ? 'Edit Vendor Pattern' : 'Add Vendor Pattern'}
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
            {/* OUI Pattern */}
            <div style={{ marginBottom: 'var(--spacing-lg)' }}>
              <label style={{
                display: 'block',
                fontSize: 'var(--text-sm)',
                fontWeight: '500',
                color: 'var(--color-text-primary)',
                marginBottom: 'var(--spacing-sm)'
              }}>
                OUI Pattern *
              </label>
              
              <input
                type="text"
                value={formData.oui_pattern}
                onChange={(e) => handleInputChange('oui_pattern', formatOuiInput(e.target.value))}
                disabled={!!initialData || isLoading}
                placeholder="XX:XX:XX"
                maxLength={8}
                style={{
                  width: '100%',
                  padding: 'var(--spacing-md)',
                  border: `1px solid ${errors.oui_pattern ? '#DC2626' : 'var(--color-border-primary)'}`,
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: (!!initialData || isLoading) ? 'var(--color-bg-tertiary)' : 'var(--color-bg-primary)',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-sm)',
                  fontFamily: 'monospace',
                  cursor: (!!initialData || isLoading) ? 'not-allowed' : 'text'
                }}
              />
              
              {errors.oui_pattern && (
                <p style={{
                  marginTop: 'var(--spacing-xs)',
                  fontSize: 'var(--text-sm)',
                  color: '#DC2626'
                }}>
                  {errors.oui_pattern}
                </p>
              )}
              
              <p style={{
                marginTop: 'var(--spacing-xs)',
                fontSize: 'var(--text-xs)',
                color: 'var(--color-text-tertiary)'
              }}>
                First 3 bytes of MAC address (e.g., 00:11:22)
              </p>
            </div>

            {/* Vendor Name */}
            <div style={{ marginBottom: 'var(--spacing-lg)' }}>
              <label style={{
                display: 'block',
                fontSize: 'var(--text-sm)',
                fontWeight: '500',
                color: 'var(--color-text-primary)',
                marginBottom: 'var(--spacing-sm)'
              }}>
                Vendor Name *
              </label>
              
              <input
                type="text"
                value={formData.vendor_name}
                onChange={(e) => handleInputChange('vendor_name', e.target.value)}
                disabled={isLoading}
                placeholder="Enter vendor name"
                maxLength={100}
                style={{
                  width: '100%',
                  padding: 'var(--spacing-md)',
                  border: `1px solid ${errors.vendor_name ? '#DC2626' : 'var(--color-border-primary)'}`,
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: isLoading ? 'var(--color-bg-tertiary)' : 'var(--color-bg-primary)',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-sm)',
                  cursor: isLoading ? 'not-allowed' : 'text'
                }}
              />
              
              {errors.vendor_name && (
                <p style={{
                  marginTop: 'var(--spacing-xs)',
                  fontSize: 'var(--text-sm)',
                  color: '#DC2626'
                }}>
                  {errors.vendor_name}
                </p>
              )}
            </div>

            {/* Device Category */}
            <div style={{ marginBottom: 'var(--spacing-xl)' }}>
              <label style={{
                display: 'block',
                fontSize: 'var(--text-sm)',
                fontWeight: '500',
                color: 'var(--color-text-primary)',
                marginBottom: 'var(--spacing-sm)'
              }}>
                Device Category
              </label>
              
              <select
                value={formData.device_category}
                onChange={(e) => handleInputChange('device_category', e.target.value)}
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
                {deviceCategories.map((category) => (
                  <option key={category.value} value={category.value}>
                    {category.label}
                  </option>
                ))}
              </select>
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

export default VendorPatternEditModal; 