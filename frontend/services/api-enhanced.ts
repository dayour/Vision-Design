/**
 * Enhanced API error handling - Export index
 * 
 * Import from here for all error handling functionality:
 * import { apiClient, isApiError, logger } from '@/services/api-enhanced';
 */

// Error types and utilities
export {
  ErrorCode,
  type ApiError,
  type ApiResult,
  isRetryableStatusCode,
  statusCodeToErrorCode,
  createApiError,
  isApiError,
  unwrapResult,
} from './api-error';

// API client with full error handling
export {
  apiRequest,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  apiPostFormData,
  createApiClient,
  apiClient,
  DEFAULT_API_OPTIONS,
  type ApiClientOptions,
} from './api-client';

// Retry mechanism
export {
  withRetry,
  fetchWithRetry,
  fetchWithTimeout,
  type RetryOptions,
} from './retry';

// Circuit breaker
export {
  CircuitBreaker,
  CircuitState,
  circuitBreakerRegistry,
  type CircuitBreakerOptions,
} from './circuit-breaker';

// Structured logging
export {
  logger,
  Logger,
  LogLevel,
  type LogContext,
  type LogEntry,
} from './logger';

// Backward compatibility wrappers
export {
  fetchFolders,
  fetchFoldersSafe,
  fetchGalleryImages,
  fetchGalleryImagesSafe,
  fetchGalleryVideos,
  fetchGalleryVideosSafe,
  checkHealth,
  checkHealthSafe,
} from './api-compat';

// Re-export types from api.ts
export { MediaType, API_BASE_URL } from './api';
export type { GalleryResponse, FolderHierarchy, GalleryItem } from './api';
