// src/frontend/utils/api.js
/**
 * Utility for making API requests with consistent error handling
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:3000/api';

/**
 * Generic fetch wrapper with error handling
 */
export async function fetchWithAuth(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  // Add default headers
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Get auth token from localStorage if available
  const token = localStorage.getItem('auth_token');
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Handle non-2xx responses
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `API error: ${response.status}`);
    }

    // Parse JSON response (or return empty object if no content)
    return response.status !== 204 
      ? await response.json() 
      : {};
      
  } catch (error) {
    console.error(`API request failed: ${url}`, error);
    throw error;
  }
}

// Convenience methods for common HTTP methods
export const api = {
  get: (endpoint, options = {}) => 
    fetchWithAuth(endpoint, { ...options, method: 'GET' }),
    
  post: (endpoint, data, options = {}) => 
    fetchWithAuth(endpoint, { 
      ...options, 
      method: 'POST',
      body: JSON.stringify(data),
    }),
    
  put: (endpoint, data, options = {}) => 
    fetchWithAuth(endpoint, { 
      ...options, 
      method: 'PUT',
      body: JSON.stringify(data),
    }),
    
  delete: (endpoint, options = {}) => 
    fetchWithAuth(endpoint, { ...options, method: 'DELETE' }),
};
