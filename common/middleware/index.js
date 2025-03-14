/**
 * Common middleware index file
 * Exports all middleware for easy importing
 */

const { authenticate, authorize } = require('./auth');
const { errorHandler, notFound, validateRequest } = require('./errorHandler');
const { requestLogger, errorLogger } = require('./logger');
const { createRateLimiter, apiLimiter, authLimiter, webhookLimiter } = require('./rateLimiter');

module.exports = {
  // Authentication
  authenticate,
  authorize,
  
  // Error handling
  errorHandler,
  notFound,
  validateRequest,
  
  // Logging
  requestLogger,
  errorLogger,
  
  // Rate limiting
  createRateLimiter,
  apiLimiter,
  authLimiter,
  webhookLimiter
};
