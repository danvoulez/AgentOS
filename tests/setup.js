// tests/setup.js
// Global setup for all tests

// Set environment to test
process.env.NODE_ENV = 'test';

// Set up mock database connection
jest.mock('../common/config/database', () => ({
  connectDB: jest.fn().mockResolvedValue(true)
}));

// Global timeout for all tests
jest.setTimeout(30000);

// Global teardown after all tests
afterAll(async () => {
  // Clean up resources if needed
});
