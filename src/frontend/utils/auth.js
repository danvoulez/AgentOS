// src/frontend/utils/auth.js
/**
 * Authentication utilities for the frontend
 */

import { api } from './api';

// Token storage keys
const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

/**
 * Store authentication data in localStorage
 */
export function setAuthData(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/**
 * Clear authentication data from localStorage
 */
export function clearAuthData() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/**
 * Get the current authenticated user
 */
export function getCurrentUser() {
  const userJson = localStorage.getItem(USER_KEY);
  return userJson ? JSON.parse(userJson) : null;
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated() {
  return !!localStorage.getItem(TOKEN_KEY);
}

/**
 * Login user with credentials
 */
export async function login(email, password) {
  try {
    const response = await api.post('/auth/login', { email, password });
    setAuthData(response.token, response.user);
    return response.user;
  } catch (error) {
    throw new Error(error.message || 'Login failed');
  }
}

/**
 * Logout current user
 */
export async function logout() {
  try {
    await api.post('/auth/logout');
  } catch (error) {
    console.error('Logout API call failed:', error);
  } finally {
    clearAuthData();
  }
}
