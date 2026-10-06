/**
 * React hooks for API error handling
 */

import { useState, useCallback, useEffect } from 'react';
import type { ApiResult, ApiError } from '@/services/api-error';
import { ErrorCode } from '@/services/api-error';
import { logger } from '@/services/logger';

export interface UseApiRequestState<T> {
  data: T | null;
  error: ApiError | null;
  isLoading: boolean;
  isRetrying: boolean;
}

export interface UseApiRequestOptions {
  onSuccess?: (data: unknown) => void;
  onError?: (error: ApiError) => void;
  autoRetry?: boolean;
  autoRetryDelay?: number;
}

/**
 * Hook for handling API requests with automatic state management
 */
export function useApiRequest<T>(
  options: UseApiRequestOptions = {}
) {
  const [state, setState] = useState<UseApiRequestState<T>>({
    data: null,
    error: null,
    isLoading: false,
    isRetrying: false,
  });

  const execute = useCallback(
    async (apiCall: () => Promise<ApiResult<T>>) => {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      try {
        const result = await apiCall();

        if (result.success) {
          setState({
            data: result.data,
            error: null,
            isLoading: false,
            isRetrying: false,
          });

          if (options.onSuccess) {
            options.onSuccess(result.data);
          }
        } else {
          setState({
            data: null,
            error: result.error,
            isLoading: false,
            isRetrying: false,
          });

          if (options.onError) {
            options.onError(result.error);
          }

          logger.error('API request failed', {
            errorCode: result.error.code,
            errorMessage: result.error.message,
            retryable: result.error.retryable,
          });
        }
      } catch (error) {
        // This should not happen with proper ApiResult pattern, but just in case
        logger.error('Unexpected error in useApiRequest', { error });
        setState({
          data: null,
          error: {
            code: ErrorCode.UNKNOWN_ERROR,
            message: error instanceof Error ? error.message : 'Unknown error',
            retryable: false,
            timestamp: new Date().toISOString(),
          },
          isLoading: false,
          isRetrying: false,
        });
      }
    },
    [options]
  );

  const retry = useCallback(
    async (apiCall: () => Promise<ApiResult<T>>) => {
      setState(prev => ({ ...prev, isRetrying: true }));
      await execute(apiCall);
    },
    [execute]
  );

  const reset = useCallback(() => {
    setState({
      data: null,
      error: null,
      isLoading: false,
      isRetrying: false,
    });
  }, []);

  return {
    ...state,
    execute,
    retry,
    reset,
  };
}

/**
 * Hook for automatic API data fetching with dependencies
 */
export function useApiData<T>(
  apiCall: () => Promise<ApiResult<T>>,
  deps: React.DependencyList = [],
  options: UseApiRequestOptions = {}
) {
  const request = useApiRequest<T>(options);

  useEffect(() => {
    request.execute(apiCall);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  const retry = useCallback(() => {
    request.retry(apiCall);
  }, [apiCall, request]);

  return {
    ...request,
    retry,
  };
}

/**
 * Hook for polling API data at regular intervals
 */
export function useApiPolling<T>(
  apiCall: () => Promise<ApiResult<T>>,
  intervalMs: number = 5000,
  options: UseApiRequestOptions & { enabled?: boolean } = {}
) {
  const { enabled = true, ...requestOptions } = options;
  const request = useApiRequest<T>(requestOptions);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    // Initial fetch
    request.execute(apiCall);

    // Set up polling
    const intervalId = setInterval(() => {
      request.execute(apiCall);
    }, intervalMs);

    return () => clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, intervalMs]);

  const retry = useCallback(() => {
    request.retry(apiCall);
  }, [apiCall, request]);

  return {
    ...request,
    retry,
  };
}

/**
 * Hook for managing multiple API requests
 */
export function useApiRequests() {
  const [requests, setRequests] = useState<Map<string, UseApiRequestState<unknown>>>(
    new Map()
  );

  const execute = useCallback(
    async <T,>(
      key: string,
      apiCall: () => Promise<ApiResult<T>>
    ) => {
      // Set loading state
      setRequests(prev => {
        const next = new Map(prev);
        next.set(key, {
          data: prev.get(key)?.data || null,
          error: null,
          isLoading: true,
          isRetrying: false,
        });
        return next;
      });

      const result = await apiCall();

      if (result.success) {
        setRequests(prev => {
          const next = new Map(prev);
          next.set(key, {
            data: result.data,
            error: null,
            isLoading: false,
            isRetrying: false,
          });
          return next;
        });
      } else {
        setRequests(prev => {
          const next = new Map(prev);
          next.set(key, {
            data: null,
            error: result.error,
            isLoading: false,
            isRetrying: false,
          });
          return next;
        });
      }

      return result;
    },
    []
  );

  const get = useCallback(
    <T,>(key: string): UseApiRequestState<T> => {
      return (requests.get(key) as UseApiRequestState<T>) || {
        data: null,
        error: null,
        isLoading: false,
        isRetrying: false,
      };
    },
    [requests]
  );

  const reset = useCallback((key?: string) => {
    if (key) {
      setRequests(prev => {
        const next = new Map(prev);
        next.delete(key);
        return next;
      });
    } else {
      setRequests(new Map());
    }
  }, []);

  return {
    execute,
    get,
    reset,
    requests,
  };
}
