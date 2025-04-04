# telegram_module.py (оновлено з підтримкою збереження медіа)
from telethon import TelegramClient, errors
from telethon.tl.types import Channel, Chat, Message
import os
from config import API_HASH, API_ID, SESSION_DIR


os.makedirs(SESSION_DIR, exist_ok=True)

class TelegramAuth:
    def __init__(self, phone_number):
        self.phone = phone_number
        session_path = os.path.join(SESSION_DIR, f"{self.phone}.session")
        self.client = TelegramClient(session_path, API_ID, API_HASH)

    async def start(self):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            try:
                await self.client.send_code_request(self.phone)
                return 'code_sent'
            except errors.PhoneNumberInvalidError:
                return 'invalid_phone'
        return 'authorized'

    async def verify_code(self, code):
        try:
            await self.client.sign_in(self.phone, code)
            return 'authorized'
        except errors.SessionPasswordNeededError:
            return '2fa_needed'
        except errors.CodeInvalidError:
            return 'invalid_code'

    async def verify_password(self, password):
        try:
            await self.client.sign_in(password=password)
            return 'authorized'
        except errors.PasswordHashInvalidError:
            return 'invalid_password'

    async def logout(self):
        await self.client.log_out()
        await self.client.disconnect()
        session_path = os.path.join(SESSION_DIR, f"{self.phone}.session")
        if os.path.exists(session_path):
            os.remove(session_path)

    async def disconnect(self):
        await self.client.disconnect()

    async def get_chats(self, limit=100):
        dialogs = await self.client.get_dialogs(limit=limit)
        chats = []

        for dialog in dialogs:
            entity = dialog.entity
            if isinstance(entity, (Channel, Chat)):
                chats.append({
                    'id': entity.id,
                    'title': entity.title,
                    'type': 'channel' if isinstance(entity, Channel) else 'chat'
                })

        return chats

    async def get_messages(self, chat_id, limit=100, base_data_dir="data", download_media=True):
        media_dir = os.path.join(base_data_dir, self.phone, "media")
        os.makedirs(media_dir, exist_ok=True)

        grouped_messages = {}
        offset_id = 0
        batch_size = 100

        print("")  # для відступу
        while len(grouped_messages) < limit:
            fetched = 0
            async for message in self.client.iter_messages(chat_id, limit=batch_size, offset_id=offset_id):
                offset_id = message.id
                fetched += 1

                grouped_id = message.grouped_id or message.id
                media_type = None
                if message.photo:
                    media_type = 'photo_album' if message.grouped_id else 'photo'

                # Перевірка на наявність тексту в повідомленні
                if not message.message and not message.photo:
                    continue  # Пропускаємо повідомлення без тексту і медіа

                # створення запису
                # створення або оновлення запису для повідомлення/групи
                if grouped_id not in grouped_messages:
                    grouped_messages[grouped_id] = {
                        'id': message.id,
                        'grouped_id': grouped_id,
                        'date': message.date.isoformat(),
                        'sender_id': message.sender_id,
                        'text': "",
                        'media_type': media_type,
                        'media_files': [],
                        'reply_to': message.reply_to_msg_id,
                        'reactions': []
                    }
                if message.message:
                    if grouped_messages[grouped_id]['text']:
                        grouped_messages[grouped_id]['text'] += "\n" + message.message.strip()
                    else:
                        grouped_messages[grouped_id]['text'] = message.message.strip()

                if message.photo and download_media:
                    try:
                        filename = f"{grouped_id}_{message.id}.jpg"
                        file_path = os.path.join(media_dir, filename)
                        saved_path = await self.client.download_media(message, file=file_path)
                        grouped_messages[grouped_id]['media_files'].append(saved_path)
                    except Exception as e:
                        grouped_messages[grouped_id]['media_files'].append(f"ERROR: {str(e)}")

                if hasattr(message, 'reactions') and message.reactions:
                    reactions = [
                        {
                            'reaction': r.reaction.emoticon if hasattr(r.reaction, 'emoticon') else str(r.reaction),
                            'count': r.count
                        } for r in message.reactions.results
                    ]
                    grouped_messages[grouped_id]['reactions'].extend(reactions)

                if len(grouped_messages) % 10 == 0:
                    print(f"🔄 Прогрес: {len(grouped_messages)} / {limit} постів")

                if len(grouped_messages) >= limit:
                    break

            if fetched == 0:
                break

        print(f"✅ Завантажено {len(grouped_messages)} унікальних постів\n")
        return list(grouped_messages.values())[:limit]

