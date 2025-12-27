import React, { useState, useEffect } from 'react';
import { FaEdit, FaTrash, FaPlus, FaSearch, FaSync } from 'react-icons/fa';
import VendorPatternEditModal from './VendorPatternEditModal';
import { VendorPattern, VendorPatternRequest } from '../../../types/reference';
import { API_BASE_URL } from '../../../config/api';

interface VendorPatternsTableProps {
  onDataChange?: () => void;
}

// Custom confirmation modal component
const ConfirmDeleteModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  patternName: string;
  vendorName: string;
}> = ({ isOpen, onClose, onConfirm, patternName, vendorName }) => {
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
          Are you sure you want to delete OUI pattern <strong style={{ color: 'var(--color-text-primary)' }}>&quot;{patternName}&quot;</strong> from <strong style={{ color: 'var(--color-text-primary)' }}>&quot;{vendorName}&quot;</strong>?
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

const VendorPatternsTable: React.FC<VendorPatternsTableProps> = ({ onDataChange }) => {
  const [patterns, setPatterns] = useState<VendorPattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingPattern, setEditingPattern] = useState<VendorPattern | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Delete confirmation modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [patternToDelete, setPatternToDelete] = useState<VendorPattern | null>(null);
  
  const itemsPerPage = 10;

  const fetchPatterns = async (page = 1, search = '') => {
    try {
      setLoading(true);
      setError(null);
      
      const offset = (page - 1) * itemsPerPage;
              let url = `${API_BASE_URL}/api/devices/reference/vendor-patterns?limit=${itemsPerPage}&offset=${offset}`;
      
      if (search.trim()) {
        url += `&vendor=${encodeURIComponent(search.trim())}`;
      }
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setPatterns(data || []);
      
      // Get total count for correct pagination
      if (page === 1) {
        try {
          const countUrl = search.trim() 
            ? `${API_BASE_URL}/api/devices/reference/vendor-patterns?limit=999999&vendor=${encodeURIComponent(search.trim())}`
            : `${API_BASE_URL}/api/devices/reference/vendor-patterns?limit=999999`;
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
      console.error('Failed to fetch patterns:', error);
      setError(error instanceof Error ? error.message : 'Failed to load vendor patterns');
      setPatterns([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatterns(currentPage, searchTerm);
  }, [currentPage, searchTerm]);

  const handleSearch = () => {
    setCurrentPage(1);
    fetchPatterns(1, searchTerm);
  };

  const handleRefresh = () => {
    setSearchTerm('');
    setCurrentPage(1);
    fetchPatterns(1, '');
  };

  const handleAdd = () => {
    setEditingPattern(null);
    setIsAddModalOpen(true);
  };

  const handleEdit = (pattern: VendorPattern) => {
    setEditingPattern(pattern);
    setIsEditModalOpen(true);
  };

  const handleDeleteClick = (pattern: VendorPattern) => {
    setPatternToDelete(pattern);
    setShowDeleteModal(true);
  };

  const handleDeleteConfirm = async () => {
    if (!patternToDelete) return;

    try {
      setIsSubmitting(true);
      
      const response = await fetch(
        `${API_BASE_URL}/api/devices/reference/vendor-patterns?oui_pattern=${encodeURIComponent(patternToDelete.oui_pattern)}`,
        { method: 'DELETE' }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      // Close modal and refresh data
      setShowDeleteModal(false);
      setPatternToDelete(null);
      await fetchPatterns(currentPage, searchTerm);
      
      if (onDataChange) {
        onDataChange();
      }

    } catch (error) {
      console.error('Failed to delete pattern:', error);
      alert(`Delete failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSavePattern = async (patternData: VendorPatternRequest) => {
    try {
      setIsSubmitting(true);
      
      let response;
      if (editingPattern) {
        // Update existing pattern
        response = await fetch(
          `${API_BASE_URL}/api/devices/reference/vendor-patterns?oui_pattern=${encodeURIComponent(editingPattern.oui_pattern)}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(patternData)
          }
        );
      } else {
        // Create new pattern
        response = await fetch(`${API_BASE_URL}/api/devices/reference/vendor-patterns`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patternData)
        });
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      // Close modals
      setIsAddModalOpen(false);
      setIsEditModalOpen(false);
      setEditingPattern(null);
      
      // Refresh data
      await fetchPatterns(currentPage, searchTerm);
      
      if (onDataChange) {
        onDataChange();
      }

    } catch (error) {
      console.error('Failed to save pattern:', error);
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

  const getStatusBadge = (category: string) => {
    const colors = {
      // Basic device types
      iot: { bg: '#3B82F6', text: '#DBEAFE' },
      smart_device: { bg: '#8B5CF6', text: '#F3E8FF' },
      mobile: { bg: '#06B6D4', text: '#CFFAFE' },
      computer: { bg: '#10B981', text: '#D1FAE5' },
      server: { bg: '#059669', text: '#D1FAE5' },
      
      // Network devices
      router: { bg: '#F59E0B', text: '#FEF3C7' },
      switch: { bg: '#EF4444', text: '#FEE2E2' },
      access_point: { bg: '#EC4899', text: '#FCE7F3' },
      network: { bg: '#7C3AED', text: '#EDE9FE' },
      
      // Smart devices
      camera: { bg: '#84CC16', text: '#ECFCCB' },
      'Smart Camera': { bg: '#84CC16', text: '#ECFCCB' },
      'Smart Light': { bg: '#F59E0B', text: '#FEF3C7' },
      'Smart Lock': { bg: '#DC2626', text: '#FECACA' },
      
      // Sensors and industrial devices
      sensor: { bg: '#14B8A6', text: '#CCFBF1' },
      'Industrial Sensor': { bg: '#0F766E', text: '#CCFBF1' },
      'Medical Device': { bg: '#DC2626', text: '#FECACA' },
      
      // Other device types
      printer: { bg: '#6366F1', text: '#E0E7FF' },
      storage: { bg: '#F97316', text: '#FED7AA' },
      entertainment: { bg: '#A855F7', text: '#F3E8FF' },
      security: { bg: '#DC2626', text: '#FECACA' },
      appliance: { bg: '#059669', text: '#D1FAE5' },
      consumer: { bg: '#0EA5E9', text: '#E0F2FE' },
      test: { bg: '#6B7280', text: '#F3F4F6' },
      unknown: { bg: '#9CA3AF', text: '#F9FAFB' }
    };
    
    const color = colors[category as keyof typeof colors] || colors.unknown;
    
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
        {category}
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
                Vendor Pattern Management
              </h3>
              <p style={{
                fontSize: 'var(--text-sm)',
                color: 'var(--color-text-tertiary)',
                margin: '0.25rem 0 0 0'
              }}>
                MAC address OUI patterns and vendor mapping relationships ({patterns.length} records)
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
                Add Pattern
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
                placeholder="Search vendor name..."
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
        ) : patterns.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 'var(--spacing-4xl)' }}>
            <div style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--text-sm)' }}>
              {searchTerm ? 'No matching records found' : 'No vendor patterns available'}
            </div>
          </div>
        ) : (
          <>
            {/* Card Grid - Using system color scheme */}
            <div style={{ display: 'grid', gap: 'var(--spacing-lg)' }}>
              {patterns.map((pattern) => (
                <div
                  key={pattern.oui_pattern}
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
                            {pattern.oui_pattern}
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
                              {pattern.vendor_name}
                            </h4>
                            {getStatusBadge(pattern.device_category)}
                          </div>
                          
                          {pattern.created_at && (
                            <p style={{
                              fontSize: 'var(--text-xs)',
                              color: 'var(--color-text-tertiary)',
                              margin: '0.25rem 0 0 0'
                            }}>
                              Created: {new Date(pattern.created_at).toLocaleDateString('en-US', {
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
                        onClick={() => handleEdit(pattern)}
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
                        onClick={() => handleDeleteClick(pattern)}
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
          setPatternToDelete(null);
        }}
        onConfirm={handleDeleteConfirm}
        patternName={patternToDelete?.oui_pattern || ''}
        vendorName={patternToDelete?.vendor_name || ''}
      />

      {/* Add Modal */}
      <VendorPatternEditModal
        isOpen={isAddModalOpen}
        onClose={() => {
          setIsAddModalOpen(false);
          setEditingPattern(null);
        }}
        onSave={handleSavePattern}
        initialData={null}
        isLoading={isSubmitting}
      />

      {/* Edit Modal */}
      <VendorPatternEditModal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditingPattern(null);
        }}
        onSave={handleSavePattern}
        initialData={editingPattern ? {
          oui_pattern: editingPattern.oui_pattern,
          vendor_name: editingPattern.vendor_name,
          device_category: editingPattern.device_category
        } : null}
        isLoading={isSubmitting}
      />
    </div>
  );
};

export default VendorPatternsTable; 