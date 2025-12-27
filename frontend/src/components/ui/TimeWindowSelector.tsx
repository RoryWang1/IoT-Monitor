import React from 'react';

export interface TimeWindow {
  value: string;
  label: string;
  description: string;
}

export const TIME_WINDOWS: TimeWindow[] = [
  { value: 'auto', label: 'Auto', description: 'Automatically adjust to data time range' },
  { value: '1h', label: 'Last 1 Hour', description: 'Real-time data from the past hour' },
  { value: '2h', label: 'Last 2 Hours', description: 'Recent activity over 2 hours' },
  { value: '6h', label: 'Last 6 Hours', description: 'Recent activity over 6 hours' },
  { value: '12h', label: 'Last 12 Hours', description: 'Half-day activity overview' },
  { value: '24h', label: 'Last 24 Hours', description: 'Full day activity analysis' },
  { value: '48h', label: 'Last 48 Hours', description: 'Two-day trend comparison' }
];

interface TimeWindowSelectorProps {
  selectedWindow: string;
  onWindowChange: (window: string) => void;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showDescription?: boolean;
}

const TimeWindowSelector: React.FC<TimeWindowSelectorProps> = ({
  selectedWindow,
  onWindowChange,
  className = '',
  size = 'md',
  showDescription = false
}) => {
  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-2',
    lg: 'text-base px-4 py-3'
  };

  const selectedWindowData = TIME_WINDOWS.find(w => w.value === selectedWindow);

  return (
    <div className={`time-window-selector ${className}`}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--spacing-sm)',
        backgroundColor: 'var(--color-bg-primary)',
        padding: 'var(--spacing-xs)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--color-border-primary)',
        flexWrap: 'wrap'
      }}>
        {TIME_WINDOWS.map((window) => (
          <button
            key={window.value}
            onClick={() => onWindowChange(window.value)}
            className={sizeClasses[size]}
            style={{
              backgroundColor: selectedWindow === window.value 
                ? 'var(--color-accent-blue)' 
                : 'transparent',
              color: selectedWindow === window.value 
                ? 'var(--color-text-primary)' 
                : 'var(--color-text-secondary)',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              fontWeight: selectedWindow === window.value ? '600' : '500',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              whiteSpace: 'nowrap',
              minWidth: 'fit-content'
            }}
            onMouseEnter={(e) => {
              if (selectedWindow !== window.value) {
                e.currentTarget.style.backgroundColor = 'var(--color-bg-secondary)';
              }
            }}
            onMouseLeave={(e) => {
              if (selectedWindow !== window.value) {
                e.currentTarget.style.backgroundColor = 'transparent';
              }
            }}
            title={window.description}
          >
            {window.label}
          </button>
        ))}
      </div>
      
      {showDescription && selectedWindowData && (
        <div style={{
          marginTop: 'var(--spacing-sm)',
          padding: 'var(--spacing-sm)',
          backgroundColor: 'var(--color-bg-secondary)',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--color-border-primary)'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--spacing-xs)'
          }}>
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: 'var(--color-accent-green)',
              animation: 'pulse 2s infinite'
            }}></div>
            <span className="text-responsive-xs" style={{
              color: 'var(--color-text-secondary)',
              fontWeight: '500'
            }}>
              {selectedWindowData.description}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimeWindowSelector; 