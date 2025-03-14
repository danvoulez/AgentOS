// common/config/constants.js

// API endpoints
export const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:3000/api';

// Authentication
export const TOKEN_EXPIRY = '24h';
export const REFRESH_TOKEN_EXPIRY = '7d';

// Service names and ports
export const SERVICES = {
  PEOPLE: {
    name: 'people-service',
    port: process.env.PEOPLE_SERVICE_PORT || 3001
  },
  MESSAGING: {
    name: 'messaging-service',
    port: process.env.MESSAGING_SERVICE_PORT || 3002
  },
  MEDIA: {
    name: 'media-service',
    port: process.env.MEDIA_SERVICE_PORT || 3003
  },
  ORDER: {
    name: 'order-service',
    port: process.env.ORDER_SERVICE_PORT || 3004
  },
  ACCESS_CONTROL: {
    name: 'access-control',
    port: process.env.ACCESS_CONTROL_PORT || 3005
  },
  AI_AGENT: {
    name: 'ai-agent',
    port: process.env.AI_AGENT_PORT || 3006
  }
};

// Common status codes
export const STATUS = {
  SUCCESS: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  SERVER_ERROR: 500
};
