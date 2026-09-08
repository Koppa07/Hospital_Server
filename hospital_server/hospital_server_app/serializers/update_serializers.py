from django.contrib.auth import get_user_model
from rest_framework import serializers

from ..models import *

User = get_user_model()


class SpecializationUpdateSerializer(serializers.Serializer):
    class Meta:
        model = Department
        fields = "spec_title"


class DepartmentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("dep_title", "name_of_manager")


class RoomUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ("room_number", "equipment")


class DiseaseUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disease
        fields = ("disease_code", "disease_title")


class DrugUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = ("drug_title", "drug_type")


class PatientUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ("patient_name", "address", "insurance")


class DoctorUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ("doctor_name", "spec", "dep", "room")
