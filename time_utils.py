from datetime import datetime, timedelta, timezone


MOSCOW_TIMEZONE = timezone(timedelta(hours=3), name="MSK")


def moscow_now():
    """Возвращает текущее время в часовом поясе Москвы."""
    return datetime.now(MOSCOW_TIMEZONE)


def moscow_iso_now():
    """Московское время в прежнем формате интерфейса, без суффикса зоны."""
    return moscow_now().replace(tzinfo=None).isoformat(timespec="seconds")


def moscow_today():
    return moscow_now().strftime("%Y-%m-%d")


def moscow_backup_timestamp():
    return moscow_now().strftime("%Y%m%d_%H%M%S_%f")
