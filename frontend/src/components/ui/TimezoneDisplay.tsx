import React from 'react';
import { useTimezone } from '../../hooks/useTimezone';

interface TimezoneDisplayProps {
  experimentId: string;
  className?: string;
  compact?: boolean;
}

const TimezoneDisplay: React.FC<TimezoneDisplayProps> = ({ 
  experimentId, 
  className = '', 
  compact = true 
}) => {
  const { timezoneInfo, loading, error } = useTimezone(experimentId);

  // Extract country/region name from display
  const getRegionName = (display: string): string => {
    if (!display || typeof display !== 'string') return 'Unknown';
    
    // Handle different display formats from API
    // Format: "London | BST | +01:00" or "Shanghai | CST | +08:00"
    if (display.includes(' | ')) {
      const parts = display.split(' | ');
      const region = parts[0];
      
      // Map region names to simplified versions
      if (region === 'London') return 'London';
      if (region === 'Shanghai') return 'Shanghai'; 
      if (region === 'New York') return 'New York';
      if (region === 'Paris') return 'Paris';
      if (region === 'UTC') return 'UTC';
      
      return region; // Return as-is for other regions
    }
    
    // Fallback for other formats
    if (display.includes('UTC')) return 'UTC';
    return display.split(' ')[0] || 'Unknown';
  };

  if (loading) {
    return (
      <div className={`text-xs text-gray-500 ${className}`}>
        Loading timezone...
      </div>
    );
  }

  if (error || !timezoneInfo) {
    return null; // Don't show anything if there's an error
  }

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-3 text-xs text-gray-300 ${className}`} style={{
        backgroundColor: 'var(--color-bg-secondary)',
        padding: '6px 12px',
        borderRadius: '6px',
        border: '1px solid var(--color-border-primary)'
      }}>
        <div className="flex items-center gap-2">
          <svg 
            className="w-4 h-4 text-blue-400" 
            fill="currentColor" 
            viewBox="0 0 20 20"
          >
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
          <div className="flex flex-col">
            <span className="font-medium text-white text-sm">
              {getRegionName(timezoneInfo.timezone_display)}
            </span>
            <div className="flex items-center gap-2 text-xs">
              <span className="font-mono text-blue-300">
                {timezoneInfo.timezone_abbr}
              </span>
              <span className="font-mono text-green-300">
                {timezoneInfo.utc_offset_display}
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`p-3 bg-gray-50 rounded-md border ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg 
            className="w-4 h-4 text-gray-600" 
            fill="currentColor" 
            viewBox="0 0 20 20"
          >
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
          <h4 className="text-sm font-medium text-gray-700">
            Timezone Information
          </h4>
        </div>
        
        {timezoneInfo.is_dst && (
          <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-full">
            DST Active
          </span>
        )}
      </div>
      
      <div className="mt-2 grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Region:</span>
          <div className="font-medium text-gray-900">
            {getRegionName(timezoneInfo.timezone_display)}
          </div>
        </div>
        
        <div>
          <span className="text-gray-500">Current Time:</span>
          <div className="font-mono text-gray-900">
            {timezoneInfo.current_time_chart}
          </div>
        </div>
        
        <div>
          <span className="text-gray-500">Timezone:</span>
          <div className="font-mono text-gray-900">
            {timezoneInfo.timezone_abbr} ({timezoneInfo.utc_offset_display})
          </div>
        </div>
        
        <div>
          <span className="text-gray-500">UTC Offset:</span>
          <div className="font-mono text-gray-900">
            {timezoneInfo.utc_offset_display}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TimezoneDisplay; 