from rules_loader import get_position_matches


OBJECT_POSITIONS = {
    "Major": ["Комплектовщик", "Работник склада", "Стикеровщик"],
    "АСКОНА": ["Разнорабочий"],
    "Агама Лешково": ["Работник производства"],
    "БелГранКорм Новгород": ["Работник производства", "Убойный цех"],
    "ГросШеф": ["Основная потребность", "Разнорабочий производства"],
    "Индейка Калуга": ["Работник производства", "Уборщик", "Упаковщик"],
    "Клинский мясокомбинат": ["Работник производства", "Ремонтные работы", "Уборщик", "Упаковщик"],
    "Креветки Клинский": ["Упаковщик"],
    "КуулКлевер": ["Работник склада", "Упаковщик", "Работник производства"],
    "Мармеладыч": ["Упаковщик"],
    "Мираторг": ["Работник производства", "Разнорабочий"],
    "Мираторг Тула": ["Работник производства"],
    "Мяснов": ["Работник производства", "Уборщик", "Упаковщик"],
    "Павловская Птицефабрика": ["Работник производства"],
    "РПС Звенигород": ["Сборщик заказов"],
    "СБЛ Ново-перед Хол": ["Комплектовщик"],
    "СДТ": ["Комплектовщик", "Работник склада", "Разнорабочий", "Уборщик", "Водитель"],
    "Сберлогистика Пушкино": ["Комплектовщик", "Работник склада"],
    "Спортмастер": ["Комплектовщик", "Работник склада"],
    "Тамбовский бекон": ["Специалист по уходу за животными"],
    "ФитнесШок": ["Уборщик", "Упаковщик"],
    "Форум Авто": ["Грузчик", "Кладовщик"],
    "Хоругвино Мираторг": ["Комплектовщик", "Основная потребность", "Водитель"],
    "Шашлык Тамбов": ["Обвальщик мяса"],
    "Яндекс Самара": ["Комплектовщик"],
}

DEFAULT_POSITIONS = {
    "АСКОНА": "Разнорабочий",
    "БелГранКорм Новгород": "Убойный цех",
    "Клинский мясокомбинат": "Работник производства",
    "ФитнесШок": "Упаковщик",
    "Индейка Калуга": "Работник производства",
    "КуулКлевер": "Работник производства",
    "Форум Авто": "Кладовщик",
}

DEFAULT_POSITIONS_BY_GENDER = {
    "Мяснов": {
        "мужчины": "Работник производства",
        "женщины": "Упаковщик",
    },
}

DEFAULT_POSITIONS_BY_MESSAGE = {
    "Мираторг": [
        ("заявка на бб", "Работник производства"),
    ],
}

POSITION_OVERRIDES_BY_OBJECT = {
    "КуулКлевер": {
        "пекарня": "Работник склада",
    },
    "СДТ": {
        "копакинг": "Разнорабочий",
        "оператор": "Разнорабочий",
    },
    "Форум Авто": {
        "комплектовщик": "Кладовщик",
        "погрузо-разгрузочные работы": "Грузчик",
    },
}


def refresh_object_positions(db_path=None):
    """Refresh the catalog in place so existing imports see current Vector data."""
    try:
        from vector_integration import load_vector_requirements

        requirements, _resolved_db_path = load_vector_requirements(db_path)
    except Exception:
        return False

    fresh_catalog = {
        object_name: list(object_data.get("positions", {}).keys())
        for object_name, object_data in requirements.items()
        if object_data.get("positions")
    }
    if not fresh_catalog:
        return False

    OBJECT_POSITIONS.clear()
    OBJECT_POSITIONS.update(fresh_catalog)
    return True


def find_default_position_in_message(object_name, text):
    lowered = text.lower()
    positions = get_object_rule(OBJECT_POSITIONS, object_name, [])
    for phrase, position in get_object_rule(DEFAULT_POSITIONS_BY_MESSAGE, object_name, []):
        if phrase in lowered and position in positions:
            return position
    return None


def get_object_rule(rules, object_name, default=None):
    """Ищет правило объекта без учёта регистра его названия."""
    if object_name in rules:
        return rules[object_name]
    normalized_name = object_name.casefold()
    for configured_name, value in rules.items():
        if configured_name.casefold() == normalized_name:
            return value
    return default


def match_catalog_position(configured_position, positions):
    """Возвращает точное название должности из актуального справочника Вектора."""
    normalized_position = configured_position.lower()
    possible_matches = get_position_matches().get(
        normalized_position, [normalized_position]
    )
    for position in positions:
        if position.lower() in possible_matches:
            return position
    for position in positions:
        position_lower = position.lower()
        if any(
            match in position_lower or position_lower in match
            for match in possible_matches
        ):
            return position
    return None


def resolve_position_for_object(object_name, parsed_position, gender=None):
    positions = get_object_rule(OBJECT_POSITIONS, object_name, [])

    if object_name.casefold() == "куулклевер":
        role = (parsed_position or "").casefold()
        if "упаков" in role:
            configured = "Упаковщик"
        elif "грузчик" in role or role == "работник склада":
            configured = "Работник склада"
        else:
            configured = "Работник производства"
        return (
            match_catalog_position(configured, positions) or configured,
            "подставлено по правилу объекта",
        )

    if not parsed_position:
        gender_defaults = get_object_rule(DEFAULT_POSITIONS_BY_GENDER, object_name, {})
        if gender in gender_defaults:
            matched = match_catalog_position(gender_defaults[gender], positions)
            if matched:
                return matched, "подставлено по правилу объекта и пола"
        configured_default = get_object_rule(DEFAULT_POSITIONS, object_name)
        if configured_default:
            matched = match_catalog_position(configured_default, positions)
            if matched:
                return matched, "подставлено по правилу объекта"
            # The configured object rule is authoritative even when the live
            # Vector catalog is temporarily unavailable or has not yet been
            # refreshed. Publication validation will still prevent writing to
            # a position that truly does not exist in Vector.
            return configured_default, "подставлено по правилу объекта"
        if len(positions) == 1:
            return positions[0], "подставлено автоматически"
        return None, "не указана"

    if not positions:
        return parsed_position, "нет объекта в справочнике"

    normalized_position = parsed_position.lower()
    object_overrides = get_object_rule(POSITION_OVERRIDES_BY_OBJECT, object_name, {})
    if normalized_position in object_overrides and object_overrides[normalized_position] in positions:
        return object_overrides[normalized_position], "подставлено по правилу объекта"

    possible_matches = get_position_matches().get(normalized_position, [normalized_position])
    for position in positions:
        position_lower = position.lower()
        if any(match == position_lower for match in possible_matches):
            return position, "найдена в сообщении"

    for position in positions:
        position_lower = position.lower()
        if any(match in position_lower or position_lower in match for match in possible_matches):
            return position, "найдена в сообщении"

    return parsed_position, "должность не найдена в справочнике"




