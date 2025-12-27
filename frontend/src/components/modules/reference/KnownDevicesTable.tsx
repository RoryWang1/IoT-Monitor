import React, { useState, useEffect } from 'react';
import { FaEdit, FaTrash, FaPlus, FaSearch, FaSync } from 'react-icons/fa';
import KnownDeviceEditModal from './KnownDeviceEditModal';
import { KnownDevice, KnownDeviceRequest } from '../../../types/reference';
import { API_BASE_URL } from '../../../config/api';

interface KnownDevicesTableProps {
  onDataChange?: () => void;
}

// Custom confirmation modal component  
const ConfirmDeleteModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  deviceName: string;
  macAddress: string;
}> = ({ isOpen, onClose, onConfirm, deviceName, macAddress }) => {
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
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'var(--color-bg-secondary)',
        border: '1px solid var(--color-border-primary)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--spacing-3xl)',
        maxWidth: '500px',
        width: '90%',
        boxShadow: 'var(--shadow-xl)'
      }}>
        <h3 style={{
          fontSize: 'var(--text-lg)',
          fontWeight: '600',
          color: 'var(--color-text-primary)',
          margin: '0 0 var(--spacing-lg) 0'
        }}>
          Confirm Deletion
        </h3>
        
        <p style={{
          fontSize: 'var(--text-base)',
          color: 'var(--color-text-secondary)',
          margin: '0 0 var(--spacing-2xl) 0',
          lineHeight: '1.5'
        }}>
          Are you sure you want to delete device <strong style={{ color: 'var(--color-text-primary)' }}>&quot;{deviceName}&quot;</strong> with MAC address <strong style={{ color: 'var(--color-text-primary)' }}>&quot;{macAddress}&quot;</strong>?
        </p>
        
        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 'var(--spacing-md)'
        }}>
          <button
            onClick={onClose}
            className="button-responsive"
            style={{
              backgroundColor: 'var(--color-bg-tertiary)',
              color: 'var(--color-text-secondary)',
              border: '1px solid var(--color-border-primary)',
              cursor: 'pointer',
              fontWeight: '500'
            }}
          >
            Cancel
          </button>
          
          <button
            onClick={onConfirm}
            className="button-responsive"
            style={{
              backgroundColor: '#DC2626',
              color: 'var(--color-text-primary)',
              border: 'none',
              cursor: 'pointer',
              fontWeight: '500'
            }}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
};

const KnownDevicesTable: React.FC<KnownDevicesTableProps> = ({ onDataChange }) => {
  const [devices, setDevices] = useState<KnownDevice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingDevice, setEditingDevice] = useState<KnownDevice | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Delete confirmation modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deviceToDelete, setDeviceToDelete] = useState<KnownDevice | null>(null);
  
  const itemsPerPage = 10;

  const fetchDevices = async (page = 1, search = '') => {
    try {
      setLoading(true);
      setError(null);
      
      const offset = (page - 1) * itemsPerPage;
              let url = `${API_BASE_URL}/api/devices/reference/known-devices?limit=${itemsPerPage}&offset=${offset}`;
      
      if (search.trim()) {
        url += `&search=${encodeURIComponent(search.trim())}`;
      }
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setDevices(data || []);
      
      // Get total count for correct pagination
      if (page === 1) {
        try {
          const countUrl = search.trim() 
            ? `${API_BASE_URL}/api/devices/reference/known-devices?limit=999999&search=${encodeURIComponent(search.trim())}`
            : `${API_BASE_URL}/api/devices/reference/known-devices?limit=999999`;
          const countResponse = await fetch(countUrl);
          if (countResponse.ok) {
            const countData = await countResponse.json();
            const totalItems = countData.length;
            setTotalPages(Math.max(1, Math.ceil(totalItems / itemsPerPage)));
          }
        } catch (countError) {
          // Fallback to estimation if count fails
          const totalItems = data.length === itemsPerPage ? (page * itemsPerPage) + 1 : (page - 1) * itemsPerPage + data.length;
          setTotalPages(Math.max(1, Math.ceil(totalItems / itemsPerPage)));
        }
      }
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to load known devices');
      setDevices([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices(currentPage, searchTerm);
  }, [currentPage, searchTerm]);

  const handleSearch = () => {
    setCurrentPage(1);
    fetchDevices(1, searchTerm);
  };

  const handleRefresh = () => {
    setSearchTerm('');
    setCurrentPage(1);
    fetchDevices(1, '');
  };

  const handleAdd = () => {
    setEditingDevice(null);
    setIsAddModalOpen(true);
  };

  const handleEdit = (device: KnownDevice) => {
    setEditingDevice(device);
    setIsEditModalOpen(true);
  };

  const handleDeleteClick = (device: KnownDevice) => {
    setDeviceToDelete(device);
    setShowDeleteModal(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deviceToDelete) return;

    try {
      setIsSubmitting(true);
      
      const response = await fetch(
        `${API_BASE_URL}/api/devices/reference/known-devices/${encodeURIComponent(deviceToDelete.mac_address)}`,
        { method: 'DELETE' }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      // Close modal and refresh data
      setShowDeleteModal(false);
      setDeviceToDelete(null);
      await fetchDevices(currentPage, searchTerm);
      
      if (onDataChange) {
        onDataChange();
      }

    } catch (error) {
      alert(`Delete failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveDevice = async (deviceData: KnownDeviceRequest) => {
    try {
      setIsSubmitting(true);
      
      let response;
      if (editingDevice) {
        // Update existing device
        response = await fetch(
          `${API_BASE_URL}/api/devices/reference/known-devices/${encodeURIComponent(editingDevice.mac_address)}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(deviceData)
          }
        );
      } else {
        // Create new device
        response = await fetch(`${API_BASE_URL}/api/devices/reference/known-devices`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(deviceData)
        });
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      // Close modals
      setIsAddModalOpen(false);
      setIsEditModalOpen(false);
      setEditingDevice(null);
      
      // Refresh data
      await fetchDevices(currentPage, searchTerm);
      
      if (onDataChange) {
        onDataChange();
      }

    } catch (error) {
      console.error('Failed to save device:', error);
      alert(`Save failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  const getStatusBadge = (type: string) => {
    const colors = {
      // 基础设备类型
      iot: { bg: '#3B82F6', text: '#DBEAFE' },
      smart_device: { bg: '#8B5CF6', text: '#F3E8FF' },
      mobile: { bg: '#06B6D4', text: '#CFFAFE' },
      computer: { bg: '#10B981', text: '#D1FAE5' },
      server: { bg: '#059669', text: '#D1FAE5' },
      
      // 网络设备
      router: { bg: '#F59E0B', text: '#FEF3C7' },
      switch: { bg: '#EF4444', text: '#FEE2E2' },
      access_point: { bg: '#EC4899', text: '#FCE7F3' },
      network: { bg: '#7C3AED', text: '#EDE9FE' },
      
      // 智能设备
      camera: { bg: '#84CC16', text: '#ECFCCB' },
      'Smart Camera': { bg: '#84CC16', text: '#ECFCCB' },
      'Smart Light': { bg: '#F59E0B', text: '#FEF3C7' },
      'Smart Lock': { bg: '#DC2626', text: '#FECACA' },
      
      // 传感器和工业设备
      sensor: { bg: '#14B8A6', text: '#CCFBF1' },
      'Industrial Sensor': { bg: '#0F766E', text: '#CCFBF1' },
      'Medical Device': { bg: '#DC2626', text: '#FECACA' },
      
      // 其他设备类型
      printer: { bg: '#6366F1', text: '#E0E7FF' },
      storage: { bg: '#F97316', text: '#FED7AA' },
      entertainment: { bg: '#A855F7', text: '#F3E8FF' },
      security: { bg: '#DC2626', text: '#FECACA' },
      appliance: { bg: '#059669', text: '#D1FAE5' },
      consumer: { bg: '#0EA5E9', text: '#E0F2FE' },
      test: { bg: '#6B7280', text: '#F3F4F6' },
      unknown: { bg: '#9CA3AF', text: '#F9FAFB' }
    };
    
    const color = colors[type as keyof typeof colors] || colors.unknown;
    
    return (
      <span style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '0.25rem 0.75rem',
        borderRadius: '9999px',
        fontSize: 'var(--text-xs)',
        fontWeight: '500',
        backgroundColor: color.bg,
        color: color.text
      }}>
        {type}
      </span>
    );
  };

  return (
    <div className="card-responsive">
      {/* Header with Actions */}
      <div style={{
        padding: 'var(--spacing-2xl)',
        borderBottom: '1px solid var(--color-border-primary)'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
          {/* Title and Stats */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h3 style={{
                fontSize: 'var(--text-lg)',
                fontWeight: '600',
                color: 'var(--color-text-primary)',
                margin: 0
              }}>
                Known Device Management
              </h3>
              <p style={{
                fontSize: 'var(--text-sm)',
                color: 'var(--color-text-tertiary)',
                margin: '0.25rem 0 0 0'
              }}>
                Specific device name mappings and detailed information ({devices.length} records)
              </p>
            </div>
            
            {/* Action Buttons */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
              <button
                onClick={handleAdd}
                disabled={isSubmitting}
                className="button-responsive"
                style={{
                  backgroundColor: 'var(--color-accent-blue)',
                  color: 'var(--color-text-primary)',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: '500',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 'var(--spacing-sm)',
                  opacity: isSubmitting ? 0.5 : 1
                }}
              >
                <FaPlus style={{ width: '1rem', height: '1rem' }} />
                Add Device
              </button>
              
              <button
                onClick={handleRefresh}
                disabled={loading || isSubmitting}
                className="button-responsive"
                style={{
                  backgroundColor: 'var(--color-bg-tertiary)',
                  color: 'var(--color-text-secondary)',
                  border: '1px solid var(--color-border-primary)',
                  cursor: 'pointer',
                  fontWeight: '500',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 'var(--spacing-sm)',
                  opacity: (loading || isSubmitting) ? 0.5 : 1
                }}
              >
                <FaSync style={{ width: '1rem', height: '1rem' }} />
                Refresh
              </button>
            </div>
          </div>
          
          {/* Search Bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <div style={{
                position: 'absolute',
                left: 'var(--spacing-md)',
                top: '50%',
                transform: 'translateY(-50%)',
                pointerEvents: 'none'
              }}>
                <FaSearch style={{ width: '1rem', height: '1rem', color: 'var(--color-text-tertiary)' }} />
              </div>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search device name or MAC address..."
                style={{
                  width: '100%',
                  paddingLeft: '2.5rem',
                  paddingRight: 'var(--spacing-md)',
                  paddingTop: 'var(--spacing-sm)',
                  paddingBottom: 'var(--spacing-sm)',
                  border: '1px solid var(--color-border-primary)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-bg-primary)',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-sm)'
                }}
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={loading}
              className="button-responsive"
              style={{
                backgroundColor: 'var(--color-bg-tertiary)',
                color: 'var(--color-text-secondary)',
                border: '1px solid var(--color-border-primary)',
                cursor: 'pointer',
                fontWeight: '500',
                opacity: loading ? 0.5 : 1
              }}
            >
              Search
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: 'var(--spacing-2xl)' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 'var(--spacing-4xl)' }}>
            <div style={{
              display: 'inline-block',
              width: '2rem',
              height: '2rem',
              border: '2px solid var(--color-border-primary)',
              borderTop: '2px solid var(--color-accent-blue)',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }}></div>
            <div style={{
              marginTop: 'var(--spacing-sm)',
              fontSize: 'var(--text-sm)',
              color: 'var(--color-text-tertiary)'
            }}>
              Loading...
            </div>
          </div>
        ) : error ? (
          <div style={{ textAlign: 'center', padding: 'var(--spacing-4xl)' }}>
            <div style={{
              color: '#EF4444',
              fontSize: 'var(--text-sm)',
              fontWeight: '500',
              marginBottom: 'var(--spacing-sm)'
            }}>
              Error loading data
            </div>
            <div style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--text-sm)' }}>
              {error}
            </div>
          </div>
        ) : devices.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 'var(--spacing-4xl)' }}>
            <div style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--text-sm)' }}>
              {searchTerm ? 'No matching records found' : 'No known devices available'}
            </div>
          </div>
        ) : (
          <>
            {/* Card Grid - Using system color scheme */}
            <div style={{ display: 'grid', gap: 'var(--spacing-lg)' }}>
              {devices.map((device) => (
                <div
                  key={device.mac_address}
                  style={{
                    backgroundColor: 'var(--color-bg-tertiary)',
                    borderRadius: 'var(--radius-lg)',
                    border: '1px solid var(--color-border-primary)',
                    padding: 'var(--spacing-lg)',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                    e.currentTarget.style.borderColor = 'var(--color-accent-blue)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = 'none';
                    e.currentTarget.style.borderColor = 'var(--color-border-primary)';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-lg)' }}>
                        <div style={{ flexShrink: 0 }}>
                          <code style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            padding: '0.375rem 0.625rem',
                            borderRadius: 'var(--radius-md)',
                            fontSize: 'var(--text-sm)',
                            fontFamily: 'monospace',
                            backgroundColor: 'var(--color-bg-secondary)',
                            color: 'var(--color-text-primary)',
                            border: '1px solid var(--color-border-secondary)'
                          }}>
                            {device.mac_address}
                          </code>
                        </div>
                        
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
                            <h4 style={{
                              fontSize: 'var(--text-sm)',
                              fontWeight: '500',
                              color: 'var(--color-text-primary)',
                              margin: 0,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}>
                              {device.device_name}
                            </h4>
                            {getStatusBadge(device.device_type)}
                          </div>
                          
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 'var(--spacing-md)',
                            marginTop: '0.25rem'
                          }}>
                            <span style={{
                              fontSize: 'var(--text-xs)',
                              color: 'var(--color-text-tertiary)'
                            }}>
                              Vendor: {device.vendor}
                            </span>
                            
                            {device.notes && (
                              <span style={{
                                fontSize: 'var(--text-xs)',
                                color: 'var(--color-text-tertiary)',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                                maxWidth: '200px'
                              }}>
                                Notes: {device.notes}
                              </span>
                            )}
                          </div>
                          
                          {device.created_at && (
                            <p style={{
                              fontSize: 'var(--text-xs)',
                              color: 'var(--color-text-tertiary)',
                              margin: '0.25rem 0 0 0'
                            }}>
                              Created: {new Date(device.created_at).toLocaleDateString('en-US', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    {/* Action Buttons */}
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: 'var(--spacing-sm)', 
                      marginLeft: 'var(--spacing-lg)' 
                    }}>
                      <button
                        onClick={() => handleEdit(device)}
                        disabled={isSubmitting}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          padding: 'var(--spacing-sm)',
                          border: 'none',
                          borderRadius: '50%',
                          color: 'var(--color-accent-blue)',
                          backgroundColor: 'transparent',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                          opacity: isSubmitting ? 0.5 : 1
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'transparent';
                        }}
                        title="Edit"
                      >
                        <FaEdit style={{ width: '1rem', height: '1rem' }} />
                      </button>
                      
                      <button
                        onClick={() => handleDeleteClick(device)}
                        disabled={isSubmitting}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          padding: 'var(--spacing-sm)',
                          border: 'none',
                          borderRadius: '50%',
                          color: '#DC2626',
                          backgroundColor: 'transparent',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                          opacity: isSubmitting ? 0.5 : 1
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = 'rgba(220, 38, 38, 0.1)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'transparent';
                        }}
                        title="Delete"
                      >
                        <FaTrash style={{ width: '1rem', height: '1rem' }} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination - Fixed format */}
            {totalPages > 1 && (
              <div style={{
                marginTop: 'var(--spacing-2xl)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderTop: '1px solid var(--color-border-primary)',
                paddingTop: 'var(--spacing-lg)',
                gap: 'var(--spacing-md)'
              }}>
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage <= 1}
                  className="button-responsive"
                  style={{
                    backgroundColor: 'var(--color-bg-tertiary)',
                    color: 'var(--color-text-secondary)',
                    border: '1px solid var(--color-border-primary)',
                    cursor: currentPage <= 1 ? 'not-allowed' : 'pointer',
                    fontWeight: '500',
                    opacity: currentPage <= 1 ? 0.5 : 1
                  }}
                >
                  Previous
                </button>
                
                <span style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--color-text-primary)',
                  fontWeight: '500',
                  minWidth: '60px',
                  textAlign: 'center'
                }}>
                  {currentPage} / {totalPages}
                </span>
                
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage >= totalPages}
                  className="button-responsive"
                  style={{
                    backgroundColor: 'var(--color-bg-tertiary)',
                    color: 'var(--color-text-secondary)',
                    border: '1px solid var(--color-border-primary)',
                    cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer',
                    fontWeight: '500',
                    opacity: currentPage >= totalPages ? 0.5 : 1
                  }}
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Custom Delete Confirmation Modal */}
      <ConfirmDeleteModal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setDeviceToDelete(null);
        }}
        onConfirm={handleDeleteConfirm}
        deviceName={deviceToDelete?.device_name || ''}
        macAddress={deviceToDelete?.mac_address || ''}
      />

      {/* Add Modal */}
      <KnownDeviceEditModal
        isOpen={isAddModalOpen}
        onClose={() => {
          setIsAddModalOpen(false);
          setEditingDevice(null);
        }}
        onSave={handleSaveDevice}
        initialData={null}
        isLoading={isSubmitting}
      />

      {/* Edit Modal */}
      <KnownDeviceEditModal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditingDevice(null);
        }}
        onSave={handleSaveDevice}
        initialData={editingDevice ? {
          mac_address: editingDevice.mac_address,
          device_name: editingDevice.device_name,
          device_type: editingDevice.device_type,
          vendor: editingDevice.vendor,
          notes: editingDevice.notes
        } : null}
        isLoading={isSubmitting}
      />
    </div>
  );
};

export default KnownDevicesTable; 