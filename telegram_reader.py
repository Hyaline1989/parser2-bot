import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from telethon import TelegramClient

from app import build_vector_rows, load_saved_drafts, write_saved_drafts
from parser import parse_messages


SESSION_NAME = os.getenv("TELEGRAM_SESSION", "parser2_readonly")
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
CHATS = [item.strip() for item in os.getenv("TELEGRAM_CHATS", "").split(",") if item.strip()]
CHAT_OBJECTS_FILE = Path(__file__).with_name("telegram_chats.json")


def load_chat_objects():
    if not CHAT_OBJECTS_FILE.exists():
        return {}
    try:
        return json.loads(CHAT_OBJECTS_FILE.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def make_telegram_key(chat_id, message_id):
    return f"telegram|{chat_id}|{message_id}"


def looks_like_need(text):
    lowered = text.lower()
    markers = [
        "потребность",
        "муж",
        "жен",
        "сем",
        "м-",
        "ж-",
        "м ",
        "ж ",
        "кмп",
        "стик",
    ]
    return any(marker in lowered for marker in markers)


def save_draft_if_new(saved_drafts, draft):
    message_key = draft["message_key"]
    if any(item.get("message_key") == message_key for item in saved_drafts):
        return False
    saved_drafts.append(draft)
    return True


async def read_chats(limit, save_drafts):
    if not API_ID or not API_HASH:
        raise RuntimeError("Нужно задать TELEGRAM_API_ID и TELEGRAM_API_HASH")
    if not CHATS:
        raise RuntimeError("Нужно задать TELEGRAM_CHATS со списком чатов")

    chat_objects = load_chat_objects()
    saved_drafts = load_saved_drafts()
    saved_count = 0
    parsed_count = 0

    async with TelegramClient(SESSION_NAME, int(API_ID), API_HASH) as client:
        for chat in CHATS:
            entity = await client.get_entity(chat)
            chat_id = entity.id
            chat_title = getattr(entity, "title", None) or str(chat)
            object_name = chat_objects.get(str(chat_id)) or chat_objects.get(chat_title) or chat_title

            async for message in client.iter_messages(entity, limit=limit):
                text = (message.raw_text or "").strip()
                if not text or not looks_like_need(text):
                    continue

                parsed_count += 1
                source = f"Telegram: {chat_title} #{message.id}"
                drafts = parse_messages(
                    [
                        {
                            "source": source,
                            "object": object_name,
                            "text": text,
                        }
                    ]
                )
                rows = build_vector_rows(drafts)
                if not rows:
                    continue

                draft = {
                    "saved_at": datetime.now().isoformat(timespec="seconds"),
                    "source": source,
                    "message_key": make_telegram_key(chat_id, message.id),
                    "source_object": object_name,
                    "telegram": {
                        "chat_id": chat_id,
                        "chat_title": chat_title,
                        "message_id": message.id,
                        "message_date": message.date.isoformat() if message.date else "",
                    },
                    "status": "черновик",
                    "rows": rows,
                }

                print(f"{source}: {len(rows)} строк")
                if save_drafts and save_draft_if_new(saved_drafts, draft):
                    saved_count += 1

    if save_drafts:
        write_saved_drafts(saved_drafts)

    print(f"Найдено сообщений: {parsed_count}")
    print(f"Сохранено новых черновиков: {saved_count}")


def main():
    parser = argparse.ArgumentParser(description="Read-only импорт потребности из Telegram")
    parser.add_argument("--limit", type=int, default=20, help="Сколько последних сообщений читать из каждого чата")
    parser.add_argument("--save-drafts", action="store_true", help="Сохранять найденное в drafts.json")
    args = parser.parse_args()
    asyncio.run(read_chats(args.limit, args.save_drafts))


if __name__ == "__main__":
    main()
