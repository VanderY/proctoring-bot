import json
from typing import List

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State

from sources.bot.loggers import LogInstaller
from sources.bot.modules.chains.survey.teacher_handlers_chain import SurveyTeacherKeyboardBuilder
from sources.bot.modules.handlers_chain import HandlersChain
from sources.bot.modules.handlers_registrar import HandlersRegistrar as Registrar
from sources.bot.modules.keyboard.keyboard import KeyboardBuilder


class SurveyStudentStates(StatesGroup):
    student_ready_to_pass_test = State()


class SurveyStudentKeyboardBuilder:
    @staticmethod
    def get_ready_to_survey_keyboard():
        return KeyboardBuilder.get_inline_keyboard_markup(
            [
                {
                    "Готов получить тест": "ready",
                }
            ]
        )


class StudentHandlersChain(HandlersChain):
    _logger = LogInstaller.get_default_logger(__name__, LogInstaller.DEBUG)

    @staticmethod
    @Registrar.message_handler(commands=["ready"])  # needs to change to callback after main menu button pressed
    async def ready_check_survey_handler(message: types.Message, state: FSMContext):
        data = await state.get_data()
        if data["type"] == "student":
            await message.answer("Нажмите кнопку ниже, чтобы получить тест",
                                 reply_markup=SurveyStudentKeyboardBuilder.get_ready_to_survey_keyboard())

    @staticmethod
    @Registrar.callback_query_handler(lambda callback: callback.data.startswith("ready"))
    async def ready_to_pass_survey_handler(query: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()

        await query.message.edit_text("Ожидайте сообщения о начале теста")
        await SurveyStudentStates.student_ready_to_pass_test.set()

    @staticmethod
    @Registrar.callback_query_handler(lambda c: c.data, state=SurveyStudentStates.student_ready_to_pass_test)
    async def passing_test_handler(callback_query: types.CallbackQuery, state: FSMContext):
        separated_data = callback_query.data.split(";")
        survey_sheet_name = separated_data[1]
        data = await state.get_data()
        tests = data.get("tests")

        with open(f'surveys/{survey_sheet_name}.json', encoding='utf-8') as json_file:
            survey = json.load(json_file)
            if tests is None:
                await state.update_data(tests={"is_finished": False, "answers": {}, "test_name": survey_sheet_name})
            question_number = int(separated_data[2])
            # Проверка ответов на правильность
            if separated_data[0] == "question":
                current_question = survey[question_number - 1]

                answers = list(tests.get('answers'))
                is_correct = False
                if current_question['правильный'] == separated_data[3]:
                    is_correct = True
                answer = {
                    "Вопрос": str(survey[question_number - 1]['Вопрос']),
                    "is_correct": is_correct
                }
                answers.append(answer)
                tests["answers"] = answers
                await state.update_data(tests=tests)
            # Формируем сообщение с вопросом и ответами
            if question_number < len(survey):
                current_question = survey[question_number]
                answers_kb = SurveyTeacherKeyboardBuilder.get_answers_keyboard(current_question, question_number,
                                                                               separated_data[1])
                await callback_query.message.edit_text(text=f"{current_question['Вопрос']}", reply_markup=answers_kb)
                await callback_query.answer()
            # Тест закончен
            else:
                tests["is_finished"] = True
                answers = tests.get("answers")

                correct_answers = 0

                for answer in answers:
                    if answer['is_correct']:
                        correct_answers += 1

                StudentHandlersChain._logger.info(f"{callback_query.from_user.username}"
                                                  f"(id:{callback_query.message.chat.id}) "
                                                  f"passed test")
                StudentHandlersChain._logger.info(f"Answers: {answers}")

                tests["answers"] = answers
                await state.update_data(tests=tests)

                await SurveyStudentStates.next()
                await callback_query.message.edit_text(text=f"Вы прошли тест на {correct_answers}/{len(answers)}")
                await callback_query.answer()
