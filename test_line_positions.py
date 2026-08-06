import unittest

from app import build_vector_rows
from parser import parse_message


MESSAGE = """Потребность на 28.07
• Мужских - 20 (Грузчики)
• Женских - 10 (Комплектовщики)
• Семейная - 2"""


class LinePositionTests(unittest.TestCase):
    def test_multiple_parenthesized_positions_on_one_line(self):
        drafts = parse_message(
            {
                "source": "MAX: Форум Авто",
                "object": "Форум Авто",
                "text": (
                    "Актуальная потребность на 06.08\n"
                    "Мужских - 5 (Грузчики), 10 (комплектовщики)"
                ),
            }
        )

        parsed = {(draft["position"], draft["gender"]): draft["quantity"] for draft in drafts}
        self.assertEqual(parsed[("Грузчик", "мужчины")], 5)
        self.assertEqual(parsed[("Кладовщик", "мужчины")], 10)

    def test_each_line_uses_its_own_position(self):
        drafts = parse_message(
            {
                "source": "MAX: Форум Авто",
                "object": "Форум Авто",
                "text": MESSAGE,
            }
        )
        rows = {
            (row["position"], column): row[column]
            for row in build_vector_rows(drafts)
            for column in ("rf_rb_m", "rf_rb_f", "rf_rb_family")
            if row[column]
        }

        self.assertEqual(rows[("Грузчик", "rf_rb_m")], 20)
        self.assertEqual(rows[("Кладовщик", "rf_rb_f")], 10)
        self.assertEqual(rows[("Грузчик", "rf_rb_family")], 2)
        self.assertNotIn(("Грузчик", "rf_rb_f"), rows)


if __name__ == "__main__":
    unittest.main()
