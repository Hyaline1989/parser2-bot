import unittest

from max_bot import (
    looks_like_candidate_medical_issue,
    looks_like_candidate_coordination,
    looks_like_candidate_profile,
    looks_like_candidate_review_question,
    looks_like_arrival_count_status,
    looks_like_arrival_coordination,
    looks_like_housing_history,
    looks_like_need,
    looks_like_need_fulfillment_question,
    looks_like_medical_exam_notice,
    looks_like_measurement_discussion,
    looks_like_passport_correction,
    looks_like_training_schedule,
    looks_like_workwear_or_safety_notice,
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

WORKWEAR_NOTICE_MESSAGE = (
    "Форма одежды, в которой должны быть сотрудники на складе. "
    "Чёрная однотонная одежда, закрытая обувь. Обязательно, чтобы была жилетка. "
    "Сегодня не пропустили 10 человек на первый рабочий день. Это требование ТБ. "
    "Из 10 новых сотрудников на КПП не пропустили 5 наших, "
    "на смену зашли 37 человек."
)

FAMILY_CANDIDATE_REVIEW_MESSAGE = (
    "Коллеги, есть семейная пара, по СБ прошли, но женщине 46 лет. "
    "Можем направить?"
)

ALREADY_DIRECTED_WITH_TICKETS_MESSAGE = (
    "У меня уже две женщины с билетами направлены на 3 и 4 число. "
    "Учтите пожалуйста это тоже"
)

MEDICAL_EXAM_NOTICE_MESSAGE = (
    "Женщина 1973 года рождения - полная медленная. Вторая молодая нормальная. "
    "Ждать им до понедельника до медкомиссии. Напоминаю — мед комиссии в Павлово "
    "проходят: понедельник, вторник, четверг. Без комиссии входа на фабрику нет."
)

ARRIVING_GROUP_APPROVAL_MESSAGE = (
    "Анна Менеджер Комплект примем 3 М одной компанией? Приезжают 03.08"
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

    def test_candidate_clothing_size_question_is_not_a_requirement(self):
        message = "Сергей Ёлчин кандидат женщина 58 размер - сможем взять?"

        self.assertTrue(looks_like_candidate_review_question(message))
        self.assertFalse(looks_like_need(message))

    def test_real_requirement_with_clothing_size_is_not_hidden(self):
        message = "Нужны 5 женщин 58 размера"

        self.assertFalse(looks_like_candidate_review_question(message))
        self.assertTrue(looks_like_need(message))

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

    def test_workwear_and_checkpoint_notice_is_not_a_requirement(self):
        self.assertTrue(looks_like_workwear_or_safety_notice(WORKWEAR_NOTICE_MESSAGE))
        self.assertFalse(looks_like_need(WORKWEAR_NOTICE_MESSAGE))

    def test_real_need_with_workwear_note_is_not_hidden(self):
        message = "Нужны 10 сотрудников. Форма одежды — чёрная футболка и закрытая обувь"
        self.assertFalse(looks_like_workwear_or_safety_notice(message))
        self.assertTrue(looks_like_need(message))

    def test_family_candidate_age_question_is_not_a_requirement(self):
        self.assertTrue(
            looks_like_candidate_review_question(FAMILY_CANDIDATE_REVIEW_MESSAGE)
        )
        self.assertFalse(looks_like_need(FAMILY_CANDIDATE_REVIEW_MESSAGE))

    def test_short_age_question_is_not_a_requirement(self):
        message = "Женщина 48 лет, можно?"
        self.assertTrue(looks_like_candidate_review_question(message))
        self.assertFalse(looks_like_need(message))

    def test_age_question_without_question_mark_is_not_a_requirement(self):
        message = "Мужчина 52 года, возьмёте"
        self.assertTrue(looks_like_candidate_review_question(message))
        self.assertFalse(looks_like_need(message))

    def test_plural_age_requirement_is_not_hidden(self):
        message = "Нужны 5 женщин до 45 лет"
        self.assertFalse(looks_like_candidate_review_question(message))
        self.assertTrue(looks_like_need(message))

    def test_already_directed_women_with_tickets_are_not_a_requirement(self):
        self.assertFalse(looks_like_need(ALREADY_DIRECTED_WITH_TICKETS_MESSAGE))

    def test_real_need_for_people_with_tickets_is_not_hidden(self):
        message = "Нужны 2 женщины с билетами"
        self.assertTrue(looks_like_need(message))

    def test_birth_year_and_medical_exam_schedule_are_not_a_requirement(self):
        self.assertTrue(looks_like_medical_exam_notice(MEDICAL_EXAM_NOTICE_MESSAGE))
        self.assertFalse(looks_like_need(MEDICAL_EXAM_NOTICE_MESSAGE))

    def test_real_need_with_medical_exam_schedule_is_not_hidden(self):
        message = "Нужны 2 женщины, медкомиссия в понедельник"
        self.assertFalse(looks_like_medical_exam_notice(message))
        self.assertTrue(looks_like_need(message))

    def test_arriving_group_approval_is_not_a_requirement(self):
        self.assertFalse(looks_like_need(ARRIVING_GROUP_APPROVAL_MESSAGE))

    def test_housing_capacity_question_is_not_a_requirement(self):
        message = (
            "Коллеги, появилась возможность открыть еще комнату. "
            "Подскажите, сможем заселить 10 человек сегодня-завтра?"
        )
        self.assertTrue(looks_like_arrival_coordination(message))
        self.assertFalse(looks_like_need(message))

    def test_crm_arrival_count_is_not_a_requirement(self):
        message = "Сегодня сколько людей будет? В срм аж 11 чел на заселение сегодня"
        self.assertTrue(looks_like_arrival_count_status(message))
        self.assertFalse(looks_like_need(message))

    def test_explicit_need_for_arrival_is_not_hidden(self):
        message = "Нужны 11 человек на заселение сегодня"
        self.assertFalse(looks_like_arrival_count_status(message))
        self.assertTrue(looks_like_need(message))

    def test_explicit_need_with_housing_information_is_not_hidden(self):
        message = "Нужны 10 кладовщиков, для них открыли комнату и можем заселить завтра"
        self.assertFalse(looks_like_arrival_coordination(message))
        self.assertTrue(looks_like_need(message))

    def test_past_housing_without_complaints_is_not_a_requirement(self):
        message = "Восемь человек там жили( 4 ж и 4 м) жалоб не было."
        self.assertTrue(looks_like_housing_history(message))
        self.assertFalse(looks_like_need(message))

    def test_candidate_pay_comment_is_not_a_requirement(self):
        self.assertFalse(looks_like_need(
            "По обстановке в квартире не похоже что эта женщина нуждается в вахте за 3500🤪"
        ))

    def test_real_need_with_pay_is_preserved(self):
        self.assertTrue(looks_like_need("Нужны 5 женщин на вахту за 3500"))

    def test_candidate_acceptance_without_question_mark_is_not_need(self):
        for message in (
            "Сергей Ëлчин можем 1 ж принять\nОчень хочет на мясокомбинат",
            "Можем 1 ж принять",
            "Можно направить 2 мужчин",
        ):
            with self.subTest(message=message):
                self.assertFalse(looks_like_need(message))

    def test_actual_need_with_acceptance_without_question_mark_is_preserved(self):
        self.assertTrue(looks_like_need("Нужна 1 женщина, можем принять сегодня"))

    def test_employee_problem_review_is_not_need(self):
        self.assertFalse(looks_like_need(
            "Просто 3 человек за неделю в не разобрано, понять в чем дело, "
            "что не устраивает с чем не справляются."
        ))

    def test_real_need_in_employee_problem_discussion_is_preserved(self):
        self.assertTrue(looks_like_need(
            "Сотрудники не справляются, нужно разобраться почему. "
            "Нужны 3 человека на замену."
        ))

    def test_directed_people_question_with_closed_need_is_not_a_request(self):
        message = (
            "Доброе утро,есть 3 направленных на сегодня. "
            "1 жен с нашими билетами уже в пути. Указали потребность 0- "
            "всех смогут принять или перенаправлять?"
        )
        self.assertFalse(looks_like_need(message))

    def test_new_need_after_closed_need_is_preserved(self):
        message = (
            "Указали потребность 0. Уже направлены кандидаты. "
            "Нужны 2 женщины, сможете принять?"
        )
        self.assertTrue(looks_like_need(message))

    def test_rate_indexation_with_dates_and_shift_lengths_is_not_need(self):
        message = (
            'С 16.10.2026 на проекте "Белгранкорм"\n'
            'Индексируем ставки, без изменения мотивационной логики.\n'
            'Разнорабочий: 360 руб./час - 3600 руб./смена (10 часов)\n'
            'Вахта от 75 смен и более 400 руб./час - 4000 руб.за смену\n'
            'Разнорабочий в убойный цех: 360 руб./час - 3960 руб. за смену (11 часов)\n'
            'Вахта от 75 смен и более 400 руб./час - 4400 руб.за смену\n'
            'Прошу принять в работу и внести изменения во все ресурсы компании.'
        )
        self.assertFalse(looks_like_need(message))

    def test_rate_change_with_actual_need_is_preserved(self):
        message = "Повышаем ставки до 400 руб./час. Нужны 5 разнорабочих."
        self.assertTrue(looks_like_need(message))

    def test_tariff_change_and_box_norms_are_not_need(self):
        message = (
            "Коллеги, всем доброго утра! Мираторг Хоругвино\n"
            "С 16.10.2026 меняется тариф для исполнителей.\n"
            "Грузчики 4000 смена(363р/ч)\n"
            "Комплектация до 500 коробов- 5000 смена (454,54 р/ч)\n"
            "Комплектация 500+ коробов 5500 смена(500р/ч)\n"
            "Прошу принять в работу и внести изменения во все ресурсы компании."
        )
        self.assertFalse(looks_like_need(message))

    def test_tariff_notice_with_new_staff_request_is_preserved(self):
        self.assertTrue(looks_like_need(
            "Меняется тариф: 4000 смена. Нужны 3 грузчика."
        ))

    def test_explicit_need_with_housing_history_is_not_hidden(self):
        message = "Нужны 4 женщины и 4 мужчины. Ранее сотрудники жили без жалоб."
        self.assertFalse(looks_like_housing_history(message))
        self.assertTrue(looks_like_need(message))

    def test_real_need_with_arrival_date_is_not_hidden(self):
        message = "Нужны 3 мужчины, приезжают 03.08"
        self.assertTrue(looks_like_need(message))

    def test_estimated_weekly_delivery_is_not_a_requirement(self):
        message = (
            "ориентировочно 14 человек, 7 на одной неделе и 7 на второй. "
            "естественно, получится больше - дадим больше"
        )
        self.assertFalse(looks_like_need(message))

    def test_short_quantity_confirmation_is_not_a_requirement(self):
        self.assertFalse(looks_like_need("80 ж?"))

    def test_explicit_need_with_estimate_is_not_hidden(self):
        self.assertTrue(looks_like_need("Ориентировочно нужны 14 человек на комплектовку"))

    def test_short_gender_quantity_without_question_remains_a_requirement(self):
        self.assertTrue(looks_like_need("80 ж"))

    def test_specific_worker_acceptance_question_is_not_a_requirement(self):
        self.assertFalse(looks_like_need("1 м грузчик сможем принять?"))

    def test_explicit_need_with_acceptance_question_is_not_hidden(self):
        self.assertTrue(looks_like_need("Нужен 1 м грузчик, сможете принять?"))

    def test_furniture_and_door_measurements_are_not_a_requirement(self):
        message = "Точно шкаф 2 м. Дверной проём метра 2, наверное, может 2.2"
        self.assertTrue(looks_like_measurement_discussion(message))
        self.assertFalse(looks_like_need(message))

    def test_explicit_need_with_male_abbreviation_is_not_hidden(self):
        message = "Нужны 2 м грузчика, дверной проём два метра"
        self.assertFalse(looks_like_measurement_discussion(message))
        self.assertTrue(looks_like_need(message))

    def test_candidate_profile_with_shift_count_is_not_a_requirement(self):
        message = (
            "Гафитулин Дамир Наилевич&#x20;\n"
            "Спормастер грузчик 15 смен&#x20;\n"
            "Заселение 25.08\n"
            "89852938318"
        )
        self.assertTrue(looks_like_candidate_profile(message))
        self.assertFalse(looks_like_need(message))

    def test_explicit_need_with_phone_and_shift_term_is_not_hidden(self):
        message = "Нужны 5 грузчиков на 15 смен, телефон для связи 89852938318"
        self.assertFalse(looks_like_candidate_profile(message))
        self.assertTrue(looks_like_need(message))

    def test_question_about_minimum_number_of_shifts_is_not_a_requirement(self):
        self.assertFalse(looks_like_need("КМП тоже от 15 смен примем?"))

    def test_explicit_need_with_shift_term_is_not_hidden(self):
        message = "Нужны 5 комплектовщиков на вахту от 15 смен"
        self.assertTrue(looks_like_need(message))

    def test_already_directed_worker_and_shift_instructions_are_not_a_requirement(self):
        message = (
            "Коллеги, добрый день.\n"
            "На 01.10., направлен комплектовщик Шабанов Денис на 21 смену.\n"
            "В потребности мужчины указаны только грузчики! "
            "Грузчиков направляйте на 35 смен пожалуйста.\n"
            "Ксения Смирнова"
        )

        self.assertTrue(looks_like_candidate_coordination(message))
        self.assertFalse(looks_like_need(message))

    def test_explicit_need_with_direction_and_shift_term_is_not_hidden(self):
        message = "Нужны 5 грузчиков, направляйте на 35 смен"

        self.assertFalse(looks_like_candidate_coordination(message))
        self.assertTrue(looks_like_need(message))

    def test_candidate_coordination_paraphrases_are_filtered(self):
        messages = [
            "Есть кандидат 49 лет, согласуете?",
            "Две девушки купили билеты и уже едут",
            "Можно направить семейную пару, приедут завтра?",
            "Троих мужчин возьмём? Они на доезде",
            "Кандидаты уже отправлены, билеты на пятницу",
        ]
        for message in messages:
            with self.subTest(message=message):
                self.assertTrue(looks_like_candidate_coordination(message))
                self.assertFalse(looks_like_need(message))

    def test_explicit_new_need_overrides_candidate_words(self):
        messages = [
            "Нужны 3 мужчины, приедут завтра",
            "Требуются две женщины с билетами",
            "Потребность: 4 кандидата",
        ]
        for message in messages:
            with self.subTest(message=message):
                self.assertFalse(looks_like_candidate_coordination(message))
                self.assertTrue(looks_like_need(message))


if __name__ == "__main__":
    unittest.main()
