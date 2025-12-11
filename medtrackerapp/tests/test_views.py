from datetime import datetime, timedelta
from unittest.mock import patch

from django.utils.timezone import make_aware
from rest_framework.test import APITestCase
from medtrackerapp.models import Medication, DoseLog
from django.urls import reverse
from rest_framework import status


class MedicationViewTests(APITestCase):
    def setUp(self):
        self.med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=2)
        self.med_data = {"name": "Aspirin", "dosage_mg": 100, "prescribed_per_day": 2}
        self.list_url = reverse("medication-list")
        self.medication = Medication.objects.create(**self.med_data)
        self.detail_url = reverse("medication-detail", kwargs={"pk": self.medication.pk})
        self.external_info_url = reverse("medication-get-external-info", kwargs={"pk": self.medication.pk})


    def test_list_medications_valid_data(self):
        url = reverse("medication-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["name"], "Aspirin")
        self.assertEqual(response.data[0]["dosage_mg"], 100)

    def test_create_medication_success(self):
        new_med_data = {"name": "Ibuprofen", "dosage_mg": 200, "prescribed_per_day": 3}
        response = self.client.post(self.list_url, new_med_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Medication.objects.count(), 3)
        self.assertEqual(response.data["name"], "Ibuprofen")

    def test_retrieve_medication_success(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Aspirin")

    def test_update_medication_success(self):
        update_data = {"dosage_mg": 81}  # Mini-dose
        response = self.client.patch(self.detail_url, update_data, format="json")
        self.medication.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.medication.dosage_mg, 81)

    def test_delete_medication_success(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Medication.objects.count(), 1)

    def test_create_medication_missing_field(self):
        invalid_data = {"dosage_mg": 50, "prescribed_per_day": 1}
        response = self.client.post(self.list_url, invalid_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)  # Check for a specific error message

    def test_retrieve_medication_not_found(self):
        non_existent_url = reverse("medication-detail", kwargs={"pk": 999})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("medtrackerapp.models.Medication.fetch_external_info")
    def test_get_external_info_external_api_failure(self, mock_fetch):
        # Simulate the error dictionary returned on failure
        mock_fetch.return_value = {"error": "External API down"}

        response = self.client.get(self.external_info_url)
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)

    @patch("medtrackerapp.models.Medication.fetch_external_info")
    def test_get_external_info_success(self, mock_fetch):

        mock_fetch.return_value = {"results": {"name": "Aspirin", "source": "OpenFDA"}}

        response = self.client.get(self.external_info_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["results"]["source"], "OpenFDA")
        mock_fetch.assert_called_once()


class DoseLogViewTests(APITestCase):

    def setUp(self):
        self.medication = Medication.objects.create(name="Placebo", dosage_mg=0, prescribed_per_day=1)
        self.log_url = reverse("doselog-list")
        self.filter_url = reverse("doselog-filter-by-date")

        today = make_aware(datetime.now())
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        self.log_yesterday = DoseLog.objects.create(
            medication=self.medication, taken_at=yesterday, was_taken=True
        )
        self.log_today = DoseLog.objects.create(
            medication=self.medication, taken_at=today, was_taken=True
        )
        self.log_tomorrow = DoseLog.objects.create(
            medication=self.medication, taken_at=tomorrow, was_taken=True
        )
        self.detail_url = reverse("doselog-detail", kwargs={"pk": self.log_today.pk})


    def test_create_doselog_success(self):
        new_log_data = {
            "medication": self.medication.pk,
            "taken_at": "2025-11-20T10:00:00Z",
            "was_taken": False,
        }
        response = self.client.post(self.log_url, new_log_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DoseLog.objects.count(), 4)
        self.assertFalse(response.data["was_taken"])

    def test_filter_by_date_success(self):
        # Query: Get logs from yesterday up to today (inclusive)
        start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        response = self.client.get(f"{self.filter_url}?start={start_date}&end={end_date}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should include yesterday's and today's log
        log_ids = [log["id"] for log in response.data]
        self.assertIn(self.log_yesterday.pk, log_ids)
        self.assertIn(self.log_today.pk, log_ids)
        self.assertNotIn(self.log_tomorrow.pk, log_ids)  # Should exclude tomorrow's log


    def test_create_doselog_invalid_medication_pk(self):
        invalid_data = {
            "medication": 9999,
            "taken_at": "2025-11-20T10:00:00Z",
            "was_taken": True,
        }
        response = self.client.post(self.log_url, invalid_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("medication", response.data)

    def test_filter_by_date_invalid_date_format(self):
        response = self.client.get(f"{self.filter_url}?start=2025/11/01&end=2025-11-07")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Both 'start' and 'end' query parameters are required and must be valid dates.",
            response.data["error"]
        )


class MedicationExpectedDosesViewTests(APITestCase):
    def setUp(self):

        self.medication = Medication.objects.create(
            name="Antibiotics",
            dosage_mg=500,
            prescribed_per_day=3
        )

        self.url = reverse("medication-expected-doses", kwargs={"pk": self.medication.pk})

    def test_expected_doses_valid_request(self):
        days = 10
        response = self.client.get(self.url, {'days': days})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify structure
        self.assertIn('medication_id', response.data)
        self.assertIn('days', response.data)
        self.assertIn('expected_doses', response.data)

        # Verify calculation (3 per day * 10 days = 30)
        self.assertEqual(response.data['expected_doses'], 30)
        self.assertEqual(response.data['medication_id'], self.medication.id)

    def test_expected_doses_missing_parameter(self):
        response = self.client.get(self.url)  # No query params
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expected_doses_invalid_parameter_type(self):
        response = self.client.get(self.url, {'days': 'ten'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expected_doses_negative_integer(self):
        response = self.client.get(self.url, {'days': -5})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expected_doses_model_value_error(self):
        # Create a medication that triggers ValueError (prescribed_per_day=0)
        bad_med = Medication.objects.create(
            name="BadConfigMed",
            dosage_mg=100,
            prescribed_per_day=0
        )
        url = reverse("medication-expected-doses", kwargs={"pk": bad_med.pk})

        response = self.client.get(url, {'days': 5})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)