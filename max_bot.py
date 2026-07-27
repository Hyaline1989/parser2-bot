import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from app import build_vector_rows, load_saved_drafts, resolve_vector_column, write_saved_drafts
from parser import parse_messages
from vector_catalog import OBJECT_POSITIONS, refresh_object_positions


BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")
API_BASE_URL = os.getenv("MAX_API_BASE_URL", "https://platform-api2.max.ru")
CHAT_OBJECTS_FILE = Path(__file__).with_name("max_chats.json")
MARKER_FILE = Path(__file__).with_name("max_marker.txt")


def load_chat_objects():
    if not CHAT_OBJECTS_FILE.exists():
        return {}
    try:
        return json.loads(CHAT_OBJECTS_FILE.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def load_marker():
    if not MARKER_FILE.exists():
        return None
    marker = MARKER_FILE.read_text(encoding="utf-8").strip()
    return marker or None


def write_marker(marker):
    if marker is not None:
        MARKER_FILE.write_text(str(marker), encoding="utf-8")


def request_json(path, params=None):
    query = f"?{urllib.parse.urlencode(params or {}, doseq=True)}" if params else ""
    request = urllib.request.Request(
        f"{API_BASE_URL}{path}{query}",
        headers={"Authorization": BOT_TOKEN, "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=100) as response:
        return json.loads(response.read().decode("utf-8"))


def get_updates(marker):
    params = {
        "limit": 100,
        "timeout": 30,
        "types": ["message_created", "bot_added", "chat_title_changed"],
    }
    if marker is not None:
        params["marker"] = marker
    return request_json("/updates", params)


def get_chat_title(chat_id):
    if chat_id is None:
        return ""
    try:
        chat = request_json(f"/chats/{chat_id}")
    except Exception:
        return ""
    return chat.get("title") or ""


def looks_like_shift_report(text):
    lowered = text.lower()
    report_markers = [
        "факт/заявка",
        "выход",
        "выход день",
        "выходной",
        "выходные",
        "смена",
        "штат смены",
        "общий штат",
        "общий штат день",
        "больничный",
        "не выход",
        "перевахтовка",
        "убывшие",
        "обучение",
        "бригадир",
        "заморозка",
        "вахта окончена",
        "прерывание вахты",
        "прогул",
        "увольнение",
        "перевод",
    ]
    need_markers = ["потребность", "потоебность", "нужн"]
    return not any(marker in lowered for marker in need_markers) and sum(marker in lowered for marker in report_markers) >= 2


def looks_like_place_question(text):
    lowered = text.lower()
    if "?" not in lowered or not re.search(r"\bмест[оа]?\b", lowered):
        return False

    strong_need_markers = [
        "потребность",
        "потоебность",
        "нужны",
        "нужно",
        "нужен",
        "нужна",
        "добавляем",
        "добавить",
    ]
    return not any(marker in lowered for marker in strong_need_markers)


def looks_like_trip_details(text):
    lowered = text.lower()
    trip_markers = [
        "детали поездки",
        "яндекс go",
        "номер водителя",
        "ссылка на отслеживание маршрута",
        "go.yandex/route",
    ]
    return any(marker in lowered for marker in trip_markers)


def looks_like_arrival_notice(text):
    lowered = text.lower()
    arrival_markers = [
        "\u043f\u0440\u0438\u0435\u0434\u0435\u0442",
        "\u043f\u0440\u0438\u0435\u0434\u0443\u0442",
        "\u043f\u0440\u0438\u0431\u0443\u0434\u0435\u0442",
        "\u043f\u0440\u0438\u0431\u0443\u0434\u0443\u0442",
    ]
    has_duration = bool(re.search(r"\b\d+\s*\u0447\.?\s*\d+\s*\u043c\.?", lowered))
    return has_duration and any(marker in lowered for marker in arrival_markers)


def looks_like_candidate_travel(text):
    lowered = text.lower()
    ticket_markers = [
        "\u0431\u0435\u0440\u0443 \u0431\u0438\u043b\u0435\u0442",
        "\u0432\u0437\u044f\u043b \u0431\u0438\u043b\u0435\u0442",
        "\u0432\u0437\u044f\u043b\u0430 \u0431\u0438\u043b\u0435\u0442",
        "\u043a\u0443\u043f\u0438\u043b \u0431\u0438\u043b\u0435\u0442",
        "\u043a\u0443\u043f\u0438\u043b\u0430 \u0431\u0438\u043b\u0435\u0442",
        "\u0431\u0438\u043b\u0435\u0442 \u043d\u0430",
        "\u043d\u0430 \u0434\u043e\u0435\u0437\u0434\u0435",
    ]
    need_markers = [
        "\u043f\u043e\u0442\u0440\u0435\u0431\u043d\u043e\u0441\u0442\u044c",
        "\u043f\u043e\u0442\u043e\u0435\u0431\u043d\u043e\u0441\u0442\u044c",
        "\u043d\u0443\u0436\u043d\u043e",
        "\u043d\u0443\u0436\u043d\u044b",
        "\u043d\u0443\u0436\u0435\u043d",
        "\u043d\u0443\u0436\u043d\u0430",
    ]
    return (
        any(marker in lowered for marker in ticket_markers)
        and not any(marker in lowered for marker in need_markers)
    )


def looks_like_candidate_arrival(text):
    lowered = text.lower()
    arrival_markers = [
        "\u043f\u0440\u0438\u043b\u0451\u0442",
        "\u043f\u0440\u0438\u043b\u0435\u0442",
        "\u043f\u0440\u0438\u0435\u0434\u0443\u0442",
        "\u043f\u0440\u0438\u0435\u0434\u0435\u0442",
        "\u0434\u043e\u043b\u0436\u043d\u044b \u0431\u044b\u0442\u044c \u0443 \u0432\u0430\u0441",
        "\u043a\u0443\u0434\u0430 \u0432\u0435\u0437\u0442\u0438",
        "\u0430\u0434\u0440\u0435\u0441 \u043a\u0443\u0434\u0430",
    ]
    need_markers = [
        "\u043f\u043e\u0442\u0440\u0435\u0431\u043d\u043e\u0441\u0442\u044c",
        "\u043f\u043e\u0442\u043e\u0435\u0431\u043d\u043e\u0441\u0442\u044c",
        "\u043d\u0443\u0436\u043d\u043e",
        "\u043d\u0443\u0436\u043d\u044b",
        "\u043d\u0443\u0436\u0435\u043d",
        "\u043d\u0443\u0436\u043d\u0430",
    ]
    has_arrival_context = any(marker in lowered for marker in arrival_markers)
    has_time = bool(re.search(r"\b\d{1,2}[.:]\d{2}\b", lowered))
    return has_arrival_context and has_time and not any(marker in lowered for marker in need_markers)


def looks_like_discussion_question(text):
    lowered = text.lower()
    if "?" not in lowered:
        return False
    question_markers = [
        "\u044f \u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u043e \u043f\u043e\u043d\u0438\u043c\u0430\u044e",
        "\u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u043e \u043f\u043e\u043d\u0438\u043c\u0430\u044e",
        "\u044f \u0432\u0435\u0440\u043d\u043e \u043f\u043e\u043d\u0438\u043c\u0430\u044e",
        "\u0432\u0435\u0440\u043d\u043e \u043b\u0438",
        "\u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u043e \u043b\u0438",
        "\u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0442\u0441\u044f \u043b\u0438",
    ]
    return any(marker in lowered for marker in question_markers)


def looks_like_operational_discussion(text):
    lowered = text.lower()
    discussion_markers = [
        "\u0441\u0442\u0430\u0431\u0438\u043b\u044c\u043d\u043e\u0433\u043e \u0432\u044b\u0445\u043e\u0434\u0430",
        "\u0441\u0442\u0430\u0431\u0438\u043b\u044c\u043d\u044b\u0439 \u0432\u044b\u0445\u043e\u0434",
        "\u043e\u0440\u0433\u0430\u043d\u0438\u0437\u043e\u0432\u0430\u0442\u044c \u0432\u0441\u0442\u0440\u0435\u0447\u0443",
        "\u043f\u0440\u043e\u0432\u0435\u0441\u0442\u0438 \u0432\u0441\u0442\u0440\u0435\u0447\u0443",
        "\u043f\u0440\u043e\u0432\u0435\u0434\u0451\u043c \u043f\u0435\u0440\u0435\u0433\u043e\u0432\u043e\u0440\u044b",
        "\u043f\u0440\u043e\u0432\u0435\u0434\u0435\u043c \u043f\u0435\u0440\u0435\u0433\u043e\u0432\u043e\u0440\u044b",
        "\u0441\u043f\u043e\u0440\u043d\u044b\u0435 \u043c\u043e\u043c\u0435\u043d\u0442\u044b",
        "\u0441\u0442\u043e\u043f \u0444\u0430\u043a\u0442\u043e\u0440\u044b",
        "\u0440\u0435\u0433\u043b\u0430\u043c\u0435\u043d\u0442\u044b",
    ]
    direct_need_markers = [
        "\u043f\u043e\u0442\u0440\u0435\u0431\u043d\u043e\u0441\u0442\u044c",
        "\u0437\u0430\u044f\u0432\u043a\u0430",
        "\u043d\u0443\u0436\u043d\u044b",
        "\u0442\u0440\u0435\u0431\u0443\u044e\u0442\u0441\u044f",
    ]
    return (
        any(marker in lowered for marker in discussion_markers)
        and not any(marker in lowered for marker in direct_need_markers)
    )


def looks_like_need_explanation(text):
    lowered = text.lower()
    previous_need_markers = [
        "\u043d\u0430\u043f\u0438\u0441\u0430\u043b\u0430 \u043f\u043e\u0442\u0440\u0435\u0431\u043d\u043e\u0441\u0442\u044c",
        "\u043d\u0430\u043f\u0438\u0441\u0430\u043b \u043f\u043e\u0442\u0440\u0435\u0431\u043d\u043e\u0441\u0442\u044c",
        "\u0443\u043a\u0430\u0437\u0430\u043b\u0430 \u043f\u043e\u0442\u0440\u0435\u0431\u043d\u043e\u0441\u0442\u044c",
        "\u0443\u043a\u0430\u0437\u0430\u043b \u043f\u043e\u0442\u0440\u0435\u0431\u043d\u043e\u0441\u0442\u044c",
        "\u043f\u043e\u0442\u0440\u0435\u0431\u043d\u043e\u0441\u0442\u044c \u043c\u0435\u043d\u044c\u0448\u0435, \u0430 \u043d\u0435 \u043f\u043e\u043b\u043d\u0443\u044e",
    ]
    explanation_markers = [
        "\u043f\u043e \u043c\u0435\u0440\u0435 \u0437\u0430\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f",
        "\u0441\u0432\u043e\u0431\u043e\u0434\u043d\u044b\u0445 \u043c\u0435\u0441\u0442",
        "\u0432\u044b\u0432\u0435\u0441\u0442\u0438 \u043d\u0430 \u043e\u0431\u0443\u0447\u0435\u043d\u0438\u0435",
        "\u0432\u044b\u0432\u043e\u0434 \u043f\u043e\u0441\u0442\u0435\u043f\u0435\u043d\u043d\u044b\u0439",
        "\u043f\u043e\u0434\u0430\u0432\u0430\u0442\u044c \u0437\u0430 \u0440\u0430\u0437 \u043d\u0430 \u0441\u0431",
    ]
    return (
        any(marker in lowered for marker in previous_need_markers)
        or sum(marker in lowered for marker in explanation_markers) >= 2
    )


def looks_like_place_availability(text):
    lowered = text.lower()
    availability_markers = [
        "\u043e\u0441\u0442\u0430\u043b\u043e\u0441\u044c",
        "\u043e\u0441\u0442\u0430\u043b\u043e\u0441\u044c \u043c\u0435\u0441\u0442",
        "\u0441\u0432\u043e\u0431\u043e\u0434\u043d\u044b\u0445",
        "\u0441\u0432\u043e\u0431\u043e\u0434\u043d\u044b\u0435 \u043c\u0435\u0441\u0442\u0430",
        "\u0441\u0432\u043e\u0431\u043e\u0434\u043d\u043e \u043c\u0435\u0441\u0442",
    ]
    direct_need_markers = [
        "\u043f\u043e\u0442\u0440\u0435\u0431\u043d\u043e\u0441\u0442\u044c",
        "\u0437\u0430\u044f\u0432\u043a\u0430",
        "\u043d\u0443\u0436\u043d\u044b",
        "\u043d\u0443\u0436\u043d\u043e",
        "\u0442\u0440\u0435\u0431\u0443\u044e\u0442\u0441\u044f",
    ]
    mentions_places = bool(re.search(r"\b\u043c\u0435\u0441\u0442\w*\b", lowered))
    return (
        mentions_places
        and any(marker in lowered for marker in availability_markers)
        and not any(marker in lowered for marker in direct_need_markers)
    )


def looks_like_age_limit_only(text):
    lowered = text.lower()
    age_pattern = r"\b(?:до|от)\s*\d{1,2}(?:\s*[-–—]\s*\d{1,2})?\s*(?:лет|года?|г\.)\b"
    if not re.search(age_pattern, lowered):
        return False

    without_age = re.sub(age_pattern, " ", lowered)
    direct_need_markers = [
        "\u043f\u043e\u0442\u0440\u0435\u0431\u043d\u043e\u0441\u0442\u044c",
        "\u0437\u0430\u044f\u0432\u043a\u0430",
        "\u043d\u0443\u0436\u043d\u044b",
        "\u043d\u0443\u0436\u043d\u043e",
        "\u0442\u0440\u0435\u0431\u0443\u044e\u0442\u0441\u044f",
    ]
    return (
        not re.search(r"\d+", without_age)
        and not any(marker in lowered for marker in direct_need_markers)
    )


def looks_like_transfer_discussion(text):
    lowered = text.lower()
    rate_markers = [
        "\u0447\u0435\u043b\u043e\u0432\u0435\u043a \u0441\u0443\u0442\u043e\u0447\u043d\u043e",
        "\u0447\u0435\u043b\u043e\u0432\u0435\u043a \u0432 \u0441\u0443\u0442\u043a\u0438",
        "\u0447\u0435\u043b\u043e\u0432\u0435\u043a \u0435\u0436\u0435\u0434\u043d\u0435\u0432\u043d\u043e",
    ]
    transfer_markers = [
        "\u0432 \u0441\u043b\u0443\u0447\u0430\u0435 \u0441\u043e\u043a\u0440\u0430\u0449\u0435\u043d\u0438\u044f \u0437\u0430\u044f\u0432\u043a\u0438",
        "\u043f\u0440\u0438 \u0441\u043e\u043a\u0440\u0430\u0449\u0435\u043d\u0438\u0438 \u0437\u0430\u044f\u0432\u043a\u0438",
        "\u043f\u0435\u0440\u0435\u0432\u0435\u0434\u0443 \u043d\u0430",
        "\u043f\u0435\u0440\u0435\u0432\u0435\u0441\u0442\u0438 \u043d\u0430",
        "\u043f\u0435\u0440\u0435\u043d\u0430\u043f\u0440\u0430\u0432\u043b\u044e \u043d\u0430",
    ]
    return (
        any(marker in lowered for marker in rate_markers)
        or sum(marker in lowered for marker in transfer_markers) >= 2
    )


def looks_like_arrival_coordination(text):
    lowered = text.lower()
    coordination_markers = [
        "\u0437\u0430\u0441\u0435\u043b\u0435\u043d\u0438\u0435",
        "\u0437\u0430\u0441\u0435\u043b\u044f\u044e\u0442\u0441\u044f",
        "\u0437\u0430\u0441\u0435\u043b\u044f\u0442\u0441\u044f",
        "\u0437\u0430\u0441\u0435\u043b\u0438\u0442\u044c\u0441\u044f",
        "\u0433\u043e\u0442\u043e\u0432\u044b \u0437\u0430\u0441\u0435\u043b\u0438\u0442\u044c\u0441\u044f",
        "\u0441\u043e\u0433\u043b\u0430\u0441\u0443\u0435\u0442\u0435",
        "\u0441\u043e\u0433\u043b\u0430\u0441\u043e\u0432\u0430\u0442\u044c",
        "\u0432\u043e\u0437\u044c\u043c\u0451\u0442\u0435",
        "\u0432\u043e\u0437\u044c\u043c\u0435\u0442\u0435",
        "\u043f\u0440\u0438\u043c\u0435\u0442\u0435",
        "\u0442\u0430\u043a\u0441\u0438",
        "\u043a\u0443\u0434\u0430 \u0432\u0435\u0437\u0442\u0438",
    ]
    direct_need_markers = [
        "\u043f\u043e\u0442\u0440\u0435\u0431\u043d\u043e\u0441\u0442\u044c",
        "\u0437\u0430\u044f\u0432\u043a\u0430",
        "\u043d\u0443\u0436\u043d\u044b",
        "\u043d\u0443\u0436\u043d\u043e",
        "\u0442\u0440\u0435\u0431\u0443\u044e\u0442\u0441\u044f",
    ]
    return (
        sum(marker in lowered for marker in coordination_markers) >= 2
        and not any(marker in lowered for marker in direct_need_markers)
    )


def looks_like_training_schedule(text):
    """Отличает расписание инструктажа/обучения от заявки на персонал."""
    lowered = text.lower()
    training_markers = [
        "\u043e\u0431\u0443\u0447\u0435\u043d\u0438",
        "\u0438\u043d\u0441\u0442\u0440\u0443\u043a\u0442\u0430\u0436",
    ]
    schedule_markers = [
        "\u0441\u0440\u043e\u043a\u0430\u0445 \u0432\u044b\u0432\u043e\u0434\u0430",
        "\u0441\u043f\u0438\u0441\u043a\u0438 \u043d\u0430 \u043e\u0431\u0443\u0447\u0435\u043d\u0438\u0435",
        "\u043f\u043e\u043f\u0430\u0434\u0443\u0442 \u043d\u0430 \u043e\u0431\u0443\u0447\u0435\u043d\u0438\u0435",
        "\u043f\u0440\u0438\u0435\u0437\u0436\u0430",
        "\u043f\u043e\u0434\u0430\u044e\u0442\u0441\u044f \u0434\u043e",
    ]
    direct_need_markers = [
        "\u043f\u043e\u0442\u0440\u0435\u0431\u043d\u043e\u0441\u0442\u044c",
        "\u0437\u0430\u044f\u0432\u043a\u0430",
        "\u043d\u0443\u0436\u043d\u044b",
        "\u043d\u0443\u0436\u043d\u043e",
        "\u0442\u0440\u0435\u0431\u0443\u044e\u0442\u0441\u044f",
    ]
    has_calendar = bool(
        re.search(
            r"\b(?:\u043f\u043d|\u0432\u0442|\u0441\u0440|\u0447\u0442|\u043f\u0442|\u0441\u0431|\u0432\u0441)"
            r"(?:\s*[-\u2013\u2014]\s*(?:\u043f\u043d|\u0432\u0442|\u0441\u0440|\u0447\u0442|\u043f\u0442|\u0441\u0431|\u0432\u0441))*\b"
            r"|\b\d{1,2}:\d{2}\b",
            lowered,
        )
    )
    return (
        any(marker in lowered for marker in training_markers)
        and (
            has_calendar
            or sum(marker in lowered for marker in schedule_markers) >= 2
        )
        and not any(marker in lowered for marker in direct_need_markers)
    )


def looks_like_need(text):
    if (
        looks_like_shift_report(text)
        or looks_like_place_question(text)
        or looks_like_trip_details(text)
        or looks_like_arrival_notice(text)
        or looks_like_candidate_travel(text)
        or looks_like_candidate_arrival(text)
        or looks_like_discussion_question(text)
        or looks_like_operational_discussion(text)
        or looks_like_need_explanation(text)
        or looks_like_place_availability(text)
        or looks_like_age_limit_only(text)
        or looks_like_transfer_discussion(text)
        or looks_like_arrival_coordination(text)
        or looks_like_training_schedule(text)
    ):
        return False

    lowered = text.lower()
    markers = [
        "потребность",
        "потоебность",
        "нужн",
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
        "комплект",
        "сбор",
        "оператор",
        "упаков",
        "убор",
        "работник",
    ]
    return (
        any(marker in lowered for marker in markers)
        or bool(re.search(r"\b[мж]\s*[-:]?\s*\d+\b", lowered))
        or bool(re.search(r"\b\d+\s*[мж]\b(?!\s*мест)", lowered))
    )


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
        for object_name in OBJECT_POSITIONS:
            if object_name.lower() in lowered:
                return object_name
    return None


def resolve_object_name(chat_id, chat_title, text):
    chat_objects = load_chat_objects()
    chat_id_key = str(chat_id) if chat_id is not None else ""
    object_from_chat = chat_objects.get(chat_id_key) or chat_objects.get(chat_title)
    if object_from_chat:
        return object_from_chat

    object_from_text = find_object_in_text(text)
    if object_from_text:
        return object_from_text

    return chat_title or "объект из MAX-чата"


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


def extract_message(update):
    if isinstance(update.get("message"), dict):
        return update["message"]
    if isinstance(update.get("payload"), dict) and isinstance(update["payload"].get("message"), dict):
        return update["payload"]["message"]
    return update


def extract_text(message):
    body = message.get("body") if isinstance(message, dict) else {}
    if isinstance(body, dict):
        text = body.get("text") or body.get("message")
        if isinstance(text, str):
            return text.strip()
    for key in ("text", "message"):
        text = message.get(key) if isinstance(message, dict) else None
        if isinstance(text, str):
            return text.strip()
    return ""


def extract_chat_id(update, message):
    for source in (update, message):
        chat_id = source.get("chat_id") if isinstance(source, dict) else None
        if chat_id is not None:
            return chat_id

    recipient = message.get("recipient") if isinstance(message, dict) else None
    if isinstance(recipient, dict):
        return recipient.get("chat_id") or recipient.get("id")
    return None


def extract_message_id(update, message, chat_id, text):
    for source in (message, update):
        for key in ("message_id", "id", "mid"):
            value = source.get(key) if isinstance(source, dict) else None
            if value is not None:
                return value

    timestamp = update.get("timestamp") or message.get("timestamp") or ""
    digest = hashlib.sha256(f"{chat_id}|{timestamp}|{text}".encode("utf-8")).hexdigest()[:12]
    return f"{timestamp}-{digest}"


def make_max_key(chat_id, message_id):
    return f"max|{chat_id}|{message_id}"


def save_rows_from_message(chat_id, chat_title, message_id, text, rows, object_name, status):
    message_key = make_max_key(chat_id, message_id)
    saved_drafts = load_saved_drafts()

    if any(draft.get("message_key") == message_key for draft in saved_drafts):
        print(f"Дубль пропущен: chat={chat_id} message={message_id}")
        return False

    saved_drafts.append(
        {
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "source": f"MAX: {chat_title or chat_id} #{message_id}",
            "message_key": message_key,
            "source_object": object_name,
            "max": {
                "chat_id": chat_id,
                "chat_title": chat_title or "",
                "message_id": message_id,
                "text": text,
            },
            "status": status,
            "rows": rows,
        }
    )
    write_saved_drafts(saved_drafts)
    return True


def process_update(update):
    refresh_object_positions()
    update_type = update.get("update_type")
    if update_type in {"bot_added", "chat_title_changed"}:
        chat_id = update.get("chat_id")
        chat_title = get_chat_title(chat_id)
        print(f"MAX событие: {update_type}, chat_id={chat_id}, chat={chat_title or 'без названия'}")
        return

    if update_type != "message_created":
        return

    message = extract_message(update)
    text = extract_text(message)
    chat_id = extract_chat_id(update, message)
    message_id = extract_message_id(update, message, chat_id, text)
    chat_title = get_chat_title(chat_id)

    print(f"Получено MAX сообщение: chat={chat_id} title={chat_title or 'без названия'} message={message_id}")
    print("Текст:", text[:500].replace("\n", " | "))

    if not text or not looks_like_need(text):
        print("Пропущено: не похоже на потребность")
        return

    object_name = resolve_object_name(chat_id, chat_title, text)
    print(f"Объект для разбора: {object_name}")

    drafts = parse_messages(
        [
            {
                "source": f"MAX: {chat_title or chat_id} #{message_id}",
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
        print(f"Не получилось собрать строки: chat={chat_id} message={message_id}")
        print("Нет даже черновых строк. Проверь текст сообщения и правила распознавания.")
        return

    saved = save_rows_from_message(chat_id, chat_title, message_id, text, rows, object_name, status)
    if saved:
        print(f"Сохранён черновик: {object_name}, строк: {len(rows)}, статус: {status}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Нужно задать MAX_BOT_TOKEN")

    marker = load_marker()
    print("MAX-бот запущен")
    print("Режим: чтение сообщений через Long Polling. Без отправки сообщений и без публикации в Вектор.")
    print("Если это первый запуск, MAX может вернуть только последнее событие, дальше пойдут новые сообщения.")

    while True:
        try:
            data = get_updates(marker)
            marker = data.get("marker", marker)
            write_marker(marker)

            updates = data.get("updates", [])
            for update in updates:
                process_update(update)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            print(f"Ошибка MAX API: HTTP {error.code}: {body[:500]}")
            time.sleep(5)
        except Exception as error:
            print(f"Ошибка подключения к MAX API: {error}")
            time.sleep(5)


if __name__ == "__main__":
    main()
