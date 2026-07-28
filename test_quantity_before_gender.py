import unittest

from parser import parse_message


class QuantityBeforeGenderTests(unittest.TestCase):
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
        self.assertTrue(all(draft["status"] == "требует проверки" for draft in drafts))


if __name__ == "__main__":
    unittest.main()
