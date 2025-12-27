import React, { useState } from 'react';
import { useRouter } from 'next/router';
import VendorPatternsTable from './VendorPatternsTable';
import KnownDevicesTable from './KnownDevicesTable';
import { API_BASE_URL } from '../../../config/api';
import { ArrowLeftIcon, DownloadIcon, UploadIcon } from '../../ui/icons';

const ReferenceDataViewer: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'vendor-patterns' | 'known-devices'>('known-devices');
  const router = useRouter();

  const handleImportData = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,.csv';
    input.multiple = false;
    
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('data_type', activeTab);
        
        const response = await fetch(`${API_BASE_URL}/api/devices/reference/import`, {
          method: 'POST',
          body: formData
        });
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `Import failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        alert(`Import successful: ${result.imported_count} records imported`);
        
        // Refresh current tab
        window.location.reload();
        
      } catch (error) {
        console.error('Import failed:', error);
        alert(`Import failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    };
    
    input.click();
  };

  const handleExportData = async () => {
    try {
      const endpoint = activeTab === 'vendor-patterns' 
            ? `${API_BASE_URL}/api/devices/reference/vendor-patterns/export`
    : `${API_BASE_URL}/api/devices/reference/known-devices/export`;
        
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }
      
      // Get filename from response headers or create default
      const contentDisposition = response.headers.get('content-disposition');
      let filename = `${activeTab}-${new Date().toISOString().split('T')[0]}.json`;
      
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match) {
          filename = match[1];
        }
      }
      
      // Download file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Export failed:', error);
      alert(`Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleBackToDashboard = () => {
    router.push('/');
  };

  return (
    <div style={{ 
      minHeight: '100vh',
      backgroundColor: 'var(--color-bg-primary)',
      color: 'var(--color-text-primary)'
    }}>
      {/* Header with Navigation */}
      <div style={{
        backgroundColor: 'var(--color-bg-secondary)',
        borderBottom: '1px solid var(--color-border-primary)',
        padding: 'var(--spacing-xl) var(--spacing-2xl)'
      }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
          {/* Back to Dashboard and Action Buttons */}
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            marginBottom: 'var(--spacing-lg)'
          }}>
            <button
              onClick={handleBackToDashboard}
              className="button-responsive"
              style={{
                backgroundColor: 'var(--color-bg-tertiary)',
                color: 'var(--color-text-secondary)',
                border: '1px solid var(--color-border-primary)',
                cursor: 'pointer',
                fontWeight: '500',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 'var(--spacing-sm)'
              }}
            >
              <ArrowLeftIcon size={16} color="#6B7280" />
              Back to Dashboard
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
              <button
                onClick={handleImportData}
                className="button-responsive"
                style={{
                  backgroundColor: 'var(--color-accent-blue)',
                  color: 'var(--color-text-primary)',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: '500',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 'var(--spacing-sm)'
                }}
              >
                <UploadIcon size={16} color="white" />
                Import Data
              </button>
              
              <button
                onClick={handleExportData}
                className="button-responsive"
                style={{
                  backgroundColor: 'var(--color-accent-blue)',
                  color: 'var(--color-text-primary)',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: '500',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 'var(--spacing-sm)'
                }}
              >
                <DownloadIcon size={16} color="white" />
                Export Data
              </button>
            </div>
          </div>

          {/* Page Title */}
          <div style={{ marginBottom: 'var(--spacing-xl)' }}>
            <h1 style={{
              fontSize: 'var(--text-2xl)',
              fontWeight: '700',
              color: 'var(--color-text-primary)',
              margin: '0 0 var(--spacing-sm) 0'
            }}>
              Reference Data Management
            </h1>
            <p style={{
              fontSize: 'var(--text-base)',
              color: 'var(--color-text-tertiary)',
              margin: 0
            }}>
              Manage vendor patterns and known device information for accurate IoT device identification
            </p>
          </div>

          {/* Tab Navigation - Modern Style */}
          <div style={{
            display: 'inline-flex',
            backgroundColor: 'var(--color-bg-tertiary)',
            border: '1px solid var(--color-border-primary)',
            borderRadius: 'var(--radius-lg)',
            padding: '0.25rem',
            gap: '0.25rem'
          }}>
            <button
              onClick={() => setActiveTab('known-devices')}
              style={{
                position: 'relative',
                padding: 'var(--spacing-md) var(--spacing-lg)',
                borderRadius: 'var(--radius-md)',
                border: 'none',
                fontSize: 'var(--text-sm)',
                fontWeight: '500',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                backgroundColor: activeTab === 'known-devices' 
                  ? 'var(--color-accent-blue)' 
                  : 'transparent',
                color: activeTab === 'known-devices' 
                  ? 'var(--color-text-primary)' 
                  : 'var(--color-text-secondary)',
                minWidth: '140px'
              }}
            >
              Known Devices
            </button>
            
            <button
              onClick={() => setActiveTab('vendor-patterns')}
              style={{
                position: 'relative',
                padding: 'var(--spacing-md) var(--spacing-lg)',
                borderRadius: 'var(--radius-md)',
                border: 'none',
                fontSize: 'var(--text-sm)',
                fontWeight: '500',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                backgroundColor: activeTab === 'vendor-patterns' 
                  ? 'var(--color-accent-blue)' 
                  : 'transparent',
                color: activeTab === 'vendor-patterns' 
                  ? 'var(--color-text-primary)' 
                  : 'var(--color-text-secondary)',
                minWidth: '140px'
              }}
            >
              Vendor Patterns
            </button>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div style={{
        maxWidth: '1400px',
        margin: '0 auto',
        padding: 'var(--spacing-2xl)'
      }}>
        {activeTab === 'vendor-patterns' ? (
          <VendorPatternsTable />
        ) : (
          <KnownDevicesTable />
        )}
      </div>
    </div>
  );
};

export default ReferenceDataViewer; 