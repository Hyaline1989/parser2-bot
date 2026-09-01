import unittest

from app import build_vector_rows
from parser import parse_message


class QuantityBeforeGenderTests(unittest.TestCase):
    def test_gender_and_quantity_without_separator(self):
        drafts = parse_message(
            {
                "source": "MAX: Агама Лешково",
                "object": "Агама Лешково",
                "text": (
                    "Потребность в персонале:\n"
                    "01.09.2026\n"
                    "Мужчины:4\n"
                    "Женщины5"
                ),
            }
        )
        quantities = {
            draft["gender"]: draft["quantity"]
            for draft in drafts
            if isinstance(draft.get("quantity"), int)
        }

        self.assertEqual(quantities, {"мужчины": 4, "женщины": 5})
        self.assertTrue(
            all(draft["position"] == "Работник производства" for draft in drafts)
        )

    def test_number_before_gender_words_creates_two_rows(self):
        drafts = parse_message(
            {
                "source": "MAX: Клинский мясокомбинат",
                "object": "Клинский мясокомбинат",
                "text": "Потребность 8 муж/ 7 жен",
            }
        )
        quantities = {
            draft["gender"]: draft["quantity"]
            for draft in drafts
            if isinstance(draft.get("quantity"), int)
        }

        self.assertEqual(quantities, {"мужчины": 8, "женщины": 7})
        self.assertTrue(all(draft["status"] == "готово к проверке" for draft in drafts))
        self.assertTrue(
            all(draft["position"] == "Работник производства" for draft in drafts)
        )
        self.assertTrue(all(draft["citizenship"] == "СНГ" for draft in drafts))

        rows = build_vector_rows(drafts)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["position"], "Работник производства")
        self.assertEqual(rows[0]["cis_m"], 8)
        self.assertEqual(rows[0]["cis_f"], 7)
        self.assertEqual(rows[0]["rf_rb_m"], 0)
        self.assertEqual(rows[0]["rf_rb_f"], 0)


if __name__ == "__main__":
    unittest.main()
