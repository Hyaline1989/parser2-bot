import re

from rules_loader import get_position_aliases, get_position_gender_defaults
from vector_catalog import find_default_position_in_message, resolve_position_for_object


NO_POSITION = "не указана"
DEFAULT_OBJECT = "объект из Telegram-чата"

POSITION_ALIASES = get_position_aliases()
POSITION_HINTS = sorted(POSITION_ALIASES, key=len, reverse=True)
POSITION_GENDER_DEFAULTS = get_position_gender_defaults()
ALL_POSITIONS = "Все должности"
DEFAULT_CITIZENSHIP_BY_OBJECT = {
    "Клинский мясокомбинат": "СНГ",
    "КуулКлевер": "СНГ",
}


def is_zero_requirement(text):
    """Распознаёт только явную команду обнулить потребность объекта."""
    lowered = clean_text(text).lower()
    patterns = [
        r"\bпотребност\w*\s*(?:[:=\-–—]\s*)?0\b",
        r"\bпотребност(?:ь|и)\s+(?:больше\s+)?нет\b",
        r"\bобнул(?:ить|ите|яем|яется)\s+потребност\w*\b",
    ]
    if any(re.search(pattern, lowered) for pattern in patterns):
        return True

    # Полная таблица потребности, где все кадровые категории равны нулю.
    # Даты и время не попадут сюда: число должно стоять рядом с полом/семьями.
    if "потребност" not in lowered:
        return False
    gender_then_quantity = re.findall(
        r"\b(?:мужск\w*|женск\w*|мужчин\w*|женщин\w*|семейн\w*)"
        r"\s*[:=\-–—]?\s*(\d+)(?!\d)",
        lowered,
    )
    quantity_then_gender = re.findall(
        r"\b(\d+)\s*(?:мужск\w*|женск\w*|мужчин\w*|женщин\w*|семейн\w*)\b",
        lowered,
    )
    staffing_quantities = [
        int(value)
        for value in gender_then_quantity + quantity_then_gender
    ]
    return bool(staffing_quantities) and all(value == 0 for value in staffing_quantities)


def parse_messages(messages):
    drafts = []
    for message in messages:
        drafts.extend(parse_message(message))
    return drafts


def parse_message(message):
    text = clean_text(message["text"])
    text_for_parsing = keep_need_block(text)
    source = message.get("source", "Тестовый чат")
    object_name = message.get("object") or DEFAULT_OBJECT
    operation = detect_operation(text)

    if is_zero_requirement(text):
        return [
            {
                "source": source,
                "text": text,
                "object": object_name,
                "position": ALL_POSITIONS,
                "position_source": "явное обнуление",
                "quantity": 0,
                "gender": "все",
                "need_type": "обнуление",
                "citizenship": "все",
                "operation": "обнулить",
                "status": "готово к проверке",
                "unclear": "",
            }
        ]

    drafts = []
    current_position = find_default_position_in_message(object_name, text)
    family_fallback_position = None
    current_citizenship = DEFAULT_CITIZENSHIP_BY_OBJECT.get(object_name, "РФ/РБ")

    for raw_line in text_for_parsing.splitlines():
        line = clean_line(raw_line)
        if not line:
            continue

        citizenship = find_citizenship(line)
        if citizenship:
            current_citizenship = citizenship
            continue

        heading_position = find_heading_position(line)
        if heading_position and not line_has_quantity(line):
            current_position = heading_position
            continue

        line_position = find_position(line)
        for item in parse_need_line(line, current_position):
            if item["quantity"] == 0:
                continue

            if item["gender"] == "мужчины" and line_position:
                family_fallback_position = line_position
            if (
                item["need_type"] == "семейная"
                and not line_position
                and family_fallback_position
            ):
                item["position"] = family_fallback_position

            parsed_position = item["position"] or current_position
            if item["position"]:
                current_position = item["position"]
            position, position_source = resolve_position_for_object(
                object_name, parsed_position, item["gender"]
            )
            position = position or NO_POSITION
            unclear = []
            if position == NO_POSITION and item["need_type"] != "семейная":
                unclear.append("должность")
            if position_source in [
                "не указана",
                "нет объекта в справочнике",
                "должность не найдена в справочнике",
            ]:
                unclear.append(position_source)

            drafts.append(
                {
                    "source": source,
                    "text": text,
                    "object": object_name,
                    "position": position,
                    "position_source": position_source,
                    "quantity": item["quantity"],
                    "gender": item["gender"],
                    "need_type": item["need_type"],
                    "citizenship": current_citizenship,
                    "operation": operation,
                    "status": "готово к проверке" if not unclear else "требует проверки",
                    "unclear": ", ".join(unclear),
                    "_aggregate_total": is_unqualified_total_line(line),
                }
            )

    if drafts:
        drafts = remove_redundant_aggregate_totals(drafts)
        for draft in drafts:
            draft.pop("_aggregate_total", None)
        return drafts

    return [
        {
            "source": source,
            "text": text,
            "object": object_name,
            "position": NO_POSITION,
            "position_source": "не указана",
            "quantity": "не найдено",
            "gender": "не указан",
            "need_type": "обычная",
            "citizenship": "не указано",
            "operation": operation,
            "status": "требует проверки",
            "unclear": "количество, должность",
        }
    ]


def is_unqualified_total_line(line):
    lowered = line.lower()
    return (
        bool(re.search(r"\b\d+\s*(?:человек|чел)\b", lowered))
        and find_explicit_gender(line) is None
        and find_position(line) is None
    )


def remove_redundant_aggregate_totals(drafts):
    aggregate_rows = [draft for draft in drafts if draft.get("_aggregate_total")]
    detail_rows = [draft for draft in drafts if not draft.get("_aggregate_total")]
    if not aggregate_rows or not detail_rows:
        return drafts

    detail_total = sum(
        draft["quantity"]
        for draft in detail_rows
        if isinstance(draft.get("quantity"), int)
    )
    redundant_ids = {
        id(draft)
        for draft in aggregate_rows
        if draft.get("quantity") == detail_total
    }
    return [draft for draft in drafts if id(draft) not in redundant_ids]


def parse_need_line(line, current_position):
    items = []
    line = remove_age_limits(line)
    lowered = remove_time_durations(line.lower())
    # Пояснения в скобках описывают условия работы и могут упоминать другие
    # должности. Они не должны переопределять заголовок текущего раздела.
    line_without_comments = re.sub(r"\([^)]*\)", " ", line)
    line_position = find_position(line_without_comments)

    for match in re.finditer(
        r"(\d+)\s*\(?\s*(муж(?:чин(?:а|ы)?|ской|ские|ских)?|жен(?:щин(?:а|ы)?|ский|ские|ских)?)\s*\)?",
        lowered,
    ):
        gender, need_type = gender_and_type(match.group(2))
        items.append(
            make_item(
                quantity=match.group(1),
                gender=gender,
                position=line_position or current_position,
                need_type=need_type,
            )
        )

    for match in re.finditer(r"(\d+)\s*\(?\s*(ж|м)\s*\)?(?![а-яё.])", lowered):
        items.append(
            make_item(
                quantity=match.group(1),
                gender=gender_from_short(match.group(2)),
                position=line_position or current_position,
            )
        )

    for match in re.finditer(r"\b(ж|м)\s*[-:]?\s*(\d+)\b(?!\s*[а-яё]{2})", lowered):
        items.append(
            make_item(
                quantity=match.group(2),
                gender=gender_from_short(match.group(1)),
                position=line_position or current_position,
            )
        )

    if items:
        return items

    quantity_position_items = parse_quantity_position_items(line)
    if quantity_position_items:
        return quantity_position_items

    position_quantity_items = parse_position_quantity_items(line)
    if position_quantity_items:
        return position_quantity_items

    gender_match = re.search(
        r"\b(муж(?:ской|ские|ских|чины|чина)?|жен(?:ский|ские|ских|щины|щина)?|сем(?:ейная|ейные|ейный)?|семейные?)(?![а-яё])",
        lowered,
    )
    if gender_match:
        quantity_match = re.search(r"[-:]?\s*(\d+)(?!\d|[.:]\d)", lowered[gender_match.end() :])
        if quantity_match:
            quantity = quantity_match.group(1)
            tail_start = gender_match.end() + quantity_match.end()
            tail = line[tail_start:]
            tail_without_comments = re.sub(r"\([^)]*\)", " ", tail)
            gender, need_type = gender_and_type(gender_match.group(1))
            position = (
                find_position_after_quantity(tail_without_comments)
                or line_position
                or current_position
            )
            return [
                make_item(
                    quantity=quantity,
                    gender=gender,
                    position=position,
                    need_type=need_type,
                )
            ]

    position = line_position or current_position
    quantity_match = re.search(r"[:\-]\s*(\d+)\b", lowered)
    if position and quantity_match:
        return [
            make_item(
                quantity=quantity_match.group(1),
                gender=find_gender(line),
                position=position,
            )
        ]

    range_quantity_match = re.search(
        r"\b\d+\s*[-–—]\s*\d+\s*(?:человек|чел)\b",
        lowered,
    )
    if range_quantity_match:
        return []
    quantity_match = None if range_quantity_match else re.search(
        r"\b(\d+)\s*(?:человек|чел)\b",
        lowered,
    )
    if quantity_match:
        quantity_tail = lowered[quantity_match.end() :]
        if re.match(r"\s*(?:суточно|в\s+сутки|ежедневно|за\s+смену)\b", quantity_tail):
            quantity_match = None
    quantity_context = lowered[max(0, quantity_match.start() - 60) : quantity_match.start()] if quantity_match else ""
    is_output_context = bool(re.search(r"\bвыход\w*(?:\s+в)?\s*$", quantity_context))
    has_direct_need = bool(re.search(r"\b(потребност\w*|заявк\w*|нужны|требуются)\b", lowered))
    if quantity_match and (not is_output_context or has_direct_need):
        return [
            make_item(
                quantity=quantity_match.group(1),
                gender=find_gender(line),
                position=position,
            )
        ]

    need_quantity_match = re.search(
        r"\bпотребность\b(?!\s+на\s+\d{1,2}\.)[^\d]{0,30}(\d+)(?!\.)\b",
        lowered,
    )
    if need_quantity_match:
        return [
            make_item(
                quantity=need_quantity_match.group(1),
                gender=find_gender(line),
                position=position,
            )
        ]

    return []


def remove_time_durations(text):
    text = re.sub(r"\b\d+\s*ч\.?\s*\d+\s*м\.?", " ", text)
    return re.sub(r"\b\d+\s*м\.", " ", text)


def remove_age_limits(text):
    return re.sub(
        r"\b(?:до|от)\s*\d{1,2}(?:\s*[-–—]\s*\d{1,2})?\s*(?:лет|года?|г\.)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )


def parse_position_quantity_items(line):
    items = []
    lowered = line.lower()
    position_pattern = "|".join(re.escape(hint) for hint in POSITION_HINTS)
    if not position_pattern:
        return items

    pattern = rf"\b({position_pattern})\b[^\d,;:]*[-:]?\s*(\d+)\b"
    for match in re.finditer(pattern, lowered):
        position_hint = match.group(1)
        position = POSITION_ALIASES[position_hint]
        gender = find_explicit_gender(line) or POSITION_GENDER_DEFAULTS.get(position_hint) or "мужчины"
        items.append(
            make_item(
                quantity=match.group(2),
                gender=gender,
                position=position,
            )
        )
    return items


def parse_quantity_position_items(line):
    items = []
    lowered = line.lower()
    position_pattern = "|".join(re.escape(hint) for hint in POSITION_HINTS)
    if not position_pattern:
        return items

    pattern = rf"\b(\d+)\s*\(?\s*({position_pattern})\b\s*\)?"
    for match in re.finditer(pattern, lowered):
        position_hint = match.group(2)
        items.append(
            make_item(
                quantity=match.group(1),
                gender=find_explicit_gender(line) or POSITION_GENDER_DEFAULTS.get(position_hint) or "мужчины",
                position=POSITION_ALIASES[position_hint],
            )
        )
    return items


def find_position_after_quantity(text):
    lowered = text.lower().strip()
    for hint in POSITION_HINTS:
        if lowered.startswith(hint):
            return POSITION_ALIASES[hint]
    return find_position(text)


def make_item(quantity, gender, position=None, need_type="обычная"):
    return {
        "quantity": int(quantity),
        "gender": gender or "мужчины",
        "position": position,
        "need_type": need_type,
    }


def clean_text(text):
    return text.replace("\xa0", " ").strip()


def keep_need_block(text):
    lines = text.splitlines()
    for index, line in enumerate(lines):
        lowered = line.lower()
        if "потребность" in lowered or "потоебность" in lowered:
            return "\n".join(lines[index:])
    return text


def clean_line(line):
    for symbol in ["*", "•", "‼️", "🚨"]:
        line = line.replace(symbol, " ")
    return re.sub(r"\s+", " ", line).strip()


def line_has_quantity(line):
    return bool(re.search(r"\d+", line))


def find_position(text):
    lowered = text.lower()
    for hint in POSITION_HINTS:
        if re.search(rf"\b{re.escape(hint)}\b", lowered):
            return POSITION_ALIASES[hint]
    return None


def find_heading_position(line):
    without_comment = re.sub(r"\([^)]*\)", " ", line)
    position = find_position(without_comment)
    if position:
        return position

    cleaned = re.sub(r"[^а-яА-ЯёЁa-zA-Z ]", " ", without_comment).strip()
    if len(cleaned.split()) > 3:
        return None
    return find_position(cleaned)


def find_gender(text):
    return find_explicit_gender(text) or "мужчины"


def find_explicit_gender(text):
    lowered = text.lower()
    if re.search(r"\bмуж", lowered):
        return "мужчины"
    if re.search(r"\b(мальчик|мальчики|мальчиков|парень|парни|парней|ребята)\b", lowered):
        return "мужчины"
    if re.search(r"\bжен", lowered):
        return "женщины"
    if re.search(r"\b(девочка|девочки|девочек|девушка|девушки|девушек|девчонки|девчонок)\b", lowered):
        return "женщины"
    if re.search(r"(?<![а-яё])ж(?![а-яё])", lowered):
        return "женщины"
    if re.search(r"(?<![а-яё])м(?![а-яё])", lowered):
        return "мужчины"
    return None


def detect_operation(text):
    lowered = text.lower()
    if (
        re.search(r"\b(добавляем|добавить|добавьте|прибавить|прибавляем|плюс)\b", lowered)
        or re.search(r"\bдоп(?:олнительная|олнительную|олнительно)?\s+потребность\b", lowered)
    ):
        return "прибавить"
    return "заменить"


def gender_from_short(short):
    return "женщины" if short == "ж" else "мужчины"


def gender_and_type(word):
    if word.startswith("сем"):
        return "семейные", "семейная"
    if word.startswith("жен"):
        return "женщины", "обычная"
    return "мужчины", "обычная"


def find_citizenship(line):
    lowered = line.lower()
    if "рф" in lowered or "рб" in lowered:
        return "РФ/РБ"
    if "снг" in lowered:
        return "СНГ"
    return None





