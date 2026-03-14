"""
Views for the pothole_api app.

  PotholeDataView  : POST /api/pothole-data/   — Receives ESP32 data
  DashboardView    : GET  /dashboard/           — Renders the map dashboard
"""

import logging
from django.conf import settings
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import PotholeDataSerializer
from . import sheets as sheets_service

logger = logging.getLogger(__name__)


class PotholeDataView(APIView):
    """
    POST /api/pothole-data/

    Accepts JSON from an ESP32 device, validates the payload, applies the
    vibration threshold filter, and stores accepted records in Google Sheets.

    Request body:
        {
            "device_id":       "ESP32-001",
            "latitude":        12.9716,
            "longitude":       77.5946,
            "vehicle_speed":   35.5,
            "vibration_value": 450.0,
            "timestamp":       "2026-03-08T16:34:56"
        }

    Responses:
        200  – Data stored successfully
        200  – Data ignored (vibration below threshold)
        400  – Validation error
        500  – Internal error (e.g., Google Sheets unreachable)
    """

    def post(self, request):
        serializer = PotholeDataSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning("Invalid pothole data received: %s", serializer.errors)
            return Response(
                {
                    'status': 'error',
                    'message': 'Invalid data.',
                    'errors': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        validated = serializer.validated_data
        vibration = validated['vibration_value']
        threshold = settings.VIBRATION_THRESHOLD

        # ── Vibration threshold filter ──────────────────────────────────────
        if vibration < threshold:
            logger.info(
                "Pothole data from %s ignored: vibration %.2f < threshold %.2f",
                validated['device_id'], vibration, threshold
            )
            return Response(
                {
                    'status': 'ignored',
                    'message': (
                        f"Vibration value ({vibration}) is below the threshold "
                        f"({threshold}). Likely a false positive, data not stored."
                    ),
                },
                status=status.HTTP_200_OK
            )

        # ── Persist to Google Sheets ────────────────────────────────────────
        try:
            sheets_service.append_pothole_row(validated)
        except Exception as exc:
            logger.error("Google Sheets write failed: %s", exc)
            return Response(
                {
                    'status': 'error',
                    'message': 'Failed to store data in Google Sheets.',
                    'detail': str(exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                'status': 'success',
                'message': 'Pothole data stored successfully.',
                'device_id': validated['device_id'],
                'vibration_value': vibration,
            },
            status=status.HTTP_200_OK
        )


class DashboardView(APIView):
    """
    GET /dashboard/

    Fetches all pothole records from Google Sheets and renders the
    interactive map dashboard.
    """

    def get(self, request):
        potholes = sheets_service.get_all_potholes()

        # Compute summary stats
        total = len(potholes)
        avg_speed = (
            round(sum(float(p['speed']) for p in potholes) / total, 1)
            if total else 0
        )
        max_vibration = (
            max(float(p['vibration']) for p in potholes)
            if total else 0
        )
        vibration_threshold = settings.VIBRATION_THRESHOLD

        context = {
            'potholes': potholes,
            'total': total,
            'avg_speed': avg_speed,
            'max_vibration': max_vibration,
            'vibration_threshold': vibration_threshold,
            'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        }
        return render(request, 'pothole_api/dashboard.html', context)
