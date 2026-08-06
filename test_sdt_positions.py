import unittest

from vector_catalog import OBJECT_POSITIONS, resolve_position_for_object


class SdtPositionsTests(unittest.TestCase):
    def test_sdt_contains_driver_from_vector(self):
        self.assertIn("Водитель", OBJECT_POSITIONS["СДТ"])
        position, source = resolve_position_for_object("СДТ", "водитель", "мужчины")
        self.assertEqual(position, "Водитель")
        self.assertEqual(source, "найдена в сообщении")


if __name__ == "__main__":
    unittest.main()
