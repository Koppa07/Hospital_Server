from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from ..models import *
from .info_serializers import *

User = get_user_model()


class DoctorRegistrationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=4)
    doctor_name = serializers.CharField(max_length=100)
    spec_id = serializers.PrimaryKeyRelatedField(
        queryset=Specialization.objects.all(), source="spec", write_only=True
    )
    dep_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source="dep", write_only=True
    )
    room_id = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(), source="room", write_only=True
    )

    class Meta:
        model = Doctor
        fields = ("username", "password", "doctor_name", "spec_id", "dep_id", "room_id")

    def create(self, validated_data):
        username = validated_data.pop("username")
        password = validated_data.pop("password")
        doctor_name = validated_data.pop("doctor_name")

        with transaction.atomic():
            user = User.objects.create(username=username, role="DOCTOR")
            user.set_password(password)
            user.save()

            doctor = Doctor.objects.create(
                user=user,
                doctor_name=doctor_name,
                spec=validated_data["spec"],
                dep=validated_data["dep"],
                room=validated_data["room"],
            )

        return doctor


class PatientRegistrationSerializer(serializers.Serializer):
    patient_name = serializers.CharField(max_length=100)
    birth_date = serializers.DateField()
    address = serializers.CharField(required=False, allow_blank=True, default="")
    insurance = serializers.CharField(max_length=16, min_length=16)

    def validate_insurance(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                "Номер полиса ОМС должен состоять только из цифр."
            )
        return value


class AppointmentBookingSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField(min_value=1)
    patient_id = serializers.IntegerField(min_value=1)
    appointment_date = serializers.DateTimeField()

    def validate_appointment_date(self, value):
        now = timezone.now()

        if value <= now:
            raise serializers.ValidationError(
                "Нельзя записаться на прошедшую дату или время."
            )

        max_future_date = now + timedelta(days=30)
        if value > max_future_date:
            raise serializers.ValidationError(
                "Запись открыта максимум на 30 дней вперед."
            )

        appointment_time = value.time()
        start_work_time = time(8, 0)  # 08:00
        end_work_time = time(20, 0)  # 20:00

        if not (start_work_time <= appointment_time < end_work_time):
            raise serializers.ValidationError(
                "Запись возможна только в рабочие часы поликлиники (с 08:00 до 20:00)."
            )

        if (
            value.minute not in (0, 15, 30, 45)
            or value.second != 0
            or value.microsecond != 0
        ):
            raise serializers.ValidationError(
                "Время приема должно быть кратно 15 минутам (например, 09:00, 09:15, 09:30, 09:45)."
            )

        return value


class CompleteReceptionSerializer(serializers.Serializer):
    log_id = serializers.IntegerField(min_value=1)
    disease_id = serializers.IntegerField(min_value=1)
    complains = serializers.CharField(min_length=5)
    recommendations = serializers.CharField(
        required=False, allow_blank=True, default=None
    )
    drugs = DrugItemSerializer(many=True, required=False, default=[])

    def validate(self, attrs):
        if attrs.get("drugs") and not attrs.get("recommendations"):
            raise serializers.ValidationError(
                {
                    "recommendations": "Укажите общие рекомендации по лечению для выписываемого рецепта."
                }
            )
        return attrs


class CancelOrNoShowSerializer(serializers.Serializer):
    log_id = serializers.IntegerField(min_value=1)
    status = serializers.ChoiceField(
        choices=["CANCELLED", "NO_SHOW"],
        error_messages={
            "invalid_choice": "Допустимы только статусы 'CANCELLED' (Отменена) или 'NO_SHOW' (Неявка)."
        },
    )


class DoctorScheduleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSchedule
        fields = (
            "schedule_id",
            "doctor",
            "date",
            "start_time",
            "end_time",
        )

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(
                {"end_time": "Время окончания смены должно быть позже времени начала."}
            )
        if attrs["date"] < timezone.now().date():
            raise serializers.ValidationError(
                {"date": "Нельзя создавать график на прошедшие даты."}
            )
        return attrs
