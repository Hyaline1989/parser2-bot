import unittest

from max_bot import (
    looks_like_candidate_medical_issue,
    looks_like_candidate_review_question,
    looks_like_need,
    looks_like_need_fulfillment_question,
    looks_like_passport_correction,
    looks_like_training_schedule,
)


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

MEDICAL_ISSUE_MESSAGE = (
    "Коллеги, добрый день! Просьба, проговаривать про критические дни у женщин. "
    "Медкомиссию нельзя пройти в этот период. 3 ж заехали вчера и у всех трех "
    "еще неделю они будут идти. Я не могу их всю неделю держать в хостеле."
)

CANDIDATE_OFFER_MESSAGE = (
    "Возьмёте 3 ж (стик или комплектовщки) и 1 м (комплектовщик) = друзья, "
    "готовы приехать сегодня."
)

PASSPORT_CORRECTION_MESSAGE = (
    "в паспорте грузчик 3 400 (300 р/ч). Исправьте пожалуйста на 3 300. "
    "работают они по 11 часов"
)

CANDIDATE_REVIEW_MESSAGE = "Женщина, 56 лет, можем рассмотреть?"

CANDIDATE_SIZE_AND_AGE_MESSAGE = (
    "Женщина 56 размер по возрасту типа 45\n\nСможем принять?"
)

NEED_FULFILLMENT_QUESTION = (
    "Подскажите, как быстро сможем закрыть потребность +4 девочки "
    "(2 день/2 ночь) на упаковку?"
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

    def test_medical_issue_of_arrived_candidates_is_not_a_requirement(self):
        self.assertTrue(looks_like_candidate_medical_issue(MEDICAL_ISSUE_MESSAGE))
        self.assertFalse(looks_like_need(MEDICAL_ISSUE_MESSAGE))

    def test_real_requirement_with_medical_note_is_not_hidden(self):
        message = "Нужны 3 женщины, медкомиссия обязательна"
        self.assertFalse(looks_like_candidate_medical_issue(message))
        self.assertTrue(looks_like_need(message))

    def test_candidate_offer_ready_to_arrive_is_not_a_requirement(self):
        self.assertFalse(looks_like_need(CANDIDATE_OFFER_MESSAGE))

    def test_real_requirement_with_same_counts_is_not_hidden(self):
        message = "Нужны 3 женщины и 1 мужчина, комплектовщики"
        self.assertTrue(looks_like_need(message))

    def test_passport_rate_correction_is_not_a_requirement(self):
        self.assertTrue(looks_like_passport_correction(PASSPORT_CORRECTION_MESSAGE))
        self.assertFalse(looks_like_need(PASSPORT_CORRECTION_MESSAGE))

    def test_real_requirement_with_passport_note_is_not_hidden(self):
        message = "Нужны 3 грузчика, ставка указана в паспорте объекта"
        self.assertFalse(looks_like_passport_correction(message))
        self.assertTrue(looks_like_need(message))

    def test_candidate_age_review_question_is_not_a_requirement(self):
        self.assertTrue(looks_like_candidate_review_question(CANDIDATE_REVIEW_MESSAGE))
        self.assertFalse(looks_like_need(CANDIDATE_REVIEW_MESSAGE))

    def test_candidate_size_and_age_question_is_not_a_requirement(self):
        self.assertTrue(
            looks_like_candidate_review_question(CANDIDATE_SIZE_AND_AGE_MESSAGE)
        )
        self.assertFalse(looks_like_need(CANDIDATE_SIZE_AND_AGE_MESSAGE))

    def test_real_requirement_with_age_limit_is_not_hidden(self):
        message = "Нужны 3 женщины до 56 лет"
        self.assertFalse(looks_like_candidate_review_question(message))
        self.assertTrue(looks_like_need(message))

    def test_question_about_closing_existing_need_is_not_a_new_requirement(self):
        self.assertTrue(
            looks_like_need_fulfillment_question(NEED_FULFILLMENT_QUESTION)
        )
        self.assertFalse(looks_like_need(NEED_FULFILLMENT_QUESTION))

    def test_direct_need_with_same_count_is_not_hidden(self):
        message = "Потребность +4 женщины на упаковку"
        self.assertFalse(looks_like_need_fulfillment_question(message))
        self.assertTrue(looks_like_need(message))


if __name__ == "__main__":
    unittest.main()
