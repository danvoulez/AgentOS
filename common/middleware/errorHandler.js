/**
 * Common error handling middleware for all microservices
 */
const { logger } = require('../config');

/**
 * Global error handling middleware
 */
const errorHandler = (err, req, res, next) => {
  // Log the error
  logger.error(`${err.name}: ${err.message}`);
  
  // Default error values
  const statusCode = err.statusCode || 500;
  const message = err.message || 'Internal Server Error';
  const errorCode = err.errorCode || 'SERVER_ERROR';
  
  // Send error response
  res.status(statusCode).json({
    success: false,
    error: {
      message,
      code: errorCode,
      ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
    }
  });
};

/**
 * Not found middleware - for handling 404 errors
 */
const notFound = (req, res, next) => {
  const error = new Error(`Not Found - ${req.originalUrl}`);
  error.statusCode = 404;
  error.errorCode = 'RESOURCE_NOT_FOUND';
  next(error);
};

/**
 * Request validation middleware
 */
const validateRequest = (schema) => {
  return (req, res, next) => {
    const { error } = schema.validate(req.body);
    if (error) {
      const message = error.details.map(detail => detail.message).join(', ');
      const err = new Error(message);
      err.statusCode = 400;
      err.errorCode = 'VALIDATION_ERROR';
      return next(err);
    }
    next();
  };
};

module.exports = {
  errorHandler,
  notFound,
  validateRequest
};
