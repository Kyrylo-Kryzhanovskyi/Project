import json
import re

def clean_text(text):
    """
    Очищає текст: прибирає HTML, спецсимволи, переводить в нижній регістр та видаляє зайві пробіли.
    """
    text = re.sub(r'<.*?>', '', text)  # Прибираємо HTML
    text = re.sub(r'http\S+|www\.\S+', ' ', text)
    text = re.sub(r'[^\w\s.,!?\"\'@#%&:;()\[\]{}-]', '', text, flags=re.UNICODE)  # Залишаємо тільки корисні символи
    text = re.sub(r'\s+', ' ', text).strip().lower()  # Прибираємо зайві пробіли та переводимо до нижнього регістру
    return text

def generate_text_for_analysis(msg):
    """
    Генерує текст для аналізу, додаючи позначки медіа, якщо є.
    """
    text = msg.get('text', '').strip()
    media_type = msg.get('media_type')
    media_tag = f"[MEDIA: {media_type}]" if media_type else ""

    if text and media_tag:
        return clean_text(text + " " + media_tag)
    elif media_tag:
        return media_tag.lower()
    elif text:
        return clean_text(text)
    else:
        return ""

import re

def filter_invalid_messages(messages):
    """
    Фільтрує та відсіює некорисні повідомлення: занадто короткі, що складаються лише з цифр або спеціальних символів, без букв або з одного повторюваного символу.
    """
    valid_messages = []
    for msg in messages:
        text = msg['text'].strip()

        # Перевірка та фільтрація повідомлення
        if len(text) < 3:
            print(f"⚠️ Пропущено повідомлення: '{text}' (занадто коротке)")
            continue
        if text.isdigit():
            print(f"⚠️ Пропущено повідомлення: '{text}' (складається лише з цифр)")
            continue
        if not any(char.isalpha() for char in text):
            print(f"⚠️ Пропущено повідомлення: '{text}' (не містить букв)")
            continue
        if len(set(text)) == 1 and len(text) >= 3:
            print(f"⚠️ Пропущено повідомлення: '{text}' (складається з одного повторюваного символу)")
            continue
        valid_messages.append(msg)

    return valid_messages


def load_and_prepare_messages(filepath):
    """
    Завантажує і обробляє повідомлення з файлу JSON, фільтрує їх перед подальшою обробкою.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        raw_messages = json.load(f)

    processed = []
    # Фільтрація повідомлень, щоб виключити ті, що непотрібні
    valid_messages = filter_invalid_messages(raw_messages)
    
    for msg in valid_messages:
        # Якщо після фільтрації текст не порожній, додаємо його в оброблені повідомлення
        prepared_text = generate_text_for_analysis(msg)
        if prepared_text:
            processed.append({
                'id': msg['id'],
                'text': prepared_text
            })

    return processed

