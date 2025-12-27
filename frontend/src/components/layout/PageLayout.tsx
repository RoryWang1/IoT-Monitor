import React from 'react';

interface PageLayoutProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  breadcrumb?: React.ReactNode;
}

const PageLayout: React.FC<PageLayoutProps> = ({ 
  children, 
  title, 
  subtitle, 
  actions,
  breadcrumb 
}) => {
  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--color-bg-primary)',
      padding: 'var(--spacing-2xl)'
    }}>
      <div className="responsive-container">
        {/* Breadcrumb */}
        {breadcrumb && (
          <div style={{ marginBottom: 'var(--spacing-lg)' }}>
            {breadcrumb}
          </div>
        )}

        {/* Header */}
        {(title || actions) && (
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: 'var(--spacing-3xl)',
            flexWrap: 'wrap',
            gap: 'var(--spacing-lg)'
          }}>
            <div style={{ flex: '1', minWidth: '0' }}>
              {title && (
                <h1 className="text-responsive-3xl" style={{
                  color: 'var(--color-text-primary)',
                  fontWeight: 'bold',
                  margin: '0 0 var(--spacing-sm) 0',
                  lineHeight: '1.2'
                }}>
                  {title}
                </h1>
              )}
              {subtitle && (
                <p className="text-responsive-base" style={{
                  color: 'var(--color-text-tertiary)',
                  margin: 0,
                  lineHeight: '1.5'
                }}>
                  {subtitle}
                </p>
              )}
            </div>
            {actions && (
              <div className="responsive-flex" style={{
                alignItems: 'center',
                flexShrink: 0
              }}>
                {actions}
              </div>
            )}
          </div>
        )}

        {/* Content */}
        <div className="animate-fadeIn">
          {children}
        </div>
      </div>
    </div>
  );
};

export default PageLayout; 