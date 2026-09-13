import secrets
import string
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from ..models import *
from .info_serializers import *

User = get_user_model()


def generate_random_password(length=8):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class DoctorRegistrationSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(max_length=100)
    spec = serializers.PrimaryKeyRelatedField(queryset=Specialization.objects.all())
    dep = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all())
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    generated_username = serializers.CharField(read_only=True)
    generated_password = serializers.CharField(read_only=True)

    class Meta:
        model = Doctor
        fields = (
            "doctor_name",
            "spec",
            "dep",
            "room",
            "generated_username",
            "generated_password",
        )

    def create(self, validated_data):
        doctor_name = validated_data.pop("doctor_name")

        base_username = f"doc_{secrets.randbelow(899999) + 100000}"
        generated_password = generate_random_password(10)

        with transaction.atomic():
            user = User.objects.create_user(
                username=base_username,
                password=generated_password,
                role="DOCTOR",
            )

            doctor = Doctor.objects.create(
                user=user,
                doctor_name=doctor_name,
                spec=validated_data["spec"],
                dep=validated_data["dep"],
                room=validated_data["room"],
            )

        doctor.generated_username = base_username
        doctor.generated_password = generated_password
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
    status = serializers.ChoiceField(
        choices=["CANCELLED", "NO_SHOW"],
        error_messages={
            "invalid_choice": "Допустимы только статусы 'CANCELLED' или 'NO_SHOW'."
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


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Старый пароль указан неверно.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
