import unittest

from app import build_vector_rows
from parser import ALL_POSITIONS, is_zero_requirement, parse_message


class ZeroRequirementTests(unittest.TestCase):
    def test_explicit_zero_creates_clear_object_row(self):
        drafts = parse_message(
            {
                "source": "MAX: тест",
                "object": "Мяснов",
                "text": "Потребность 0",
            }
        )
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["position"], ALL_POSITIONS)
        self.assertEqual(drafts[0]["quantity"], 0)
        self.assertEqual(drafts[0]["operation"], "обнулить")

        rows = build_vector_rows(drafts)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["operation"], "обнулить")
        self.assertEqual(rows[0]["total"], 0)

    def test_common_clear_phrases(self):
        self.assertTrue(is_zero_requirement("Потребности больше нет"))
        self.assertTrue(is_zero_requirement("Обнулить потребность"))
        self.assertFalse(is_zero_requirement("Закрыть потребность"))
        self.assertFalse(
            is_zero_requirement(
                "Как быстро сможем закрыть потребность +4 девочки?"
            )
        )

    def test_unrelated_zero_is_not_clear_command(self):
        self.assertFalse(is_zero_requirement("Выход сегодня 0 человек"))
        self.assertFalse(is_zero_requirement("Потребность была 5, вышло 0"))

    def test_all_zero_staffing_table_clears_object(self):
        message = """31.07.2026
ПОТРЕБНОСТЬ В ПЕРСОНАЛЕ
• мужских: 0 ПЕКАРНЯ
• женских: 0 (пекарня)
• женских: 0 (холодное производство)
• 0 женщины (с 7.00 до 19.00)
• 0 мужчина (с 19.00 до 7.00)
• 0 мужчина (с 7.00 до 19.00)"""

        self.assertTrue(is_zero_requirement(message))
        drafts = parse_message(
            {
                "source": "MAX: КуулКлевер",
                "object": "КуулКлевер",
                "text": message,
            }
        )
        self.assertEqual(drafts[0]["position"], ALL_POSITIONS)
        self.assertEqual(drafts[0]["operation"], "обнулить")

    def test_mixed_zero_and_positive_table_does_not_clear_object(self):
        message = """ПОТРЕБНОСТЬ В ПЕРСОНАЛЕ
мужских: 0
женских: 5"""
        self.assertFalse(is_zero_requirement(message))

    def test_mixed_zero_and_positive_on_one_line_is_not_clear(self):
        message = "Потребность 0 муж/5 жен"

        self.assertFalse(is_zero_requirement(message))
        drafts = parse_message(
            {
                "source": "MAX: Креветки Клинский",
                "object": "Креветки Клинский",
                "text": message,
            }
        )

        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["gender"], "женщины")
        self.assertEqual(drafts[0]["quantity"], 5)
        self.assertEqual(drafts[0]["citizenship"], "СНГ")
        self.assertNotEqual(drafts[0]["position"], ALL_POSITIONS)

    def test_positive_position_row_prevents_clear_object(self):
        message = """КОРРЕКТИРОВКА
ПОТРЕБНОСТЬ НА 24.09
• Мужских - 0
• Женских - 0
        • Сан служба - 1"""

        self.assertFalse(is_zero_requirement(message))
        catalog = __import__("vector_catalog").OBJECT_POSITIONS
        original_positions = catalog.get("ФитнесШок")
        catalog["ФитнесШок"] = ["Уборщик", "Упаковщик"]
        try:
            drafts = parse_message(
                {
                    "source": "MAX: ФитнесШок",
                    "object": "ФитнесШок",
                    "text": message,
                }
            )
            rows = build_vector_rows(drafts)
        finally:
            if original_positions is None:
                catalog.pop("ФитнесШок", None)
            else:
                catalog["ФитнесШок"] = original_positions

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["position"], "Уборщик")
        self.assertEqual(rows[0]["rf_rb_m"], 0)
        self.assertEqual(rows[0]["rf_rb_f"], 1)
        self.assertEqual(rows[0]["total"], 1)

    def test_quantities_joined_to_positions_are_not_mistaken_for_all_zero(self):
        message = """ПОТРЕБНОСТЬ В ПЕРСОНАЛЕ:
На 01.08.2026
* мужских: 6кмп*
* мужских: 7грузчик*
* женских: 6кмп*
* женских 6стик*
Семейная: 0"""

        self.assertFalse(is_zero_requirement(message))
        drafts = parse_message(
            {
                "source": "MAX: тест",
                "object": "тестовый объект",
                "text": message,
            }
        )
        self.assertNotEqual(drafts[0]["position"], ALL_POSITIONS)
        self.assertEqual(sum(draft["quantity"] for draft in drafts), 25)


if __name__ == "__main__":
    unittest.main()
