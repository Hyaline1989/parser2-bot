import unittest

from parser import parse_message
from app import build_vector_rows


MESSAGE = """12.10.2026
ПОТРЕБНОСТЬ В ПЕРСОНАЛЕ
мужских: 0 ПЕКАРНЯ!!! (всё что связано с тестом и выпечкой)
женских: 0 (пекарня, всё что связано с тестом и выпечкой)
женских: 2 (день/2 ночь), (подготовитель пищ. сырья, холодное производство)
мужских: 2 (день/2 ночь), (подготовитель пищ. сырья, холодное производство)
женщины: 1 (с 7.00 до 19.00) - упаковка.
мужских: 2 (с 7:00 до 19:00) - оператор в соусный цех
мужских: 1 (с 07:00 до 19:00) - приготовление фарша
мужских: 2 (с 7:00 до 19:00) - транспортировщик/разнорабочий
женщины: 1 (с 7.00 до 19.00) - оператор блинного аппарата
Готовы принять с понедельника 12.10., граждан других государств, не только Киргизии.
Обязательно разговорный русский язык и наличие всех документов."""


class FoodProductionTests(unittest.TestCase):
    def test_all_counts_and_tasks_are_preserved(self):
        drafts = parse_message({"object": "КуулКлевер", "text": MESSAGE})
        rows = {r["position"]: r for r in build_vector_rows(drafts)}
        self.assertEqual(set(rows), {"Работник производства", "Упаковщик"})
        self.assertEqual(rows["Работник производства"]["cis_m"], 7)
        self.assertEqual(rows["Работник производства"]["cis_f"], 3)
        self.assertEqual(rows["Упаковщик"]["cis_f"], 1)
        self.assertTrue(all(d["citizenship"] == "СНГ" for d in drafts))
        self.assertTrue(all(d["status"] == "готово к проверке" for d in drafts))

    def test_loaders_remain_separate_from_other_tasks(self):
        drafts = parse_message({"object": "КуулКлевер", "text":
            "Потребность\nмужских: 2 грузчик\nженщины: 1 упаковка\nмужских: 3 оператор"})
        rows = {r["position"]: r for r in build_vector_rows(drafts)}
        self.assertEqual(rows["Работник склада"]["cis_m"], 2)
        self.assertEqual(rows["Упаковщик"]["cis_f"], 1)
        self.assertEqual(rows["Работник производства"]["cis_m"], 3)


if __name__ == "__main__":
    unittest.main()
