import React, { useState, useEffect } from 'react';
import { apiClient } from '../../services/apiClient';

interface Timezone {
  name: string;
  display: string;
}

interface TimezoneInfo {
  timezone: string;
  currentTime: string;
  currentTimeDisplay: string;
  utcOffset: string;
  isDst: boolean;
}

interface TimezoneSelectorProps {
  experimentId: string;
  className?: string;
  onTimezoneChange?: (timezone: string) => void;
}

const TimezoneSelector: React.FC<TimezoneSelectorProps> = ({
  experimentId,
  className = '',
  onTimezoneChange
}) => {
  const [timezones, setTimezones] = useState<Timezone[]>([]);
  const [currentTimezone, setCurrentTimezone] = useState<TimezoneInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load supported timezones
  useEffect(() => {
    const loadTimezones = async () => {
      try {
        const response = await apiClient.get<{ supported_timezones?: string[] }>('/api/experiments/timezones');
        // Get the list of time zones from the correct fields and add null value checks
        const timezoneList = response.supported_timezones || [];
        if (timezoneList.length === 0) {
          console.warn('No timezones returned from API');
          setError('No timezones available');
          return;
        }
        
        // Convert string array to Timezone objects - only select common timezones
        const commonTimezones = [
          'UTC',
          'Europe/London', 
          'America/New_York',
          'Asia/Shanghai',
          'Europe/Paris'
        ];
        
        const timezoneObjects: Timezone[] = commonTimezones
          .filter(tz => timezoneList.includes(tz))
          .map(tz => ({
            name: tz,
            display: tz === 'UTC' ? 'UTC' : tz.replace('_', ' ')
          }));
          
        setTimezones(timezoneObjects);
      } catch (err) {
        console.error('Failed to load timezones:', err);
        setError('Failed to load timezones');
      }
    };

    loadTimezones();
  }, []);

  // Load current timezone for experiment
  useEffect(() => {
    const loadCurrentTimezone = async () => {
      if (!experimentId) return;

      try {
        setLoading(true);
        const response = await apiClient.get<TimezoneInfo>(`/api/experiments/${experimentId}/timezone`);
        setCurrentTimezone(response);
      } catch (err) {
        console.error('Failed to load current timezone:', err);
        setError('Failed to load current timezone');
      } finally {
        setLoading(false);
      }
    };

    loadCurrentTimezone();
  }, [experimentId]);

  const handleTimezoneChange = async (newTimezone: string) => {
    if (!experimentId || newTimezone === currentTimezone?.timezone) return;

    try {
      setLoading(true);
      setError(null);

      await apiClient.put(`/api/experiments/${experimentId}/timezone`, {
        timezone: newTimezone
      });

      // Always reload timezone info after successful update
      const updatedInfo = await apiClient.get<TimezoneInfo>(`/api/experiments/${experimentId}/timezone`);
      setCurrentTimezone(updatedInfo);
      
      // Notify parent component
      onTimezoneChange?.(newTimezone);
    } catch (err) {
      console.error('Failed to update timezone:', err);
      setError('Failed to update timezone');
    } finally {
      setLoading(false);
    }
  };

  if (error) {
    return (
      <div className={`timezone-selector error ${className}`}>
        <span style={{ color: '#EF4444', fontSize: '12px' }}>
          {error}
        </span>
      </div>
    );
  }

  return (
    <div className={`timezone-selector ${className}`} style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      padding: '12px',
      backgroundColor: 'var(--color-bg-secondary)',
      borderRadius: '8px',
      border: '1px solid var(--color-border-primary)'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <label style={{
          fontSize: '12px',
          fontWeight: 'bold',
          color: '#9CA3AF',
          textTransform: 'uppercase'
        }}>
          Timezone
        </label>
        {loading && (
          <div style={{
            width: '16px',
            height: '16px',
            border: '2px solid var(--color-border-primary)',
            borderTop: '2px solid var(--color-accent-blue)',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }}></div>
        )}
      </div>

      <select
        value={currentTimezone?.timezone || ''}
        onChange={(e) => handleTimezoneChange(e.target.value)}
        disabled={loading || !timezones.length}
        style={{
          backgroundColor: 'var(--color-bg-primary)',
          border: '1px solid var(--color-border-primary)',
          borderRadius: '6px',
          padding: '8px 12px',
          color: '#E5E7EB',
          fontSize: '14px',
          cursor: loading ? 'not-allowed' : 'pointer',
          outline: 'none'
        }}
      >
        {timezones.map((tz) => (
          <option key={tz.name} value={tz.name}>
            {tz.display}
          </option>
        ))}
      </select>

      {currentTimezone && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
          marginTop: '8px',
          paddingTop: '8px',
          borderTop: '1px solid var(--color-border-secondary)'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '11px',
            color: '#9CA3AF'
          }}>
            <span>Current Time:</span>
            <span style={{ fontFamily: 'monospace', color: '#E5E7EB' }}>
              {currentTimezone.currentTimeDisplay}
            </span>
          </div>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '11px',
            color: '#9CA3AF'
          }}>
            <span>UTC Offset:</span>
            <span style={{ fontFamily: 'monospace', color: '#E5E7EB' }}>
              {currentTimezone.utcOffset}
            </span>
          </div>

        </div>
      )}
    </div>
  );
};

export default TimezoneSelector; 