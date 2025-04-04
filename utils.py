# utils.py
import os
import json
import re

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', '_', name.strip().replace(' ', '_'))

def ensure_data_dir(phone):
    data_dir = os.path.join("data", phone)
    media_dir = os.path.join(data_dir, "media")
    os.makedirs(media_dir, exist_ok=True)
    return data_dir, media_dir

def save_chats(phone, chats):
    data_dir, _ = ensure_data_dir(phone)
    path = os.path.join(data_dir, "chats.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chats, f, ensure_ascii=False, indent=2)

def save_messages(phone, chat_title, messages):
    data_dir, _ = ensure_data_dir(phone)
    safe_title = sanitize_filename(chat_title)
    filename = f"messages_{safe_title}.json"
    path = os.path.join(data_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)