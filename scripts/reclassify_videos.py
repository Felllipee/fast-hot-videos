
import os
import json
import sys

# Ensure we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.categorizer import detect_category

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
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=4, ensure_ascii=False)

def main():
    print("📂 Loading videos...")
    videos = load_videos()
    print(f"✅ Loaded {len(videos)} videos.")
    
    updated_count = 0
    
    print("🔄 Reclassifying...")
    for video in videos:
        old_cat = video.get("category", "Outros")
        title = video.get("title", "")
        new_cat = detect_category(title)
        
        # Update if category changed or if it was "Outros" and we found something better
        # Actually, detect_category returns "Outros" if no match.
        # We should overwrite existing category? 
        # Yes, because existing might be "Outros" or wrong. 
        # But if user manually set it? The user asked for automation.
        # Let's overwrite.
        
        if new_cat != "Outros" and old_cat != new_cat:
            video["category"] = new_cat
            print(f"📝 '{title}' -> {new_cat} (was {old_cat})")
            updated_count += 1
            
    if updated_count > 0:
        save_videos(videos)
        print(f"💾 Updated {updated_count} videos.")
    else:
        print("✨ No changes needed.")

if __name__ == "__main__":
    main()
