/**
 * Enhanced API client with retry, circuit breaker, and comprehensive error handling
 */

import { type ApiResult, createApiError } from './api-error';
import { fetchWithRetry, type RetryOptions } from './retry';
import { circuitBreakerRegistry } from './circuit-breaker';
import { logger } from './logger';

export interface ApiClientOptions {
  retry?: RetryOptions;
  circuitBreaker?: {
    enabled?: boolean;
    failureThreshold?: number;
    successThreshold?: number;
    timeout?: number;
  };
  timeout?: number;
}

/**
 * Make an API request with full error handling, retry, and circuit breaker
 */
export async function apiRequest<T>(
  url: string,
  init?: RequestInit,
  options?: ApiClientOptions
): Promise<ApiResult<T>> {
  const method = init?.method || 'GET';
  const endpoint = new URL(url).pathname;
  const context = {
    endpoint,
    method,
    requestId: logger.generateRequestId(),
  };
  
  try {
    logger.info(`API request started`, context);
    
    // Get circuit breaker for this endpoint
    const breaker = options?.circuitBreaker?.enabled !== false
      ? circuitBreakerRegistry.getBreaker(endpoint, options?.circuitBreaker)
      : null;
    
    // Execute request with circuit breaker (if enabled) and retry
    const response = await (breaker
      ? breaker.execute(
          () => fetchWithRetry(url, init, options?.retry),
          context
        )
      : fetchWithRetry(url, init, options?.retry));
    
    // Parse JSON response
    const data = await response.json();
    
    logger.info(`API request succeeded`, {
      ...context,
      status: response.status,
    });
    
    return { success: true, data };
  } catch (error) {
    // Create structured error
    const apiError = createApiError(error, context);
    
    logger.error(`API request failed`, {
      ...context,
      error: apiError,
    });
    
    return { success: false, error: apiError };
  }
}

/**
 * Make a GET request
 */
export async function apiGet<T>(
  url: string,
  options?: ApiClientOptions
): Promise<ApiResult<T>> {
  return apiRequest<T>(url, { method: 'GET' }, options);
}

/**
 * Make a POST request
 */
export async function apiPost<T>(
  url: string,
  body?: unknown,
  options?: ApiClientOptions
): Promise<ApiResult<T>> {
  const init: RequestInit = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  };
  
  return apiRequest<T>(url, init, options);
}

/**
 * Make a PUT request
 */
export async function apiPut<T>(
  url: string,
  body?: unknown,
  options?: ApiClientOptions
): Promise<ApiResult<T>> {
  const init: RequestInit = {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  };
  
  return apiRequest<T>(url, init, options);
}

/**
 * Make a DELETE request
 */
export async function apiDelete<T>(
  url: string,
  options?: ApiClientOptions
): Promise<ApiResult<T>> {
  return apiRequest<T>(url, { method: 'DELETE' }, options);
}

/**
 * Make a multipart form data request (for file uploads)
 */
export async function apiPostFormData<T>(
  url: string,
  formData: FormData,
  options?: ApiClientOptions
): Promise<ApiResult<T>> {
  const init: RequestInit = {
    method: 'POST',
    body: formData,
    // Don't set Content-Type header - browser will set it with boundary
  };
  
  return apiRequest<T>(url, init, options);
}

/**
 * Default API client options
 */
export const DEFAULT_API_OPTIONS: ApiClientOptions = {
  retry: {
    maxAttempts: 3,
    initialDelayMs: 1000,
    maxDelayMs: 10000,
    timeoutMs: 15000,
  },
  circuitBreaker: {
    enabled: true,
    failureThreshold: 5,
    successThreshold: 2,
    timeout: 60000,
  },
};

/**
 * Create an API client with default options
 */
export function createApiClient(baseOptions?: ApiClientOptions) {
  const options = { ...DEFAULT_API_OPTIONS, ...baseOptions };
  
  return {
    get: <T>(url: string, opts?: ApiClientOptions) =>
      apiGet<T>(url, { ...options, ...opts }),
    
    post: <T>(url: string, body?: unknown, opts?: ApiClientOptions) =>
      apiPost<T>(url, body, { ...options, ...opts }),
    
    put: <T>(url: string, body?: unknown, opts?: ApiClientOptions) =>
      apiPut<T>(url, body, { ...options, ...opts }),
    
    delete: <T>(url: string, opts?: ApiClientOptions) =>
      apiDelete<T>(url, { ...options, ...opts }),
    
    postFormData: <T>(url: string, formData: FormData, opts?: ApiClientOptions) =>
      apiPostFormData<T>(url, formData, { ...options, ...opts }),
  };
}

// Export default client instance
export const apiClient = createApiClient();
