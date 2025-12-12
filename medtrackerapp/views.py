from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.dateparse import parse_date
from .models import Medication, DoseLog, Note
from .serializers import MedicationSerializer, DoseLogSerializer, NoteSerializer


class MedicationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and managing medications.

    Provides standard CRUD operations via the Django REST Framework
    `ModelViewSet`, as well as a custom action for retrieving
    additional information from an external API (OpenFDA).

    Endpoints:
        - GET /medications/ — list all medications
        - POST /medications/ — create a new medication
        - GET /medications/{id}/ — retrieve a specific medication
        - PUT/PATCH /medications/{id}/ — update a medication
        - DELETE /medications/{id}/ — delete a medication
        - GET /medications/{id}/info/ — fetch external drug info from OpenFDA
    """
    queryset = Medication.objects.all()
    serializer_class = MedicationSerializer

    @action(detail=True, methods=["get"], url_path="info")
    def get_external_info(self, request, pk=None):
        """
        Retrieve external drug information from the OpenFDA API.

        Calls the `Medication.fetch_external_info()` method, which
        delegates to the `DrugInfoService` for API access.

        Args:
            request (Request): The current HTTP request.
            pk (int): Primary key of the medication record.

        Returns:
            Response:
                - 200 OK: External API data returned successfully.
                - 502 BAD GATEWAY: If the external API request failed.

        Example:
            GET /medications/1/info/
        """
        medication = self.get_object()
        data = medication.fetch_external_info()

        if isinstance(data, dict) and data.get("error"):
            return Response(data, status=status.HTTP_502_BAD_GATEWAY)
        return Response(data)

    @action(detail=True, methods=["get"], url_path="expected-doses")
    def expected_doses(self, request, pk=None):
        """
        Calculate expected doses for a specific medication.

        Args:
            request: HTTP request containing required 'days' query parameter.
            pk: Primary key of the medication.

        Returns:
            Response:
                - 200 OK: JSON with medication_id, days, and expected_doses.
                - 400 BAD REQUEST: If 'days' is missing, invalid, or calculation fails.

        Example:
            GET /api/medications/1/expected-doses/?days=5
        """
        days_str = request.query_params.get("days")

        if days_str is None:
            return Response(
                {"error": "The 'days' parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            days = int(days_str)
            if days <= 0:
                raise ValueError
        except ValueError:
            return Response(
                {"error": "Days must be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        medication = self.get_object()

        try:
            total_doses = medication.expected_doses(days)
            return Response({
                "medication_id": medication.id,
                "days": days,
                "expected_doses": total_doses
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class DoseLogViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and managing dose logs.

    A DoseLog represents an event where a medication dose was either
    taken or missed. This viewset provides standard CRUD operations
    and a custom filtering action by date range.

    Endpoints:
        - GET /logs/ — list all dose logs
        - POST /logs/ — create a new dose log
        - GET /logs/{id}/ — retrieve a specific log
        - PUT/PATCH /logs/{id}/ — update a dose log
        - DELETE /logs/{id}/ — delete a dose log
        - GET /logs/filter/?start=YYYY-MM-DD&end=YYYY-MM-DD —
          filter logs within a date range
    """
    queryset = DoseLog.objects.all()
    serializer_class = DoseLogSerializer

    @action(detail=False, methods=["get"], url_path="filter")
    def filter_by_date(self, request):
        """
        Retrieve all dose logs within a given date range.

        Query Parameters:
            - start (YYYY-MM-DD): Start date of the range (inclusive).
            - end (YYYY-MM-DD): End date of the range (inclusive).

        Returns:
            Response:
                - 200 OK: A list of dose logs between the two dates.
                - 400 BAD REQUEST: If start or end parameters are missing or invalid.

        Example:
            GET /logs/filter/?start=2025-11-01&end=2025-11-07
        """
        start = parse_date(request.query_params.get("start"))
        end = parse_date(request.query_params.get("end"))

        if not start or not end:
            return Response(
                {"error": "Both 'start' and 'end' query parameters are required and must be valid dates."},
                status=status.HTTP_400_BAD_REQUEST
            )

        logs = self.get_queryset().filter(
            taken_at__date__gte=start,
            taken_at__date__lte=end
        ).order_by("taken_at")

        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)


class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer

    def update(self, request, *args, **kwargs):

        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):

        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)