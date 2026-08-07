import unittest

from parser import parse_message


MESSAGE = """07.08.2026
ПОТРЕБНОСТЬ В ПЕРСОНАЛЕ

Комплектовщики
• мужских: 4 (смены день/ ночь)
• женских: 0

Копакинг/Оператор
• мужских 0 (смены день/ ночь)
• женских 6 (3 ночь/ 3 день), (опыт работы с компьютером)

Грузчики
• Мужских: 12 (6 ночь, 6 день)

Разнорабочий
• Мужских: 6 (3 ночь, 3 день), (работа комплектовщик-грузчик, копакинг, зависит от потребности склада)

Водилель высотного штабелера
• Мужских: 4 (2 день/ 2 ночь, обязательное наличие прав). Перемещение товара по складу.

Уборщица
• Женских 0"""


class SdtSectionPositionTests(unittest.TestCase):
    def test_parenthetical_job_names_do_not_override_section_heading(self):
        drafts = parse_message(
            {
                "source": "MAX: СДТ",
                "object": "СДТ",
                "text": MESSAGE,
            }
        )
        parsed = {
            (draft["position"], draft["gender"]): draft["quantity"]
            for draft in drafts
        }

        self.assertEqual(parsed[("Комплектовщик", "мужчины")], 4)
        self.assertEqual(parsed[("Разнорабочий", "женщины")], 6)
        self.assertEqual(parsed[("Работник склада", "мужчины")], 12)
        self.assertEqual(parsed[("Разнорабочий", "мужчины")], 6)
        self.assertEqual(parsed[("Водитель", "мужчины")], 4)
        self.assertEqual(len(parsed), 5)


if __name__ == "__main__":
    unittest.main()
