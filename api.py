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
VIDEO_CACHE = {}

# Global client variable
stream_client = None

def load_videos():
    global VIDEO_CACHE
    if VIDEO_CACHE:
        return VIDEO_CACHE
    
    if not os.path.exists(DATA_FILE):
        return {}
        
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            videos = json.load(f)
            # Create a dict for O(1) lookup by file_id
            VIDEO_CACHE = {v.get("file_id"): v for v in videos}
            return VIDEO_CACHE
        except json.JSONDecodeError:
            return {}

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
    # Pre-load videos
    load_videos()

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
    return jsonify(list(videos.values()))

@app.route("/stream/<file_id>")
async def stream_video(file_id):
    """
    Streams a video file directly from Telegram using Pyrogram with HTTP Range support.
    """
    if not stream_client:
        return "Stream client not initialized", 500
    
    from quart import request, Response
    
    videos = load_videos()
    video_info = videos.get(file_id)
    
    if not video_info:
         # Try to find by id if file_id fails (fallback)
         found = next((v for v in videos.values() if str(v.get("id")) == str(file_id)), None)
         if found:
             video_info = found
             file_id = found.get("file_id")
    
    if not video_info:
        return "Video not found", 404

    file_size = video_info.get("file_size", 0)
    
    # Range handling
    range_header = request.headers.get('Range')
    start = 0
    end = file_size - 1
    
    if range_header:
        try:
            bytes_range = range_header.replace("bytes=", "").split("-")
            start = int(bytes_range[0])
            if len(bytes_range) > 1 and bytes_range[1]:
                end = int(bytes_range[1])
        except ValueError:
            pass
            
    # Validations
    if start >= file_size or end >= file_size:
        return Response(status=416, headers={"Content-Range": f"bytes */{file_size}"})
        
    chunk_size = end - start + 1
    
    # Log for debugging
    # print(f"Streaming {file_id}: {start}-{end} ({chunk_size} bytes)")

    async def generate():
        try:
            # Pyrogram allows offset and limit
            # Note: Pyrogram 2.x stream_media supports offset/limit in chunks (1MB usually)
            # But the most reliable way for random access without downloading everything 
            # is to assume the client handles it or use the `offset` parameter if available.
            # Pyrogram's `stream_media` yields chunks. We can skip chunks until we reach start.
            # IMPROVEMENT: Use `stream_media(file_id, offset=start, limit=chunk_size)`
            # This is much more efficient as Telegram API supports it.
            
            # NOTE: offset in stream_media is in chunks (usually 1MB), NOT bytes for some versions,
            # BUT for `stream_media` specifically, the documentation says:
            # "offset (int, optional) – The offset from which the generation should start."
            # and it seems to be in chunks for documents? 
            # Actually, standard Pyrogram stream_media doesn't expose byte-level offset easily in recent versions?
            # Let's verify: client.stream_media returns a generator.
            # For exact byte seeking, we might need a custom implementation or use `get_file` with offset/limit.
            # BUT `get_file` downloads. `stream_media` is for streaming.
            
            # Let's try to map byte offset to chunks if needed, OR relies on Pyrogram's smarts.
            # Pyrogram `stream_media` takes `offset` (int): Sequential number of the first chunk to be generated.
            # Default chunk size is 1MB (1024*1024).
            
            PYROGRAM_CHUNK_SIZE = 1024 * 1024
            chunk_start_index = start // PYROGRAM_CHUNK_SIZE
            byte_offset_within_chunk = start % PYROGRAM_CHUNK_SIZE
            
            chunks_to_stream = (end // PYROGRAM_CHUNK_SIZE) - chunk_start_index + 1
            
            stream = stream_client.stream_media(
                file_id,
                offset=chunk_start_index,
                limit=chunks_to_stream
            )
            
            current_pos = chunk_start_index * PYROGRAM_CHUNK_SIZE
            bytes_yielded = 0
            
            async for chunk in stream:
                # We might need to trim the first chunk
                if current_pos < start:
                    # Skip bytes at start of this chunk
                    trim_start = start - current_pos
                    if trim_start < len(chunk):
                         chunk = chunk[trim_start:]
                         current_pos += trim_start
                    else:
                         # Should not happen if logic is correct
                         current_pos += len(chunk)
                         continue
                
                # Check if we need to trim the end
                if bytes_yielded + len(chunk) > chunk_size:
                    trim_end = chunk_size - bytes_yielded
                    chunk = chunk[:trim_end]
                
                yield chunk
                bytes_yielded += len(chunk)
                current_pos += len(chunk)
                
                if bytes_yielded >= chunk_size:
                    break
                    
        except Exception as e:
            print(f"Streaming error: {e}")
            
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": "video/mp4",
    }
    
    return Response(generate(), status=206, headers=headers)

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
