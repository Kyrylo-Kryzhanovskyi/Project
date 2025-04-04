import asyncio
from telegram_module import TelegramAuth
from preprocessing import load_and_prepare_messages
from classifier import TextClassifier
from report_generator import *
from utils import save_messages, sanitize_filename
import os
import json
import getpass 

async def main():
    print("👋 Вітаємо в Telegram-класифікаторі токсичного контенту!")
    phone = input("📱 Введіть ваш номер телефону: ").strip()

    tg = TelegramAuth(phone)
    status = await tg.start()

    if status == 'code_sent':
        code = input("🔐 Введіть код із Telegram: ").strip()
        status = await tg.verify_code(code)

        if status == '2fa_needed':
            password = getpass.getpass("🔒 Введіть 2FA пароль: ")  # Вводимо пароль без його відображення
            status = await tg.verify_password(password)

    if status != 'authorized':
        print("❌ Не вдалося авторизуватись. Статус:", status)
        return

    print("✅ Авторизація успішна!")
    chats = await tg.get_chats(limit=100)

    # Перевіряємо, чи існує збережений вибір каналів
    last_sel_path = os.path.join("data", phone, "last_selection.json")
    use_saved = False
    saved_selection = []
    if os.path.exists(last_sel_path):
        try:
            with open(last_sel_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                saved_selection = data.get("chats", [])
            if saved_selection:
                use = input("💾 Знайдено збережений вибір каналів. Використати його? (y/n): ").strip().lower()
                if use in ["y", "yes", "т", "tak", "так"]:
                    use_saved = True
        except Exception:
            saved_selection = []
    selected_chats = []
    if use_saved:
        for sel in saved_selection:
            for chat in chats:
                if chat['id'] == sel['id']:
                    selected_chats.append({ 'id': chat['id'], 'title': chat['title'], 'limit': sel.get('limit', 100) })
                    break
        missing = len(saved_selection) - len(selected_chats)
        if missing:
            print(f"⚠️ Деякі збережені канали недоступні ({missing} не знайдено). Використовуємо тільки знайдені.")
        if not selected_chats:
            print("❌ Збережені канали недоступні. Будь ласка, оберіть канали вручну.")
            use_saved = False
    if not use_saved:
        print("\n📋 Доступні чати/канали:")
        for idx, chat in enumerate(chats):
            print(f"{idx + 1}. {chat['title']} ({chat['type']})")
        indices = []
        while not indices:
            selected = input("\n🔎 Введіть номери каналів через кому для аналізу (наприклад: 1,3,5): ").strip()
            indices = [int(i.strip()) - 1 for i in selected.split(',') if i.strip().isdigit() and 0 < int(i.strip()) <= len(chats)]
            if not indices:
                print("⚠️ Не вибрано жодного правильного номера чату. Спробуйте ще раз.")
        for idx in indices:
            chat = chats[idx]
            try:
                limit = int(input(f"\n📌 Скільки повідомлень завантажити з каналу «{chat['title']}»? ").strip())
            except ValueError:
                limit = 100
                print("⚠️ Некоректне число. Встановлено значення за замовчуванням: 100")
            selected_chats.append({ 'id': chat['id'], 'title': chat['title'], 'limit': limit })
    # Підтвердження вибору перед аналізом
    print("\n✅ Ви вибрали такі канали:")
    for sel in selected_chats:
        print(f"- {sel['title']} (останні {sel['limit']} повідомлень)")
    confirm = input("▶️ Розпочати аналіз? (y/n): ").strip().lower()
    if confirm not in ["y", "yes", "т", "tak", "так"]:
        print("⚠️ Аналіз скасовано користувачем.")
        return
    os.makedirs(os.path.join("data", phone), exist_ok=True)
    try:
        with open(last_sel_path, 'w', encoding='utf-8') as f:
            json.dump({"chats": selected_chats}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Помилка збереження налаштувань: {e}")
    
    classifier = TextClassifier()

    for sel in selected_chats:
        chat_id = sel['id']
        chat_title = sel['title']
        limit = sel['limit']
        print(f"\n📥 Завантаження повідомлень з каналу: {chat_title}...")
        messages = await tg.get_messages(chat_id, limit=limit, download_media=False)
        if len(messages) < limit:
            print(f"⚠️ Завантажено лише {len(messages)} повідомлень з каналу \"{chat_title}\" (запитувалось {limit}).")
        save_messages(phone, chat_title, messages)
        filename = f"data/{phone}/messages_{sanitize_filename(chat_title)}.json"
        prepared = load_and_prepare_messages(filename)
        texts = [msg['text'] for msg in prepared]
        if not texts:
            print(f"❌ Немає повідомлень для класифікації з каналу «{chat_title}»!")
            continue
        print("🧠 Класифікація повідомлень...")
        results = classifier.classify(texts)
        for result, msg in zip(results, prepared):
            result['id'] = msg['id']
        output_file = filename.replace("messages_", "classified_")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("📊 Генерація звіту...")
        results_data = load_classification_results(output_file)
        name = safe_dir_name(output_file)
        output_path = create_output_folder("reports", name)
        label_counter, multi_label_counts, scores_per_label, lengths_per_label = summarize_classification(results_data)
        print_summary(label_counter, multi_label_counts, scores_per_label, lengths_per_label, output_path)
        show_top_examples(results_data, output_path)
        show_top_toxic(results_data, output_path)
        save_per_category(results_data, output_path)
        save_bar_chart(label_counter, output_path)

    await tg.disconnect()
    print("\n🏁 Аналіз завершено для всіх вибраних каналів.")

if __name__ == "__main__":
    asyncio.run(main())
