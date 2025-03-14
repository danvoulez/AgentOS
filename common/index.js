/**
 * Main export file for common utilities and configurations
 */

// Export utilities
const logger = require('./utils/logger');
const { AppError, handleError, errorMiddleware } = require('./utils/errorHandler');

// Export configurations
const { connectToDatabase, mongoose } = require('./config/database');
const config = require('./config/configManager');

// Export middleware
const { authenticate, authorize } = require('./middleware/auth');

// Export models
const { createBaseSchema } = require('./models');

module.exports = {
  // Utils
  logger,
  AppError,
  handleError,
  errorMiddleware,
  
  // Config
  config,
  connectToDatabase,
  mongoose,
  
  // Middleware
  authenticate,
  authorize,
  
  // Models
  createBaseSchema
};
