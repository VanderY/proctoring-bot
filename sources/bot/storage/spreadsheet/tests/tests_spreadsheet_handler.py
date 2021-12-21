from .base_tests_spreadsheet_handler import BaseTestsSpreadsheetHandler
import json
import os
import sys
from datetime import datetime

import apiclient
import httplib2
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials

from .base_tests_spreadsheet_handler import BaseTestsSpreadsheetHandler


class TestsSpreadsheetHandler(BaseTestsSpreadsheetHandler):
    def __init__(self, credentials_file_name: str):
        self._loaded_tests = {}
        self._current_test_id = ""
        self._http_auth = ServiceAccountCredentials.from_json_keyfile_name(
            credentials_file_name,
            ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
        ).authorize(httplib2.Http())
        self._service = apiclient.discovery.build("sheets", "v4", http=self._http_auth)

    def _add_row(self, test_name: str, row: list[str], test_id: str):
        self._service.spreadsheets().values().append(spreadsheetId=test_id,
                                                     range=test_name,
                                                     valueInputOption="USER_ENTERED",
                                                     insertDataOption="INSERT_ROWS",
                                                     body={"values": [row]}).execute()

    def _create_page(self, title: str, spreadsheet_id: str):
        data = {'requests': [
            {
                'addSheet': {
                    'properties': {'title': title}
                }
            }
        ]}
        self._service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id,
                                                 body=data).execute()

    def load_test_by_link(self, url: str):
        url_details = url.split("/")
        spreadsheet_id = url_details[url_details.index("d") + 1]
        self._current_test_id = spreadsheet_id
        return self._get_test(spreadsheet_id)

    def _get_test(self, spreadsheet_id: str) -> tuple[str, list[dict]]:
        try:
            spreadsheets = self._service.spreadsheets().get(spreadsheetId=spreadsheet_id,
                                                            includeGridData=True).execute()
        except HttpError:
            return "", []
        test_name = spreadsheets["properties"]["title"]
        raw_data = []
        for sheet in spreadsheets["sheets"]:
            if sheet["properties"]["title"] == "Тест":
                for sheet_data in sheet["data"][0]["rowData"]:
                    if len(sheet_data) > 0:
                        raw_data.append(sheet_data)

        survey = []
        keys = []

        for key in raw_data[0]["values"]:
            keys.append(key["formattedValue"])

        raw_data.remove(raw_data[0])
        for element in raw_data:
            question = {}
            index = 0
            for string in element["values"]:
                if len(string) > 3:
                    question[str(keys[index])] = string["formattedValue"]
                index += 1
            survey.append(question)

        for el in survey:
            if len(el) < 1:
                survey.remove(el)

        self._save_test(test_name, survey)
        return test_name, survey

    def _save_test(self, test_name: str, test: list[dict]) -> None:
        if not test_name == "":
            current_path = os.path.dirname(sys.argv[0])  # needs to be configured in config.ini
            path = f'{current_path}\\surveys'
            os.makedirs(path, exist_ok=True)
            with open(f'surveys/{test_name}.json', 'w', encoding='utf-8') as f:
                json.dump(test, f, ensure_ascii=False, indent=4)

    def add_result_to_worksheet(self, test_name, user_data, result_list) -> None:
        if test_name + "_result" not in self._get_page_names(self._current_test_id):
            self._create_page(test_name + "_result", self._current_test_id)
            top_row = ["Студент", "Время"]
            for q in result_list:
                top_row.append(q["Вопрос"])
            top_row.append("Результат")
            self._add_row(test_name + "_result", top_row, self._current_test_id)

        correct_answers = 0
        boolean_answer_list = []

        for answer in result_list:
            if answer['is_correct']:
                correct_answers += 1
                boolean_answer_list.append("Верно")
            else:
                boolean_answer_list.append("Неверно")

        row = [user_data, str(datetime.now())]

        for ans in boolean_answer_list:
            row.append(ans)

        row.append(f"{correct_answers}/{len(result_list)}")

        self._add_row(test_name + "_result", row, self._current_test_id)

    def _get_page_names(self, spreadsheet_id: str) -> list:
        try:
            sheet_metadata = self._service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        except HttpError:
            return []

        sheets = sheet_metadata.get('sheets', '')

        sheet_names = []

        for sheet in sheets:
            sheet_names.append(sheet["properties"]["title"])

        return sheet_names

