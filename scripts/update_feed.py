import asyncio
import os
import json
import sys

# Ensure we can import config relative to root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyrogram import Client
from pyrogram import Client
from config import Config
from utils.categorizer import detect_category

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "data", "videos.json")

def load_videos():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def save_videos(videos):
    # Ensure directory exists
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=4, ensure_ascii=False)

async def main():
    print("🚀 Starting Video Feed Updater...")
    
    # Check key vars
    if not Config.API_ID or not Config.API_HASH or not Config.BOT_TOKEN:
        print("❌ Missing API credentials in env vars.")
        return

    # Initialize Client (Session name 'updater')
    async with Client("updater_session", 
                      api_id=Config.API_ID, 
                      api_hash=Config.API_HASH, 
                      bot_token=Config.BOT_TOKEN,
                      in_memory=True) as app:
        
        print(f"✅ Connected as {app.me.username}")
        
        # Load existing
        videos = load_videos()
        existing_ids = set(str(v.get('id')) for v in videos)
        
        print(f"📂 Loaded {len(videos)} existing videos.")
        
        new_count = 0
        # Validate BIN_CHANNEL
        try:
            bin_channel = int(str(Config.BIN_CHANNEL).replace(" ", "").strip())
            print(f"ℹ️ BIN_CHANNEL Type: {type(bin_channel)}")
            print(f"ℹ️ BIN_CHANNEL validation: Is Negative? {bin_channel < 0}, Is Zero? {bin_channel == 0}")
        except Exception as e:
            print(f"❌ Error parsing BIN_CHANNEL: {e}")
            return

        print(f"🔄 Scanning Channel ID (Sanitized): {bin_channel}...")
        
        # Fetch last 1000 messages (Increased limit)
        async for message in app.get_chat_history(bin_channel, limit=1000):
            if not message.video:
                continue
                
            msg_id = str(message.id)
            if msg_id in existing_ids:
                continue
                
            # It's a new video!
            title = message.video.file_name or "Sem Título"
            # Clean title logic simplified
            title = title.replace(".mp4", "").replace(".mkv", "").replace("_", " ")
            
            entry = {
                "id": msg_id,
                "file_id": message.video.file_id,
                "file_unique_id": message.video.file_unique_id,
                "title": title,
                "category": detect_category(title), # Auto-detect category
                "duration": message.video.duration,
                "file_size": message.video.file_size,
                "width": message.video.width,
                "height": message.video.height,
                "thumb_id": message.video.thumbs[0].file_id if message.video.thumbs else None,
                "upload_date": str(message.date)
            }
            
            videos.insert(0, entry)
            print(f"➕ Added: {title}")
            new_count += 1
            
        if new_count > 0:
            save_videos(videos)
            print(f"💾 Saved {new_count} new videos to videos.json")
        else:
            print("✅ No new videos found.")

if __name__ == "__main__":
    asyncio.run(main())
