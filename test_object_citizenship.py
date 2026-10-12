import unittest

from app import build_vector_rows
from parser import parse_message


MESSAGE = """ПОТРЕБНОСТЬ В ПЕРСОНАЛЕ
• мужских: 0 ПЕКАРНЯ
• женских: 0 (пекарня)
• женских: 0 (холодное производство)
• 5 женщины. (с 7.00 до 19.00)-салаты, сэндвичи.
• 1 мужчина. (с 19.00 до 7.00)-замесы сырников.
• 1 мужчина. (с 7.00 до 19.00)-замес блинов."""

KOOlKLEVER_WITH_NONZERO_BAKERY = """ПОТРЕБНОСТЬ В ПЕРСОНАЛЕ
• мужских: 3 ПЕКАРНЯ!!! (всё что связано с тестом и выпечкой)
• женских: 0 (пекарня, всё что связано с тестом и выпечкой)
• женских: 4 (день/ночь), (холодное производство)
• 0 женщины. (с 7.00 до 19.00)-салаты, сэндвичи.
• 2 мужчина. (с 7:00 до 19:00)-соусный цех. Приготовление фарша.
• 1 мужчина. (с 19:00 до 07:00)-супы и вторые блюда"""


class ObjectCitizenshipTests(unittest.TestCase):
    def test_koolklever_bakery_section_maps_to_default_vector_position(self):
        drafts = parse_message(
            {
                "source": "MAX: КуулКлевер",
                "object": "КуулКлевер",
                "text": KOOlKLEVER_WITH_NONZERO_BAKERY,
            }
        )
        rows = build_vector_rows(drafts)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["position"], "Работник производства")
        self.assertEqual(rows[0]["cis_m"], 6)
        self.assertEqual(rows[0]["cis_f"], 4)

    def test_koolklever_defaults_to_cis(self):
        drafts = parse_message(
            {
                "source": "MAX: КуулКлевер",
                "object": "КуулКлевер",
                "text": MESSAGE,
            }
        )
        rows = build_vector_rows(drafts)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cis_m"], 2)
        self.assertEqual(rows[0]["cis_f"], 5)
        self.assertEqual(rows[0]["rf_rb_m"], 0)
        self.assertEqual(rows[0]["rf_rb_f"], 0)

    def test_other_objects_still_default_to_rf_rb(self):
        drafts = parse_message(
            {
                "source": "MAX: Яндекс Самара",
                "object": "Яндекс Самара",
                "text": "Нужны 2 мужчины комплектовщики",
            }
        )
        rows = build_vector_rows(drafts)

        self.assertEqual(rows[0]["rf_rb_m"], 2)
        self.assertEqual(rows[0]["cis_m"], 0)

    def test_klinsky_defaults_to_cis(self):
        drafts = parse_message(
            {
                "source": "MAX: Клинский мясокомбинат",
                "object": "Клинский мясокомбинат",
                "text": "Потребность 8 муж/ 7 жен",
            }
        )
        rows = build_vector_rows(drafts)

        self.assertEqual(rows[0]["cis_m"], 8)
        self.assertEqual(rows[0]["cis_f"], 7)
        self.assertEqual(rows[0]["rf_rb_m"], 0)
        self.assertEqual(rows[0]["rf_rb_f"], 0)

    def test_klinsky_shrimps_defaults_to_cis(self):
        drafts = parse_message(
            {
                "source": "MAX: Креветки Клинский",
                "object": "Креветки Клинский",
                "text": "Коллеги, заявка\n10м\n10ж",
            }
        )
        rows = build_vector_rows(drafts)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["position"], "Упаковщик")
        self.assertEqual(rows[0]["cis_m"], 10)
        self.assertEqual(rows[0]["cis_f"], 10)
        self.assertEqual(rows[0]["rf_rb_m"], 0)
        self.assertEqual(rows[0]["rf_rb_f"], 0)

    def test_explicit_rf_rb_overrides_klinsky_shrimps_default(self):
        drafts = parse_message(
            {
                "source": "MAX: Креветки Клинский",
                "object": "Креветки Клинский",
                "text": "Коллеги, заявка\nРФ/РБ\n10м\n10ж",
            }
        )
        rows = build_vector_rows(drafts)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["rf_rb_m"], 10)
        self.assertEqual(rows[0]["rf_rb_f"], 10)
        self.assertEqual(rows[0]["cis_m"], 0)
        self.assertEqual(rows[0]["cis_f"], 0)


if __name__ == "__main__":
    unittest.main()
