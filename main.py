import asyncio
import sys

# Set Windows Asyncio Policy at the absolute top
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Force loop creation before any other imports
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import time
import json
import os
import re
import socket
import logging
import uvicorn
import random
import asyncio
import subprocess
import threading
import time
from quart import Quart, render_template, jsonify, Response, redirect, request, send_from_directory
from quart_cors import cors
from pyrogram import Client, filters, idle
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import Config
from utils.logger import setup_logger

logger = setup_logger()
app_web = Quart(__name__)
app_web = cors(app_web, allow_origin="*")

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "videos.json")
if not os.path.exists(os.path.join(BASE_DIR, "data")):
    os.makedirs(os.path.join(BASE_DIR, "data"))

THUMBS_DIR = os.path.join(BASE_DIR, "data", "thumbnails")
os.makedirs(THUMBS_DIR, exist_ok=True)
if not os.path.exists(THUMBS_DIR):
    os.makedirs(THUMBS_DIR)

# Helper to get local IP for mobile access
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

PUBLIC_IP_VM = "35.192.109.211" 

def get_base_url():
    # Priority 1: .env BASE_URL (if it's not the wrong internal IP)
    env_url = Config.BASE_URL
    if env_url and "192.168" not in env_url and "127.0.0.1" not in env_url:
        return env_url
    # Priority 2: Hardcoded Public IP (Fail-safe)
    return f"http://{PUBLIC_IP_VM}:{Config.PORT}"

BASE_URL = get_base_url()
GITHUB_URL = "https://felllipee.github.io/fast-hot-videos/"

# Universal Categories (Sync between Bot and Web)
CATEGORIES = sorted([
    "Tudo", "Amador", "Profissional", "Latina", "Brazilian", "Pov", "Hardcore", "Softcore",
    "Anal", "Asiática", "ASMR", "BBW", "Bi", "Boquete", "Brasileira", "Bunda Grande", "Casada", 
    "Caseiro", "Coroa", "DP", "Fisting", "Gangbang", "Gay", "Gostosa", "IA", "Indiano", "Interracial", 
    "Japonesa", "Legendado", "Lésbicas", "Lingerie", "Loira", "Madrasta", "Mae", "Magrinha", 
    "Massagem", "Meias", "Milf", "Morena", "Novinhas", "Pau grande", "Peitão", "Preto", "Ruivas", 
    "Siririca", "Solo", "Squirting", "Transexual", "Outros"
])

def clean_filename(name):
    if not name: return "Sem Título"
    # Remove numbers and extensions, then clean up spaces
    name = re.sub(r'\d+', '', name)
    name = re.sub(r'\.(mp4|mkv|avi|mov)$', '', name, flags=re.I)
    return name.replace('_', ' ').replace('-', ' ').strip() or "Sem Título"

# Global Client Placeholder (Typed as Client | None for Pyre)
bot: Client = None # type: ignore
# In-memory session state
user_states: dict = {}

# Rate Limiter Semaphore (Limits concurrent thumbnail downloads to prevent FloodWait)
thumb_semaphore = asyncio.Semaphore(2)

# In-Memory Cache
VIDEOS_CACHE = None
LAST_LOAD_TIME = 0
CACHE_DURATION = 60 # seconds

def load_videos(force=False):
    global VIDEOS_CACHE, LAST_LOAD_TIME
    now = time.time()
    
    # Return cache if valid
    if VIDEOS_CACHE is not None and not force and (now - LAST_LOAD_TIME < CACHE_DURATION):
        return VIDEOS_CACHE

    # Otherwise load from disk
    if not os.path.exists(DATA_FILE):
        VIDEOS_CACHE = []
    else:
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                VIDEOS_CACHE = data if isinstance(data, list) else []
        except json.JSONDecodeError:
            VIDEOS_CACHE = []
            
    LAST_LOAD_TIME = now
    return VIDEOS_CACHE

def save_videos(videos):
    global VIDEOS_CACHE, LAST_LOAD_TIME
    # Update Cache immediately
    VIDEOS_CACHE = videos
    LAST_LOAD_TIME = time.time()
    
    # Write to disk
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=4, ensure_ascii=False)

def save_video_entry(entry):
    videos = load_videos()
    v_id = entry.get('id')
    v_unique_id = entry.get('file_unique_id')
    # Check if video already exists by file_unique_id to avoid duplicates
    if any(v.get('file_unique_id') == v_unique_id for v in videos):
        logger.info(f"Save: Skipping duplicate video {v_unique_id}")
        return
    videos.insert(0, entry)
    save_videos(videos)
    logger.info(f"Save: Successfully saved video {v_id} to database")

def delete_video_by_id(video_id):
    videos = load_videos()
    new_videos = [v for v in videos if str(v.get('id')) != str(video_id)]
    if len(new_videos) != len(videos):
        save_videos(new_videos)
        return True
    return False

# Global shutdown event
shutdown_event = asyncio.Event()

async def prefetch_thumbnails():
    """Background task to slowly download missing thumbnails to warm up cache."""
    logger.info("Starting Background Thumbnail Prefetcher...")
    while not shutdown_event.is_set():
        try:
            if not bot or not bot.is_connected:
                # Use wait_for to be responsive to shutdown
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=5)
                except asyncio.TimeoutError:
                    pass
                continue

            videos = load_videos()
            missing_thumbs = []
            
            for v in videos:
                if shutdown_event.is_set(): break
                vid_id = v.get('id')
                thumb_path = os.path.join(THUMBS_DIR, f"{vid_id}.jpg")
                if not os.path.exists(thumb_path):
                    missing_thumbs.append(v)

            if not missing_thumbs:
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=60)
                except asyncio.TimeoutError:
                    pass
                continue
                
            logger.info(f"Prefetcher: Found {len(missing_thumbs)} missing thumbnails. Processing...")
            
            for v in missing_thumbs:
                if shutdown_event.is_set(): break
                vid_id = v.get('id')
                thumb_path = os.path.join(THUMBS_DIR, f"{vid_id}.jpg")
                
                if os.path.exists(thumb_path): continue
                    
                file_id = v.get('file_id')
                thumb_file_id = v.get('thumb_id')
                
                try:
                    if thumb_file_id:
                        await bot.download_media(thumb_file_id, file_name=thumb_path)
                    elif v.get('message_id'):
                        msg = await bot.get_messages(Config.BIN_CHANNEL, int(v.get('message_id')))
                        if msg.video and msg.video.thumbs:
                             await bot.download_media(msg.video.thumbs[0].file_id, file_name=thumb_path)
                    
                    if os.path.exists(thumb_path):
                        logger.info(f"Prefetched thumb for {vid_id}")
                    
                    # Responsive sleep
                    try:
                        await asyncio.wait_for(shutdown_event.wait(), timeout=random.uniform(3.0, 6.0))
                    except asyncio.TimeoutError:
                        pass
                    
                except Exception as e:
                    logger.warning(f"Prefetch failed for {vid_id}: {e}")
                    try:
                        await asyncio.wait_for(shutdown_event.wait(), timeout=10)
                    except asyncio.TimeoutError:
                        pass
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Prefetcher Loop Error: {e}")
            await asyncio.sleep(5)
    logger.info("Prefetcher stopped.")

# --- STREAMING UTILITIES ---
async def stream_video_from_telegram(identifier: str, file_id: str, start: int, end: int | None, status_code: int, headers: dict):
    """
    Streams a video file from Telegram using Pyrogram's stream_media.
    Optimized for efficient chunking and includes error handling.
    """
    PYRO_CHUNK_SIZE = 512 * 1024 # 512KB chunks for lower memory spikes on 1GB RAM VMs
    
    try:
        offset_chunks = start // PYRO_CHUNK_SIZE
        start_in_chunk = start % PYRO_CHUNK_SIZE
        
        stream = bot.stream_media(
            file_id,
            offset=offset_chunks,
            limit=0 
        )
        
        async def stream_chunks():
            first = True
            bytes_sent = 0
            to_send = (end - start + 1) if end is not None else None
            
            # For very small videos (like 2s), ensure we don't get stuck in chunking
            # If we know the total size and it's small, we could potentially yield everything immediately,
            # but Pyrogram's stream_media is already chunked. 
            # We just need to make sure we yield chunks as they come.
            
            try:
                async for chunk in stream:
                    # Adjust first chunk for byte offset
                    if first:
                        if start_in_chunk > 0:
                            chunk = chunk[start_in_chunk:]
                        first = False
                    
                    chunk_len = len(chunk)
                    
                    # Truncate last chunk if we have a limit
                    if to_send is not None:
                        if bytes_sent + chunk_len > to_send:
                            chunk = chunk[:to_send - bytes_sent]
                            yield chunk
                            break
                    
                    yield chunk
                    bytes_sent += chunk_len
                    
            except Exception as e:
                logger.error(f"Stream chunk error: {e}")

        # Add appropriate headers for caching and type
        headers["Cache-Control"] = "no-cache"
        headers["X-Content-Type-Options"] = "nosniff"
        headers["Accept-Ranges"] = "bytes"
        headers["Connection"] = "keep-alive"

        return Response(stream_chunks(), status=status_code, headers=headers)

    except Exception as e:
        logger.error(f"Error streaming video {identifier}: {e}")
        return "Error during streaming", 500

# --- BOT HANDLERS ---

async def start_handler(client: Client, message: Message):
    from pyrogram.types import ReplyKeyboardMarkup
    await message.reply_text(
        "👋 **Olá! Bem-vindo ao Fast Hot!**\n\n"
        "Envie-me um **vídeo** para postar no site ou use o menu abaixo para gerenciar seus vídeos.",
        reply_markup=ReplyKeyboardMarkup(
            [["📋 Meus Vídeos", "🌐 Ver Site"], ["📦 Em Massa", "⚙️ Menu"]],
            resize_keyboard=True
        )
    )

async def menu_handler(client: Client, message: Message):
    await message.reply_text(
        "⚙️ **Menu de Gerenciamento**\n\n"
        "Escolha uma opção para gerenciar seu conteúdo no site:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Iniciar Envio em Massa", callback_data="start_bulk")],
            [InlineKeyboardButton("🗑️ Apagar em Massa (por Data)", callback_data="list_bulk_delete")],
            [InlineKeyboardButton("📋 Listar Meus Vídeos", callback_data="list_videos")]
        ])
    )

async def list_videos_func(client: Client, user_id: int, message_to_edit=None, page=0):
    videos = load_videos()
    user_videos = [v for v in videos if v.get('user_id') == user_id or v.get('user_id') is None]
    
    if not user_videos:
        text = "📭 Nenhum vídeo encontrado."
        if message_to_edit:
            await message_to_edit.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="back_start")]]))
        else:
            await client.send_message(user_id, text)
        return

    PAGE_SIZE = 5
    total_pages = (len(user_videos) + PAGE_SIZE - 1) // PAGE_SIZE
    
    # Ensure page is within bounds
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    current_page_videos = user_videos[start_idx:end_idx]
    
    text = f"📋 **Seus Vídeos ({len(user_videos)}):**\n\nPágina {page + 1}/{total_pages}\nClique em um vídeo para gerenciar:"
    
    buttons = []
    for v in current_page_videos:
        title = v.get('title', 'Sem Título')
        # Truncate title if too long
        if len(title) > 30: title = title[:27] + "..."
        buttons.append([InlineKeyboardButton(f"🎥 {title}", callback_data=f"view_{v.get('id')}")])
    
    # Navigation Buttons
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"list_videos_page_{page-1}"))
    
    # Find middle button (Page indicator or just spacer)
    nav_row.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Próximo ➡️", callback_data=f"list_videos_page_{page+1}"))
        
    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton("🔙 Voltar", callback_data="back_start")])
    
    if message_to_edit:
        await message_to_edit.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await client.send_message(user_id, text, reply_markup=InlineKeyboardMarkup(buttons))

async def video_handler_func(client: Client, message: Message):
    if not message.video:
        return
    
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    try:
        forwarded_msg = await message.forward(Config.BIN_CHANNEL)
        
        # BULK MODE LOGIC
        if state and state.get("step") == "BULK_MODE":
            from datetime import datetime
            
            # Import categorizer here to avoid circular imports if any
            from utils.categorizer import detect_category
            
            bulk_id = state.get("bulk_id")
            title = clean_filename(message.video.file_name)
            category = state.get("category", "Outros")
            
            # AUTO-DETECT Logic
            if category == "AUTO":
                category = detect_category(title)
                
                # Log unknown categories
                if category == "Outros":
                    try:
                        with open("uncategorized.log", "a", encoding="utf-8") as log_file:
                            log_file.write(f"{title}\n")
                    except Exception as e:
                        print(f"⚠️ Failed to Log: {e}")
            
            video_entry = {
                "id": str(forwarded_msg.id),
                "file_id": message.video.file_id,
                "file_unique_id": message.video.file_unique_id,
                "file_name": message.video.file_name,
                "file_size": message.video.file_size,
                "duration": message.video.duration,
                "thumb_id": message.video.thumbs[0].file_id if message.video.thumbs else None,
                "width": message.video.width,
                "height": message.video.height,
                "message_id": forwarded_msg.id,
                "user_id": user_id,
                "title": title,
                "category": category,
                "bulk_id": bulk_id
            }
            save_video_entry(video_entry)
            await message.reply_text(f"✅ **Postado (Massa):** `{title}`")
            return

        # NORMAL MODE
        logger.info(f"Bot: Video received from {user_id} (ID: {forwarded_msg.id}). Pending post.")
        stream_link = f"{BASE_URL}/stream/{forwarded_msg.id}"
        await message.reply_text(
            f"✅ **Vídeo Recebido!**\n\n📁 **Arquivo:** `{message.video.file_name or 'Sem Nome'}`\n💾 **Tamanho:** {message.video.file_size} bytes\n\n🌐 **Site (Mais Rápido):** {BASE_URL}\n📡 **Site (GitHub):** {GITHUB_URL}\n\n⚡️ *Dica: Use o site da VM para reprodução instantânea!*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Stream", url=stream_link), InlineKeyboardButton("⬇️ Download", url=stream_link)],
                [InlineKeyboardButton("📤 Postar no Site", callback_data=f"post_{forwarded_msg.id}")],
                [InlineKeyboardButton("📋 Meus Vídeos", callback_data="list_videos")]
            ])
        )
    except Exception as e:
        logger.error(f"Bot: Error handling video from {user_id}: {e}")
        await message.reply_text("Erro ao processar vídeo.")

async def post_callback_func(client: Client, callback_query: CallbackQuery):
    if not callback_query.matches:
        return
    message_id = int(callback_query.matches[0].group(1))
    user_id = callback_query.from_user.id
    try:
        bin_msg: Message = await client.get_messages(Config.BIN_CHANNEL, message_id)
        if not bin_msg or not bin_msg.video:
            await callback_query.answer("Vídeo não encontrado.", show_alert=True)
            return
        user_states[user_id] = {
            "step": "WAITING_TITLE",
            "video_data": {
                "id": str(message_id),
                "file_id": bin_msg.video.file_id,
                "file_unique_id": bin_msg.video.file_unique_id,
                "file_name": bin_msg.video.file_name,
                "file_size": bin_msg.video.file_size,
                "duration": bin_msg.video.duration,
                "thumb_id": bin_msg.video.thumbs[0].file_id if bin_msg.video.thumbs else None,
                "width": bin_msg.video.width,
                "height": bin_msg.video.height,
                "message_id": message_id,
                "user_id": user_id
            }
        }
        await callback_query.message.reply_text(
            "📝 Qual o **Título** do vídeo?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Ver Meus Vídeos", callback_data="list_videos")]])
        )
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await callback_query.answer("Erro ao iniciar postagem.", show_alert=True)

async def text_handler_func(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Handle menu buttons
    if message.text == "📋 Meus Vídeos":
        await list_videos_func(client, user_id)
        return
    elif message.text == "🌐 Ver Site":
        await message.reply_text(f"🚀 **Site (Velocidade Máxima):** {BASE_URL}\n\n📡 **Site (GitHub):** {GITHUB_URL}\n\n⚠️ *Nota: O link da VM é mais rápido no carregamento dos vídeos.*")
        return
    elif message.text == "📦 Em Massa":
        await menu_handler(client, message)
        return
    elif message.text == "⚙️ Menu" or message.text == "/menu":
        await menu_handler(client, message)
        return

    state = user_states.get(user_id)
    if not state: return
    
    if state.get("step") == "WAITING_TITLE":
        video_data = state.get("video_data")
        if not isinstance(video_data, dict): return
        video_data["title"] = (message.text or "").strip()
        state["step"] = "WAITING_CATEGORY"
        
        buttons = []
        row = []
        for cat in CATEGORIES:
            row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row: buttons.append(row)
        await message.reply_text("Escolha a **Categoria**:", reply_markup=InlineKeyboardMarkup(buttons))
    
    elif state.get("step") == "WAITING_BULK_CATEGORY":
        category = (message.text or "Outros").strip()
        from datetime import datetime
        bulk_id = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_states[user_id] = {
            "step": "BULK_MODE",
            "category": category,
            "bulk_id": bulk_id
        }
        await message.reply_text(
            f"🚀 **Modo Envio em Massa Ativado!**\n\n📌 **Categoria:** {category}\n📅 **ID do Lote:** `{bulk_id}`\n\nTodos os vídeos que você enviar agora serão postados AUTOMATICAMENTE.\n\nPara parar, use /start ou clique em um botão do menu.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Parar Envio em Massa", callback_data="back_start")]])
        )

async def category_callback_func(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    state = user_states.get(user_id)
    if not state or state.get("step") != "WAITING_CATEGORY" or not callback_query.matches:
        return
        
    category = callback_query.matches[0].group(1)
    video_data = state.get("video_data")
    if not isinstance(video_data, dict):
        return

    video_data["category"] = category
    save_video_entry(video_data)
    video_title = video_data.get("title", "Sem Título")
    user_states.pop(user_id, None)
    await callback_query.message.edit_text(
        f"✅ **Postado!**\n\n📌 **{video_title}** ({category})\n\nVeja em: {BASE_URL}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Ver Meus Vídeos", callback_data="list_videos")],
            [InlineKeyboardButton("🌐 Ver Site", url=BASE_URL)]
        ])
    )

async def manage_callback_func(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if data == "list_videos":
        await list_videos_func(client, user_id, callback_query.message, page=0)
    
    elif data.startswith("list_videos_page_"):
        page = int(data.split("_")[-1])
        await list_videos_func(client, user_id, callback_query.message, page=page)
    
    elif data == "back_start":
        user_states.pop(user_id, None)
        await callback_query.message.edit_text(
            "👋 **Fast Hot Bot!**\n\nUse o menu abaixo:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 Em Massa", callback_data="start_bulk")],
                [InlineKeyboardButton("🌐 Ver Site", url=BASE_URL)]
            ])
        )

    elif data == "start_bulk":
        user_states[user_id] = {"step": "WAITING_BULK_CATEGORY"}
        buttons = []
        # Add Automatic Option First
        buttons.append([InlineKeyboardButton("🤖 Automática (I.A. Lite)", callback_data="bulkcat_AUTO")])
        
        row = []
        for cat in CATEGORIES:
            row.append(InlineKeyboardButton(cat, callback_data=f"bulkcat_{cat}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 Voltar", callback_data="back_start")])
        await callback_query.message.edit_text("Para o envio em massa, escolha a **Categoria**:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("bulkcat_"):
        category = data.split("_")[1]
        from datetime import datetime
        bulk_id = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_states[user_id] = {
            "step": "BULK_MODE",
            "category": category,
            "bulk_id": bulk_id
        }
        await callback_query.message.edit_text(
            f"🚀 **Modo Envio em Massa Ativado!**\n\n📌 **Categoria:** {category}\n📅 **ID do Lote:** `{bulk_id}`\n\nEnvie os vídeos agora!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Parar", callback_data="back_start")]])
        )

    elif data == "list_bulk_delete":
        videos = load_videos()
        bulk_ids = sorted(list(set(v.get('bulk_id') for v in videos if v.get('bulk_id'))), reverse=True)
        if not bulk_ids:
            await callback_query.answer("Nenhum lote de envio em massa encontrado.", show_alert=True)
            return
        
        buttons = []
        for bid in bulk_ids:
            # Count videos in this bulk
            count = len([v for v in videos if v.get('bulk_id') == bid])
            buttons.append([InlineKeyboardButton(f"📅 {bid} ({count} vídeos)", callback_data=f"conf_delbulk_{bid}")])
        
        buttons.append([InlineKeyboardButton("🔙 Voltar", callback_data="back_start")])
        await callback_query.message.edit_text("🗑️ **Apagar Envio em Massa**\n\nEscolha o lote para apagar permanentemente:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("conf_delbulk_"):
        bulk_id = data.replace("conf_delbulk_", "")
        await callback_query.message.edit_text(
            f"⚠️ **TEM CERTEZA?**\n\nVocê está prestes a apagar TODOS os vídeos do lote `{bulk_id}`.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ SIM, APAGAR TUDO", callback_data=f"exec_delbulk_{bulk_id}")],
                [InlineKeyboardButton("❌ CANCELAR", callback_data="list_bulk_delete")]
            ])
        )

    elif data.startswith("exec_delbulk_"):
        bulk_id = data.replace("exec_delbulk_", "")
        videos = load_videos()
        new_videos = [v for v in videos if v.get('bulk_id') != bulk_id]
        deleted_count = len(videos) - len(new_videos)
        save_videos(new_videos)
        await callback_query.answer(f"✅ {deleted_count} vídeos removidos!", show_alert=True)
        await callback_query.message.edit_text("✅ Lote removido com sucesso.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="back_start")]]))

    elif data.startswith("view_"):
        video_id = data.split("_")[1]
        videos = load_videos()
        video = next((v for v in videos if str(v.get('id')) == video_id), None)
        if not video:
            await callback_query.answer("Vídeo não encontrado.", show_alert=True)
            return
        
        await callback_query.message.edit_text(
            f"🎬 **Detalhes do Vídeo**\n\n"
            f"📌 **Título:** {video.get('title')}\n"
            f"📂 **Categoria:** {video.get('category')}\n"
            f"💾 **Tamanho:** {video.get('file_size')} bytes",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑 Deletar Este Vídeo", callback_data=f"del_{video_id}")],
                [InlineKeyboardButton("🔙 Voltar para Lista", callback_data="list_videos")]
            ])
        )

    elif data.startswith("del_"):
        video_id = data.split("_")[1]
        if delete_video_by_id(video_id):
            await callback_query.answer("✅ Vídeo removido!")
            await list_videos_func(client, user_id, callback_query.message)
        else:
            await callback_query.answer("❌ Erro ao deletar ou vídeo não encontrado.", show_alert=True)

# --- WEB ROUTES ---

@app_web.route("/")
async def index():
    return await send_from_directory(".", "index.html")

@app_web.route("/<path:path>")
async def static_proxy(path):
    # This serves files from the template directory as if they were static files
    # to support the relative links in index.html
    template_dir = os.path.join("templates", "fast-hot-premium---streaming-dashboard")
    file_path = os.path.join(template_dir, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        from quart import send_from_directory
        return await send_from_directory(template_dir, path)
    return "Not Found", 404

@app_web.route("/api/videos")
async def api_videos():
    videos = load_videos()
    logger.info(f"API: Serving {len(videos)} videos")
    return jsonify(videos)

@app_web.route("/api/categories")
async def api_categories():
    videos = load_videos()
    used_cats = set(v.get('category').strip() for v in videos if v.get('category'))
    # Filter CATEGORIES to keep order but only show those that have content (or is 'Tudo')
    active_categories = [cat for cat in CATEGORIES if cat == "Tudo" or cat in used_cats]
    return jsonify(active_categories)


@app_web.route("/stream/<identifier>")
async def stream_video(identifier):
    if not bot:
        return "Bot not initialized", 500
    try:
        file_id = None
        file_size = 0

        # Try to treat identifier as message_id first (numeric)
        if identifier.isdigit():
            msg_id = int(identifier)
            try:
                msg: Message = await bot.get_messages(Config.BIN_CHANNEL, msg_id)
                if msg and msg.video:
                    file_id = msg.video.file_id
                    file_size = msg.video.file_size
            except Exception as e:
                logger.warning(f"Failed to get message {msg_id} from bin: {e}")

        # If not found by message_id, it might be a file_id directly or a string ID
        if not file_id:
            videos = load_videos()
            # Normalize identifier: check if it's in the list as ID or file_id
            video = next((v for v in videos if str(v.get('id')) == identifier or 
                                              v.get('file_id') == identifier or 
                                              v.get('file_unique_id') == identifier), None)
            if video:
                file_id = video.get('file_id')
                file_size = video.get('file_size', 0)
            else:
                # If still not found, but looks like a likely file_id (long string)
                if len(identifier) > 20: 
                    file_id = identifier
                    # Try to find file_size from ANY entry with this file_id
                    v_fid = next((v for v in videos if v.get('file_id') == identifier), None)
                    if v_fid:
                        file_size = v_fid.get('file_size', 0)
                
        if not file_id:
            return "Video not found", 404
        
        range_header = request.headers.get("Range")
        
        start = 0
        end = file_size - 1 if file_size > 0 else None
        status_code = 200

        if range_header and file_size > 0:
            match = re.search(r"bytes=(\d+)-(\d*)", range_header)
            if match:
                start = int(match.group(1))
                if match.group(2):
                    end = int(match.group(2))
                status_code = 206

        headers = {
            "Content-Type": "video/mp4",
            "Accept-Ranges": "bytes",
        }
        
        if end is not None:
             headers["Content-Length"] = str(end - start + 1)

        if range_header:
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            
        return await stream_video_from_telegram(identifier, file_id, start, end, status_code, headers)
    except Exception as e:
        logger.error(f"Stream error: {e}")
        return str(e), 500

# Thumbnail generation via CV2 removed to save memory (OOM avoidance)

@app_web.route("/static/<path:filename>")
async def static_files(filename):
    return await send_from_directory("static", filename)

@app_web.route("/thumb/<identifier>")
async def proxy_thumb(identifier):
    if not identifier or identifier in ("None", "null"):
        return await send_from_directory(os.path.join("static", "img"), "no_thumb.png")
    
    # Check if we have it locally first (cached)
    # Using a hash of the file_id for non-numeric identifiers to avoid long filenames or invalid chars
    safe_name = identifier if identifier.isdigit() else str(hash(identifier))
    thumb_path = os.path.join(THUMBS_DIR, f"{safe_name}.jpg")
    
    if os.path.exists(thumb_path):
        from quart import send_file
        return await send_file(thumb_path)

    # If it's not local, try to get it from Telegram
    if bot and bot.is_connected:
        try:
            async with thumb_semaphore:
                file_id_to_download = None
                
                if identifier.isdigit():
                    # It's a message ID
                    msg = await bot.get_messages(Config.BIN_CHANNEL, int(identifier))
                    if msg and msg.video and msg.video.thumbs:
                        file_id_to_download = msg.video.thumbs[0].file_id
                else:
                    # It looks like a file_id itself
                    file_id_to_download = identifier

                if file_id_to_download:
                    await bot.download_media(file_id_to_download, file_name=thumb_path)
                    if os.path.exists(thumb_path):
                        from quart import send_file
                        return await send_file(thumb_path)
        except Exception as e:
            logger.warning(f"Failed to fetch thumb {identifier}: {e}")
    
    # Fallback to default
    return await send_from_directory(os.path.join("static", "img"), "no_thumb.png")

@app_web.route("/health")
async def health_check():
    bot_status = "uninitialized"
    bot_me = None
    if bot:
        bot_status = "connected" if bot.is_connected else "disconnected"
        if bot.is_connected:
            me = await bot.get_me()
            bot_me = f"@{me.username}"
    
    return jsonify({
        "status": "ok",
        "bot": {
            "status": bot_status,
            "me": bot_me
        },
        "local_ip": LOCAL_IP,
        "base_url": BASE_URL
    })

# --- SERVEO AUTO-RECONNECT (Added as requested) ---
def start_serveo_thread():
    if "--serveo" not in sys.argv:
        return

    def run_serveo():
        logger.info("🚀 Iniciando Serveo com reconexão automática...")
        while True:
            try:
                # SWITCHED TO LOCALHOST.RUN (More stable)
                cmd = [
                    'ssh',
                    '-tt',
                    '-o', 'ServerAliveInterval=60',
                    '-o', 'ServerAliveCountMax=3',
                    '-o', 'StrictHostKeyChecking=no', # Avoid prompt
                    '-R', f'80:localhost:{Config.PORT}',
                    'nokey@localhost.run'
                ]
                
                # Redirect stdout/stderr to file to capture URL reliably
                with open("serveo.log", "w") as log_file: # Keep same log name for simplicity
                    process = subprocess.Popen(
                        cmd, 
                        stdout=log_file, 
                        stderr=log_file, 
                        text=True,
                        bufsize=1
                    )
                
                logger.info("Tunnel process started (localhost.run). Monitoring log for URL...")
                
                # Monitor the log file
                start_time = time.time()
                found_url = False
                while time.time() - start_time < 30: 
                    if not os.path.exists("serveo.log"):
                        time.sleep(0.5)
                        continue
                        
                    with open("serveo.log", "r") as f:
                        content = f.read()
                    
                    # localhost.run output: "https://<subdomain>.lhr.life" or "http://..."
                    if "lhr.life" in content:
                         url_match = re.search(r'https?://[^\s]+\.lhr\.life', content)
                         if url_match:
                             url = url_match.group(0)
                             logger.info(f"🌍 Public URL: {url}")
                             print(f"\n\n{'='*40}\n🌍 PUBLIC URL: {url}\n{'='*40}\n\n")
                             found_url = True
                             break
                    
                    if process.poll() is not None:
                        break
                    time.sleep(1)
                
                if not found_url:
                     logger.warning("Tunnel URL not found in logs yet.")

                # Wait for process to end
                exit_code = process.wait()
                
                logger.warning(f"Serveo process exited with code {exit_code}. Reconectando em 30s...")
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Erro no Serveo: {e}. Tentando reconectar em 30s...")
                time.sleep(30)

    # Run in a daemon thread so it doesn't block the main loop and dies with the app
    t = threading.Thread(target=run_serveo, daemon=True)
    t.start()

# --- STARTUP ---

async def start_app():
    global bot
    logger.info("Starting Unified App Components...")
    
    import pyrogram
    logger.info(f"TgCrypto Status: {'INSTALLED (Turbo Active)' if pyrogram.crypto else 'MISSING (Slow Mode)'}")

    bot = Client(
        "bot_session",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        sleep_threshold=60
    )
    
    # Register handlers
    bot.add_handler(MessageHandler(start_handler, filters.command("start") & filters.private))
    bot.add_handler(MessageHandler(menu_handler, filters.command("menu") & filters.private))
    bot.add_handler(MessageHandler(lambda c, m: list_videos_func(c, m.from_user.id), filters.command("meus_videos") & filters.private))
    bot.add_handler(MessageHandler(video_handler_func, filters.video & filters.private))
    bot.add_handler(CallbackQueryHandler(post_callback_func, filters.regex(r"^post_(\d+)")))
    bot.add_handler(MessageHandler(text_handler_func, filters.text & filters.private))
    bot.add_handler(CallbackQueryHandler(category_callback_func, filters.regex(r"^cat_(.+)")))
    bot.add_handler(CallbackQueryHandler(manage_callback_func, filters.regex(r"^(list_videos|list_videos_page_|back_start|view_|del_|start_bulk|bulkcat_|list_bulk_delete|conf_delbulk_|exec_delbulk_)")))
    
    await bot.start()
    
    # Set Bot Commands for the menu
    from pyrogram.types import BotCommand
    await bot.set_bot_commands([
        BotCommand("start", "Inicia o bot e mostra o menu"),
        BotCommand("menu", "Menu de gerenciamento e envio em massa"),
        BotCommand("meus_videos", "Lista seus vídeos postados")
    ])
    
    me = await bot.get_me()
    logger.info(f"Bot started as {me.first_name} (@{me.username})")
    
    config = uvicorn.Config(app_web, host="0.0.0.0", port=Config.PORT, log_level="info", loop="asyncio")
    server = uvicorn.Server(config)
    
    logger.info(f"Local IP: {PUBLIC_IP_VM}")
    print(f"Site Disponivel em: {BASE_URL}")
    logger.info(f"Site available at: {BASE_URL}")

    # Start Background Tasks
    # asyncio.create_task(prefetch_thumbnails()) # Disabled per user request
    # start_serveo_thread() # Disabled as it can cause conflicts
    
    try:
        await asyncio.gather(server.serve(), idle())
    finally:
        await bot.stop()


# --- ANALYTICS SYSTEM (Real & Persistent) ---
STATS_FILE = os.path.join(BASE_DIR, "data", "stats.json")

# Initialize or Load Stats
if os.path.exists(STATS_FILE):
    try:
        with open(STATS_FILE, "r") as f:
            analytics_data = json.load(f)
    except:
        analytics_data = {"total_requests": 0, "daily_visits": 0, "history": [], "start_time": time.time()}
else:
    analytics_data = {
        "total_requests": 0, 
        "daily_visits": 0, 
        "history": [], # List of {"timestamp": ts, "count": int}
        "start_time": time.time()
    }

# Ensure volatile fields are reset/init
analytics_data["active_users"] = {} 
if "history" not in analytics_data: analytics_data["history"] = []
if "start_time" not in analytics_data: analytics_data["start_time"] = time.time()

def save_analytics():
    # Save only persistent data (exclude active_users which is volatile)
    data_to_save = {
        "total_requests": analytics_data["total_requests"],
        "daily_visits": analytics_data["daily_visits"],
        "history": analytics_data["history"][-100:], # Keep last 100 entries
        "start_time": analytics_data["start_time"]
    }
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(data_to_save, f)
    except Exception as e:
        logger.error(f"Failed to save stats: {e}")

@app_web.before_request
def track_request():
    # Ignore static, stats, admin dashboard, and favicon
    if (request.path.startswith("/static") or 
        request.path.startswith("/api/stats") or 
        request.path.startswith("/admin") or 
        request.path == "/favicon.ico"):
        return
        
    # Track Request
    analytics_data["total_requests"] += 1
    
    # Track Active Users (IP based)
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    analytics_data["active_users"][ip] = time.time()
    
    # History Snapshot (Simple: Add to current bucket or create new)
    now = time.time()
    if not analytics_data["history"] or (now - analytics_data["history"][-1]["timestamp"] > 600): # New bucket every 10 mins
        analytics_data["history"].append({"timestamp": now, "count": 1, "active": len(analytics_data["active_users"])})
    else:
        analytics_data["history"][-1]["count"] += 1
        analytics_data["history"][-1]["active"] = len(analytics_data["active_users"])

    # Periodic Save (naive implementation)
    if analytics_data["total_requests"] % 10 == 0:
        save_analytics()

@app_web.route("/api/track", methods=["POST", "OPTIONS"])
async def external_track():
    # Allow CORS for this endpoint so GitHub Pages can call it
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type"
        }
        return Response("", status=204, headers=headers)

    # Record the visit
    analytics_data["total_requests"] += 1
    
    # Return CORS headers
    headers = {"Access-Control-Allow-Origin": "*"}
    return jsonify({"status": "tracked"}), 200, headers

@app_web.route("/api/stats")
async def get_stats():
    now = time.time()
    uptime = int(now - analytics_data["start_time"])
    
    # Cleanup active users
    active_ips = [ip for ip, ts in analytics_data["active_users"].items() if now - ts < 300]
    analytics_data["active_users"] = {ip: analytics_data["active_users"][ip] for ip in active_ips}
    
    return jsonify({
        "active_users": len(active_ips),
        "total_requests": analytics_data["total_requests"],
        "uptime_seconds": uptime,
        "history": analytics_data["history"][-20:], # Send last 20 points for chart
        "bandwidth_estimate": f"{analytics_data['total_requests'] * 1.5:.1f} MB"
    })

@app_web.route("/admin/dashboard")
async def admin_dashboard():
    return await render_template("dashboard.html")

if __name__ == "__main__":
    try:
        # Load stats on startup
        if not os.path.exists("data"): os.makedirs("data")
            
        loop.run_until_complete(start_app())
    except KeyboardInterrupt:
        save_analytics() # Save on exit
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        save_analytics()
