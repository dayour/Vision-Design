# Frontend Error Handling & API Integration

## Overview

The frontend now includes comprehensive error handling infrastructure with:
- **Type-safe API results** using `ApiResult<T>` pattern
- **Automatic retry logic** with exponential backoff
- **Circuit breaker pattern** to prevent cascade failures
- **Structured logging** for better debugging
- **Backward compatibility** with existing code

## Quick Start

### Using the Enhanced API Client

```typescript
import { apiClient } from '@/services/api-client';
import { isApiError } from '@/services/api-error';

// Make a request that returns ApiResult<T>
const result = await apiClient.get<GalleryResponse>('/api/v1/gallery/images');

if (result.success) {
  // Handle success
  console.log(result.data);
} else {
  // Handle error with full context
  console.error(result.error.message);
  if (result.error.retryable) {
    // Show retry UI
  }
}
```

### Using Compatibility Wrappers

For gradual migration, use the "Safe" variants that return `ApiResult`:

```typescript
import { fetchGalleryImagesSafe } from '@/services/api-compat';

const result = await fetchGalleryImagesSafe();
if (result.success) {
  setImages(result.data.items);
} else {
  // Handle error gracefully without throwing
  showErrorToast(result.error.message);
}
```

## API Error Types

### ApiResult<T>

```typescript
type ApiResult<T> = 
  | { success: true; data: T }
  | { success: false; error: ApiError };
```

### ApiError

```typescript
interface ApiError {
  code: ErrorCode;           // Standardized error code
  message: string;           // Human-readable message
  retryable: boolean;        // Whether operation can be retried
  statusCode?: number;       // HTTP status code if applicable
  details?: Record<string, unknown>;  // Additional context
  timestamp: string;         // ISO timestamp
}
```

### Error Codes

```typescript
enum ErrorCode {
  // Network errors
  NETWORK_ERROR = 'NETWORK_ERROR',
  TIMEOUT = 'TIMEOUT',
  CONNECTION_REFUSED = 'CONNECTION_REFUSED',
  
  // HTTP errors (4xx)
  BAD_REQUEST = 'BAD_REQUEST',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  NOT_FOUND = 'NOT_FOUND',
  TOO_MANY_REQUESTS = 'TOO_MANY_REQUESTS',
  
  // HTTP errors (5xx)
  INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',
  GATEWAY_TIMEOUT = 'GATEWAY_TIMEOUT',
  
  // Application errors
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  PARSE_ERROR = 'PARSE_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
}
```

## Retry Logic

Automatic retry with exponential backoff:

```typescript
import { withRetry } from '@/services/retry';

const data = await withRetry(
  async () => {
    const response = await fetch('/api/endpoint');
    return response.json();
  },
  {
    maxAttempts: 3,           // Maximum retry attempts
    initialDelayMs: 1000,     // Start with 1 second delay
    maxDelayMs: 10000,        // Cap at 10 seconds
    backoffMultiplier: 2,     // Double delay each time
    timeoutMs: 15000,         // 15 second timeout per attempt
  }
);
```

### Default Retry Configuration

- **Max Attempts**: 3
- **Initial Delay**: 1 second
- **Backoff**: Exponential (2x)
- **Max Delay**: 10 seconds
- **Timeout**: 15 seconds per attempt
- **Jitter**: ±20% to prevent thundering herd

## Circuit Breaker

Prevents overwhelming a failing backend:

```typescript
import { circuitBreakerRegistry } from '@/services/circuit-breaker';

// Get circuit breaker for an endpoint
const breaker = circuitBreakerRegistry.getBreaker('/api/v1/gallery/images');

// Execute with circuit breaker protection
await breaker.execute(async () => {
  return await fetch('/api/v1/gallery/images');
});

// Check circuit status
const state = breaker.getState(); // CLOSED, OPEN, or HALF_OPEN
```

### Circuit States

1. **CLOSED**: Normal operation, all requests pass through
2. **OPEN**: Too many failures, rejecting all requests
3. **HALF_OPEN**: Testing if service recovered

### Default Circuit Configuration

- **Failure Threshold**: 5 failures in 2 minutes
- **Success Threshold**: 2 consecutive successes to close
- **Timeout**: 60 seconds before retry
- **Monitoring Period**: 2 minutes

## Structured Logging

Better debugging with context:

```typescript
import { logger } from '@/services/logger';

logger.info('User action', {
  userId: user.id,
  action: 'upload_image',
  endpoint: '/api/v1/images/upload',
});

logger.error('Upload failed', {
  userId: user.id,
  errorCode: 'NETWORK_ERROR',
  retryable: true,
});
```

### Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General informational messages
- **WARN**: Warning messages for potential issues
- **ERROR**: Error messages for failures

### Environment Configuration

Logging is automatically enabled when:
- `NEXT_PUBLIC_DEBUG_MODE=true` in `.env`
- `NODE_ENV=development`

## Migration Guide

### Step 1: Add Error Handling to Components

```typescript
// Before
const loadImages = async () => {
  try {
    const data = await fetchGalleryImages();
    setImages(data.items);
  } catch (error) {
    console.error('Failed to load images:', error);
  }
};

// After
const loadImages = async () => {
  const result = await fetchGalleryImagesSafe();
  if (result.success) {
    setImages(result.data.items);
  } else {
    // Show user-friendly error message
    toast.error(result.error.message);
    
    // Show retry button if error is retryable
    if (result.error.retryable) {
      setShowRetryButton(true);
    }
  }
};
```

### Step 2: Handle Retryable Errors

```typescript
import { isApiError } from '@/services/api-error';

if (!result.success && result.error.retryable) {
  // Show retry UI
  return (
    <div>
      <p>{result.error.message}</p>
      <Button onClick={loadImages}>Retry</Button>
    </div>
  );
}
```

### Step 3: Monitor Circuit Breaker Status

```typescript
import { circuitBreakerRegistry } from '@/services/circuit-breaker';

// Check all circuit breakers
const status = circuitBreakerRegistry.getStatus();
status.forEach(({ name, state, metrics }) => {
  if (state === 'OPEN') {
    console.warn(`Circuit ${name} is open:`, metrics);
  }
});
```

## Best Practices

### 1. Always Handle Both Success and Error Cases

```typescript
const result = await apiClient.get<Data>('/api/endpoint');

if (result.success) {
  // Handle success
  processData(result.data);
} else {
  // Handle error
  handleError(result.error);
}
```

### 2. Show User-Friendly Error Messages

```typescript
function getErrorMessage(error: ApiError): string {
  switch (error.code) {
    case ErrorCode.NETWORK_ERROR:
      return 'Unable to connect. Please check your internet connection.';
    case ErrorCode.TIMEOUT:
      return 'Request timed out. Please try again.';
    case ErrorCode.SERVICE_UNAVAILABLE:
      return 'Service temporarily unavailable. Please try again later.';
    default:
      return error.message;
  }
}
```

### 3. Implement Retry UI for Retryable Errors

```typescript
{!result.success && result.error.retryable && (
  <Alert>
    <AlertDescription>{result.error.message}</AlertDescription>
    <Button onClick={retry} variant="outline" size="sm">
      Retry
    </Button>
  </Alert>
)}
```

### 4. Log Errors with Context

```typescript
if (!result.success) {
  logger.error('API request failed', {
    endpoint: '/api/v1/images',
    errorCode: result.error.code,
    statusCode: result.error.statusCode,
    retryable: result.error.retryable,
  });
}
```

## Testing Error Scenarios

### Simulate Network Error

```typescript
// In tests
jest.mock('@/services/api-client', () => ({
  apiClient: {
    get: jest.fn(() => Promise.resolve({
      success: false,
      error: {
        code: 'NETWORK_ERROR',
        message: 'Network error',
        retryable: true,
        timestamp: new Date().toISOString(),
      },
    })),
  },
}));
```

### Simulate Circuit Breaker Open

```typescript
import { circuitBreakerRegistry } from '@/services/circuit-breaker';

// Force circuit open
const breaker = circuitBreakerRegistry.getBreaker('/api/endpoint');
breaker.execute(() => Promise.reject(new Error('Test')));
// ... repeat until circuit opens
```

## Performance Considerations

### 1. Circuit Breaker Prevents Cascade Failures

When a backend service is failing, the circuit breaker:
- Stops sending requests immediately after threshold
- Prevents wasting resources on doomed requests
- Allows service time to recover

### 2. Exponential Backoff Reduces Load

Retry logic with exponential backoff:
- Prevents overwhelming a recovering service
- Adds jitter to prevent thundering herd
- Respects rate limits (429 responses)

### 3. Timeout Configuration

Default timeouts are set to balance:
- User experience (don't wait too long)
- Service recovery (give backend time to respond)
- Resource usage (don't hold connections forever)

## Troubleshooting

### Circuit Breaker Stuck Open

```typescript
// Check circuit status
const status = circuitBreakerRegistry.getStatus();
console.log(status);

// Manual reset if needed
circuitBreakerRegistry.resetAll();
```

### Too Many Retries

If you see excessive retries:
1. Check if error is marked as non-retryable
2. Reduce `maxAttempts` in retry options
3. Increase failure threshold in circuit breaker

### Timeout Issues

If timeouts are too aggressive:
```typescript
const result = await apiClient.get('/api/slow-endpoint', {
  retry: {
    timeoutMs: 30000,  // 30 seconds
  },
});
```

## API Reference

See individual files for detailed API documentation:
- `api-error.ts` - Error types and utilities
- `api-client.ts` - Enhanced API client
- `retry.ts` - Retry logic
- `circuit-breaker.ts` - Circuit breaker implementation
- `logger.ts` - Structured logging
- `api-compat.ts` - Backward compatibility wrappers
