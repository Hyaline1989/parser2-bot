import unittest

from parser import parse_message
from vector_catalog import resolve_position_for_object


class AskonaDefaultPositionTests(unittest.TestCase):
    def test_missing_position_defaults_to_general_worker(self):
        drafts = parse_message(
            {
                "source": "MAX: АСКОНА",
                "object": "АСКОНА",
                "text": "Потребность 10 мужчин",
            }
        )

        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["position"], "Разнорабочий")
        self.assertEqual(drafts[0]["quantity"], 10)
        self.assertEqual(drafts[0]["citizenship"], "РФ/РБ")

    def test_explicit_position_has_priority_over_default(self):
        original_positions = list(__import__("vector_catalog").OBJECT_POSITIONS["АСКОНА"])
        __import__("vector_catalog").OBJECT_POSITIONS["АСКОНА"] = [
            "Разнорабочий",
            "Упаковщик",
        ]
        try:
            position, source = resolve_position_for_object(
                "АСКОНА", "упаковщик", "мужчины"
            )
        finally:
            __import__("vector_catalog").OBJECT_POSITIONS["АСКОНА"] = original_positions

        self.assertEqual(position, "Упаковщик")
        self.assertEqual(source, "найдена в сообщении")

    def test_default_works_with_vector_object_casing_and_position_variant(self):
        catalog = __import__("vector_catalog").OBJECT_POSITIONS
        original = catalog.pop("АСКОНА")
        catalog["Аскона"] = ["Разнорабочий производства", "Упаковщик"]
        try:
            position, source = resolve_position_for_object(
                "Аскона", None, "мужчины"
            )
        finally:
            catalog.pop("Аскона")
            catalog["АСКОНА"] = original

        self.assertEqual(position, "Разнорабочий производства")
        self.assertEqual(source, "подставлено по правилу объекта")

    def test_default_works_when_object_is_missing_from_loaded_catalog(self):
        catalog = __import__("vector_catalog").OBJECT_POSITIONS
        original = catalog.pop("АСКОНА")
        try:
            position, source = resolve_position_for_object(
                "АСКОНА", None, "мужчины"
            )
        finally:
            catalog["АСКОНА"] = original

        self.assertEqual(position, "Разнорабочий")
        self.assertEqual(source, "подставлено по правилу объекта")


if __name__ == "__main__":
    unittest.main()
