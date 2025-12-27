/**
 * API Error Handler Component
 * Displays API error messages with retry functionality
 */

import React from 'react';
import Card from './Card';
import { WarningIcon } from './icons';

interface ApiError {
  message: string;
  status?: number;
  code?: string;
}

interface ApiErrorHandlerProps {
  error: ApiError | Error | string | null;
  onRetry?: () => void;
  onDismiss?: () => void;
  showRetry?: boolean;
  showDismiss?: boolean;
  className?: string;
}

const ApiErrorHandler: React.FC<ApiErrorHandlerProps> = ({
  error,
  onRetry,
  onDismiss,
  showRetry = true,
  showDismiss = false,
  className
}) => {
  if (!error) return null;

  const getErrorMessage = (error: ApiError | Error | string): string => {
    if (typeof error === 'string') {
      return error;
    }
    if (error instanceof Error) {
      return error.message;
    }
    return error.message || 'An unexpected error occurred';
  };

  const getErrorStatus = (error: ApiError | Error | string): number | undefined => {
    if (typeof error === 'object' && 'status' in error) {
      return error.status;
    }
    return undefined;
  };

  const getErrorTitle = (status?: number): string => {
    switch (status) {
      case 400:
        return 'Bad Request';
      case 401:
        return 'Unauthorized';
      case 403:
        return 'Forbidden';
      case 404:
        return 'Not Found';
      case 500:
        return 'Server Error';
      case 502:
        return 'Bad Gateway';
      case 503:
        return 'Service Unavailable';
      default:
        return 'Connection Error';
    }
  };

  const errorMessage = getErrorMessage(error);
  const errorStatus = getErrorStatus(error);
  const errorTitle = getErrorTitle(errorStatus);

  return (
    <Card 
      className={className}
      padding="lg" 
      style={{
        backgroundColor: 'var(--color-bg-error)',
        border: '1px solid var(--color-border-error)',
        borderRadius: 'var(--radius-md)'
      }}
    >
      <div style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 'var(--spacing-md)'
      }}>
        {/* Error Icon */}
        <div style={{
          color: 'var(--color-text-error)',
          fontSize: 'var(--font-size-xl)',
          lineHeight: 1,
          marginTop: '2px'
        }}>
          <WarningIcon size={20} color="#EF4444" />
        </div>

        {/* Error Content */}
        <div style={{ flex: 1 }}>
          <div style={{
            fontSize: 'var(--font-size-lg)',
            fontWeight: 'bold',
            color: 'var(--color-text-error)',
            marginBottom: 'var(--spacing-xs)'
          }}>
            {errorTitle}
            {errorStatus && (
              <span style={{
                fontSize: 'var(--font-size-sm)',
                fontWeight: 'normal',
                marginLeft: 'var(--spacing-xs)',
                opacity: 0.8
              }}>
                ({errorStatus})
              </span>
            )}
          </div>
          
          <div style={{
            fontSize: 'var(--font-size-md)',
            color: 'var(--color-text-secondary)',
            marginBottom: showRetry || showDismiss ? 'var(--spacing-lg)' : 0,
            lineHeight: 1.5
          }}>
            {errorMessage}
          </div>

          {/* Action Buttons */}
          {(showRetry || showDismiss) && (
            <div style={{
              display: 'flex',
              gap: 'var(--spacing-sm)',
              flexWrap: 'wrap'
            }}>
              {showRetry && onRetry && (
                <button
                  onClick={onRetry}
                  style={{
                    padding: 'var(--spacing-xs) var(--spacing-md)',
                    backgroundColor: 'var(--color-accent-blue)',
                    color: 'white',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: '500',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--color-accent-blue-hover)';
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--color-accent-blue)';
                  }}
                >
                  Retry
                </button>
              )}
              
              {showDismiss && onDismiss && (
                <button
                  onClick={onDismiss}
                  style={{
                    padding: 'var(--spacing-xs) var(--spacing-md)',
                    backgroundColor: 'transparent',
                    color: 'var(--color-text-secondary)',
                    border: '1px solid var(--color-border-primary)',
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: '500',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--color-bg-hover)';
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  Dismiss
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};

export default ApiErrorHandler; 