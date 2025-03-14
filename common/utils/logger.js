/**
 * Common logging utility for all microservices
 */
const winston = require('winston');

// Define log format
const logFormat = winston.format.printf(({ level, message, timestamp, service }) => {
  return `${timestamp} [${service}] ${level}: ${message}`;
});

// Create the logger instance
const createLogger = (service) => {
  return winston.createLogger({
    level: process.env.LOG_LEVEL || 'info',
    format: winston.format.combine(
      winston.format.timestamp(),
      winston.format.colorize(),
      logFormat
    ),
    defaultMeta: { service },
    transports: [
      new winston.transports.Console(),
      new winston.transports.File({ 
        filename: `logs/${service}-error.log`, 
        level: 'error' 
      }),
      new winston.transports.File({ 
        filename: `logs/${service}-combined.log` 
      })
    ]
  });
};

module.exports = createLogger;
