/**
 * Connection Status Component
 * Displays WebSocket connection status indicator
 */

import React, { useState, useEffect } from 'react';
import wsClient from '@/services/websocketClient';

interface ConnectionStatusProps {
  className?: string;
  showText?: boolean;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'inline';
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  className,
  showText = false,
  position = 'top-right'
}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

  useEffect(() => {
    // Only run WebSocket code in client environment
    if (typeof window === 'undefined') {
      return;
    }

    try {
      // Initial status
      setIsConnected(wsClient.isConnected());

      // Connection handler
      const connectionHandler = {
        onConnectionChange: (connected: boolean) => {
          setIsConnected(connected);
          setIsConnecting(!connected);
        }
      };

      // Subscribe to connection events
      const unsubscribe = wsClient.addConnectionHandler(connectionHandler);

      // Cleanup
      return () => {
        try {
          unsubscribe();
        } catch (error) {
          // Silent error handling
        }
      };
    } catch (error) {
      setIsConnected(false);
      setIsConnecting(false);
    }
  }, []);

  const getStatusColor = () => {
    if (isConnected) return 'var(--color-accent-green)';
    if (isConnecting) return 'var(--color-accent-yellow)';
    return 'var(--color-accent-red)';
  };

  const getStatusText = () => {
    if (isConnected) return 'Connected';
    if (isConnecting) return 'Connecting...';
    return 'Disconnected';
  };

  const getPositionStyles = () => {
    if (position === 'inline') return {};
    
    const baseStyles = {
      position: 'fixed' as const,
      zIndex: 1000,
      padding: 'var(--spacing-sm)',
    };

    switch (position) {
      case 'top-right':
        return { ...baseStyles, top: 'var(--spacing-md)', right: 'var(--spacing-md)' };
      case 'top-left':
        return { ...baseStyles, top: 'var(--spacing-md)', left: 'var(--spacing-md)' };
      case 'bottom-right':
        return { ...baseStyles, bottom: 'var(--spacing-md)', right: 'var(--spacing-md)' };
      case 'bottom-left':
        return { ...baseStyles, bottom: 'var(--spacing-md)', left: 'var(--spacing-md)' };
      default:
        return baseStyles;
    }
  };

  return (
    <div
      className={className}
      style={{
        ...getPositionStyles(),
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--spacing-xs)',
        backgroundColor: 'var(--color-bg-secondary)',
        border: '1px solid var(--color-border-primary)',
        borderRadius: 'var(--radius-full)',
        padding: showText ? 'var(--spacing-xs) var(--spacing-sm)' : 'var(--spacing-xs)',
        fontSize: 'var(--font-size-xs)',
        color: 'var(--color-text-secondary)',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
        transition: 'all 0.2s ease'
      }}
      title={getStatusText()}
    >
      {/* Status Indicator */}
      <div
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: getStatusColor(),
          transition: 'all 0.2s ease',
          animation: isConnecting ? 'pulse 1.5s infinite' : 'none'
        }}
      />
      
      {/* Status Text */}
      {showText && (
        <span style={{
          fontWeight: '500',
          whiteSpace: 'nowrap'
        }}>
          {getStatusText()}
        </span>
      )}

      {/* CSS Animation for pulse effect */}
      <style jsx>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.5;
            transform: scale(1.2);
          }
        }
      `}</style>
    </div>
  );
};

export default ConnectionStatus; 