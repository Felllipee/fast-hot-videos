
import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, AuthState } from '../types';

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => void;
  toggleFavorite: (videoId: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
  });

  // Carregar sessão ao iniciar
  useEffect(() => {
    const savedSession = localStorage.getItem('fasthot_session');
    if (savedSession) {
      setAuthState({
        user: JSON.parse(savedSession),
        isAuthenticated: true,
      });
    }
  }, []);

  const login = async (email: string, password: string) => {
    // Simulação de delay de rede
    await new Promise(resolve => setTimeout(resolve, 800));

    // Lógica de "armazenamento" local para simular um banco de dados
    const users = JSON.parse(localStorage.getItem('fasthot_users') || '[]');
    let user = users.find((u: any) => u.email === email);

    if (!user) {
      // Se não existe, criamos um novo (comportamento de protótipo)
      user = {
        email,
        name: email.split('@')[0],
        favorites: [],
      };
      users.push(user);
      localStorage.setItem('fasthot_users', JSON.stringify(users));
    }

    setAuthState({ user, isAuthenticated: true });
    localStorage.setItem('fasthot_session', JSON.stringify(user));
  };

  const loginWithGoogle = async () => {
    await new Promise(resolve => setTimeout(resolve, 1000));
    const mockUser: User = {
      email: 'user.google@gmail.com',
      name: 'Usuário Google',
      favorites: [],
    };
    setAuthState({ user: mockUser, isAuthenticated: true });
    localStorage.setItem('fasthot_session', JSON.stringify(mockUser));
  };

  const logout = () => {
    setAuthState({ user: null, isAuthenticated: false });
    localStorage.removeItem('fasthot_session');
  };

  const toggleFavorite = (videoId: string) => {
    if (!authState.user) return;

    const updatedUser = { ...authState.user };
    const index = updatedUser.favorites.indexOf(videoId);
    
    if (index > -1) {
      updatedUser.favorites.splice(index, 1);
    } else {
      updatedUser.favorites.push(videoId);
    }

    setAuthState(prev => ({ ...prev, user: updatedUser }));
    localStorage.setItem('fasthot_session', JSON.stringify(updatedUser));
    
    // Atualizar no "banco de dados" local
    const users = JSON.parse(localStorage.getItem('fasthot_users') || '[]');
    const userIndex = users.findIndex((u: any) => u.email === updatedUser.email);
    if (userIndex > -1) {
      users[userIndex] = updatedUser;
      localStorage.setItem('fasthot_users', JSON.stringify(users));
    }
  };

  return (
    <AuthContext.Provider value={{ ...authState, login, loginWithGoogle, logout, toggleFavorite }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
