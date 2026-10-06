/**
 * Retry mechanism with exponential backoff for API calls
 */

import { createApiError, type ApiError } from './api-error';
import { logger } from './logger';

export interface RetryOptions {
  maxAttempts?: number;
  initialDelayMs?: number;
  maxDelayMs?: number;
  backoffMultiplier?: number;
  timeoutMs?: number;
  shouldRetry?: (error: ApiError) => boolean;
}

const DEFAULT_RETRY_OPTIONS: Required<RetryOptions> = {
  maxAttempts: 3,
  initialDelayMs: 1000,
  maxDelayMs: 10000,
  backoffMultiplier: 2,
  timeoutMs: 15000,
  shouldRetry: (error: ApiError) => error.retryable,
};

/**
 * Sleep for a specified duration
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Calculate exponential backoff delay
 */
function calculateBackoffDelay(
  attempt: number,
  initialDelay: number,
  maxDelay: number,
  multiplier: number
): number {
  const delay = initialDelay * Math.pow(multiplier, attempt - 1);
  // Add jitter (±20%) to prevent thundering herd
  const jitter = delay * 0.2 * (Math.random() * 2 - 1);
  return Math.min(delay + jitter, maxDelay);
}

/**
 * Execute a function with retry logic and exponential backoff
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {},
  context?: { endpoint?: string; method?: string }
): Promise<T> {
  const opts = { ...DEFAULT_RETRY_OPTIONS, ...options };
  let lastError: ApiError | null = null;
  
  for (let attempt = 1; attempt <= opts.maxAttempts; attempt++) {
    try {
      logger.debug(`Attempt ${attempt}/${opts.maxAttempts}`, context);
      
      // Create abort controller for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), opts.timeoutMs);
      
      try {
        // Execute the function with abort signal if it accepts it
        const result = await fn();
        clearTimeout(timeoutId);
        
        if (attempt > 1) {
          logger.info(`Succeeded on attempt ${attempt}`, context);
        }
        
        return result;
      } catch (error) {
        clearTimeout(timeoutId);
        throw error;
      }
    } catch (error) {
      // Create structured error
      const apiError = createApiError(error, context);
      lastError = apiError;
      
      logger.warn(`Attempt ${attempt} failed: ${apiError.message}`, {
        ...context,
        errorCode: apiError.code,
        statusCode: apiError.statusCode,
        retryable: apiError.retryable,
      });
      
      // Check if we should retry
      const shouldRetry = opts.shouldRetry(apiError);
      const isLastAttempt = attempt === opts.maxAttempts;
      
      if (!shouldRetry || isLastAttempt) {
        logger.error(`Failed after ${attempt} attempt(s)`, {
          ...context,
          error: apiError,
        });
        throw error;
      }
      
      // Calculate backoff delay
      const delay = calculateBackoffDelay(
        attempt,
        opts.initialDelayMs,
        opts.maxDelayMs,
        opts.backoffMultiplier
      );
      
      logger.info(`Retrying in ${Math.round(delay)}ms...`, context);
      await sleep(delay);
    }
  }
  
  // This should never be reached, but TypeScript requires it
  throw lastError || new Error('Retry failed');
}

/**
 * Create a fetch wrapper with retry logic
 */
export async function fetchWithRetry(
  url: string,
  init?: RequestInit,
  options?: RetryOptions
): Promise<Response> {
  const method = init?.method || 'GET';
  const context = { endpoint: url, method };
  
  return withRetry(
    async () => {
      logger.debug(`Fetching ${method} ${url}`, context);
      
      const response = await fetch(url, init);
      
      // Check if response is not ok and create appropriate error
      if (!response.ok) {
        const error = {
          status: response.status,
          statusText: response.statusText,
        };
        
        // Try to get error details from response body
        try {
          const text = await response.text();
          if (text) {
            logger.debug(`Error response body: ${text}`, context);
          }
        } catch {
          // Ignore error reading body
        }
        
        throw error;
      }
      
      return response;
    },
    options,
    context
  );
}

/**
 * Enhanced fetch with timeout and better error handling
 */
export async function fetchWithTimeout(
  url: string,
  init?: RequestInit,
  timeoutMs: number = 15000
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  
  try {
    const response = await fetch(url, {
      ...init,
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.text();
        if (errorData) {
          errorMessage += ` - ${errorData}`;
        }
      } catch {
        // Ignore error text parsing failures
      }
      throw new Error(errorMessage);
    }
    
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeoutMs}ms`);
    }
    throw error;
  }
}
