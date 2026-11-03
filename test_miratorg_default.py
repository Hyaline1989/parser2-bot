import unittest

from app import build_vector_rows
from parser import parse_message, parse_need_line, is_zero_requirement


class MiratorgDefaultTests(unittest.TestCase):
    def test_short_family_and_default_position(self):
        drafts = parse_message({"object": "Мираторг", "text":
            "Актуальная потребность:\nЖ-11\nМ-7\nС-6"})
        rows = build_vector_rows(drafts)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["position"], "Работник производства")
        self.assertEqual(rows[0]["rf_rb_m"], 7)
        self.assertEqual(rows[0]["rf_rb_f"], 11)
        self.assertEqual(rows[0]["rf_rb_family"], 6)

    def test_specific_position_is_preserved(self):
        drafts = parse_message({"object": "Мираторг", "text": "Нужны 3 разнорабочие"})
        self.assertEqual(drafts[0]["position"], "Разнорабочий")

    def test_time_is_not_short_family(self):
        self.assertEqual(parse_need_line("с 6", None), [])

    def test_positive_families_prevent_object_clear(self):
        self.assertFalse(is_zero_requirement("Потребность:\nМужских: 0\nЖенских: 0\nС-6"))


if __name__ == "__main__":
    unittest.main()
