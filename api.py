import sys
import asyncio

# Fix for Windows Event Loop - MUST be before any other async imports
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Explicitly create a loop to satisfy Pyrogram's import-time check
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import json
import os
from quart import Quart, render_template, jsonify, Response, redirect
from pyrogram import Client
from config import Config
import uvicorn

app = Quart(__name__)

# Constants
DATA_FILE = "data/videos.json"

# Global client variable
stream_client = None

def load_videos():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

@app.before_serving
async def start_bot():
    """Start the Pyrogram client when Quart starts."""
    global stream_client
    print("Initializing Streamer Client...")
    stream_client = Client(
        "streamer_session",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN, 
    )
    await stream_client.start()
    print("Streamer Client Started!")

@app.after_serving
async def stop_bot():
    """Stop the Pyrogram client when Quart stops."""
    global stream_client
    if stream_client and stream_client.is_connected:
        await stream_client.stop()
    print("Streamer Client Stopped!")

@app.route("/")
async def index():
    return await render_template("fast-hot-premium---streaming-dashboard/index.html")

# Serve root static files (images, css, global js)
@app.route("/static/<path:path>")
async def root_static(path):
    if os.path.exists(os.path.join("static", path)):
        from quart import send_from_directory
        return await send_from_directory("static", path)
    return "Not Found", 404

# Proxy for Dashboard-specific assets (like script.js inside the template folder)
@app.route("/<path:path>")
async def dashboard_proxy(path):
    # This serves files from the template directory as if they were static files
    template_dir = os.path.join("templates", "fast-hot-premium---streaming-dashboard")
    file_path = os.path.join(template_dir, path)
    if os.path.exists(file_path):
        from quart import send_from_directory
        return await send_from_directory(template_dir, path)
    return "Not Found", 404

@app.route("/api/videos")
async def api_videos():
    videos = load_videos()
    return jsonify(videos)

@app.route("/stream/<file_id>")
async def stream_video(file_id):
    """
    Streams a video file directly from Telegram using Pyrogram.
    """
    if not stream_client:
        return "Stream client not initialized", 500
        
    try:
        async def generate():
            stream = stream_client.stream_media(file_id)
            async for chunk in stream:
                yield chunk

        return Response(generate(), mimetype="video/mp4")

    except Exception as e:
        print(f"Error streaming file: {e}")
        return f"Error: {e}", 500

@app.route("/thumb/<thumb_id>")
async def proxy_thumb(thumb_id):
    if not thumb_id or thumb_id in ["None", "undefined", "null"]:
        return redirect("/static/img/no_thumb.png")
    
    if not stream_client:
        return redirect("/static/img/no_thumb.png")

    try:
        async def generate():
            stream = stream_client.stream_media(thumb_id)
            async for chunk in stream:
                yield chunk
        
        return Response(generate(), mimetype="image/jpeg")
    except Exception as e:
         return redirect("/static/img/no_thumb.png")

if __name__ == "__main__":
    # Run with Uvicorn
    uvicorn.run(app, host=Config.WEB_SERVER_BIND_ADDRESS, port=Config.PORT)
