/**
 * API Error Display Component
 * Shows user-friendly error messages with optional retry functionality
 */

import React from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { AlertCircle, RefreshCw, WifiOff, Clock, Server } from 'lucide-react';
import { type ApiError, ErrorCode } from '@/services/api-error';

export interface ApiErrorDisplayProps {
  error: ApiError;
  onRetry?: () => void;
  isRetrying?: boolean;
  className?: string;
}

/**
 * Get icon for error code
 */
function getErrorIcon(code: ErrorCode) {
  switch (code) {
    case ErrorCode.NETWORK_ERROR:
    case ErrorCode.CONNECTION_REFUSED:
      return WifiOff;
    case ErrorCode.TIMEOUT:
    case ErrorCode.GATEWAY_TIMEOUT:
      return Clock;
    case ErrorCode.SERVICE_UNAVAILABLE:
    case ErrorCode.INTERNAL_SERVER_ERROR:
    case ErrorCode.BAD_GATEWAY:
      return Server;
    default:
      return AlertCircle;
  }
}

/**
 * Get user-friendly error message
 */
function getUserFriendlyMessage(error: ApiError): string {
  switch (error.code) {
    case ErrorCode.NETWORK_ERROR:
      return 'Unable to connect to the server. Please check your internet connection.';
    case ErrorCode.CONNECTION_REFUSED:
      return 'The server is not responding. It may be offline or restarting.';
    case ErrorCode.TIMEOUT:
      return 'The request took too long to complete. The server may be busy.';
    case ErrorCode.SERVICE_UNAVAILABLE:
      return 'The service is temporarily unavailable. Please try again in a few moments.';
    case ErrorCode.INTERNAL_SERVER_ERROR:
      return 'The server encountered an error. This has been logged and will be investigated.';
    case ErrorCode.TOO_MANY_REQUESTS:
      return 'Too many requests. Please wait a moment before trying again.';
    case ErrorCode.UNAUTHORIZED:
      return 'You need to be authenticated to access this resource.';
    case ErrorCode.FORBIDDEN:
      return 'You don\'t have permission to access this resource.';
    case ErrorCode.NOT_FOUND:
      return 'The requested resource was not found.';
    default:
      return error.message || 'An unexpected error occurred.';
  }
}

/**
 * Get error title based on error code
 */
function getErrorTitle(error: ApiError): string {
  if (error.retryable) {
    return 'Connection Issue';
  }
  
  switch (error.code) {
    case ErrorCode.UNAUTHORIZED:
    case ErrorCode.FORBIDDEN:
      return 'Access Denied';
    case ErrorCode.NOT_FOUND:
      return 'Not Found';
    case ErrorCode.VALIDATION_ERROR:
    case ErrorCode.BAD_REQUEST:
      return 'Invalid Request';
    default:
      return 'Error';
  }
}

/**
 * Component to display API errors with retry functionality
 */
export function ApiErrorDisplay({
  error,
  onRetry,
  isRetrying = false,
  className = '',
}: ApiErrorDisplayProps) {
  const Icon = getErrorIcon(error.code);
  const message = getUserFriendlyMessage(error);
  const title = getErrorTitle(error);
  const showRetry = error.retryable && onRetry;
  
  return (
    <Alert variant="destructive" className={className}>
      <Icon className="h-4 w-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="mt-2">
        <div className="flex flex-col gap-3">
          <p>{message}</p>
          
          {error.statusCode && (
            <p className="text-xs opacity-75">
              Error Code: {error.code} (HTTP {error.statusCode})
            </p>
          )}
          
          {showRetry && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                disabled={isRetrying}
                className="bg-background"
              >
                {isRetrying ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Retrying...
                  </>
                ) : (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Retry
                  </>
                )}
              </Button>
              <p className="text-xs opacity-75">
                This error may be temporary
              </p>
            </div>
          )}
        </div>
      </AlertDescription>
    </Alert>
  );
}

/**
 * Compact inline error display (for smaller spaces)
 */
export function ApiErrorInline({
  error,
  onRetry,
  isRetrying = false,
  className = '',
}: ApiErrorDisplayProps) {
  const message = getUserFriendlyMessage(error);
  const showRetry = error.retryable && onRetry;
  
  return (
    <div className={`flex items-center justify-between p-3 rounded-md bg-destructive/10 border border-destructive/20 ${className}`}>
      <div className="flex items-center gap-2 flex-1">
        <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0" />
        <p className="text-sm text-destructive">{message}</p>
      </div>
      
      {showRetry && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onRetry}
          disabled={isRetrying}
          className="ml-2 flex-shrink-0"
        >
          {isRetrying ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
        </Button>
      )}
    </div>
  );
}

/**
 * Empty state with error (for when data fails to load)
 */
export function ApiErrorEmptyState({
  error,
  onRetry,
  isRetrying = false,
  title = 'Failed to Load',
  className = '',
}: ApiErrorDisplayProps & { title?: string }) {
  const Icon = getErrorIcon(error.code);
  const message = getUserFriendlyMessage(error);
  const showRetry = error.retryable && onRetry;
  
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center ${className}`}>
      <div className="rounded-full bg-destructive/10 p-3 mb-4">
        <Icon className="h-8 w-8 text-destructive" />
      </div>
      
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground mb-4 max-w-md">
        {message}
      </p>
      
      {showRetry && (
        <Button
          variant="default"
          onClick={onRetry}
          disabled={isRetrying}
        >
          {isRetrying ? (
            <>
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              Retrying...
            </>
          ) : (
            <>
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </>
          )}
        </Button>
      )}
      
      {error.statusCode && (
        <p className="text-xs text-muted-foreground mt-4">
          Error: {error.code} {error.statusCode ? `(HTTP ${error.statusCode})` : ''}
        </p>
      )}
    </div>
  );
}
