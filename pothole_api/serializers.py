"""
Serializer for validating incoming pothole data from ESP32 devices.
"""

from rest_framework import serializers


class PotholeDataSerializer(serializers.Serializer):
    """
    Validates the JSON payload sent by ESP32 devices.

    Expected fields:
        device_id       : Unique identifier of the ESP32 device
        latitude        : GPS latitude (-90 to 90)
        longitude       : GPS longitude (-180 to 180)
        vehicle_speed   : Speed in km/h (must be >= 0)
        vibration_value : Raw accelerometer vibration reading (must be >= 0)
        timestamp       : ISO-8601 datetime string (e.g. "2026-03-08T16:34:56")
    """

    device_id = serializers.CharField(
        max_length=64,
        error_messages={'required': 'device_id is required.'}
    )
    latitude = serializers.FloatField(
        min_value=-90.0,
        max_value=90.0,
        error_messages={
            'required': 'latitude is required.',
            'min_value': 'latitude must be >= -90.',
            'max_value': 'latitude must be <= 90.',
        }
    )
    longitude = serializers.FloatField(
        min_value=-180.0,
        max_value=180.0,
        error_messages={
            'required': 'longitude is required.',
            'min_value': 'longitude must be >= -180.',
            'max_value': 'longitude must be <= 180.',
        }
    )
    vehicle_speed = serializers.FloatField(
        min_value=0.0,
        error_messages={
            'required': 'vehicle_speed is required.',
            'min_value': 'vehicle_speed must be >= 0.',
        }
    )
    vibration_value = serializers.FloatField(
        min_value=0.0,
        error_messages={
            'required': 'vibration_value is required.',
            'min_value': 'vibration_value must be >= 0.',
        }
    )
    timestamp = serializers.CharField(
        max_length=32,
        error_messages={'required': 'timestamp is required.'}
    )

    def validate_device_id(self, value):
        """Strip whitespace from device_id."""
        return value.strip()

    def validate_timestamp(self, value):
        """Basic sanity check — ensure timestamp is not an empty string."""
        if not value.strip():
            raise serializers.ValidationError("timestamp must not be empty.")
        return value.strip()
