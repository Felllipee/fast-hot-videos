import asyncio
import json
import os
import sys

# Windows Event Loop Policy must be set AND a loop must be created
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Explicitly create a loop to satisfy Pyrogram's import-time check
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import Config
from utils.logger import setup_logger

logger = setup_logger()

# Pyrogram Client
app = Client(
    "bot_session",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# Simple in-memory state management
# Structure: { user_id: { "step": "WAITING_TITLE", "video_data": {...} } }
user_states = {}

DATA_FILE = "data/videos.json"

def load_videos():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_video_entry(entry):
    videos = load_videos()
    videos.insert(0, entry) # Prepend to show newest first
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=4, ensure_ascii=False)

@app.on_message(filters.video & filters.private)
async def video_handler(client, message: Message):
    try:
        # Forward to BIN_CHANNEL
        forwarded_msg = await message.forward(Config.BIN_CHANNEL)
        
        # Prepare data for state (temporarily just basic info)
        file_id = forwarded_msg.video.file_id
        file_unique_id = forwarded_msg.video.file_unique_id
        file_name = forwarded_msg.video.file_name or "Sem Nome"
        file_size = forwarded_msg.video.file_size
        duration = forwarded_msg.video.duration
        
        # Store essential info in specific unique ID map if needed, 
        # but for now we just reply with buttons. 
        # We need to carry context. We'll use the message ID of the forwarded message as reference if possible,
        # or just attached to the user's interaction flow.
        
        # Reply to user
        await message.reply_text(
            f"✅ **Vídeo Recebido!**\n\n"
            f"📁 **Arquivo:** `{file_name}`\n"
            f"💾 **Tamanho:** `{file_size}` bytes\n"
            f"⏱ **Duração:** `{duration}` seg",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("▶️ Stream", url=f"http://127.0.0.1:{Config.PORT}/stream/{forwarded_msg.id}"), # Placeholder
                    InlineKeyboardButton("⬇️ Download", url=f"http://127.0.0.1:{Config.PORT}/stream/{forwarded_msg.id}")
                ],
                [InlineKeyboardButton("📤 Postar no Site", callback_data=f"post_{forwarded_msg.id}")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error handling video: {e}")
        await message.reply_text("Erro ao processar vídeo.")

@app.on_callback_query(filters.regex(r"^post_(\d+)"))
async def post_callback(client, callback_query: CallbackQuery):
    message_id = int(callback_query.matches[0].group(1))
    user_id = callback_query.from_user.id
    
    # Fetch the message from BIN to get details again or ensure existence
    try:
        bin_msg = await client.get_messages(Config.BIN_CHANNEL, message_id)
        if not bin_msg or not bin_msg.video:
            await callback_query.answer("Vídeo não encontrado no canal de armazenamento.", show_alert=True)
            return

        # Initialize state
        user_states[user_id] = {
            "step": "WAITING_TITLE",
            "video_data": {
                "id": str(message_id), # Use message_id as unique ID for simplicity
                "file_id": bin_msg.video.file_id,
                "file_unique_id": bin_msg.video.file_unique_id,
                "file_name": bin_msg.video.file_name,
                "file_size": bin_msg.video.file_size,
                "duration": bin_msg.video.duration,
                "thumb_id": bin_msg.video.thumbs[0].file_id if bin_msg.video.thumbs else None
            }
        }
        
        await callback_query.message.reply_text(
            "📝 **Postando no Site**\n\nQual o **Título** que você quer dar para este vídeo?\nDigite abaixo:"
        )
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        await callback_query.answer("Ocorreu um erro.", show_alert=True)

@app.on_message(filters.text & filters.private)
async def text_handler(client, message: Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    if not state:
        return # Ignore chat if not in state
    
    if state["step"] == "WAITING_TITLE":
        title = message.text.strip()
        state["video_data"]["title"] = title
        state["step"] = "WAITING_CATEGORY"
        
        # Ask for category
        categories = ["Ação", "Comédia", "Drama", "Tutorial", "Pessoal", "Outros"]
        buttons = []
        row = []
        for cat in categories:
            row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
            
        await message.reply_text(
            f"Ótimo! Título: **{title}**.\n\nAgora escolha a **Categoria**:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

@app.on_callback_query(filters.regex(r"^cat_(.+)"))
async def category_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    state = user_states.get(user_id)
    
    if not state or state["step"] != "WAITING_CATEGORY":
        await callback_query.answer("Sessão expirada ou inválida.", show_alert=True)
        return

    category = callback_query.matches[0].group(1)
    state["video_data"]["category"] = category
    
    # Save to JSON
    save_video_entry(state["video_data"])
    
    # Clear state
    video_title = state["video_data"]["title"]
    del user_states[user_id]
    
    await callback_query.message.edit_text(
        f"✅ **Vídeo Postado com Sucesso!**\n\n"
        f"📌 **Título:** {video_title}\n"
        f"📂 **Categoria:** {category}\n\n"
        f"Agora ele já aparece no site!"
    )

if __name__ == "__main__":
    print("Bot Iniciado...")
    app.run()
