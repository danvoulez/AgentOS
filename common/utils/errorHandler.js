/**
 * Common error handling utility for all microservices
 */

class AppError extends Error {
  constructor(message, statusCode, errorCode) {
    super(message);
    this.statusCode = statusCode || 500;
    this.errorCode = errorCode || 'INTERNAL_ERROR';
    this.isOperational = true;
    
    Error.captureStackTrace(this, this.constructor);
  }
}

const handleError = (err, res) => {
  const { statusCode = 500, message, errorCode = 'INTERNAL_ERROR' } = err;
  
  res.status(statusCode).json({
    status: 'error',
    errorCode,
    message: statusCode === 500 ? 'Internal server error' : message
  });
};

const errorMiddleware = (err, req, res, next) => {
  err.statusCode = err.statusCode || 500;
  err.message = err.message || 'Something went wrong';
  
  // Log the error
  console.error(`[ERROR] ${err.stack}`);
  
  handleError(err, res);
};

module.exports = {
  AppError,
  handleError,
  errorMiddleware
};
