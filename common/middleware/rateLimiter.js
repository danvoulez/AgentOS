/**
 * Rate limiting middleware for API protection
 */
const rateLimit = require('express-rate-limit');
const { AppError } = require('../utils/errorHandler');

/**
 * Create a rate limiter with custom configuration
 * @param {Object} options - Rate limiter options
 * @returns {Function} Express middleware
 */
const createRateLimiter = (options = {}) => {
  const defaultOptions = {
    windowMs: 15 * 60 * 1000, // 15 minutes by default
    max: 100, // Limit each IP to 100 requests per windowMs
    standardHeaders: true, // Return rate limit info in the `RateLimit-*` headers
    legacyHeaders: false, // Disable the `X-RateLimit-*` headers
    message: 'Too many requests from this IP, please try again later',
    handler: (req, res, next, options) => {
      next(new AppError(options.message, 429, 'RATE_LIMIT_EXCEEDED'));
    }
  };

  return rateLimit({
    ...defaultOptions,
    ...options
  });
};

/**
 * Common rate limiters for different API endpoints
 */
const apiLimiter = createRateLimiter();

const authLimiter = createRateLimiter({
  windowMs: 60 * 60 * 1000, // 1 hour
  max: 10, // 10 requests per hour
  message: 'Too many authentication attempts, please try again later'
});

const webhookLimiter = createRateLimiter({
  windowMs: 5 * 60 * 1000, // 5 minutes
  max: 50 // 50 requests per 5 minutes
});

module.exports = {
  createRateLimiter,
  apiLimiter,
  authLimiter,
  webhookLimiter
};
