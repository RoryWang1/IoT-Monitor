import React from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

const Modal: React.FC<ModalProps> = ({ 
  isOpen, 
  onClose, 
  title, 
  children, 
  size = 'md' 
}) => {
  const sizeMap = {
    sm: 'var(--container-xs)',
    md: 'var(--container-sm)',
    lg: 'var(--container-md)',
    xl: 'var(--container-lg)'
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
      padding: 'var(--spacing-lg)',
      backdropFilter: 'blur(4px)'
    }}>
      <div 
        className="modal-responsive animate-fadeIn"
        style={{
          backgroundColor: 'var(--color-bg-secondary)',
          borderRadius: 'var(--radius-xl)',
          border: '1px solid var(--color-border-primary)',
          maxWidth: sizeMap[size],
          width: '100%',
          maxHeight: '90vh',
          overflow: 'auto',
          boxShadow: 'var(--shadow-xl)',
          position: 'relative'
        }}
      >
        {/* Header */}
        {title && (
          <div style={{
            padding: 'var(--spacing-xl) var(--spacing-2xl)',
            borderBottom: '1px solid var(--color-border-primary)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            position: 'sticky',
            top: 0,
            backgroundColor: 'var(--color-bg-secondary)',
            zIndex: 1
          }}>
            <h2 className="text-responsive-xl" style={{
              color: 'var(--color-text-primary)',
              fontWeight: 'bold',
              margin: 0,
              lineHeight: '1.3'
            }}>
              {title}
            </h2>
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--color-text-tertiary)',
                cursor: 'pointer',
                padding: 'var(--spacing-sm)',
                borderRadius: 'var(--radius-md)',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 'var(--spacing-3xl)',
                height: 'var(--spacing-3xl)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-bg-tertiary)';
                e.currentTarget.style.color = 'var(--color-text-primary)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = 'var(--color-text-tertiary)';
              }}
              aria-label="Close modal"
            >
              <svg 
                width="20" 
                height="20" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2" 
                strokeLinecap="round" 
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        )}

        {/* Content */}
        <div style={{
          padding: title ? 'var(--spacing-2xl)' : 'var(--spacing-3xl)',
          color: 'var(--color-text-secondary)',
          lineHeight: '1.6'
        }}>
          {children}
        </div>
      </div>
    </div>
  );
};

export default Modal; 