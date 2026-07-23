import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app import build_vector_rows, load_saved_drafts, resolve_vector_column, write_saved_drafts
from parser import parse_messages
from vector_catalog import OBJECT_POSITIONS


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_OBJECTS_FILE = Path(__file__).with_name("telegram_chats.json")
router = Router()


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
        "груз",
        "разнораб",
    ]
    return any(marker in lowered for marker in markers) or bool(re.search(r"\b[мж]\s*\d+\b", lowered))


def get_chat_title(message):
    return message.chat.title or message.chat.full_name or "без названия"


def find_object_in_text(text):
    for line in text.splitlines()[:5]:
        cleaned = line.strip()
        lowered = cleaned.lower()
        if lowered.startswith("объект:"):
            candidate = cleaned.split(":", 1)[1].strip()
            if candidate in OBJECT_POSITIONS:
                return candidate
        if lowered.startswith("объект "):
            candidate = cleaned[7:].strip()
            if candidate in OBJECT_POSITIONS:
                return candidate
    return None


def resolve_object_name(message, text=""):
    object_from_text = find_object_in_text(text)
    if object_from_text:
        return object_from_text

    chat_objects = load_chat_objects()
    chat_id = str(message.chat.id)
    chat_title = get_chat_title(message)
    return chat_objects.get(chat_id) or chat_objects.get(chat_title) or chat_title


def rows_from_review_drafts(drafts):
    rows = []
    for draft in drafts:
        if not isinstance(draft.get("quantity"), int):
            continue

        row = {
            "object": draft["object"],
            "position": draft["position"] if draft["position"] != "не указана" else "требует выбора",
            "rf_rb_m": 0,
            "rf_rb_f": 0,
            "rf_rb_family": 0,
            "cis_m": 0,
            "cis_f": 0,
            "cis_family": 0,
            "total": draft["quantity"],
            "operation": draft.get("operation", "заменить"),
        }
        column = resolve_vector_column(draft)
        if column:
            row[column] = draft["quantity"]
        rows.append(row)
    return rows


def save_rows_from_message(message, rows, object_name, status="черновик"):
    message_key = make_telegram_key(message.chat.id, message.message_id)
    saved_drafts = load_saved_drafts()

    if any(draft.get("message_key") == message_key for draft in saved_drafts):
        print(f"Дубль пропущен: chat={message.chat.id} message={message.message_id}")
        return False

    saved_drafts.append(
        {
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "source": f"Telegram: {message.chat.title or message.chat.id} #{message.message_id}",
            "message_key": message_key,
            "source_object": object_name,
            "telegram": {
                "chat_id": message.chat.id,
                "chat_title": message.chat.title or "",
                "message_id": message.message_id,
                "message_date": message.date.isoformat() if message.date else "",
            },
            "status": status,
            "rows": rows,
        }
    )
    write_saved_drafts(saved_drafts)
    return True


async def process_text_message(message: Message, update_type: str):
    text = (message.text or "").strip()
    title = get_chat_title(message)
    print(f"Получено {update_type}: chat={message.chat.id} title={title} message={message.message_id}")
    print("Текст:", text[:500].replace("\n", " | "))

    if not text or not looks_like_need(text):
        print("Пропущено: не похоже на потребность")
        return

    object_name = resolve_object_name(message, text)
    print(f"Объект для разбора: {object_name}")

    drafts = parse_messages(
        [
            {
                "source": f"Telegram: {message.chat.title or message.chat.id} #{message.message_id}",
                "object": object_name,
                "text": text,
            }
        ]
    )
    rows = build_vector_rows(drafts)
    status = "черновик"

    if not rows:
        rows = rows_from_review_drafts(drafts)
        status = "требует проверки"

    if not rows:
        print(f"Не получилось собрать строки: chat={message.chat.id} message={message.message_id}")
        print("Нет даже черновых строк. Проверь текст сообщения и правила распознавания.")
        return

    saved = save_rows_from_message(message, rows, object_name, status=status)
    if saved:
        print(f"Сохранён черновик: {object_name}, строк: {len(rows)}, статус: {status}")


@router.message(Command("chatid"))
async def show_chat_id(message: Message):
    title = get_chat_title(message)
    await message.answer(f"chat_id: {message.chat.id}\nchat: {title}")
    print(f"/chatid: chat={message.chat.id} title={title}")


@router.message(F.text)
async def handle_group_or_private_message(message: Message):
    await process_text_message(message, "сообщение")


@router.channel_post(F.text)
async def handle_channel_post(message: Message):
    await process_text_message(message, "пост канала")


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("Нужно задать TELEGRAM_BOT_TOKEN")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    me = await bot.get_me()
    print(f"Бот запущен: @{me.username}")
    print("Режим: чтение сообщений, групп и постов каналов. Без публикации в Вектор.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
