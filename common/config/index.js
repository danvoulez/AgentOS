// common/config/index.js
import env from './env.js';
import connectDB from './database.js';
import logger from './logger.js';
import * as constants from './constants.js';

// Export all configuration modules
export {
  env,
  connectDB,
  logger,
  constants
};

// Default export for convenience
export default {
  env,
  connectDB,
  logger,
  constants
};
