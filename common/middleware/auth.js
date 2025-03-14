/**
 * Common authentication middleware for all microservices
 */
const jwt = require('jsonwebtoken');
const { AppError } = require('../utils/errorHandler');

/**
 * Verify JWT token and attach user to request
 */
const authenticate = (req, res, next) => {
  try {
    // Get token from Authorization header
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      throw new AppError('Authentication required', 401, 'AUTH_REQUIRED');
    }
    
    const token = authHeader.split(' ')[1];
    
    if (!token) {
      throw new AppError('Invalid authentication token', 401, 'INVALID_TOKEN');
    }
    
    // Verify token
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'your-secret-key');
    
    // Attach user to request
    req.user = decoded;
    
    next();
  } catch (error) {
    if (error.name === 'JsonWebTokenError') {
      return next(new AppError('Invalid token', 401, 'INVALID_TOKEN'));
    }
    
    if (error.name === 'TokenExpiredError') {
      return next(new AppError('Token expired', 401, 'TOKEN_EXPIRED'));
    }
    
    next(error);
  }
};

/**
 * Check if user has required roles
 * @param {Array} roles - Array of required roles
 */
const authorize = (roles = []) => {
  return (req, res, next) => {
    if (!req.user) {
      return next(new AppError('Authentication required', 401, 'AUTH_REQUIRED'));
    }
    
    if (roles.length && !roles.includes(req.user.role)) {
      return next(new AppError('Not authorized to access this resource', 403, 'FORBIDDEN'));
    }
    
    next();
  };
};

module.exports = {
  authenticate,
  authorize
};
