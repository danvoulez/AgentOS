// tests/unit/middleware/authMiddleware.test.js
const { authenticate, authorize } = require('../../../common/middleware/auth');
const jwt = require('jsonwebtoken');

// Mock dependencies
jest.mock('jsonwebtoken');
jest.mock('../../../common/utils/errorHandler', () => ({
  AppError: class AppError extends Error {
    constructor(message, statusCode, errorCode) {
      super(message);
      this.statusCode = statusCode;
      this.errorCode = errorCode;
    }
  }
}));

describe('Authentication Middleware', () => {
  let req, res, next;
  
  beforeEach(() => {
    req = {
      headers: {
        authorization: 'Bearer valid-token'
      }
    };
    res = {};
    next = jest.fn();
  });
  
  afterEach(() => {
    jest.clearAllMocks();
  });
  
  test('should call next if token is valid', () => {
    // Mock JWT verify to return decoded user
    jwt.verify.mockReturnValue({ id: '123', role: 'admin' });
    
    authenticate(req, res, next);
    
    expect(jwt.verify).toHaveBeenCalledWith('valid-token', expect.any(String));
    expect(req.user).toEqual({ id: '123', role: 'admin' });
    expect(next).toHaveBeenCalled();
  });
  
  test('should throw error if no authorization header', () => {
    req.headers.authorization = undefined;
    
    authenticate(req, res, next);
    
    expect(next).toHaveBeenCalledWith(expect.objectContaining({
      message: 'Authentication required',
      statusCode: 401,
      errorCode: 'AUTH_REQUIRED'
    }));
  });
  
  test('should throw error if token is invalid', () => {
    jwt.verify.mockImplementation(() => {
      throw new Error('Invalid token');
    });
    
    authenticate(req, res, next);
    
    expect(next).toHaveBeenCalledWith(expect.any(Error));
  });
  
  test('authorize middleware should allow access for correct role', () => {
    req.user = { role: 'admin' };
    
    authorize(['admin'])(req, res, next);
    
    expect(next).toHaveBeenCalled();
  });
  
  test('authorize middleware should deny access for incorrect role', () => {
    req.user = { role: 'user' };
    
    authorize(['admin'])(req, res, next);
    
    expect(next).toHaveBeenCalledWith(expect.objectContaining({
      statusCode: 403
    }));
  });
});
