import unittest

from max_bot import looks_like_need, looks_like_training_schedule


TRAINING_SCHEDULE_MESSAGE = (
    "Просьба сообщать кандидатам о сроках вывода на инструктаж, приезжают часто "
    "в четверг вечером или пятницу и не готовы на такое ожидание. У кмпл обучение "
    "проходит пн-ср-пт. Списки на обучение подаются до 14:00, соответственно те, "
    "кто приезжает в четверг вечером или пт-сб (кмпл или груз) попадут на обучение "
    "в понедельник. А приезжающие кмпл в пн, попадут на обучение только в среду"
)

TRAVEL_STATUS_MESSAGE = (
    "Добрый день. С учетом сегодняшнего дня, на ближайшие дни "
    "с 28.07 9 человек на доезде"
)


class MaxBotFilterTests(unittest.TestCase):
    def test_training_schedule_is_not_a_requirement(self):
        self.assertTrue(looks_like_training_schedule(TRAINING_SCHEDULE_MESSAGE))
        self.assertFalse(looks_like_need(TRAINING_SCHEDULE_MESSAGE))

    def test_real_requirement_with_training_word_is_not_hidden(self):
        message = "Нужны 5 упаковщиков, обучение в понедельник"
        self.assertFalse(looks_like_training_schedule(message))
        self.assertTrue(looks_like_need(message))

    def test_people_already_in_transit_are_not_a_requirement(self):
        self.assertFalse(looks_like_need(TRAVEL_STATUS_MESSAGE))


if __name__ == "__main__":
    unittest.main()
