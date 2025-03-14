/**
 * Logging middleware for request/response logging
 */
const { logger } = require('../config');

/**
 * Request logging middleware
 */
const requestLogger = (req, res, next) => {
  // Generate a unique request ID
  req.requestId = req.headers['x-request-id'] || `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  
  // Log the request
  logger.info({
    message: `Incoming request: ${req.method} ${req.originalUrl}`,
    requestId: req.requestId,
    method: req.method,
    url: req.originalUrl,
    ip: req.ip,
    userAgent: req.headers['user-agent'],
    body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined
  });
  
  // Track response time
  const start = Date.now();
  
  // Override end method to log response
  const originalEnd = res.end;
  res.end = function(chunk, encoding) {
    // Calculate response time
    const responseTime = Date.now() - start;
    
    // Log the response
    logger.info({
      message: `Outgoing response: ${res.statusCode} ${req.method} ${req.originalUrl}`,
      requestId: req.requestId,
      statusCode: res.statusCode,
      responseTime: `${responseTime}ms`
    });
    
    // Call the original end method
    originalEnd.call(this, chunk, encoding);
  };
  
  next();
};

/**
 * Error logging middleware
 */
const errorLogger = (err, req, res, next) => {
  logger.error({
    message: `Error: ${err.message}`,
    requestId: req.requestId,
    method: req.method,
    url: req.originalUrl,
    statusCode: err.statusCode || 500,
    errorCode: err.errorCode,
    stack: err.stack
  });
  
  next(err);
};

module.exports = {
  requestLogger,
  errorLogger
};
