
import json
from collections import Counter

with open('data/videos.json', 'r', encoding='utf-8') as f:
    try:
        videos = json.load(f)
        categories = [v.get('category', 'None') for v in videos]
        print(Counter(categories))
    except Exception as e:
        print(f"Error: {e}")
