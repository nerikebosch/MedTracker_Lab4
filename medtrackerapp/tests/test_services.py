from unittest import TestCase
from unittest.mock import patch, MagicMock
from requests.exceptions import RequestException
import logging

from medtrackerapp.services import DrugInfoService

MOCK_SUCCESS_DATA = {
    "results": [{
        "openfda": {
            "generic_name": ["IBUPROFEN"],
            "manufacturer_name": ["MCKESSON"],
        },
        "warnings": ["Keep out of reach of children."],
        "purpose": ["Pain reliever/fever reducer"],
        "id": "12345"
    }]
}

EXPECTED_SUCCESS_DATA = {
    "name": "IBUPROFEN",
    "manufacturer": "MCKESSON",
    "warnings": ["Keep out of reach of children."],
    "purpose": ["Pain reliever/fever reducer"],
}

MOCK_NO_RESULTS_DATA = {
    "meta": {},
    "results": []
}


class DrugInfoServiceTests(TestCase):

    def setUp(self):
        self.service = DrugInfoService()
        self.drug_name = "ibuprofen"


    @patch('medtrackerapp.services.requests.get')
    def test_get_drug_info_success(self, mock_get):

        # 1. Create a MagicMock object to stand in for the HTTP response
        mock_response = MagicMock()

        # 2. Program the MagicMock's attributes and methods
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_SUCCESS_DATA

        # Tell the mocked requests.get function to return our fake response object
        mock_get.return_value = mock_response

        # Execute the method under test
        result = self.service.get_drug_info(self.drug_name)

        # Assertions
        self.assertEqual(result, EXPECTED_SUCCESS_DATA)
        mock_get.assert_called_once()


    def test_get_drug_info_missing_name(self):

        with self.assertRaisesRegex(ValueError, "drug_name is required"):
            self.service.get_drug_info("")

    @patch('medtrackerapp.services.requests.get')
    def test_get_drug_info_api_error_status(self, mock_get):


        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with self.assertRaisesRegex(ValueError, "OpenFDA API error: 404"):
            self.service.get_drug_info(self.drug_name)

    @patch('medtrackerapp.services.requests.get')
    def test_get_drug_info_no_results(self, mock_get):

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_NO_RESULTS_DATA

        mock_get.return_value = mock_response

        with self.assertRaisesRegex(ValueError, "No results found for this medication."):
            self.service.get_drug_info(self.drug_name)

    @patch('medtrackerapp.services.requests.get')
    def test_get_drug_info_network_failure(self, mock_get):
        mock_get.side_effect = RequestException("Simulated Network Error")

        with self.assertRaisesRegex(RequestException, "Simulated Network Error"):
            self.service.get_drug_info(self.drug_name)

    @patch('medtrackerapp.services.requests.get')
    def test_get_drug_info_partial_data_parsing(self, mock_get):

        MOCK_PARTIAL_DATA = {
            "results": [{
                "openfda": {
                    "generic_name": "SingleName",  # Not a list
                    # manufacturer_name is missing entirely
                },
                # warnings is missing entirely
                "purpose": ["Single purpose list"]
            }]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_PARTIAL_DATA
        mock_get.return_value = mock_response

        result = self.service.get_drug_info(self.drug_name)

        self.assertEqual(result["name"], "SingleName")
        self.assertEqual(result["manufacturer"], "Unknown")
        self.assertEqual(result["warnings"], ["No warnings available"])
        self.assertEqual(result["purpose"], ["Single purpose list"])