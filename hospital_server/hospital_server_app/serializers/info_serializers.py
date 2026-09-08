from django.contrib.auth import get_user_model
from rest_framework import serializers

from ..models import *

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "password", "role")
        extra_kwargs = {
            "password": {"write_only": True, "min_length": 4},
            "id": {"read_only": True},
        }

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class DoctorProfileSerializer(serializers.ModelSerializer):
    spec_title = serializers.CharField(source="spec.spec_title", read_only=True)
    room_number = serializers.IntegerField(source="room.room_number", read_only=True)
    department_title = serializers.CharField(source="dep.dep_title", read_only=True)

    class Meta:
        model = Doctor
        fields = ("doctor_id", "doctor_name", "spec_title", "dep_title", "room_number")


class UserWithDoctorSerializer(serializers.ModelSerializer):
    doctor_profile = DoctorProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "role", "doctor_profile")


class DrugItemSerializer(serializers.Serializer):
    drug_id = serializers.IntegerField(min_value=1)
    dosage = serializers.CharField(max_length=50)


class PrescriptionDrugDetailSerializer(serializers.ModelSerializer):
    drug_title = serializers.CharField(source="drug_id.drug_title", read_only=True)
    drug_type = serializers.CharField(source="drug_id.drug_type", read_only=True)

    class Meta:
        model = PrescriptionDrug
        fields = ("drug_title", "drug_type", "dosage")


class PrescriptionDetailSerializer(serializers.ModelSerializer):
    drugs = PrescriptionDrugDetailSerializer(
        source="prescriptiondrug_set", many=True, read_only=True
    )

    class Meta:
        model = Prescription
        fields = ("pres_id", "recommendations", "pres_date", "drugs")


class MedicalHistorySerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor_id.doctor_name", read_only=True)
    doctor_specialization = serializers.CharField(
        source="doctor_id.spec.spec_title", read_only=True
    )
    disease_title = serializers.CharField(
        source="disease_id.disease_title", read_only=True
    )
    disease_code = serializers.CharField(
        source="disease_id.disease_code", read_only=True
    )
    prescription = PrescriptionDetailSerializer(source="pres_id", read_only=True)

    class Meta:
        model = ReceptionLog
        fields = (
            "log_id",
            "appointment_date",
            "doctor_name",
            "doctor_specialization",
            "disease_code",
            "disease_title",
            "complains",
            "prescription",
        )


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ("card_number", "patient_name", "birth_date", "address", "insurance")


class SpecializationSerializer(serializers.Serializer):
    class Meta:
        model = Department
        fields = ("spec_id", "spec_title")


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("dep_id", "dep_title", "name_of_manager")


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ("room_id", "room_number", "equipment")


class DiseaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disease
        fields = ("disease_id", "disease_code", "disease_title")


class DrugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = ("drug_id", "drug_title", "drug_type")


class AvailableTimeSlotSerializer(serializers.ModelSerializer):
    start_time = serializers.DateTimeField(source="start_datetime", format="%H:%M")
    end_time = serializers.DateTimeField(source="end_datetime", format="%H:%M")
    date = serializers.DateTimeField(source="start_datetime", format="%Y-%m-%d")

    class Meta:
        model = TimeSlot
        fields = ("slot_id", "doctor_id", "date", "start_time", "end_time", "is_booked")
