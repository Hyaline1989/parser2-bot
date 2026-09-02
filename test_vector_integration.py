import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from vector_catalog import OBJECT_POSITIONS, refresh_object_positions
from vector_integration import (
    build_vector_batches_preview,
    build_vector_preview,
    publish_vector_batches,
    publish_vector_rows,
)


class VectorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "requirements.db"
        self.original_backup_dir = os.environ.get("VECTOR_BACKUP_DIR")
        os.environ["VECTOR_BACKUP_DIR"] = str(Path(self.temp_dir.name) / "backups")
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE current_requirements (
                object_name TEXT NOT NULL,
                position_name TEXT NOT NULL,
                rf_men INTEGER DEFAULT 0,
                rf_women INTEGER DEFAULT 0,
                rf_family INTEGER DEFAULT 0,
                cis_men INTEGER DEFAULT 0,
                cis_women INTEGER DEFAULT 0,
                cis_family INTEGER DEFAULT 0,
                is_high INTEGER DEFAULT 0,
                updated_at TEXT
            )
            """
        )
        conn.executescript(
            """
            CREATE TABLE vacancy_objects (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            );
            CREATE TABLE vacancy_positions (
                id INTEGER PRIMARY KEY,
                object_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                UNIQUE(object_id, name)
            );
            CREATE TABLE vacancy_requirements (
                id INTEGER PRIMARY KEY,
                position_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                rf_men INTEGER DEFAULT 0,
                rf_women INTEGER DEFAULT 0,
                rf_family INTEGER DEFAULT 0,
                cis_men INTEGER DEFAULT 0,
                cis_women INTEGER DEFAULT 0,
                cis_family INTEGER DEFAULT 0,
                is_high INTEGER DEFAULT 0,
                updated_at TEXT,
                UNIQUE(position_id, date)
            );
            INSERT INTO vacancy_objects (id, name)
            VALUES (1, 'РўРµСЃС‚РѕРІС‹Р№ РѕР±СЉРµРєС‚');
            INSERT INTO vacancy_positions (id, object_id, name)
            VALUES
                (10, 1, 'Р”РѕР»Р¶РЅРѕСЃС‚СЊ Рђ'),
                (11, 1, 'РќРѕРІР°СЏ РґРѕР»Р¶РЅРѕСЃС‚СЊ');
            """
        )
        conn.executemany(
            """
            INSERT INTO current_requirements (
                object_name, position_name, rf_men, rf_women,
                rf_family, cis_men, cis_women, cis_family, is_high
            ) VALUES (?, ?, ?, ?, 0, 0, 0, 0, 0)
            """,
            [
                ("Тестовый объект", "Должность А", 5, 1),
                ("Тестовый объект", "Новая должность", 7, 0),
            ],
        )
        object_name, first_position = conn.execute(
            """
            SELECT object_name, position_name
            FROM current_requirements
            ORDER BY rowid
            LIMIT 1
            """
        ).fetchone()
        second_position = conn.execute(
            """
            SELECT position_name
            FROM current_requirements
            ORDER BY rowid
            LIMIT 1 OFFSET 1
            """
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO vacancy_objects (id, name) VALUES (?, ?)",
            (2, object_name),
        )
        conn.executemany(
            "INSERT INTO vacancy_positions (id, object_id, name) VALUES (?, 2, ?)",
            [(20, first_position), (21, second_position)],
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        if self.original_backup_dir is None:
            os.environ.pop("VECTOR_BACKUP_DIR", None)
        else:
            os.environ["VECTOR_BACKUP_DIR"] = self.original_backup_dir
        self.temp_dir.cleanup()

    def row(self, men, operation="заменить"):
        return {
            "object": "Тестовый объект",
            "position": "Должность А",
            "rf_rb_m": men,
            "rf_rb_f": 0,
            "rf_rb_family": 0,
            "cis_m": 0,
            "cis_f": 0,
            "cis_family": 0,
            "operation": operation,
        }

    def read_men(self):
        conn = sqlite3.connect(self.db_path)
        try:
            return dict(
                conn.execute(
                    "SELECT position_name, rf_men FROM current_requirements"
                ).fetchall()
            )
        finally:
            conn.close()

    def test_catalog_is_refreshed_from_vector(self):
        self.assertTrue(refresh_object_positions(self.db_path))
        self.assertEqual(
            OBJECT_POSITIONS["Тестовый объект"],
            ["Должность А", "Новая должность"],
        )

    def test_replace_resets_other_positions_for_object(self):
        preview = build_vector_preview([self.row(2)], self.db_path)
        self.assertFalse(preview["errors"])
        self.assertTrue(
            any(
                change["position"] == "Новая должность"
                and change["current"] == 7
                and change["new"] == 0
                for change in preview["changes"]
            )
        )

        publish_vector_rows([self.row(2)], self.db_path)
        self.assertEqual(self.read_men(), {"Должность А": 2, "Новая должность": 0})

    def test_object_and_position_names_are_matched_without_case(self):
        source_row = self.row(3)
        source_row["object"] = "тЕСТОВЫЙ ОБЪЕКТ"
        source_row["position"] = "дОЛЖНОСТЬ а"

        preview = build_vector_preview([source_row], self.db_path)

        self.assertFalse(preview["errors"])
        self.assertTrue(
            any(
                change["object"] == "Тестовый объект"
                and change["position"] == "Должность А"
                and change["new"] == 3
                for change in preview["changes"]
            )
        )
        publish_vector_rows([source_row], self.db_path)
        self.assertEqual(self.read_men(), {"Должность А": 3, "Новая должность": 0})

    def test_add_keeps_other_positions(self):
        result = publish_vector_rows([self.row(3, "прибавить")], self.db_path)
        self.assertEqual(self.read_men(), {"Должность А": 8, "Новая должность": 7})
        self.assertTrue(Path(result["backup_path"]).exists())

    def test_batches_follow_message_order(self):
        batches = [
            [self.row(2, "заменить")],
            [self.row(3, "прибавить")],
        ]
        preview = build_vector_batches_preview(batches, self.db_path)
        self.assertFalse(preview["errors"])

        publish_vector_batches(batches, self.db_path)
        self.assertEqual(self.read_men(), {"Должность А": 5, "Новая должность": 0})

    def test_replace_combines_gender_rows_for_same_position(self):
        men = self.row(11, "заменить")
        women = self.row(0, "заменить")
        women["rf_rb_f"] = 10

        preview = build_vector_batches_preview([[men, women]], self.db_path)
        changes = {
            change["field"]: change["new"]
            for change in preview["changes"]
            if change["position"] == "Должность А"
        }
        self.assertEqual(changes["РФ/РБ М"], 11)
        self.assertEqual(changes["РФ/РБ Ж"], 10)


    def test_publish_synchronizes_current_and_daily_tables(self):
        source_row = self.row(9)
        publish_vector_rows([source_row], self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            current = conn.execute(
                """
                SELECT rf_men
                FROM current_requirements
                WHERE object_name = ? AND position_name = ?
                """,
                (source_row["object"], source_row["position"]),
            ).fetchone()[0]
            daily = conn.execute(
                """
                SELECT vr.rf_men
                FROM vacancy_requirements vr
                JOIN vacancy_positions vp ON vp.id = vr.position_id
                JOIN vacancy_objects vo ON vo.id = vp.object_id
                WHERE vo.name = ? AND vp.name = ?
                """,
                (source_row["object"], source_row["position"]),
            ).fetchone()[0]
        finally:
            conn.close()

        self.assertEqual(current, 9)
        self.assertEqual(daily, 9)

    def test_replace_can_clear_position_missing_from_daily_plan(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "DELETE FROM vacancy_positions WHERE id = 21"
            )
            conn.commit()
        finally:
            conn.close()

        publish_vector_rows([self.row(2)], self.db_path)

        self.assertEqual(self.read_men(), {"Должность А": 2, "Новая должность": 0})

    def test_positive_value_still_requires_position_in_daily_plan(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "DELETE FROM vacancy_positions WHERE id = 20"
            )
            conn.commit()
        finally:
            conn.close()

        with self.assertRaisesRegex(Exception, "должность не найдена в дневном плане"):
            publish_vector_rows([self.row(2)], self.db_path)

        self.assertEqual(self.read_men(), {"Должность А": 5, "Новая должность": 7})

    def test_clear_object_does_not_require_a_position(self):
        clear_row = {
            "object": self.row(1)["object"],
            "position": "Все должности",
            "rf_rb_m": 0,
            "rf_rb_f": 0,
            "rf_rb_family": 0,
            "cis_m": 0,
            "cis_f": 0,
            "cis_family": 0,
            "total": 0,
            "operation": "обнулить",
        }

        preview = build_vector_preview([clear_row], self.db_path)
        self.assertFalse(preview["errors"])
        self.assertTrue(preview["changes"])
        self.assertTrue(
            all(change["operation"] == "обнулить" for change in preview["changes"])
        )

        publish_vector_rows([clear_row], self.db_path)
        self.assertTrue(all(value == 0 for value in self.read_men().values()))


if __name__ == "__main__":
    unittest.main()
