// script.js for FastHot Premium
let allVideos = [];
let currentCategory = 'Tudo';
let favoriteIds = JSON.parse(localStorage.getItem('fasthot_favorites') || '[]');
let currentPage = 1;
const itemsPerPage = 20;

document.addEventListener('DOMContentLoaded', () => {
    fetchCategories();
    fetchVideos();
    setupEventListeners();
    setInterval(fetchVideos, 60000); // Auto refresh
});

// Detect environment and setup API base
const isGitHub = window.location.hostname.includes('github.io');
const API_BASE = isGitHub ? 'http://35.192.109.211:8080' : window.location.origin;
const DATA_SOURCE = `${API_BASE}/api/videos`;

async function fetchCategories() {
    try {
        // On GitHub, we might need a static categories file or just hardcode/extract from videos
        // For now, if GitHub, we rely on the hardcoded 'Tudo' and maybe generic ones, 
        // or we need a static categories.json. Let's try the local API if not on GitHub.
        const url = isGitHub ? `${API_BASE}/api/categories` : '/api/categories';
        // fallback: If GitHub, we just use the static list defined below or extracted from video list.
        if (isGitHub) {
            // Mock categories for GitHub Pages (Synced with main.py)
            const categories = ["Tudo", "Amador", "Anal", "ASMR", "Asiática", "BBW", "Bi", "Boquete", "Brasileira", "Brazilian", "Bunda Grande", "Casada", "Caseiro", "Coroa", "DP", "Fisting", "Gangbang", "Gay", "Gostosa", "Hardcore", "IA", "Indiano", "Interracial", "Japonesa", "Latina", "Legendado", "Lésbicas", "Lingerie", "Loira", "Madrasta", "Mae", "Magrinha", "Massagem", "Meias", "Milf", "Morena", "Novinhas", "Outros", "Pau grande", "Peitão", "Pov", "Preto", "Profissional", "Ruivas", "Siririca", "Softcore", "Solo", "Squirting", "Transexual"];
            renderCategories(categories.sort((a, b) => a.localeCompare(b, 'pt-BR')));
            return;
        }

        const response = await fetch(url);
        const categories = await response.json();
        renderCategories(categories);
    } catch (e) {
        console.error("Error fetching categories:", e);
        // Fallback
        renderCategories(["Tudo", "Outros"]);
    }
}

async function fetchVideos() {
    // 1. Try to load from LocalStorage (Instant Render)
    const cachedData = localStorage.getItem('cachedVideos');
    if (cachedData) {
        try {
            allVideos = JSON.parse(cachedData);
            updateHero();
            renderVideos();
            console.log("Loaded from cache (Instant!)");
        } catch (e) {
            console.error("Cache corrupted", e);
        }
    }

    try {
        // 2. Fetch Fresh Data (Background Update)
        const response = await fetch(DATA_SOURCE);
        if (!response.ok) throw new Error("Network response was not ok");
        const videos = await response.json();

        // 3. Update if changed
        if (JSON.stringify(videos) !== cachedData) {
            // Sort by ID to ensure newest is first
            allVideos = videos.sort((a, b) => (parseInt(b.id) || 0) - (parseInt(a.id) || 0));
            localStorage.setItem('cachedVideos', JSON.stringify(allVideos));
            updateHero();
            renderVideos();
            console.log("Updated from server");
        }
    } catch (e) {
        console.error("Error fetching videos:", e);
        const grid = document.getElementById('videoGrid');
        if (grid && !allVideos.length) {
            grid.innerHTML = '<div class="col-span-full py-20 text-center text-red-500 font-bold">Erro ao carregar vídeos (Mode: ' + (isGitHub ? 'Static' : 'Local') + ').</div>';
        }
    }
}

function updateHero() {
    if (allVideos.length > 0) {
        const randomIndex = Math.floor(Math.random() * Math.min(5, allVideos.length));
        const heroVideoData = allVideos[randomIndex];

        const heroVideo = document.getElementById('heroVideo');
        if (!heroVideo) return;

        const vId = heroVideoData.id || heroVideoData.file_id;
        // STREAMING URL STRATEGY:
        // Local: /stream/{id}
        // GitHub: http://127.0.0.1:8080/stream/{id} (Requires local server running)
        const streamUrl = `${API_BASE}/stream/${vId}`;

        // Thumbnail: If local, /thumb/{id}. If GitHub, we can't generate. 
        // But we are using Video Tags now, so this matters less for poster.
        const thumbUrl = heroVideoData.thumb_id ? `${API_BASE}/thumb/${heroVideoData.thumb_id}` : 'static/img/no_thumb.png';

        if (heroVideo.dataset.currentId !== vId) {
            heroVideo.dataset.currentId = vId;
            heroVideo.poster = thumbUrl;
            heroVideo.src = streamUrl;
        }
    }
}

function renderCategories(categories) {
    const container = document.getElementById('categoryContainer');
    if (!container) return;

    // Clear dynamic categories but keep "Tudo"
    const tudoBtn = document.getElementById('cat-Tudo');
    container.innerHTML = '';
    if (tudoBtn) container.appendChild(tudoBtn);

    categories.forEach(cat => {
        if (cat === 'Tudo') return;
        const btn = document.createElement('button');
        btn.id = `cat-${cat}`;
        btn.textContent = cat;
        btn.onclick = () => filterByCategory(cat);
        btn.className = getCategoryBtnClass(cat === currentCategory);
        container.appendChild(btn);
    });
}

function getCategoryBtnClass(isActive) {
    return `px-6 py-2 rounded-full text-sm font-bold transition-all whitespace-nowrap border ${isActive
        ? 'bg-red-600 border-red-600 text-white shadow-lg shadow-red-600/30'
        : 'bg-gray-900 border-white/5 text-gray-400 hover:border-red-600/50 hover:text-white'
        }`;
}

function filterByCategory(category) {
    currentCategory = category;
    currentPage = 1; // Reset to page 1
    renderVideos();
    updateCategoryButtons();
}

function toggleShowOnlyFavorites() {
    currentCategory = 'Favoritos';
    currentPage = 1;
    renderVideos();
    updateCategoryButtons();
}

function updateCategoryButtons() {
    // Update category container buttons
    const buttons = document.querySelectorAll('#categoryContainer button');
    buttons.forEach(btn => {
        const cat = btn.textContent;
        // If current is Favoritos, no category btn is active unless we explicitly add a "Favoritos" btn there (we don't)
        // Check if button text matches currentCategory
        const isActive = cat === currentCategory;
        btn.className = getCategoryBtnClass(isActive);
    });

    // Update Header Favorites Button State
    const navFavBtn = document.getElementById('navFavorites');
    if (navFavBtn) {
        if (currentCategory === 'Favoritos') {
            navFavBtn.classList.remove('text-gray-400');
            navFavBtn.classList.add('text-red-500');
        } else {
            navFavBtn.classList.add('text-gray-400');
            navFavBtn.classList.remove('text-red-500');
        }
    }
}

function renderVideos() {
    const grid = document.getElementById('videoGrid');
    const shortsGrid = document.getElementById('shortsGrid');
    const shortsSection = document.getElementById('shortsSection');
    const searchQuery = document.getElementById('searchInput')?.value.toLowerCase() || "";
    const paginationContainer = document.getElementById('paginationContainer');

    if (!grid) return;
    grid.innerHTML = '';
    if (shortsGrid) shortsGrid.innerHTML = '';
    if (paginationContainer) {
        paginationContainer.innerHTML = '';
        paginationContainer.style.display = 'none';
    }

    const filtered = allVideos.filter(v => {
        if (currentCategory === 'Favoritos') {
            const vId = v.id || v.file_id;
            const matchesSearch = (v.title || "").toLowerCase().includes(searchQuery);
            return favoriteIds.includes(vId) && matchesSearch;
        }
        const matchesCategory = currentCategory === 'Tudo' || v.category === currentCategory;
        const matchesSearch = (v.title || "").toLowerCase().includes(searchQuery) || (v.category || "").toLowerCase().includes(searchQuery);
        return matchesCategory && matchesSearch;
    });

    if (filtered.length === 0) {
        grid.innerHTML = '<div class="col-span-full py-20 text-center text-gray-500 italic">Nenhum vídeo encontrado.</div>';
        if (shortsSection) shortsSection.classList.add('hidden');
        return;
    }

    // Pagination logic
    const totalPages = Math.ceil(filtered.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const paginatedItems = filtered.slice(startIndex, startIndex + itemsPerPage);

    const shorts = paginatedItems.filter(v => (v.height || 0) > (v.width || 0));
    const regular = paginatedItems.filter(v => (v.height || 0) <= (v.width || 0) || !v.width);

    if (shorts.length > 0 && shortsSection && shortsGrid) {
        shortsSection.classList.remove('hidden');
        shorts.forEach(v => renderCard(v, shortsGrid, true));
    } else if (shortsSection) {
        shortsSection.classList.add('hidden');
    }

    regular.forEach(v => renderCard(v, grid, false));

    if (totalPages > 1 && paginationContainer) {
        paginationContainer.style.display = 'flex';
        renderPagination(totalPages);
    }
}

function renderPagination(totalPages) {
    const container = document.getElementById('paginationContainer');
    if (!container) return;

    const maxVisible = 10;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);

    if (end - start + 1 < maxVisible) {
        start = Math.max(1, end - maxVisible + 1);
    }

    if (start > 1) {
        addPageBtn(1, container);
        if (start > 2) {
            const span = document.createElement('span');
            span.textContent = '...';
            span.className = 'text-gray-600 px-2';
            container.appendChild(span);
        }
    }

    for (let i = start; i <= end; i++) {
        addPageBtn(i, container);
    }

    if (end < totalPages) {
        if (end < totalPages - 1) {
            const span = document.createElement('span');
            span.textContent = '...';
            span.className = 'text-gray-600 px-2';
            container.appendChild(span);
        }
        addPageBtn(totalPages, container);
    }
}

function addPageBtn(i, container) {
    const btn = document.createElement('button');
    btn.textContent = i;
    btn.onclick = () => {
        currentPage = i;
        renderVideos();
        document.getElementById('recent')?.scrollIntoView({ behavior: 'smooth' });
    };

    const isActive = i === currentPage;
    btn.className = `w-10 h-10 rounded-sm font-bold transition-all ${isActive
        ? 'bg-red-600 text-white'
        : 'bg-[#1a1a1e] text-gray-400 hover:text-white hover:bg-[#2a2a2e]'
        }`;
    container.appendChild(btn);
}


function renderCard(video, container, isShort) {
    const vId = video.id || video.file_id;
    const isFav = favoriteIds.includes(vId);

    // Thumbnail: Use the proxy_thumb endpoint
    // Using video.id (message_id) is prioritized
    const thumbUrl = `${API_BASE}/thumb/${video.id || vId}`;

    const card = document.createElement('div');

    const thumbHtml = `
        <img 
            src="${thumbUrl}" 
            alt="${video.title}"
            class="w-full h-full object-cover brightness-75 group-hover:brightness-100 transition duration-700 group-hover:scale-110"
            loading="lazy"
            onerror="this.src='static/img/no_thumb.png'"
        >
    `;

    if (isShort) {
        card.className = 'group relative aspect-[9/16] bg-[#0f0f12] rounded-2xl overflow-hidden cursor-pointer transition-all duration-300 hover:scale-[1.05] hover:z-10 border border-white/5 hover:border-red-600/50';
        card.innerHTML = `
            ${thumbHtml}
            <div class="absolute inset-x-0 bottom-0 p-4 bg-gradient-to-t from-black/90 to-transparent pointer-events-none">
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
            <div class="aspect-video relative overflow-hidden bg-black">
                ${thumbHtml}
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

    // Attach IntersectionObserver to lazy load video metadata
    const videoEl = card.querySelector('video');
    if (videoEl) {
        lazyLoadVideo(videoEl);
    }

    const favBtn = document.createElement('button');
    favBtn.className = `absolute top-3 right-3 z-30 p-2 rounded-full backdrop-blur-md transition-all ${isFav ? 'bg-red-600 text-white' : 'bg-black/40 text-gray-400 hover:text-white'}`;
    favBtn.innerHTML = `<svg class="w-4 h-4" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path></svg>`;
    favBtn.onclick = (e) => {
        e.stopPropagation();
        toggleFavorite(vId);
    };
    card.appendChild(favBtn);

    card.onclick = () => openModal(video);
    container.appendChild(card);
}

function toggleFavorite(vId) {
    const index = favoriteIds.indexOf(vId);
    if (index > -1) favoriteIds.splice(index, 1);
    else favoriteIds.push(vId);
    localStorage.setItem('fasthot_favorites', JSON.stringify(favoriteIds));
    renderVideos();
}

function openModal(video) {
    const modal = document.getElementById('videoModal');
    const player = document.getElementById('modalVideo');
    if (!modal || !player) return;

    const vId = video.id || video.file_id;
    const streamUrl = `${API_BASE}/stream/${vId}`;

    document.getElementById('modalTitle').textContent = video.title || "Vídeo Fast Hot";
    document.getElementById('modalCategory').textContent = video.category || "Geral";
    document.getElementById('modalDuration').textContent = formatDuration(video.duration);
    document.getElementById('modalSize').textContent = formatSize(video.file_size);
    document.getElementById('modalDownloadBtn').href = streamUrl;

    player.src = streamUrl;
    modal.classList.remove('hidden');
    player.play();
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

function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.oninput = () => {
            currentPage = 1;
            renderVideos();
        };
    }
}

function formatDuration(seconds) {
    if (!seconds) return "00:00";
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function formatSize(bytes) {
    if (!bytes) return "0 MB";
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + ['B', 'KB', 'MB', 'GB', 'TB'][i];
}

// --- Analytics Tracking ---
(function () {
    // URL do Backend (Serveo/Localhost)
    // O usuário deve atualizar isso se o link mudar, ou usar um domínio fixo.
    // Tenta detectar se está rodando localmente ou no GitHub
    let backendUrl = "http://35.192.109.211:8080";

    // Se estiver no GitHub, pode precisar configurar a URL manualmente ou usar a última conhecida
    // Exemplo: const PUBLIC_URL = "https://seu-link.lhr.life";

    // Simple pixel tracking
    try {
        // Tenta usar a URL atual se for compatível, senão usa o fallback
        if (window.location.hostname.includes("lhr.life")) {
            backendUrl = window.location.origin;
        }

        // Se estiver no GitHub, precisamos da URL pública do backend
        if (window.location.hostname.includes("github.io")) {
            // TODO: O usuário precisa definir a URL pública aqui quando ela mudar
            // backendUrl = "https://URL-DO-SERVEO.lhr.life"; 
            console.log("Analytics: Configure a URL do backend no script.js para rastrear do GitHub.");
            return;
        }

        fetch(backendUrl + "/api/track", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ page: window.location.pathname })
        }).catch(e => console.log("Analytics erro:", e));

    } catch (e) {
        console.log("Analytics init erro:", e);
    }
})();
