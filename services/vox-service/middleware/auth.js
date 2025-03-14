/**
 * Authentication Middleware
 * Verifies JWT tokens and adds user information to request
 */

const jwt = require('jsonwebtoken');
const { AppError } = require('../../../common/utils/errorHandler');
const { logger } = require('../../../common/config/logger');

/**
 * Middleware to verify JWT token
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 * @param {Function} next - Express next function
 */
exports.verifyToken = (req, res, next) => {
  try {
    // Get token from header
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return next(new AppError('No authentication token provided', 401));
    }
    
    const token = authHeader.split(' ')[1];
    
    // Verify token
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    
    // Add user info to request
    req.user = decoded;
    
    logger.info(`Authenticated user: ${decoded.id}`);
    
    next();
  } catch (error) {
    if (error.name === 'JsonWebTokenError') {
      return next(new AppError('Invalid token', 401));
    }
    
    if (error.name === 'TokenExpiredError') {
      return next(new AppError('Token expired', 401));
    }
    
    logger.error(`Authentication error: ${error.message}`);
    next(new AppError('Authentication failed', 401));
  }
};

/**
 * Middleware to check if user has required role
 * @param {String[]} roles - Array of allowed roles
 * @returns {Function} - Express middleware
 */
exports.hasRole = (roles) => {
  return (req, res, next) => {
    if (!req.user) {
      return next(new AppError('User not authenticated', 401));
    }
    
    if (!roles.includes(req.user.role)) {
      return next(new AppError('Unauthorized: Insufficient permissions', 403));
    }
    
    next();
  };
};

/**
 * Optional authentication middleware
 * Verifies token if present but doesn't require it
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 * @param {Function} next - Express next function
 */
exports.optionalAuth = (req, res, next) => {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      // No token provided, continue as guest
      req.user = { id: 'guest', role: 'guest' };
      return next();
    }
    
    const token = authHeader.split(' ')[1];
    
    // Verify token
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    
    // Add user info to request
    req.user = decoded;
    
    next();
  } catch (error) {
    // Token invalid, continue as guest
    req.user = { id: 'guest', role: 'guest' };
    next();
  }
};
