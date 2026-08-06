from rules_loader import get_position_matches


OBJECT_POSITIONS = {
    "Major": ["Комплектовщик", "Работник склада", "Стикеровщик"],
    "Агама Лешково": ["Работник производства"],
    "БелГранКорм Новгород": ["Работник производства", "Убойный цех"],
    "ГросШеф": ["Основная потребность", "Разнорабочий производства"],
    "Индейка Калуга": ["Работник производства", "Уборщик", "Упаковщик"],
    "Клинский мясокомбинат": ["Работник производства", "Ремонтные работы", "Уборщик", "Упаковщик"],
    "Креветки Клинский": ["Упаковщик"],
    "КуулКлевер": ["Работник склада", "Упаковщик"],
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
    "БелГранКорм Новгород": "Убойный цех",
    "Клинский мясокомбинат": "Работник производства",
    "ФитнесШок": "Упаковщик",
    "Индейка Калуга": "Работник производства",
    "КуулКлевер": "Работник склада",
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
    positions = OBJECT_POSITIONS.get(object_name, [])
    for phrase, position in DEFAULT_POSITIONS_BY_MESSAGE.get(object_name, []):
        if phrase in lowered and position in positions:
            return position
    return None


def resolve_position_for_object(object_name, parsed_position, gender=None):
    positions = OBJECT_POSITIONS.get(object_name, [])

    if not parsed_position:
        gender_defaults = DEFAULT_POSITIONS_BY_GENDER.get(object_name, {})
        if gender in gender_defaults and gender_defaults[gender] in positions:
            return gender_defaults[gender], "подставлено по правилу объекта и пола"
        if object_name in DEFAULT_POSITIONS and DEFAULT_POSITIONS[object_name] in positions:
            return DEFAULT_POSITIONS[object_name], "подставлено по правилу объекта"
        if len(positions) == 1:
            return positions[0], "подставлено автоматически"
        return None, "не указана"

    if not positions:
        return parsed_position, "нет объекта в справочнике"

    normalized_position = parsed_position.lower()
    object_overrides = POSITION_OVERRIDES_BY_OBJECT.get(object_name, {})
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




