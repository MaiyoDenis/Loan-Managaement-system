import React, { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';
import { authAPI } from '../services/api';

interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  branch_id?: number;
  first_name?: string;
  last_name?: string;
  username?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    // Initialize user from localStorage
    const token = localStorage.getItem('access_token');
    if (token) {
      const userData = localStorage.getItem('user');
      if (userData && userData !== 'undefined') {
        try {
          return JSON.parse(userData);
        } catch {
          // Invalid user data in localStorage, clear it
          localStorage.removeItem('user');
          return null;
        }
      }
    }
    return null;
  });
  const [loading] = useState(false);

  const login = async (email: string, password: string) => {
    // Backend returns tokens but may not include user; fetch user after login
    const response = await authAPI.login(email, password);
    const { access_token, refresh_token } = response;

    if (!access_token) {
      throw new Error('Login failed: missing access token');
    }

    localStorage.setItem('access_token', access_token);
    if (refresh_token) {
      localStorage.setItem('refresh_token', refresh_token);
    }

    // Fetch current user using the new token
    const userData = await authAPI.getCurrentUser(access_token);
    if (!userData) {
      throw new Error('Login failed: unable to load user');
    }

    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setUser(null);
    authAPI.logout();
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    login,
    logout,
    loading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
