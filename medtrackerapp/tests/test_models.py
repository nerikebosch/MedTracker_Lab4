from django.test import TestCase
from medtrackerapp.models import Medication, DoseLog
from django.utils import timezone
from datetime import timedelta, date
import datetime


class MedicationModelTests(TestCase):

    def test_str_returns_name_and_dosage(self):
        med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=2)
        self.assertEqual(str(med), "Aspirin (100mg)")

    def test_adherence_rate_all_doses_taken(self):
        med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=2)

        now = timezone.now()
        DoseLog.objects.create(medication=med, taken_at=now - timedelta(hours=30))
        DoseLog.objects.create(medication=med, taken_at=now - timedelta(hours=1))

        adherence = med.adherence_rate()
        self.assertEqual(adherence, 100.0)

    def test_expected_doses_invalid_days(self):
        med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=0)
        days = 1
        with self.assertRaises(ValueError):
            med.expected_doses(days)

    def test_expected_doses_correct_dose_count(self):
        med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=2)
        days = 3
        dose_count = med.expected_doses(days)

        self.assertEqual(dose_count, 6)

    def test_adherence_rate_over_period_higher_start_date(self):
        med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=2)
        start_date = date(2020, 5, 15)
        end_date = date(2020, 1, 31)

        with self.assertRaises(ValueError):
            med.adherence_rate_over_period(start_date, end_date)

    def test_adherence_rate_over_period_rate(self):
        med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=2)
        start_date = date(2025, 11, 24)
        end_date = date(2025, 11, 26)

        dt1 = timezone.make_aware(datetime.datetime(2025, 11, 24))
        dt2 = timezone.make_aware(datetime.datetime(2025, 11, 25))

        DoseLog.objects.create(medication=med, taken_at=dt1 - timedelta(hours=30))
        DoseLog.objects.create(medication=med, taken_at=dt2 - timedelta(hours=1))

        rate = med.adherence_rate_over_period(start_date, end_date)

        self.assertEqual(rate, 16.67)

    def test_str_dose_log_returns_name_status_and_when(self):
        med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=2)

        taken_time = timezone.now() - timedelta(hours=30)
        dose_log = DoseLog.objects.create(medication=med, taken_at= taken_time, was_taken=True)

        self.assertEqual(str(dose_log), f"Aspirin at {timezone.localtime(taken_time).strftime('%Y-%m-%d %H:%M')} - Taken")
