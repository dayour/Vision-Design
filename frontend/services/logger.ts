/**
 * Structured logging utility for API operations
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

export interface LogContext {
  [key: string]: unknown;
  endpoint?: string;
  method?: string;
  requestId?: string;
  timestamp?: string;
}

export interface LogEntry {
  level: LogLevel;
  message: string;
  context?: LogContext;
  timestamp: string;
}

class Logger {
  private currentLevel: LogLevel;
  private enabled: boolean;
  
  constructor() {
    // Enable debug mode if NEXT_PUBLIC_DEBUG_MODE is set
    this.enabled = process.env.NEXT_PUBLIC_DEBUG_MODE === 'true' || 
                   process.env.NODE_ENV === 'development';
    
    this.currentLevel = this.enabled ? LogLevel.DEBUG : LogLevel.WARN;
  }
  
  /**
   * Set the minimum log level
   */
  setLevel(level: LogLevel): void {
    this.currentLevel = level;
  }
  
  /**
   * Enable or disable logging
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
  }
  
  /**
   * Generate a unique request ID
   */
  generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  }
  
  /**
   * Format log entry for output
   */
  private formatLogEntry(entry: LogEntry): string {
    const levelName = LogLevel[entry.level];
    const contextStr = entry.context ? ` ${JSON.stringify(entry.context)}` : '';
    return `[${entry.timestamp}] [${levelName}] ${entry.message}${contextStr}`;
  }
  
  /**
   * Internal log method
   */
  private log(level: LogLevel, message: string, context?: LogContext): void {
    if (!this.enabled || level < this.currentLevel) {
      return;
    }
    
    const entry: LogEntry = {
      level,
      message,
      context: context ? { ...context, timestamp: new Date().toISOString() } : undefined,
      timestamp: new Date().toISOString(),
    };
    
    const formatted = this.formatLogEntry(entry);
    
    switch (level) {
      case LogLevel.DEBUG:
        console.debug(formatted);
        break;
      case LogLevel.INFO:
        console.info(formatted);
        break;
      case LogLevel.WARN:
        console.warn(formatted);
        break;
      case LogLevel.ERROR:
        console.error(formatted);
        break;
    }
  }
  
  /**
   * Log debug message
   */
  debug(message: string, context?: LogContext): void {
    this.log(LogLevel.DEBUG, message, context);
  }
  
  /**
   * Log info message
   */
  info(message: string, context?: LogContext): void {
    this.log(LogLevel.INFO, message, context);
  }
  
  /**
   * Log warning message
   */
  warn(message: string, context?: LogContext): void {
    this.log(LogLevel.WARN, message, context);
  }
  
  /**
   * Log error message
   */
  error(message: string, context?: LogContext): void {
    this.log(LogLevel.ERROR, message, context);
  }
  
  /**
   * Create a child logger with additional context
   */
  child(context: LogContext): Logger {
    const childLogger = new Logger();
    childLogger.currentLevel = this.currentLevel;
    childLogger.enabled = this.enabled;
    
    // Override log method to include parent context
    const originalLog = childLogger.log.bind(childLogger);
    childLogger.log = (level: LogLevel, message: string, childContext?: LogContext) => {
      const mergedContext = { ...context, ...childContext };
      originalLog(level, message, mergedContext);
    };
    
    return childLogger;
  }
}

// Export singleton instance
export const logger = new Logger();

// Export Logger class for testing
export { Logger };
