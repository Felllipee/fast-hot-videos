
import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Header } from './components/Header';
import { VideoCard } from './components/VideoCard';
import { LoginModal } from './components/LoginModal';
import { Video, Category } from './types';
import { MOCK_VIDEOS, CATEGORIES, HERO_VIDEOS } from './constants';
import { getSmartRecommendations } from './geminiService';
import { AuthProvider, useAuth } from './contexts/AuthContext';

const AppContent: React.FC = () => {
  const { user, isAuthenticated, toggleFavorite } = useAuth();
  const [selectedCategory, setSelectedCategory] = useState<Category>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);
  const [aiResponse, setAiResponse] = useState<{text: string, suggestedCategory?: string, highlightVideoTitle?: string} | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [showAiBox, setShowAiBox] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showOnlyFavorites, setShowOnlyFavorites] = useState(false);
  const [bgVideoIndex, setBgVideoIndex] = useState(0);

  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const calculateIndex = () => {
      const thirtyMinutes = 30 * 60 * 1000;
      const index = Math.floor(Date.now() / thirtyMinutes) % HERO_VIDEOS.length;
      setBgVideoIndex(index);
    };

    calculateIndex();
    const interval = setInterval(calculateIndex, 60000);
    return () => clearInterval(interval);
  }, []);

  const filteredVideos = useMemo(() => {
    const userFavorites = user?.favorites || [];
    return MOCK_VIDEOS.filter(v => {
      const matchesCategory = selectedCategory === 'All' || v.category === selectedCategory;
      const matchesSearch = v.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                           v.category.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesFavorites = !showOnlyFavorites || userFavorites.includes(v.id);
      return matchesCategory && matchesSearch && matchesFavorites;
    });
  }, [selectedCategory, searchQuery, showOnlyFavorites, user?.favorites]);

  const regularVideos = filteredVideos.filter(v => !v.isShort);
  const shortVideos = filteredVideos.filter(v => v.isShort);

  const handleAiAsk = async (prompt: string) => {
    if (!prompt.trim()) return;
    setIsAiLoading(true);
    const result = await getSmartRecommendations(prompt);
    setAiResponse(result);
    setIsAiLoading(false);

    // Se a IA sugerir uma categoria, mudamos automaticamente
    if (result.suggestedCategory && CATEGORIES.includes(result.suggestedCategory as Category)) {
      setSelectedCategory(result.suggestedCategory as Category);
      setShowOnlyFavorites(false);
    }
  };

  const onToggleFavorite = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!isAuthenticated) {
      setShowLoginModal(true);
      return;
    }
    toggleFavorite(id);
  };

  const handleOpenFavorites = () => {
    if (!isAuthenticated) {
      setShowLoginModal(true);
      return;
    }
    setShowOnlyFavorites(true);
    const contentElement = document.getElementById('main-content');
    if (contentElement) {
      contentElement.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleCloseModal = () => {
    setSelectedVideo(null);
  };

  return (
    <div className="min-h-screen pb-20">
      <Header 
        onSearch={setSearchQuery} 
        onOpenLogin={() => setShowLoginModal(true)}
        onToggleFavorites={() => setShowOnlyFavorites(!showOnlyFavorites)}
        showOnlyFavorites={showOnlyFavorites}
      />

      <LoginModal isOpen={showLoginModal} onClose={() => setShowLoginModal(false)} />

      {/* Hero Section */}
      <section className="relative h-[65vh] md:h-[80vh] w-full flex items-end justify-start overflow-hidden pt-16">
        <video 
          key={HERO_VIDEOS[bgVideoIndex]}
          className="absolute inset-0 w-full h-full object-cover opacity-50 pointer-events-none"
          autoPlay muted loop playsInline
          src={HERO_VIDEOS[bgVideoIndex]}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#08080a] via-[#08080a]/40 to-transparent"></div>
        <div className="absolute inset-0 bg-gradient-to-r from-[#08080a] via-[#08080a]/20 to-transparent"></div>
        
        <div className="relative z-10 container mx-auto px-6 pb-20 max-w-4xl">
          <div className="flex items-center gap-2 mb-4">
            <span className="bg-red-600 text-white text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-widest">Original</span>
            <span className="text-gray-400 text-xs font-medium">Fast Hot Produções • 2024</span>
          </div>
          <h1 className="text-5xl md:text-8xl font-bold mb-4 tracking-tighter leading-none italic uppercase">
            BEM <br/> <span className="text-red-600 not-italic">VINDO(A)!</span>
          </h1>
          <p className="text-gray-300 text-lg md:text-xl mb-8 max-w-xl font-light">
            Experiência ultra-premium sem censura direto na sua pele. Prazer e puro tesão.
          </p>
          <div className="flex flex-wrap gap-4">
            <button 
              onClick={() => {
                setShowAiBox(true);
                document.getElementById('ai-input-anchor')?.scrollIntoView({ behavior: 'smooth' });
              }}
              className="bg-red-600 text-white hover:bg-red-700 px-8 py-3 rounded-lg font-bold flex items-center gap-3 transition-all transform active:scale-95 shadow-xl shadow-red-600/20"
            >
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Escolha Inteligente
            </button>
            <button 
              onClick={handleOpenFavorites}
              className="bg-gray-800/80 backdrop-blur-md text-white hover:bg-gray-700 px-8 py-3 rounded-lg font-bold flex items-center gap-3 transition-all border border-gray-700"
            >
              <svg className="w-5 h-5 text-red-600 fill-current" viewBox="0 0 24 24">
                <path d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              Meus Favoritos
            </button>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <main id="main-content" className="container mx-auto px-4 md:px-6 relative z-20 -mt-10">
        
        {/* Espaçamento para âncora de scroll */}
        <div id="ai-input-anchor" className="h-4"></div>

        {/* AI Discovery Box Reestilizado */}
        {showAiBox && (
          <div className="mb-12 p-1 bg-gradient-to-r from-red-600/30 to-purple-600/30 rounded-2xl animate-in slide-in-from-bottom-4 duration-500 shadow-2xl">
            <div className="bg-[#0f0f12] rounded-[14px] p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold flex items-center gap-2">
                  <span className="text-red-600 animate-pulse">✨</span> 
                  O que você deseja sentir agora?
                </h2>
                <button onClick={() => { setShowAiBox(false); setAiResponse(null); }} className="text-gray-500 hover:text-white transition-colors">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              </div>
              
              <div className="flex flex-col md:flex-row gap-4">
                <div className="relative flex-grow">
                  <input 
                    type="text"
                    placeholder="Descreva seu fetiche, categoria ou humor..."
                    className="w-full bg-black/40 border border-gray-800 rounded-xl px-4 py-4 text-white placeholder:text-gray-600 focus:outline-none focus:border-red-600 transition-all shadow-inner"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleAiAsk((e.target as HTMLInputElement).value);
                    }}
                  />
                  {isAiLoading && (
                    <div className="absolute right-4 top-1/2 -translate-y-1/2">
                      <div className="w-5 h-5 border-2 border-red-600 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                  )}
                </div>
                <button 
                  className="bg-red-600 hover:bg-red-700 text-white px-8 py-4 rounded-xl font-bold transition-all disabled:opacity-50 whitespace-nowrap shadow-lg shadow-red-600/20"
                  onClick={() => {
                    const input = document.querySelector('#ai-input-anchor + div input') as HTMLInputElement;
                    handleAiAsk(input.value);
                  }}
                  disabled={isAiLoading}
                >
                  {isAiLoading ? 'Explorando...' : 'Encontrar para Mim'}
                </button>
              </div>

              {aiResponse && !isAiLoading && (
                <div className="mt-6 p-5 bg-red-600/5 rounded-xl border border-red-600/10 animate-in fade-in zoom-in duration-300">
                  <p className="text-gray-200 text-lg leading-relaxed mb-3 italic">
                    "{aiResponse.text}"
                  </p>
                  {aiResponse.suggestedCategory && (
                    <div className="flex items-center gap-2 text-xs font-bold text-red-500 uppercase tracking-widest">
                      <span className="w-2 h-2 bg-red-600 rounded-full"></span>
                      Filtrado por: {aiResponse.suggestedCategory}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="flex items-center gap-3 overflow-x-auto hide-scrollbar py-6 mb-4">
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => { setSelectedCategory(cat); setShowOnlyFavorites(false); }}
              className={`px-6 py-2 rounded-full text-sm font-semibold transition-all whitespace-nowrap border ${
                selectedCategory === cat && !showOnlyFavorites
                ? 'bg-red-600 border-red-600 text-white shadow-lg shadow-red-600/30' 
                : 'bg-gray-900 border-gray-800 text-gray-400 hover:border-gray-700 hover:text-white'
              }`}
            >
              {cat === 'All' ? 'Tudo' : cat}
            </button>
          ))}
        </div>

        {!showOnlyFavorites && shortVideos.length > 0 && (
          <section className="mb-12">
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-2 uppercase tracking-tighter">
              <svg className="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 24 24"><path d="M17.74 3.53H6.26c-.7 0-1.27.57-1.27 1.27v14.4c0 .7.57 1.27 1.27 1.27h11.48c.7 0 1.27-.57 1.27-1.27V4.8c0-.7-.57-1.27-1.27-1.27zM9.5 14.5v-5l4.5 2.5-4.5 2.5z"/></svg>
              Vídeos Curtos
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {shortVideos.map(video => (
                <VideoCard 
                  key={video.id} 
                  video={video} 
                  isFavorite={(user?.favorites || []).includes(video.id)}
                  onToggleFavorite={onToggleFavorite}
                  onClick={setSelectedVideo} 
                />
              ))}
            </div>
          </section>
        )}

        <section>
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3 uppercase tracking-tighter">
            <span className="w-1.5 h-8 bg-red-600 rounded-full"></span>
            {showOnlyFavorites ? 'Meus Favoritos' : selectedCategory === 'All' ? 'Recomendado para Você' : `O Melhor de ${selectedCategory}`}
          </h2>
          {regularVideos.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
              {regularVideos.map(video => (
                <VideoCard 
                  key={video.id} 
                  video={video} 
                  isFavorite={(user?.favorites || []).includes(video.id)}
                  onToggleFavorite={onToggleFavorite}
                  onClick={setSelectedVideo} 
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-20 bg-gray-900/50 rounded-2xl border border-gray-800">
              <p className="text-gray-500 italic">
                {showOnlyFavorites ? 'Você ainda não tem favoritos.' : 'Nenhum vídeo encontrado. Tente outro filtro!'}
              </p>
            </div>
          )}
        </section>
      </main>

      {selectedVideo && (
        <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-md flex items-center justify-center p-4 md:p-8 animate-in fade-in duration-300">
          <button 
            onClick={handleCloseModal}
            className="absolute top-6 right-6 text-gray-400 hover:text-white transition-colors z-[110]"
          >
            <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12" /></svg>
          </button>

          <div className="w-full max-w-6xl flex flex-col gap-4">
            <div className={`relative bg-black rounded-2xl overflow-hidden shadow-2xl border border-gray-800 ${selectedVideo.isShort ? 'max-w-md mx-auto aspect-[9/16]' : 'aspect-video w-full'}`}>
              <video 
                ref={videoRef}
                src={selectedVideo.videoUrl} 
                controls 
                autoPlay 
                className="w-full h-full object-contain"
              />
            </div>
            
            <div className="flex flex-col md:flex-row justify-between gap-4 p-4 md:p-0">
              <div className="flex-grow">
                <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">{selectedVideo.title}</h3>
                <div className="flex flex-wrap items-center gap-4 text-sm text-gray-400 font-medium">
                  <span className="bg-red-600/10 text-red-500 border border-red-600/20 px-3 py-0.5 rounded-full">{selectedVideo.category}</span>
                  <span className="flex items-center gap-1.5">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                    {selectedVideo.views} visualizações
                  </span>
                  <span className="flex items-center gap-1.5 text-yellow-500 font-bold">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
                    {selectedVideo.rating}
                  </span>
                </div>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button 
                  onClick={(e) => onToggleFavorite(e, selectedVideo.id)}
                  className={`p-3 rounded-xl transition-all border ${ (user?.favorites || []).includes(selectedVideo.id) ? 'bg-red-600 border-red-600 text-white' : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-white hover:bg-gray-700'}`}
                >
                  <svg className={`w-6 h-6 ${(user?.favorites || []).includes(selectedVideo.id) ? 'fill-current' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/></svg>
                </button>
                <button className="bg-gray-800 hover:bg-gray-700 p-3 rounded-xl transition-colors border border-gray-700"><svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/></svg></button>
                <button className="bg-red-600 hover:bg-red-700 px-6 py-2 rounded-xl font-bold transition-all shadow-lg shadow-red-600/20">Download HD</button>
              </div>
            </div>
          </div>
        </div>
      )}

      <footer className="mt-20 py-12 border-t border-gray-800 bg-[#08080a]">
        <div className="container mx-auto px-6 grid grid-cols-1 md:grid-cols-4 gap-12">
          <div>
            <span className="text-2xl font-bold tracking-tighter uppercase mb-4 block">Fast<span className="text-red-600">Hot</span></span>
            <p className="text-gray-500 text-sm leading-relaxed">
              Fast Hot Premium Streaming. A maior rede de curadoria de conteúdo exclusivo do Telegram direto para o seu navegador.
            </p>
          </div>
          <div>
            <h4 className="font-bold mb-6 text-white uppercase tracking-wider text-xs">Categorias</h4>
            <ul className="space-y-3 text-gray-500 text-sm">
              <li><a href="#" className="hover:text-red-500 transition-colors">Escolhas Amadoras</a></li>
              <li><a href="#" className="hover:text-red-500 transition-colors">Estúdios Profissionais</a></li>
              <li><a href="#" className="hover:text-red-500 transition-colors">Experiência POV</a></li>
              <li><a href="#" className="hover:text-red-500 transition-colors">Hits Globais</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold mb-6 text-white uppercase tracking-wider text-xs">Legal</h4>
            <ul className="space-y-3 text-gray-500 text-sm">
              <li><a href="#" className="hover:text-red-500 transition-colors">Termos de Serviço</a></li>
              <li><a href="#" className="hover:text-red-500 transition-colors">Privacidade</a></li>
              <li><a href="#" className="hover:text-red-500 transition-colors">18 U.S.C. 2257</a></li>
              <li><a href="#" className="hover:text-red-500 transition-colors">Compliance</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold mb-6 text-white uppercase tracking-wider text-xs">Suporte</h4>
            <ul className="space-y-3 text-gray-500 text-sm">
              <li><a href="#" className="hover:text-red-500 transition-colors">Central de Ajuda</a></li>
              <li><a href="#" className="hover:text-red-500 transition-colors">Suporte Telegram</a></li>
              <li><a href="#" className="hover:text-red-500 transition-colors">API para Criadores</a></li>
              <li><a href="#" className="hover:text-red-500 transition-colors">Contato</a></li>
            </ul>
          </div>
        </div>
        <div className="container mx-auto px-6 mt-12 pt-8 border-t border-gray-900 text-center text-gray-600 text-[10px] uppercase tracking-widest">
          © 2024 Fast Hot Media Group. Todos os direitos reservados.
        </div>
      </footer>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
