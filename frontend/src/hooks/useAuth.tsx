import { useMutation, useQueryClient } from '@tanstack/react-query';
import React, { useState, useEffect, createContext, useContext, ReactNode } from 'react';
import api from '../api';

interface User {
  username: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  login: (credentials: LoginCredentials) => Promise<any>;
  register: (userData: RegisterData) => Promise<any>;
  logout: () => void;
}

interface LoginCredentials {
  username: string;
  password: string;
}

interface RegisterData {
  username: string;
  password: string;
}

interface AuthProviderProps {
  children: ReactNode;
}

// Auth Context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuthContext = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
};

// Auth Provider Component
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('access');
    if (token) {
      setIsAuthenticated(true);
      // You could also verify the token here
    }
    setIsLoading(false);
  }, []);

  const login = async (credentials: LoginCredentials) => {
    const response = await api.post('/api/token/', credentials);
    const { access, refresh } = response.data;

    localStorage.setItem('access', access);
    localStorage.setItem('refresh', refresh);

    setIsAuthenticated(true);
    setUser({ username: credentials.username });

    return response.data;
  };

  const register = async (userData: RegisterData) => {
    const response = await api.post('/api/user/register/', userData);

    // Auto-login after registration
    const loginResponse = await api.post('/api/token/', {
      username: userData.username,
      password: userData.password
    });

    const { access, refresh } = loginResponse.data;
    localStorage.setItem('access', access);
    localStorage.setItem('refresh', refresh);

    setIsAuthenticated(true);
    setUser({ username: userData.username });

    return response.data;
  };

  const logout = () => {
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    setIsAuthenticated(false);
    setUser(null);
  };

  const value: AuthContextType = {
    isAuthenticated,
    isLoading,
    user,
    login,
    register,
    logout
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook for using auth in components
export const useAuth = () => {
  const queryClient = useQueryClient();
  const { login: loginFn, register: registerFn, logout: logoutFn } = useAuthContext();

  const login = useMutation({
    mutationFn: loginFn,
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });

  const register = useMutation({
    mutationFn: registerFn,
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });

  const logout = useMutation({
    mutationFn: logoutFn,
    onSuccess: () => {
      queryClient.clear();
    },
  });

  return {
    login,
    register,
    logout
  };
};