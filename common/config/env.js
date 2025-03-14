// common/config/env.js
import dotenv from 'dotenv';
import path from 'path';

// Load environment variables from .env file
dotenv.config({ path: path.resolve(process.cwd(), '..', '..', '.env') });

// Environment configuration
const env = {
  NODE_ENV: process.env.NODE_ENV || 'development',
  PORT: process.env.PORT || 3000,
  
  // Database
  MONGO_URI: process.env.MONGO_URI || 'mongodb://localhost:27017/agentos',
  
  // JWT
  JWT_SECRET: process.env.JWT_SECRET || 'supersecretkey',
  JWT_EXPIRE: process.env.JWT_EXPIRE || '24h',
  
  // Services
  API_URL: process.env.API_URL || 'http://localhost:3000',
  
  // CORS
  CORS_ORIGIN: process.env.CORS_ORIGIN || '*',
  
  // Logging
  LOG_LEVEL: process.env.LOG_LEVEL || 'info',
  
  // Feature flags
  ENABLE_AI_FEATURES: process.env.ENABLE_AI_FEATURES === 'true',
  ENABLE_WHATSAPP: process.env.ENABLE_WHATSAPP === 'true',
  
  // Check if we're in production
  isProd: process.env.NODE_ENV === 'production',
  
  // Check if we're in development
  isDev: process.env.NODE_ENV === 'development' || !process.env.NODE_ENV,
  
  // Check if we're in test
  isTest: process.env.NODE_ENV === 'test',
};

export default env;
