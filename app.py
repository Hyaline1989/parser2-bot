import hashlib
import json
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from parser import parse_messages
from sample_messages import SAMPLE_MESSAGES
from vector_integration import (
    VectorIntegrationError,
    build_vector_batches_preview,
    build_vector_preview,
    publish_vector_batches,
    publish_vector_rows,
)
from vector_catalog import OBJECT_POSITIONS, refresh_object_positions


app = Flask(__name__)
DRAFTS_FILE = Path(__file__).with_name("drafts.json")
PUBLICATION_HISTORY_FILE = Path(__file__).with_name("data") / "publication_history.json"


@app.before_request
def refresh_vector_catalog():
    refresh_object_positions()


def resolve_draft_index(payload, saved_drafts, index_field="index"):
    message_key = str(payload.get("message_key") or "").strip()
    if message_key:
        return next(
            (
                index
                for index, draft in enumerate(saved_drafts)
                if draft.get("message_key") == message_key
            ),
            None,
        )
    return payload.get(index_field)


@app.route("/", methods=["GET"])
def index():
    saved_drafts = prepare_saved_drafts(load_saved_drafts())
    publication_history = load_publication_history()

    return render_template(
        "index.html",
        saved_drafts=saved_drafts,
        object_positions=OBJECT_POSITIONS,
        publication_history=publication_history[:50],
        publication_count=len(publication_history),
    )


@app.route("/confirm-draft", methods=["POST"])
def confirm_draft():
    payload = request.get_json(silent=True) or {}
    saved_drafts = load_saved_drafts()
    draft_index = resolve_draft_index(payload, saved_drafts)

    if draft_index is None or not isinstance(draft_index, int):
        return jsonify({"ok": False, "message": "Не найден номер черновика"}), 400
    if draft_index < 0 or draft_index >= len(saved_drafts):
        return jsonify({"ok": False, "message": "Черновик не найден"}), 404
    if draft_has_unselected_positions(saved_drafts[draft_index]):
        return jsonify({"ok": False, "message": "Сначала выбери должность в строках, где указано “требует выбора”"}), 400

    saved_drafts[draft_index]["status"] = "подтверждён"
    saved_drafts[draft_index]["confirmed_at"] = datetime.now().isoformat(timespec="seconds")
    write_saved_drafts(saved_drafts)
    return jsonify({"ok": True, "message": "Черновик подтверждён"})


@app.route("/reject-draft", methods=["POST"])
def reject_draft():
    payload = request.get_json(silent=True) or {}
    saved_drafts = load_saved_drafts()
    draft_index = resolve_draft_index(payload, saved_drafts)

    if draft_index is None or not isinstance(draft_index, int):
        return jsonify({"ok": False, "message": "Не найден номер черновика"}), 400
    if draft_index < 0 or draft_index >= len(saved_drafts):
        return jsonify({"ok": False, "message": "Черновик не найден"}), 404

    saved_drafts[draft_index]["status"] = "отклонён"
    saved_drafts[draft_index]["rejected_at"] = datetime.now().isoformat(timespec="seconds")
    write_saved_drafts(saved_drafts)
    return jsonify({"ok": True, "message": "Черновик отклонён"})


@app.route("/delete-draft", methods=["POST"])
def delete_draft():
    payload = request.get_json(silent=True) or {}
    saved_drafts = load_saved_drafts()
    draft_index = resolve_draft_index(payload, saved_drafts)

    if draft_index is None or not isinstance(draft_index, int):
        return jsonify({"ok": False, "message": "Не найден номер черновика"}), 400
    if draft_index < 0 or draft_index >= len(saved_drafts):
        return jsonify({"ok": False, "message": "Черновик не найден"}), 404

    saved_drafts.pop(draft_index)
    write_saved_drafts(saved_drafts)
    return jsonify({"ok": True, "message": "Черновик удалён"})


@app.route("/delete-working-drafts", methods=["POST"])
def delete_working_drafts():
    delete_statuses = {"черновик", "требует проверки"}
    saved_drafts = load_saved_drafts()
    kept_drafts = [
        draft
        for draft in saved_drafts
        if draft.get("status", "черновик") not in delete_statuses
    ]
    deleted_count = len(saved_drafts) - len(kept_drafts)

    write_saved_drafts(kept_drafts)
    return jsonify(
        {
            "ok": True,
            "message": f"Удалено черновиков: {deleted_count}",
            "deleted_count": deleted_count,
        }
    )


@app.route("/vector-preview-draft", methods=["POST"])
def vector_preview_draft():
    payload = request.get_json(silent=True) or {}
    saved_drafts = load_saved_drafts()
    draft_index = resolve_draft_index(payload, saved_drafts)

    if draft_index is None or not isinstance(draft_index, int):
        return jsonify({"ok": False, "message": "Не найден номер черновика"}), 400
    if draft_index < 0 or draft_index >= len(saved_drafts):
        return jsonify({"ok": False, "message": "Черновик не найден"}), 404

    draft = saved_drafts[draft_index]
    if draft.get("status") != "подтверждён":
        return jsonify({"ok": False, "message": "Сначала подтверди черновик"}), 400

    try:
        preview = build_vector_preview(draft.get("rows", []))
    except VectorIntegrationError as error:
        return jsonify({"ok": False, "message": str(error)}), 400
    except Exception as error:
        return jsonify({"ok": False, "message": f"Ошибка проверки Вектора: {error}"}), 500

    return jsonify({"ok": True, "preview": preview})


@app.route("/publish-draft-to-vector", methods=["POST"])
def publish_draft_to_vector():
    payload = request.get_json(silent=True) or {}
    saved_drafts = load_saved_drafts()
    draft_index = resolve_draft_index(payload, saved_drafts)

    if draft_index is None or not isinstance(draft_index, int):
        return jsonify({"ok": False, "message": "Не найден номер черновика"}), 400
    if draft_index < 0 or draft_index >= len(saved_drafts):
        return jsonify({"ok": False, "message": "Черновик не найден"}), 404

    draft = saved_drafts[draft_index]
    if draft.get("status") == "опубликовано":
        return jsonify({"ok": False, "message": "Этот черновик уже опубликован"}), 400
    if draft.get("status") != "подтверждён":
        return jsonify({"ok": False, "message": "Публиковать можно только подтверждённый черновик"}), 400

    try:
        preview = publish_vector_rows(draft.get("rows", []))
    except VectorIntegrationError as error:
        return jsonify({"ok": False, "message": str(error)}), 400
    except Exception as error:
        return jsonify({"ok": False, "message": f"Ошибка публикации в Вектор: {error}"}), 500

    published_at = datetime.now().isoformat(timespec="seconds")
    draft["status"] = "опубликовано"
    draft["published_at"] = published_at
    draft["vector_preview"] = preview
    write_saved_drafts(saved_drafts)
    append_publication_history([draft], preview, "одиночная публикация")

    return jsonify(
        {
            "ok": True,
            "message": "Черновик опубликован в Вектор",
            "published_at": published_at,
            "preview": preview,
        }
    )


@app.route("/vector-preview-confirmed", methods=["POST"])
def vector_preview_confirmed():
    confirmed = get_confirmed_drafts(load_saved_drafts())
    if not confirmed:
        return jsonify({"ok": False, "message": "Нет подтверждённых черновиков"}), 400

    try:
        preview = build_vector_batches_preview([draft.get("rows", []) for _index, draft in confirmed])
    except VectorIntegrationError as error:
        return jsonify({"ok": False, "message": str(error)}), 400
    except Exception as error:
        return jsonify({"ok": False, "message": f"Ошибка проверки Вектора: {error}"}), 500

    return jsonify({"ok": True, "preview": preview, "draft_count": len(confirmed)})


@app.route("/publish-confirmed-to-vector", methods=["POST"])
def publish_confirmed_to_vector():
    saved_drafts = load_saved_drafts()
    confirmed = get_confirmed_drafts(saved_drafts)
    if not confirmed:
        return jsonify({"ok": False, "message": "Нет подтверждённых черновиков"}), 400

    try:
        preview = publish_vector_batches([draft.get("rows", []) for _index, draft in confirmed])
    except VectorIntegrationError as error:
        return jsonify({"ok": False, "message": str(error)}), 400
    except Exception as error:
        return jsonify({"ok": False, "message": f"Ошибка публикации в Вектор: {error}"}), 500

    published_at = datetime.now().isoformat(timespec="seconds")
    published_drafts = []
    for index, draft in confirmed:
        saved_drafts[index]["status"] = "опубликовано"
        saved_drafts[index]["published_at"] = published_at
        saved_drafts[index]["vector_preview"] = preview
        published_drafts.append(saved_drafts[index])

    write_saved_drafts(saved_drafts)
    append_publication_history(published_drafts, preview, "массовая публикация")
    return jsonify(
        {
            "ok": True,
            "message": f"Опубликовано черновиков: {len(published_drafts)}",
            "published_at": published_at,
            "draft_count": len(published_drafts),
            "preview": preview,
        }
    )


@app.route("/update-saved-row", methods=["POST"])
def update_saved_row():
    payload = request.get_json(silent=True) or {}
    row_index = payload.get("row_index")
    row = payload.get("row")
    saved_drafts = load_saved_drafts()
    draft_index = resolve_draft_index(payload, saved_drafts, "draft_index")

    if not isinstance(draft_index, int) or not isinstance(row_index, int):
        return jsonify({"ok": False, "message": "Не найден номер строки"}), 400
    if draft_index < 0 or draft_index >= len(saved_drafts):
        return jsonify({"ok": False, "message": "Черновик не найден"}), 404
    rows = saved_drafts[draft_index].get("rows", [])
    if row_index < 0 or row_index >= len(rows):
        return jsonify({"ok": False, "message": "Строка не найдена"}), 404
    if not isinstance(row, dict):
        return jsonify({"ok": False, "message": "Нет данных строки"}), 400

    cleaned_row = clean_vector_row(row)
    object_name = cleaned_row["object"]
    position = cleaned_row["position"]
    allowed_positions = OBJECT_POSITIONS.get(object_name, [])
    if allowed_positions and position not in allowed_positions:
        return jsonify({"ok": False, "message": "Такой должности нет у выбранного объекта"}), 400

    rows[row_index] = cleaned_row
    saved_drafts[draft_index]["status"] = "черновик"
    saved_drafts[draft_index]["updated_at"] = datetime.now().isoformat(timespec="seconds")
    write_saved_drafts(saved_drafts)
    return jsonify({"ok": True, "message": "Строка сохранена", "row": cleaned_row})


@app.route("/delete-saved-row", methods=["POST"])
def delete_saved_row():
    payload = request.get_json(silent=True) or {}
    row_index = payload.get("row_index")
    saved_drafts = load_saved_drafts()
    draft_index = resolve_draft_index(payload, saved_drafts, "draft_index")

    if not isinstance(draft_index, int) or not isinstance(row_index, int):
        return jsonify({"ok": False, "message": "Не найден номер строки"}), 400
    if draft_index < 0 or draft_index >= len(saved_drafts):
        return jsonify({"ok": False, "message": "Черновик не найден"}), 404

    rows = saved_drafts[draft_index].get("rows", [])
    if row_index < 0 or row_index >= len(rows):
        return jsonify({"ok": False, "message": "Строка не найдена"}), 404

    rows.pop(row_index)
    draft_removed = False
    if rows:
        saved_drafts[draft_index]["updated_at"] = datetime.now().isoformat(timespec="seconds")
    else:
        saved_drafts.pop(draft_index)
        draft_removed = True

    write_saved_drafts(saved_drafts)
    return jsonify({"ok": True, "message": "Строка удалена", "draft_removed": draft_removed})


@app.route("/save-draft", methods=["POST"])
def save_draft():
    payload = request.get_json(silent=True) or {}
    rows = payload.get("rows", [])
    message_key = payload.get("message_key") or make_rows_key(rows)

    if not rows:
        return jsonify({"ok": False, "message": "Нет строк для сохранения"}), 400

    saved_drafts = load_saved_drafts()
    duplicate = next(
        (draft for draft in saved_drafts if draft.get("message_key") == message_key),
        None,
    )
    if duplicate:
        return jsonify(
            {
                "ok": False,
                "duplicate": True,
                "message": f"Такой черновик уже сохранён: {duplicate.get('saved_at', '')}",
            }
        ), 409

    saved_drafts.append(
        {
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "source": payload.get("source", "Ручное сохранение"),
            "message_key": message_key,
            "source_object": payload.get("object", ""),
            "status": "черновик",
            "rows": rows,
        }
    )
    write_saved_drafts(saved_drafts)

    return jsonify({"ok": True, "message": "Черновик сохранён", "count": len(saved_drafts)})


def prepare_saved_drafts(saved_drafts):
    status_order = {
        "требует проверки": 0,
        "черновик": 1,
        "подтверждён": 2,
        "опубликовано": 3,
        "отклонён": 4,
    }
    indexed = [
        {**draft, "original_index": index}
        for index, draft in enumerate(saved_drafts)
    ]
    return sorted(
        indexed,
        key=lambda draft: (
            status_order.get(draft.get("status", "черновик"), 9),
            draft.get("saved_at", ""),
        ),
        reverse=False,
    )


def get_confirmed_drafts(saved_drafts):
    confirmed = [
        (index, draft)
        for index, draft in enumerate(saved_drafts)
        if draft.get("status") == "подтверждён" and draft.get("rows")
    ]
    return sorted(confirmed, key=lambda item: item[1].get("saved_at", ""))


def load_publication_history():
    if not PUBLICATION_HISTORY_FILE.exists():
        return []
    try:
        history = json.loads(PUBLICATION_HISTORY_FILE.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return []
    return sorted(history, key=lambda entry: entry.get("published_at", ""), reverse=True)


def append_publication_history(drafts, preview, mode):
    history = load_publication_history()
    published_at = datetime.now().isoformat(timespec="seconds")
    rows = [row for draft in drafts for row in draft.get("rows", [])]
    entry = {
        "publication_id": hashlib.sha256(
            f"{published_at}|{mode}|{len(history)}".encode("utf-8")
        ).hexdigest()[:12],
        "published_at": published_at,
        "mode": mode,
        "draft_count": len(drafts),
        "objects": sorted({row.get("object", "") for row in rows if row.get("object")}),
        "sources": [draft.get("source", "") for draft in drafts],
        "rows": rows,
        "changes": preview.get("changes", []),
        "backup_path": preview.get("backup_path", ""),
    }
    history.insert(0, entry)
    PUBLICATION_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    PUBLICATION_HISTORY_FILE.write_text(
        json.dumps(history[:500], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return entry


def load_saved_drafts():
    if not DRAFTS_FILE.exists():
        return []
    try:
        return json.loads(DRAFTS_FILE.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []


def write_saved_drafts(saved_drafts):
    DRAFTS_FILE.write_text(
        json.dumps(saved_drafts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clean_vector_row(row):
    number_fields = [
        "rf_rb_m",
        "rf_rb_f",
        "rf_rb_family",
        "cis_m",
        "cis_f",
        "cis_family",
    ]
    cleaned = {
        "object": str(row.get("object", "")).strip(),
        "position": str(row.get("position", "")).strip() or "требует выбора",
    }
    for field in number_fields:
        cleaned[field] = max(0, int(row.get(field) or 0))
    cleaned["total"] = sum(cleaned[field] for field in number_fields)
    return cleaned


def draft_has_unselected_positions(draft):
    return any(
        str(row.get("position", "")).strip().lower() in {"", "требует выбора", "не указана"}
        for row in draft.get("rows", [])
    )


def make_message_key(object_name, text):
    normalized_text = " ".join(text.lower().split())
    raw_key = f"manual|{object_name.strip().lower()}|{normalized_text}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def make_rows_key(rows):
    raw_key = json.dumps(rows, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def build_vector_rows(drafts):
    rows = {}
    for draft in drafts:
        if draft["status"] == "требует проверки":
            continue

        key = (draft["object"], draft["position"])
        if key not in rows:
            rows[key] = {
                "object": draft["object"],
                "position": draft["position"],
                "rf_rb_m": 0,
                "rf_rb_f": 0,
                "rf_rb_family": 0,
                "cis_m": 0,
                "cis_f": 0,
                "cis_family": 0,
                "total": 0,
                "operation": draft.get("operation", "заменить"),
            }

        column = resolve_vector_column(draft)
        if column:
            rows[key][column] += draft["quantity"]
            rows[key]["total"] += draft["quantity"]

    return list(rows.values())


def resolve_vector_column(draft):
    citizenship_prefix = "cis" if draft["citizenship"] == "СНГ" else "rf_rb"

    if draft["need_type"] == "семейная" or draft["gender"] == "семейные":
        return f"{citizenship_prefix}_family"
    if draft["gender"] == "женщины":
        return f"{citizenship_prefix}_f"
    if draft["gender"] == "мужчины":
        return f"{citizenship_prefix}_m"
    return None


if __name__ == "__main__":
    app.run(debug=True)

