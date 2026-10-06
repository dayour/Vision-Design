/**
 * Circuit breaker pattern to prevent cascade failures
 */

import { logger } from './logger';

export enum CircuitState {
  CLOSED = 'CLOSED',     // Normal operation
  OPEN = 'OPEN',         // Circuit is open, rejecting requests
  HALF_OPEN = 'HALF_OPEN', // Testing if service recovered
}

export interface CircuitBreakerOptions {
  failureThreshold?: number;      // Number of failures before opening
  successThreshold?: number;      // Successes in half-open before closing
  timeout?: number;               // Time to wait before half-open (ms)
  monitoringPeriod?: number;      // Time window for failure counting (ms)
}

interface CircuitMetrics {
  failures: number;
  successes: number;
  consecutiveSuccesses: number;
  lastFailureTime?: number;
  lastSuccessTime?: number;
  recentFailures: number[];  // Timestamps of recent failures
}

const DEFAULT_OPTIONS: Required<CircuitBreakerOptions> = {
  failureThreshold: 5,
  successThreshold: 2,
  timeout: 60000,           // 60 seconds
  monitoringPeriod: 120000, // 2 minutes
};

export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private options: Required<CircuitBreakerOptions>;
  private metrics: CircuitMetrics;
  private nextAttemptTime: number = 0;
  private readonly name: string;
  
  constructor(name: string, options: CircuitBreakerOptions = {}) {
    this.name = name;
    this.options = { ...DEFAULT_OPTIONS, ...options };
    this.metrics = {
      failures: 0,
      successes: 0,
      consecutiveSuccesses: 0,
      recentFailures: [],
    };
  }
  
  /**
   * Get current circuit state
   */
  getState(): CircuitState {
    return this.state;
  }
  
  /**
   * Get circuit metrics
   */
  getMetrics(): Readonly<CircuitMetrics> {
    return { ...this.metrics };
  }
  
  /**
   * Clean up old failures outside monitoring period
   */
  private cleanOldFailures(): void {
    const now = Date.now();
    const cutoff = now - this.options.monitoringPeriod;
    this.metrics.recentFailures = this.metrics.recentFailures.filter(
      timestamp => timestamp > cutoff
    );
  }
  
  /**
   * Record a successful call
   */
  private recordSuccess(): void {
    this.metrics.successes++;
    this.metrics.consecutiveSuccesses++;
    this.metrics.lastSuccessTime = Date.now();
    
    logger.debug(`Circuit breaker success recorded`, {
      circuitBreaker: this.name,
      state: this.state,
      consecutiveSuccesses: this.metrics.consecutiveSuccesses,
    });
    
    // If in half-open state, check if we should close the circuit
    if (this.state === CircuitState.HALF_OPEN) {
      if (this.metrics.consecutiveSuccesses >= this.options.successThreshold) {
        this.closeCircuit();
      }
    }
  }
  
  /**
   * Record a failed call
   */
  private recordFailure(): void {
    const now = Date.now();
    this.metrics.failures++;
    this.metrics.consecutiveSuccesses = 0;
    this.metrics.lastFailureTime = now;
    this.metrics.recentFailures.push(now);
    
    this.cleanOldFailures();
    
    logger.warn(`Circuit breaker failure recorded`, {
      circuitBreaker: this.name,
      state: this.state,
      recentFailures: this.metrics.recentFailures.length,
      threshold: this.options.failureThreshold,
    });
    
    // Check if we should open the circuit
    if (this.state === CircuitState.CLOSED || this.state === CircuitState.HALF_OPEN) {
      if (this.metrics.recentFailures.length >= this.options.failureThreshold) {
        this.openCircuit();
      }
    }
  }
  
  /**
   * Open the circuit (stop allowing requests)
   */
  private openCircuit(): void {
    this.state = CircuitState.OPEN;
    this.nextAttemptTime = Date.now() + this.options.timeout;
    
    logger.error(`Circuit breaker opened`, {
      circuitBreaker: this.name,
      failures: this.metrics.recentFailures.length,
      nextAttemptTime: new Date(this.nextAttemptTime).toISOString(),
    });
  }
  
  /**
   * Half-open the circuit (allow test request)
   */
  private halfOpenCircuit(): void {
    this.state = CircuitState.HALF_OPEN;
    this.metrics.consecutiveSuccesses = 0;
    
    logger.info(`Circuit breaker half-opened`, {
      circuitBreaker: this.name,
    });
  }
  
  /**
   * Close the circuit (resume normal operation)
   */
  private closeCircuit(): void {
    this.state = CircuitState.CLOSED;
    this.metrics.recentFailures = [];
    this.metrics.consecutiveSuccesses = 0;
    
    logger.info(`Circuit breaker closed`, {
      circuitBreaker: this.name,
      totalSuccesses: this.metrics.successes,
    });
  }
  
  /**
   * Check if a request can proceed
   */
  private canProceed(): boolean {
    // If circuit is closed, allow request
    if (this.state === CircuitState.CLOSED) {
      return true;
    }
    
    // If circuit is open, check if timeout has elapsed
    if (this.state === CircuitState.OPEN) {
      const now = Date.now();
      if (now >= this.nextAttemptTime) {
        this.halfOpenCircuit();
        return true;
      }
      return false;
    }
    
    // If half-open, allow one request at a time
    return this.state === CircuitState.HALF_OPEN;
  }
  
  /**
   * Execute a function with circuit breaker protection
   */
  async execute<T>(
    fn: () => Promise<T>,
    context?: { endpoint?: string; method?: string }
  ): Promise<T> {
    // Check if circuit allows request
    if (!this.canProceed()) {
      const timeUntilRetry = Math.max(0, this.nextAttemptTime - Date.now());
      const error = new Error(
        `Circuit breaker is OPEN for ${this.name}. ` +
        `Retry after ${Math.ceil(timeUntilRetry / 1000)}s`
      );
      
      logger.warn(`Circuit breaker rejected request`, {
        circuitBreaker: this.name,
        state: this.state,
        timeUntilRetry: Math.ceil(timeUntilRetry / 1000),
        ...context,
      });
      
      throw error;
    }
    
    try {
      const result = await fn();
      this.recordSuccess();
      return result;
    } catch (error) {
      this.recordFailure();
      throw error;
    }
  }
  
  /**
   * Reset the circuit breaker to initial state
   */
  reset(): void {
    this.state = CircuitState.CLOSED;
    this.metrics = {
      failures: 0,
      successes: 0,
      consecutiveSuccesses: 0,
      recentFailures: [],
    };
    this.nextAttemptTime = 0;
    
    logger.info(`Circuit breaker reset`, {
      circuitBreaker: this.name,
    });
  }
}

/**
 * Global circuit breaker registry
 */
class CircuitBreakerRegistry {
  private breakers = new Map<string, CircuitBreaker>();
  
  /**
   * Get or create a circuit breaker for an endpoint
   */
  getBreaker(name: string, options?: CircuitBreakerOptions): CircuitBreaker {
    if (!this.breakers.has(name)) {
      this.breakers.set(name, new CircuitBreaker(name, options));
    }
    return this.breakers.get(name)!;
  }
  
  /**
   * Reset all circuit breakers
   */
  resetAll(): void {
    this.breakers.forEach(breaker => breaker.reset());
  }
  
  /**
   * Get all circuit breakers status
   */
  getStatus(): Array<{ name: string; state: CircuitState; metrics: CircuitMetrics }> {
    return Array.from(this.breakers.entries()).map(([name, breaker]) => ({
      name,
      state: breaker.getState(),
      metrics: breaker.getMetrics() as CircuitMetrics,
    }));
  }
}

// Export singleton registry
export const circuitBreakerRegistry = new CircuitBreakerRegistry();
