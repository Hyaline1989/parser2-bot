import os
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4


NUMBER_FIELDS = {
    "rf_rb_m": ("rf_men", "РФ/РБ М"),
    "rf_rb_f": ("rf_women", "РФ/РБ Ж"),
    "rf_rb_family": ("rf_family", "РФ/РБ Семьи"),
    "cis_m": ("cis_men", "СНГ М"),
    "cis_f": ("cis_women", "СНГ Ж"),
    "cis_family": ("cis_family", "СНГ Семьи"),
}


class VectorIntegrationError(Exception):
    pass


def find_vector_db_path():
    configured_path = os.getenv("VECTOR_DB_PATH")
    candidates = []
    if configured_path:
        candidates.append(Path(configured_path))

    candidates.extend(
        [
            Path.home() / "Desktop" / "vs" / "requirements.db",
            Path("/var/www/check_comple_usr/data/www/check.complect.org/checkform/requirements.db"),
            Path("/var/www/check_comple_usr/data/www/check.complect.org/checkform/instance/requirements.db"),
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(configured_path) if configured_path else candidates[0]


def load_vector_requirements(db_path=None):
    db_path = Path(db_path) if db_path else find_vector_db_path()
    if not db_path.exists():
        raise VectorIntegrationError(f"База Вектора не найдена: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT object_name, position_name,
                   rf_men, rf_women, rf_family,
                   cis_men, cis_women, cis_family,
                   is_high
            FROM current_requirements
            """
        ).fetchall()
    finally:
        conn.close()

    requirements = {}
    for row in rows:
        object_name = row["object_name"]
        position_name = row["position_name"]
        requirements.setdefault(
            object_name,
            {
                "positions": {},
                "is_high": bool(row["is_high"]),
            },
        )
        requirements[object_name]["positions"][position_name] = {
            "rf_men": row["rf_men"] or 0,
            "rf_women": row["rf_women"] or 0,
            "rf_family": row["rf_family"] or 0,
            "cis_men": row["cis_men"] or 0,
            "cis_women": row["cis_women"] or 0,
            "cis_family": row["cis_family"] or 0,
        }
    return requirements, db_path


def safe_int(value):
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def calculate_vector_batches(row_batches, db_path=None):
    requirements, resolved_db_path = load_vector_requirements(db_path)
    errors = []
    valid_batches = []

    for rows in row_batches:
        valid_rows = []
        for row in rows:
            object_name = row.get("object", "").strip()
            position_name = row.get("position", "").strip()
            operation = row.get("operation") or "заменить"

            if object_name not in requirements:
                errors.append(f"{object_name}: объект не найден в Векторе")
                continue
            if position_name not in requirements[object_name]["positions"]:
                errors.append(f"{object_name} / {position_name}: должность не найдена в Векторе")
                continue

            valid_rows.append((row, object_name, position_name, operation))
        valid_batches.append(valid_rows)

    if errors:
        return requirements, resolved_db_path, {}, [], errors

    affected_objects = {
        object_name
        for valid_rows in valid_batches
        for _row, object_name, _position, _operation in valid_rows
    }
    target_values = {}
    operation_by_position = {}

    for object_name in affected_objects:
        for position_name, current in requirements[object_name]["positions"].items():
            key = (object_name, position_name)
            target_values[key] = {
                vector_field: safe_int(current.get(vector_field))
                for vector_field, _label in NUMBER_FIELDS.values()
            }

    for valid_rows in valid_batches:
        reset_objects = {
            object_name
            for _row, object_name, _position, operation in valid_rows
            if operation != "прибавить"
        }
        for object_name in reset_objects:
            for position_name in requirements[object_name]["positions"]:
                key = (object_name, position_name)
                for vector_field, _label in NUMBER_FIELDS.values():
                    target_values[key][vector_field] = 0
                operation_by_position[key] = "заменить"

        for row, object_name, position_name, operation in valid_rows:
            key = (object_name, position_name)
            for parser_field, (vector_field, _label) in NUMBER_FIELDS.items():
                row_value = safe_int(row.get(parser_field))
                if operation == "прибавить":
                    target_values[key][vector_field] += row_value
                else:
                    # One message can contain separate rows for men and women
                    # for the same position. The object was reset above, so
                    # replacement rows must be combined instead of overwriting
                    # one another.
                    target_values[key][vector_field] += row_value
            operation_by_position[key] = operation

    changes = []
    for (object_name, position_name), values in target_values.items():
        current = requirements[object_name]["positions"][position_name]
        for _parser_field, (vector_field, label) in NUMBER_FIELDS.items():
            current_value = safe_int(current.get(vector_field))
            new_value = values[vector_field]
            if new_value == current_value:
                continue
            changes.append(
                {
                    "object": object_name,
                    "position": position_name,
                    "field": label,
                    "operation": operation_by_position.get((object_name, position_name), "заменить"),
                    "current": current_value,
                    "new": new_value,
                }
            )

    return requirements, resolved_db_path, target_values, changes, []


def calculate_vector_update(rows, db_path=None):
    return calculate_vector_batches([rows], db_path)


def build_vector_preview(rows, db_path=None):
    _requirements, resolved_db_path, _target_values, changes, errors = calculate_vector_update(rows, db_path)
    return {
        "db_path": str(resolved_db_path),
        "changes": changes,
        "errors": errors,
    }


def build_vector_batches_preview(row_batches, db_path=None):
    _requirements, resolved_db_path, _target_values, changes, errors = calculate_vector_batches(row_batches, db_path)
    return {
        "db_path": str(resolved_db_path),
        "changes": changes,
        "errors": errors,
    }


def create_vector_backup(db_path):
    source_path = Path(db_path)
    configured_dir = os.getenv("VECTOR_BACKUP_DIR")
    backup_dir = Path(configured_dir) if configured_dir else Path(__file__).with_name("data") / "vector_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = backup_dir / f"requirements_before_{timestamp}_{uuid4().hex[:8]}.db"

    source = sqlite3.connect(source_path)
    backup = sqlite3.connect(backup_path)
    try:
        source.backup(backup)
    finally:
        backup.close()
        source.close()

    backups = sorted(backup_dir.glob("requirements_before_*.db"), key=lambda path: path.stat().st_mtime)
    for old_backup in backups[:-30]:
        old_backup.unlink(missing_ok=True)
    return backup_path


def publish_vector_batches(row_batches, db_path=None):
    _requirements, resolved_db_path, target_values, changes, errors = calculate_vector_batches(row_batches, db_path)
    if errors:
        raise VectorIntegrationError("; ".join(errors))

    backup_path = create_vector_backup(resolved_db_path)
    conn = sqlite3.connect(Path(resolved_db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        today = datetime.now().strftime("%Y-%m-%d")
        for (object_name, position_name), values in target_values.items():
            cursor.execute(
                """
                UPDATE current_requirements
                SET rf_men = ?, rf_women = ?, rf_family = ?,
                    cis_men = ?, cis_women = ?, cis_family = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE object_name = ? AND position_name = ?
                """,
                (
                    values["rf_men"],
                    values["rf_women"],
                    values["rf_family"],
                    values["cis_men"],
                    values["cis_women"],
                    values["cis_family"],
                    object_name,
                    position_name,
                ),
            )
            if cursor.rowcount != 1:
                raise VectorIntegrationError(f"{object_name} / {position_name}: строка не обновлена в Векторе")

            cursor.execute(
                """
                SELECT vp.id
                FROM vacancy_positions vp
                JOIN vacancy_objects vo ON vo.id = vp.object_id
                WHERE vo.name = ? AND vp.name = ?
                """,
                (object_name, position_name),
            )
            position_row = cursor.fetchone()
            if not position_row:
                raise VectorIntegrationError(
                    f"{object_name} / {position_name}: должность не найдена в дневном плане Вектора"
                )

            position_id = position_row[0]
            cursor.execute(
                """
                SELECT rf_men, rf_women, rf_family,
                       cis_men, cis_women, cis_family
                FROM vacancy_requirements
                WHERE position_id = ? AND date = ?
                """,
                (position_id, today),
            )
            existing = cursor.fetchone()
            ordered_values = (
                values["rf_men"], values["rf_women"], values["rf_family"],
                values["cis_men"], values["cis_women"], values["cis_family"],
            )
            if existing:
                daily_maximums = tuple(
                    max(safe_int(old_value), new_value)
                    for old_value, new_value in zip(existing, ordered_values)
                )
                cursor.execute(
                    """
                    UPDATE vacancy_requirements
                    SET rf_men = ?, rf_women = ?, rf_family = ?,
                        cis_men = ?, cis_women = ?, cis_family = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE position_id = ? AND date = ?
                    """,
                    (*daily_maximums, position_id, today),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO vacancy_requirements
                        (position_id, date, rf_men, rf_women, rf_family,
                         cis_men, cis_women, cis_family, is_high)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (position_id, today, *ordered_values),
                )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "db_path": str(resolved_db_path),
        "backup_path": str(backup_path),
        "changes": changes,
        "errors": [],
    }


def publish_vector_rows(rows, db_path=None):
    return publish_vector_batches([rows], db_path)
