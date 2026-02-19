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
from pyrogram import Client, filters, idle
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
import cv2
from config import Config
from utils.logger import setup_logger

logger = setup_logger()
app_web = Quart(__name__)

# CORS Headers (Simple middleware)
@app_web.after_request
async def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Constants
DATA_FILE = "data/videos.json"
if not os.path.exists("data"):
    os.makedirs("data")

# Assuming BASE_DIR is defined elsewhere or intended to be defined.
# For this change, we'll define it as the current working directory to ensure syntactic correctness.
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Added for syntactic correctness based on instruction

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

LOCAL_IP = get_local_ip()
BASE_URL = Config.BASE_URL or f"http://{LOCAL_IP}:{Config.PORT}"

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

def load_videos():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

def save_videos(videos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=4, ensure_ascii=False)

def save_video_entry(entry):
    videos = load_videos()
    # Check if video already exists by file_unique_id to avoid duplicates
    if any(v.get('file_unique_id') == entry.get('file_unique_id') for v in videos):
        return
    videos.insert(0, entry)
    save_videos(videos)

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
        stream_link = f"{BASE_URL}/stream/{forwarded_msg.id}"
        await message.reply_text(
            f"✅ **Vídeo Recebido!**\n\n📁 **Arquivo:** `{message.video.file_name or 'Sem Nome'}`\n💾 **Tamanho:** {message.video.file_size} bytes",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Stream", url=stream_link), InlineKeyboardButton("⬇️ Download", url=stream_link)],
                [InlineKeyboardButton("📤 Postar no Site", callback_data=f"post_{forwarded_msg.id}")],
                [InlineKeyboardButton("📋 Meus Vídeos", callback_data="list_videos")]
            ])
        )
    except Exception as e:
        logger.error(f"Error handling video: {e}")
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
        await message.reply_text(f"🌐 Acesse o site aqui: {BASE_URL}")
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
    return await render_template("fast-hot-premium---streaming-dashboard/index.html")

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

@app_web.route("/thumb/<video_id>")
async def get_thumb(video_id):
    # Sanitize video_id to prevent directory traversal
    if not video_id.isdigit(): return "Invalid ID", 400
    
    thumb_path = os.path.join(THUMBS_DIR, f"{video_id}.jpg")
    if os.path.exists(thumb_path):
        from quart import send_file
        return await send_file(thumb_path)
    
    # Return placeholder if not found
    return await send_from_directory(os.path.join("static", "img"), "no_thumb.png")

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

        # Chunk size for internal logic (Pyrogram uses 1MB)
        CHUNK_SIZE = 1024 * 1024
        
        async def generate():
            if not bot: return
            
            # Simple offset calculation
            offset_chunks = start // CHUNK_SIZE
            start_in_chunk = start % CHUNK_SIZE
            
            # RESILIENT STREAMING
            MAX_RETRIES = 3
            retry_count = 0
            
            while retry_count < MAX_RETRIES:
                try:
                    # Stream from Telegram
                    first = True
                    # If retrying, we might want to adjust offset, but bot.stream_media takes chunk offset.
                    # Ideally we track how many bytes we sent and resume, but Pyrogram granularity is 1MB chunks.
                    # For simplicity in this MVP, we restart the chunk we were on if it failed mid-way, 
                    # but since we yield directly, the browser handles the "where to resume" via new range requests usually.
                    # So here catching an error mostly helps purely transient network glitches during a chunk fetch.
                    
                    async for chunk in bot.stream_media(file_id, offset=offset_chunks):
                        if first and start_in_chunk > 0:
                            yield chunk[start_in_chunk:]
                            first = False
                        else:
                            yield chunk
                        
                        # If we successfully yield a chunk, we are making progress.
                        # We could reset retry_count here if we wanted "infinite" retries for long streams,
                        # provided we are strictly moving forward.
                        retry_count = 0 
                        
                    # If loop finishes normally
                    break
                    
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Streaming chunk error (Attempt {retry_count}/{MAX_RETRIES}): {e}")
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"Streaming failed after retries: {e}")
                        break
                    await asyncio.sleep(1) # Wait before retry

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": "video/mp4",
            "Access-Control-Allow-Origin": "*",
        }
        
        # We only send Content-Range if we are confident, otherwise standard 200 stream often works better for unstable sources
        if status_code == 206 and end is not None:
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            # IMPORTANT: We do NOT set Content-Length here to avoid ProtocolError if we are off by 1 byte
            # Quart/Hypercorn will handle chunked encoding
        elif file_size > 0:
            headers["Content-Length"] = str(file_size)
            
        return Response(generate(), status=status_code, headers=headers)
    except Exception as e:
        logger.error(f"Stream error: {e}")
        return str(e), 500

async def generate_thumbnail(video_id, file_id):
    """Generates a thumbnail from a video stream using OpenCV in a separate thread."""
    thumb_path = os.path.join(THUMBS_DIR, f"{video_id}.jpg")
    
    # Return cached if exists
    if os.path.exists(thumb_path):
        return thumb_path

    logger.info(f"Generating thumbnail for video {video_id}")
    stream_url = f"http://127.0.0.1:{Config.PORT}/stream/{video_id}"
    
    def extract_frame_sync():
        try:
            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                return None
            
            # Smart seek: 5s or 10% of video
            cap.set(cv2.CAP_PROP_POS_MSEC, 5000)
            
            success, frame = cap.read()
            cap.release()
            
            if success:
                frame = cv2.resize(frame, (640, 360))
                cv2.imwrite(thumb_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                return thumb_path
            return None
        except Exception as e:
            logger.error(f"CV2 Error: {e}")
            return None

    # Run blocking CV2 code in a thread pool execution
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, extract_frame_sync)

@app_web.route("/static/<path:filename>")
async def static_files(filename):
    return await send_from_directory("static", filename)

@app_web.route("/thumb/<identifier>")
async def proxy_thumb(identifier):
    if not identifier or identifier in ("None", "null"):
        return redirect("/static/img/no_thumb.png")
    
    # Check if we have it locally first
    thumb_path = os.path.join(THUMBS_DIR, f"{identifier}.jpg")
    if os.path.exists(thumb_path):
        from quart import send_file
        return await send_file(thumb_path)

    # SAFE MODE with limits: Try to get the thumbnail from Telegram
    if bot and bot.is_connected and identifier.isdigit():
        try:
            # Acquire semaphore to execute download (Wait if too many active downloads)
            async with thumb_semaphore:
                # We use get_messages which is lighter
                msg = await bot.get_messages(Config.BIN_CHANNEL, int(identifier))
                if msg and msg.video and msg.video.thumbs:
                    # Download the thumbnail
                    await bot.download_media(
                        msg.video.thumbs[0].file_id,
                        file_name=thumb_path
                    )
                    if os.path.exists(thumb_path):
                        from quart import send_file
                        return await send_file(thumb_path)
                else:
                     # If no thumbnail or message not found, fallback
                     pass
        except Exception as e:
            logger.warning(f"Failed to fetch thumb {identifier} from TG: {e}")
            # Do NOT log stack trace to keep logs clean
    
    # If all fails, return default image to avoid crashing or banning
    return redirect("/static/img/no_thumb.png")

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
    
    logger.info(f"Local IP: {LOCAL_IP}")
    print(f"Site Disponivel em: {BASE_URL}")
    logger.info(f"Site available at: {BASE_URL}")

    # Start Background Tasks
    # asyncio.create_task(prefetch_thumbnails()) # Disabled per user request
    # start_serveo_thread() # Disabled per user request (returning to local)
    
    try:
        await asyncio.gather(server.serve(), idle())
    finally:
        await bot.stop()

if __name__ == "__main__":
    try:
        loop.run_until_complete(start_app())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}")
