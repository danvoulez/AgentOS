import React, { createContext, useState, useEffect, ReactNode, useCallback } from 'react';
import apiClient from '../apiClient';
import { UserMeResponse, AuthTokenResponse } from '../types/api';

interface AuthContextType {
  isAuthenticated: boolean;
  user: UserMeResponse | null;
  token: string | null;
  isLoading: boolean;
  login: (emailOrUsername: string, password: string) => Promise<void>;
  logout: () => void;
  fetchCurrentUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<UserMeResponse | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('authToken'));
  const [isLoading, setIsLoading] = useState(true);

  const fetchCurrentUser = useCallback(async () => {
    if (!token) {
      setIsAuthenticated(false);
      setUser(null);
      setIsLoading(false);
      return;
    }
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    try {
      const response = await apiClient.get<UserMeResponse>('/users/me');
      setUser(response.data);
      setIsAuthenticated(true);
    } catch (error) {
      localStorage.removeItem('authToken');
      setToken(null);
      setUser(null);
      setIsAuthenticated(false);
      apiClient.defaults.headers.common['Authorization'] = '';
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) fetchCurrentUser();
    else setIsLoading(false);
  }, [token, fetchCurrentUser]);

  const login = async (emailOrUsername: string, password: string) => {
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('username', emailOrUsername);
      formData.append('password', password);

      const response = await apiClient.post<AuthTokenResponse>(
        '/auth/token',
        formData,
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
      );
      const newAccessToken = response.data.access_token;
      localStorage.setItem('authToken', newAccessToken);
      setToken(newAccessToken);
    } catch (error) {
      setIsLoading(false);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('authToken');
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    apiClient.defaults.headers.common['Authorization'] = '';
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, token, isLoading, login, logout, fetchCurrentUser }}>
      {children}
    </AuthContext.Provider>
  );
};