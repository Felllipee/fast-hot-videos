
import json
import os

with open('data/videos.json', 'r', encoding='utf-8') as f:
    videos = json.load(f)

print("Videos in 'Outros':")
for v in videos:
    if v.get('category') == 'Outros':
        print(f"- {v.get('title')}")
