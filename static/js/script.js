// Main JS for Fast Hot - Final Functional Restoration
document.addEventListener('DOMContentLoaded', () => {
    initAuth();
    fetchCategories();
    fetchVideos();
    setupEventListeners();

    // Auto refresh every 60 seconds
    setInterval(fetchVideos, 60000);
});

// --- AUTH & STATE ---
let currentUser = null;
let favoriteIds = [];
let allVideos = [];
let currentCategory = 'All';
let showOnlyFavorites = false;

function initAuth() {
    const session = localStorage.getItem('fasthot_session');
    if (session) {
        currentUser = JSON.parse(session);
        favoriteIds = currentUser.favorites || [];
        updateAuthUI();
    }
}

function updateAuthUI() {
    const authArea = document.getElementById('authArea');
    if (!authArea) return;

    if (currentUser) {
        authArea.innerHTML = `
            <div class="flex items-center gap-3 bg-white/5 border border-white/10 px-3 py-1.5 rounded-full">
                <div class="w-6 h-6 rounded-full bg-red-600 flex items-center justify-center text-[10px] font-black uppercase italic">
                    ${currentUser.name.charAt(0)}
                </div>
                <span class="text-[10px] font-bold text-gray-300 uppercase tracking-widest hidden md:block">${currentUser.name}</span>
                <button onclick="handleLogout()" class="text-gray-500 hover:text-white transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
                </button>
            </div>
        `;
    } else {
        authArea.innerHTML = `
            <button onclick="openLoginModal()" class="bg-red-600 hover:bg-red-700 text-white text-[10px] font-bold px-4 py-2 rounded-full transition-all flex-shrink-0 uppercase tracking-widest">
                Entrar
            </button>
        `;
    }
}

function openLoginModal() {
    document.getElementById('loginModal').classList.remove('hidden');
}

function closeLoginModal() {
    document.getElementById('loginModal').classList.add('hidden');
}

async function handleLogin(email, password) {
    if (!email) return alert("Insira um email");
    const name = email.split('@')[0];
    const user = { email, name: name, favorites: favoriteIds };
    currentUser = user;
    localStorage.setItem('fasthot_session', JSON.stringify(user));
    updateAuthUI();
    closeLoginModal();
    renderVideos(allVideos);
}

function handleLogout() {
    currentUser = null;
    localStorage.removeItem('fasthot_session');
    updateAuthUI();
    renderVideos(allVideos);
}

// --- TOGGLES & SCREENS ---
function toggleAiBox() {
    const aiBox = document.getElementById('aiBox');
    aiBox.classList.toggle('hidden');
    if (!aiBox.classList.contains('hidden')) {
        aiBox.scrollIntoView({ behavior: 'smooth' });
    }
}

function toggleShowOnlyFavorites() {
    showOnlyFavorites = !showOnlyFavorites;
    if (showOnlyFavorites) {
        currentCategory = 'Favorites';
    } else {
        currentCategory = 'All';
    }
    applyScreenState();
    renderCategories();
    renderVideos(allVideos);
}

function applyScreenState() {
    const hero = document.querySelector('section.relative.h-\\[70vh\\], section.relative.h-\\[85vh\\]');
    const aiBox = document.getElementById('aiBox');
    const navFav = document.getElementById('navFavorites');

    // Reset Hero visibility based on category
    if (currentCategory === 'All') {
        if (hero) hero.classList.remove('hidden');
    } else {
        if (hero) hero.classList.add('hidden');
        if (aiBox) aiBox.classList.add('hidden');
    }

    // Toggle Favorite Link Glow
    if (currentCategory === 'Favorites') {
        if (navFav) {
            navFav.classList.add('text-red-500');
            navFav.classList.remove('text-gray-400');
        }
    } else {
        if (navFav) {
            navFav.classList.remove('text-red-500');
            navFav.classList.add('text-gray-400');
        }
    }
}

// --- DATA FETCHING ---
let CATEGORIES = [];
async function fetchCategories() {
    try {
        const response = await fetch('/api/categories');
        CATEGORIES = await response.json();
        renderCategories();
    } catch (e) {
        console.error("Failed to fetch categories:", e);
    }
}

async function fetchVideos() {
    try {
        const response = await fetch('/api/videos');
        if (!response.ok) throw new Error('Network error');
        allVideos = await response.json();
        renderVideos(allVideos);
    } catch (error) {
        console.error('Error fetching videos:', error);
        document.getElementById('videoGrid').innerHTML = '<div class="col-span-full py-20 text-center text-red-500 uppercase font-black tracking-widest">Erro ao carregar vídeos. Verifique se o backend está rodando.</div>';
    }
}

// --- RENDERING ---
function renderVideos(videos) {
    const grid = document.getElementById('videoGrid');
    const shortsGrid = document.getElementById('shortsGrid');
    const shortsSection = document.getElementById('shortsSection');
    const sectionTitle = document.getElementById('sectionTitle');

    if (!grid || !shortsGrid) return;

    if (sectionTitle) {
        let titleText = currentCategory;
        if (currentCategory === 'All') titleText = 'Recomendado para Você';
        if (currentCategory === 'Favorites') titleText = 'Meus Favoritos';
        sectionTitle.innerHTML = `<span class="w-1.5 h-8 bg-red-600 rounded-full"></span> ${titleText}`;
    }

    grid.innerHTML = '';
    shortsGrid.innerHTML = '';

    const searchQuery = document.getElementById('searchInput').value.toLowerCase();

    const filtered = videos.filter(v => {
        const vId = String(v.id || v.file_id);
        const matchesCategory = currentCategory === 'All' ||
            (currentCategory === 'Favorites' ? favoriteIds.includes(vId) : (v.category && v.category === currentCategory));
        const matchesQuery = (v.title && v.title.toLowerCase().includes(searchQuery)) ||
            (v.category && v.category.toLowerCase().includes(searchQuery));
        return matchesCategory && matchesQuery;
    });

    if (filtered.length === 0) {
        grid.innerHTML = '<div class="col-span-full text-gray-700 text-center py-20 uppercase font-black tracking-widest opacity-20 text-4xl italic">Nenhum Vídeo Encontrado</div>';
        shortsSection.classList.add('hidden');
        return;
    }

    const shorts = filtered.filter(v => (v.height || 0) > (v.width || 0));
    const regular = filtered.filter(v => (v.height || 0) <= (v.width || 0) || !v.width);

    // Filtered Content rendering logic
    const renderCard = (video, container, isShort = false) => {
        const vId = String(video.id || video.file_id);
        const isFav = favoriteIds.includes(vId);
        const thumbUrl = video.thumb_id ? `/thumb/${video.thumb_id}` : 'https://placehold.co/600x400/1a1a1a/FFF?text=No+Thumb';

        const card = document.createElement('div');
        if (isShort) {
            card.className = 'group relative aspect-[9/16] bg-[#0f0f12] rounded-2xl overflow-hidden cursor-pointer transition-all duration-300 hover:scale-[1.05] hover:z-10 border border-white/5 hover:border-red-600/50';
            card.innerHTML = `
                <img src="${thumbUrl}" alt="${video.title}" class="w-full h-full object-cover brightness-75 group-hover:brightness-100 transition duration-700 group-hover:scale-110">
                <div class="absolute inset-x-0 bottom-0 p-4 bg-gradient-to-t from-black/90 to-transparent">
                    <h3 class="font-black text-xs truncate text-white mb-1 tracking-tight uppercase italic">${video.title || "Sem Título"}</h3>
                    <div class="flex items-center justify-between text-[8px] text-gray-400 font-bold uppercase tracking-widest">
                        <span>${video.category || "Geral"}</span>
                        <span>${formatDuration(video.duration)}</span>
                    </div>
                </div>
            `;
        } else {
            card.className = 'group relative overflow-hidden rounded-2xl bg-[#0f0f12] border border-white/5 transition-all duration-300 hover:scale-[1.02] hover:border-red-600/50 hover:shadow-[0_0_30px_rgba(220,38,38,0.15)] cursor-pointer';
            card.innerHTML = `
                <div class="aspect-video relative overflow-hidden rounded-xl m-2 bg-black">
                    <img src="${thumbUrl}" alt="${video.title}" class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110 opacity-70 group-hover:opacity-100">
                    <div class="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
                        <div class="bg-red-600 rounded-full p-4 transform scale-75 group-hover:scale-100 transition-transform duration-300">
                            <svg class="w-8 h-8 text-white fill-current" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                        </div>
                    </div>
                </div>
                <div class="p-4 pt-1">
                    <h3 class="text-sm font-black text-white truncate group-hover:text-red-500 transition-colors uppercase tracking-tight italic">${video.title || "Sem Título"}</h3>
                    <div class="flex justify-between items-center mt-2">
                        <span class="text-[10px] text-gray-500 font-black uppercase tracking-widest">${video.category || "Geral"}</span>
                        <span class="text-[10px] text-gray-600 font-bold uppercase tracking-widest">${formatDuration(video.duration)}</span>
                    </div>
                </div>
            `;
        }

        // Action Buttons Overlay (Favorite Button)
        const overlay = document.createElement('div');
        overlay.className = 'absolute top-3 right-3 z-30';
        const favBtn = document.createElement('button');
        favBtn.className = `p-2 rounded-full backdrop-blur-md transition-all ${isFav ? 'bg-red-600 text-white shadow-lg' : 'bg-black/40 text-gray-400 hover:text-white'}`;
        favBtn.innerHTML = `<svg class="w-4 h-4" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path></svg>`;

        favBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleFavorite(vId);
        });

        overlay.appendChild(favBtn);
        card.appendChild(overlay);

        // Core Click Event to open modal
        card.addEventListener('click', () => {
            openModal(video);
        });

        container.appendChild(card);
    };

    // Render Shorts if present
    if (shorts.length > 0 && currentCategory !== 'Favorites') {
        shortsSection.classList.remove('hidden');
        shorts.forEach(v => renderCard(v, shortsGrid, true));
    } else {
        shortsSection.classList.add('hidden');
    }

    // Render Regular Videos
    regular.forEach(v => {
        renderCard(v, grid, false);
    });
}

function renderCategories() {
    const container = document.getElementById('categoryContainer');
    if (!container) return;
    container.innerHTML = `
        <button onclick="filterByCategory('All')" id="cat-All"
            class="px-6 py-2 rounded-full text-sm font-bold transition-all whitespace-nowrap border ${currentCategory === 'All' ? 'bg-red-600 border-red-600 text-white shadow-lg shadow-red-600/30' : 'bg-gray-900 border-white/5 text-gray-400 hover:border-red-600/50 hover:text-white'}">
            Tudo
        </button>
    `;
    CATEGORIES.forEach(cat => {
        const btn = document.createElement('button');
        btn.onclick = () => filterByCategory(cat);
        const isActive = currentCategory === cat;
        btn.className = `px-6 py-2 rounded-full text-sm font-bold transition-all whitespace-nowrap border ${isActive ? 'bg-red-600 border-red-600 text-white shadow-lg shadow-red-600/30' : 'bg-gray-900 border-white/5 text-gray-400 hover:border-red-600/50 hover:text-white'}`;
        btn.textContent = cat;
        container.appendChild(btn);
    });
}

function filterByCategory(category) {
    currentCategory = category;
    showOnlyFavorites = false;
    applyScreenState();
    renderCategories();
    renderVideos(allVideos);
}

// --- MODAL & PLAYER ---
function openModal(video) {
    console.log("Attempting to play video:", video);
    const modal = document.getElementById('videoModal');
    const player = document.getElementById('modalVideo');
    if (!modal || !player) {
        console.error("Modal or player element not found!");
        return;
    }

    const vId = String(video.id || video.file_id);

    // Set metadata safely
    const titleEl = document.getElementById('modalTitle');
    const catEl = document.getElementById('modalCategory');
    const durEl = document.getElementById('modalDuration');
    const sizeEl = document.getElementById('modalSize');

    if (titleEl) titleEl.textContent = video.title || "Vídeo Fast Hot";
    if (catEl) catEl.textContent = video.category || "Geral";
    if (durEl) durEl.textContent = formatDuration(video.duration);
    if (sizeEl) sizeEl.textContent = formatSize(video.file_size);

    // Setup Video source
    player.src = `/stream/${vId}`;
    player.load();

    // Setup Download Link
    const downloadBtn = document.getElementById('modalDownloadBtn');
    if (downloadBtn) downloadBtn.href = `/stream/${vId}`;

    // Update Favorite State in Modal
    updateModalFavoriteState(vId);

    // Show Modal
    modal.classList.remove('hidden');

    // Attempt playback
    player.play().catch(e => {
        console.warn("Autoplay blocked or player error:", e);
        // Sometimes play() fails on mobile/certain browsers without interaction
    });
}

function closeModal() {
    const modal = document.getElementById('videoModal');
    const player = document.getElementById('modalVideo');
    if (player) {
        player.pause();
        player.src = "";
    }
    if (modal) modal.classList.add('hidden');
}

function toggleFavorite(videoId, e) {
    if (e) e.stopPropagation();
    videoId = String(videoId);
    const index = favoriteIds.indexOf(videoId);
    if (index > -1) {
        favoriteIds.splice(index, 1);
    } else {
        favoriteIds.push(videoId);
    }

    if (currentUser) {
        currentUser.favorites = favoriteIds;
        localStorage.setItem('fasthot_session', JSON.stringify(currentUser));
    }

    // Sync UI
    renderVideos(allVideos);
    updateModalFavoriteState(videoId);
}

function updateModalFavoriteState(vId) {
    const modalFavBtn = document.getElementById('modalFavBtn');
    if (!modalFavBtn) return;

    const isFav = favoriteIds.includes(String(vId));
    modalFavBtn.onclick = (e) => toggleFavorite(vId, e);

    modalFavBtn.innerHTML = `
        <svg class="w-6 h-6 ${isFav ? 'text-red-600 fill-current' : 'text-gray-400'}" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path>
        </svg>
    `;
}

// --- AI DISCOVERY ---
async function handleAiDiscovery() {
    const input = document.getElementById('aiInput');
    const prompt = input.value.trim().toLowerCase();
    if (!prompt) return;

    const btn = input.nextElementSibling;
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = "Buscando...";

    try {
        await new Promise(r => setTimeout(r, 800));
        const matches = allVideos.filter(v =>
            (v.title && v.title.toLowerCase().includes(prompt)) ||
            (v.category && v.category.toLowerCase().includes(prompt))
        );

        if (matches.length > 0) {
            renderVideos(matches);
            document.getElementById('recent').scrollIntoView({ behavior: 'smooth' });
        } else {
            const cat = CATEGORIES.find(c => prompt.includes(c.toLowerCase()));
            if (cat) filterByCategory(cat);
        }
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) searchInput.oninput = () => renderVideos(allVideos);
    const aiInput = document.getElementById('aiInput');
    if (aiInput) aiInput.onkeypress = (e) => { if (e.key === 'Enter') handleAiDiscovery(); };
}

function formatDuration(seconds) {
    if (!seconds) return "00:00";
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function formatSize(bytes) {
    if (!bytes) return "0 MB";
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
    return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i];
}
