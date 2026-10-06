/**
 * Comprehensive error handling types for API operations
 */

export enum ErrorCode {
  // Network errors
  NETWORK_ERROR = 'NETWORK_ERROR',
  TIMEOUT = 'TIMEOUT',
  CONNECTION_REFUSED = 'CONNECTION_REFUSED',
  
  // HTTP errors
  BAD_REQUEST = 'BAD_REQUEST',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  NOT_FOUND = 'NOT_FOUND',
  CONFLICT = 'CONFLICT',
  TOO_MANY_REQUESTS = 'TOO_MANY_REQUESTS',
  INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR',
  BAD_GATEWAY = 'BAD_GATEWAY',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',
  GATEWAY_TIMEOUT = 'GATEWAY_TIMEOUT',
  
  // Application errors
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  PARSE_ERROR = 'PARSE_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
}

export interface ApiError {
  code: ErrorCode;
  message: string;
  retryable: boolean;
  statusCode?: number;
  details?: Record<string, unknown>;
  timestamp: string;
}

export type ApiResult<T> = 
  | { success: true; data: T }
  | { success: false; error: ApiError };

/**
 * Determine if an HTTP status code indicates a retryable error
 */
export function isRetryableStatusCode(status: number): boolean {
  // Retry on:
  // - 408 Request Timeout
  // - 429 Too Many Requests (rate limited)
  // - 500 Internal Server Error
  // - 502 Bad Gateway
  // - 503 Service Unavailable
  // - 504 Gateway Timeout
  return status === 408 || status === 429 || (status >= 500 && status < 600);
}

/**
 * Map HTTP status code to ErrorCode
 */
export function statusCodeToErrorCode(status: number): ErrorCode {
  switch (status) {
    case 400:
      return ErrorCode.BAD_REQUEST;
    case 401:
      return ErrorCode.UNAUTHORIZED;
    case 403:
      return ErrorCode.FORBIDDEN;
    case 404:
      return ErrorCode.NOT_FOUND;
    case 408:
      return ErrorCode.TIMEOUT;
    case 409:
      return ErrorCode.CONFLICT;
    case 429:
      return ErrorCode.TOO_MANY_REQUESTS;
    case 500:
      return ErrorCode.INTERNAL_SERVER_ERROR;
    case 502:
      return ErrorCode.BAD_GATEWAY;
    case 503:
      return ErrorCode.SERVICE_UNAVAILABLE;
    case 504:
      return ErrorCode.GATEWAY_TIMEOUT;
    default:
      return ErrorCode.UNKNOWN_ERROR;
  }
}

/**
 * Create an ApiError from various error sources
 */
export function createApiError(
  error: unknown,
  context?: { endpoint?: string; method?: string }
): ApiError {
  const timestamp = new Date().toISOString();
  
  // Handle AbortError (timeout)
  if (error instanceof Error && error.name === 'AbortError') {
    return {
      code: ErrorCode.TIMEOUT,
      message: 'Request timeout - the server did not respond in time',
      retryable: true,
      timestamp,
      details: context,
    };
  }
  
  // Handle TypeError (network error)
  if (error instanceof TypeError) {
    // TypeError often indicates network issues like CORS, connection refused, etc.
    const message = error.message.toLowerCase();
    if (message.includes('failed to fetch') || message.includes('network')) {
      return {
        code: ErrorCode.NETWORK_ERROR,
        message: 'Network error - unable to reach the server. Please check your connection.',
        retryable: true,
        timestamp,
        details: context,
      };
    }
  }
  
  // Handle HTTP errors with status codes
  if (typeof error === 'object' && error !== null && 'status' in error) {
    const status = (error as { status: number }).status;
    const code = statusCodeToErrorCode(status);
    const retryable = isRetryableStatusCode(status);
    
    let message = `HTTP ${status}`;
    if ('statusText' in error) {
      message += `: ${(error as { statusText: string }).statusText}`;
    }
    
    return {
      code,
      message,
      retryable,
      statusCode: status,
      timestamp,
      details: context,
    };
  }
  
  // Handle Error instances
  if (error instanceof Error) {
    return {
      code: ErrorCode.UNKNOWN_ERROR,
      message: error.message || 'An unknown error occurred',
      retryable: false,
      timestamp,
      details: context,
    };
  }
  
  // Handle string errors
  if (typeof error === 'string') {
    return {
      code: ErrorCode.UNKNOWN_ERROR,
      message: error,
      retryable: false,
      timestamp,
      details: context,
    };
  }
  
  // Fallback for unknown error types
  return {
    code: ErrorCode.UNKNOWN_ERROR,
    message: 'An unknown error occurred',
    retryable: false,
    timestamp,
    details: { ...context, originalError: String(error) },
  };
}

/**
 * Type guard to check if a result is an error
 */
export function isApiError<T>(result: ApiResult<T>): result is { success: false; error: ApiError } {
  return !result.success;
}

/**
 * Extract data from ApiResult, throwing on error
 */
export function unwrapResult<T>(result: ApiResult<T>): T {
  if (result.success) {
    return result.data;
  }
  throw new Error(result.error.message);
}
