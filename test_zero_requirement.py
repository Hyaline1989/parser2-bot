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
        self.assertTrue(is_zero_requirement("Закрыть потребность"))

    def test_unrelated_zero_is_not_clear_command(self):
        self.assertFalse(is_zero_requirement("Выход сегодня 0 человек"))
        self.assertFalse(is_zero_requirement("Потребность была 5, вышло 0"))


if __name__ == "__main__":
    unittest.main()
