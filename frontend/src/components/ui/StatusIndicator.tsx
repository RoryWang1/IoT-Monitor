import React from 'react';

interface StatusIndicatorProps {
  status: 'active' | 'inactive' | 'unknown' | 'online' | 'offline' | 'error' | 'warning';
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  color?: string;
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ 
  status, 
  size = 'md',
  showText = true,
  color 
}) => {
  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'active':
      case 'online':
        return {
          color: color || '#10B981',
          text: status === 'active' ? 'Active' : 'Online',
          bgColor: 'rgba(16, 185, 129, 0.1)'
        };
      case 'inactive':
      case 'offline':
        return {
          color: color || '#EF4444',
          text: status === 'inactive' ? 'Inactive' : 'Offline',
          bgColor: 'rgba(239, 68, 68, 0.1)'
        };

      case 'error':
        return {
          color: color || '#EF4444',
          text: 'Error',
          bgColor: 'rgba(239, 68, 68, 0.1)'
        };
      case 'warning':
        return {
          color: color || '#F59E0B',
          text: 'Warning',
          bgColor: 'rgba(245, 158, 11, 0.1)'
        };
      default:
        return {
          color: color || '#6B7280',
          text: 'Unknown',
          bgColor: 'rgba(107, 114, 128, 0.1)'
        };
    }
  };

  const sizeMap = {
    sm: { dot: 6, text: 12, padding: '2px 6px' },
    md: { dot: 8, text: 14, padding: '4px 8px' },
    lg: { dot: 10, text: 16, padding: '6px 12px' }
  };

  const config = getStatusConfig(status);
  const sizeConfig = sizeMap[size];

  if (!showText) {
    return (
      <div style={{
        width: `${sizeConfig.dot}px`,
        height: `${sizeConfig.dot}px`,
        borderRadius: '50%',
        backgroundColor: config.color
      }} />
    );
  }

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      backgroundColor: config.bgColor,
      padding: sizeConfig.padding,
      borderRadius: '12px',
      border: `1px solid ${config.color}20`
    }}>
      <div style={{
        width: `${sizeConfig.dot}px`,
        height: `${sizeConfig.dot}px`,
        borderRadius: '50%',
        backgroundColor: config.color
      }} />
      <span style={{
        color: config.color,
        fontSize: `${sizeConfig.text}px`,
        fontWeight: 'bold'
      }}>
        {config.text}
      </span>
    </div>
  );
};

export default StatusIndicator; 