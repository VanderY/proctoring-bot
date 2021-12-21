import unittest

from ..auth_spreadsheet_handler import AuthSpreadsheetHandler


class TestSpreadsheet(unittest.TestCase):
    def setUp(self):
        token_path = "../../../../../tokens/auth_token.json"
        self.handler = AuthSpreadsheetHandler("", token_path)
        self.handler.create_spreadsheet()
