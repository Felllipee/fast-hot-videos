
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface HeaderProps {
  onSearch: (query: string) => void;
  onOpenLogin: () => void;
  onToggleFavorites: () => void;
  showOnlyFavorites: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onSearch, onOpenLogin, onToggleFavorites, showOnlyFavorites }) => {
  const { user, isAuthenticated, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[#08080a]/80 backdrop-blur-xl border-b border-gray-800">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between gap-4">
        {/* Logo - Removido o ícone quadrado 'F' */}
        <div className="flex items-center gap-2 flex-shrink-0 cursor-pointer" onClick={() => window.location.reload()}>
          <span className="text-xl font-bold tracking-tighter uppercase">Fast<span className="text-red-600">Hot</span></span>
        </div>

        {/* Navigation - Center */}
        <nav className="hidden lg:flex items-center gap-6">
          <a href="#" className="text-sm font-medium hover:text-red-500 transition-colors">Início</a>
          <a href="#" className="text-sm text-gray-400 font-medium hover:text-white transition-colors">Populares</a>
          <button 
            onClick={onToggleFavorites}
            className={`text-sm font-medium transition-colors flex items-center gap-2 ${showOnlyFavorites ? 'text-red-500' : 'text-gray-400 hover:text-white'}`}
          >
            <svg className={`w-4 h-4 ${showOnlyFavorites ? 'fill-current' : 'fill-none'}`} stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
            Favoritos
          </button>
          <a href="#" className="text-sm text-gray-400 font-medium hover:text-white transition-colors">Premium</a>
        </nav>

        {/* Search & Profile - Right */}
        <div className="flex items-center gap-4 flex-grow max-w-md lg:max-w-xs">
          <div className="relative w-full">
            <input 
              type="text" 
              placeholder="Busque algo quente..."
              onChange={(e) => onSearch(e.target.value)}
              className="w-full bg-gray-900 border border-gray-800 rounded-full px-4 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-600/50 transition-all pl-10"
            />
            <svg className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          
          {!isAuthenticated ? (
            <button 
              onClick={onOpenLogin}
              className="bg-red-600 hover:bg-red-700 text-white text-xs font-bold px-4 py-2 rounded-full transition-all flex-shrink-0"
            >
              Entrar
            </button>
          ) : (
            <div className="relative">
              <div 
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="w-9 h-9 rounded-full bg-gradient-to-br from-red-600 to-purple-600 flex-shrink-0 cursor-pointer border-2 border-gray-800 hover:border-red-600 transition-all flex items-center justify-center text-white font-bold text-xs"
              >
                {user?.name.charAt(0).toUpperCase()}
              </div>
              
              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-48 bg-[#0f0f12] border border-gray-800 rounded-xl shadow-2xl overflow-hidden py-2 animate-in slide-in-from-top-2 duration-200">
                  <div className="px-4 py-2 border-b border-gray-800 mb-2">
                    <p className="text-xs text-gray-400 truncate">{user?.email}</p>
                    <p className="text-sm font-bold text-white">{user?.name}</p>
                  </div>
                  <button className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-800 transition-colors">Meu Perfil</button>
                  <button className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-800 transition-colors">Configurações</button>
                  <button 
                    onClick={() => { logout(); setShowUserMenu(false); }}
                    className="w-full text-left px-4 py-2 text-sm text-red-500 hover:bg-red-500/10 transition-colors mt-2 border-t border-gray-800 pt-2"
                  >
                    Sair
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
