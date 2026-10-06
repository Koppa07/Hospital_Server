from django.db import DatabaseError, connection, transaction
from django.utils import timezone
from datetime import timedelta, datetime, time
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import ReceptionLog, TimeSlot
from ..serializers.action_serializers import (
    AppointmentBookingSerializer,
    CancelOrNoShowSerializer,
    CompleteReceptionSerializer,
    DoctorScheduleCreateSerializer,
)
from ..serializers.info_serializers import (
    AvailableTimeSlotSerializer,
    MedicalHistorySerializer,
    AppointmentSerializer,
)
from ..services import generate_time_slots_for_schedule


@api_view(["POST"])
def book_appointment(request):
    serializer = AppointmentBookingSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data

    try:
        with transaction.atomic():
            slot = (
                TimeSlot.objects.select_for_update()
                .filter(
                    slot_id=data["slot_id"],
                    doctor_id=data["doctor_id"],
                    is_booked=False,
                )
                .first()
            )

            if not slot:
                return Response(
                    {
                        "error": "Выбранное время уже занято или отсутствует в расписании."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT book_appointment(%s, %s, %s);",
                    [
                        data["doctor_id"],
                        data["patient_id"],
                        slot.start_datetime,
                    ],
                )

            slot.is_booked = True
            slot.save(update_fields=["is_booked"])

        return Response(
            {"message": "Вы успешно записаны на прием!"},
            status=status.HTTP_201_CREATED,
        )

    except DatabaseError as e:
        error_message = str(e).split("CONTEXT:")[0].replace("ERROR:", "").strip()

        return Response(
            {"error": error_message},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
def complete_reception(request):
    serializer = CompleteReceptionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COMPLETE_RECEPTION(%s, %s, %s, %s);",
                    [
                        data["log_id"],
                        data["disease_id"],
                        data["complains"],
                        data["recommendations"],
                    ],
                )
                new_pres_id = cursor.fetchone()[0]

                if new_pres_id and data.get("drugs"):
                    for drug in data["drugs"]:
                        cursor.execute(
                            "CALL add_drug_to_prescription(%s, %s, %s);",
                            [new_pres_id, drug["drug_id"], drug["dosage"]],
                        )

        return Response(
            {
                "message": "Прием успешно завершен",
                "log_id": data["log_id"],
                "prescription_id": new_pres_id,
            },
            status=status.HTTP_200_OK,
        )
    except DatabaseError as e:
        error_message = str(e).split("CONTEXT:")[0].strip()
        return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PATCH", "POST"])
def cancel_or_no_show_appointment(request, log_id):
    serializer = CancelOrNoShowSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    new_status = serializer.validated_data["status"]
    user = request.user

    try:
        appointment = ReceptionLog.objects.select_related("patient_id").get(
            log_id=log_id
        )
    except ReceptionLog.DoesNotExist:
        return Response(
            {"detail": "Запись на прием не найдена."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if getattr(user, "role", None) == "PATIENT":
        if new_status == "NO_SHOW":
            return Response(
                {"detail": "Пациент не имеет права отмечать неявку."},
                status=status.HTTP_403_FORBIDDEN,
            )

        patient_profile = getattr(user, "patient_profile", None)
        if (
            not patient_profile
            or appointment.patient_id.card_number != patient_profile.card_number
        ):
            return Response(
                {"detail": "Вы не можете отменить чужую запись."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if appointment.appointment_date <= timezone.now():
            return Response(
                {
                    "detail": "Нельзя отменить запись, время приема которой уже наступило или прошло."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    with transaction.atomic():
        appointment.status = new_status
        appointment.save(update_fields=["status"])

        if new_status == "CANCELLED":
            TimeSlot.objects.filter(
                doctor_id=appointment.doctor_id_id,
                start_datetime=appointment.appointment_date,
            ).update(is_booked=False)

    status_labels = {
        "CANCELLED": "Запись успешно отменена",
        "NO_SHOW": "Зафиксирована неявка пациента",
    }

    return Response(
        {
            "message": status_labels.get(new_status, "Статус обновлен"),
            "log_id": appointment.log_id,
            "status": appointment.status,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def create_schedule(request):
    serializer = DoctorScheduleCreateSerializer(data=request.data)
    if serializer.is_valid():
        schedule = serializer.save()
        generate_time_slots_for_schedule(schedule)
        return Response(
            {
                "detail": "График успешно создан, слоты записи сформированы.",
                "schedule_id": schedule.schedule_id,
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def get_available_slots(request):
    doctor_id = request.query_params.get("doctor_id")
    target_date_str = request.query_params.get("date")

    if not doctor_id or not target_date_str:
        return Response(
            {
                "detail": "Укажите параметры doctor_id и date (?doctor_id=1&date=YYYY-MM-DD)"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = timezone.now()

    available_slots = TimeSlot.objects.filter(
        doctor_id=doctor_id,
        start_datetime__date=target_date_str,
        start_datetime__gt=now,
        is_booked=False,
    ).order_by("start_datetime")

    serializer = AvailableTimeSlotSerializer(available_slots, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_schedule(request):
    doctor_id = request.query_params.get("doctor_id")
    start_date = request.query_params.get("start")
    end_date = request.query_params.get("end")

    user = request.user
    role = getattr(user, "role", None)

    if role == "DOCTOR":
        doctor_profile = getattr(user, "doctor_profile", None)

        if not doctor_profile:
            return Response(
                {"detail": "Для пользователя не найден профиль врача."},
                status=status.HTTP_404_NOT_FOUND,
            )

        doctor_id = doctor_profile.doctor_id

    if not doctor_id:
        return Response(
            {"detail": "Необходимо указать doctor_id."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    queryset = (
        ReceptionLog.objects.filter(doctor_id=doctor_id)
        .select_related("patient_id", "doctor_id")
        .order_by("appointment_date")
    )

    if start_date:
        queryset = queryset.filter(appointment_date__gte=start_date)

    if end_date:
        queryset = queryset.filter(appointment_date__lte=end_date)

    events = [
        {
            "id": log.log_id,
            "title": f"Пациент: {log.patient_id.patient_name}",
            "start": log.appointment_date.isoformat(),
            "end": (log.appointment_date + timezone.timedelta(minutes=15)).isoformat(),
            "status": log.status,
            "patient_id": log.patient_id.card_number,
            "doctor_id": log.doctor_id_id,
        }
        for log in queryset
    ]

    return Response(
        events,
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
def medical_history(request):
    user = request.user
    role = getattr(user, "role", None)

    queryset = ReceptionLog.objects.select_related("patient_id", "doctor_id").filter(
        status="COMPLETED"
    )

    if role == "PATIENT":
        patient_profile = getattr(user, "patient_profile", None)
        if not patient_profile:
            return Response([], status=status.HTTP_200_OK)
        queryset = queryset.filter(patient_id=patient_profile)

    elif role == "DOCTOR":
        doctor_profile = getattr(user, "doctor_profile", None)
        if not doctor_profile:
            return Response([], status=status.HTTP_200_OK)
        queryset = queryset.filter(doctor_id=doctor_profile)

        patient_id = request.query_params.get("patient_id")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

    elif role in ["ADMIN", "REGISTRAR"]:
        patient_id = request.query_params.get("patient_id")
        doctor_id = request.query_params.get("doctor_id")

        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

    else:
        return Response(
            {"detail": "Доступ запрещен."}, status=status.HTTP_403_FORBIDDEN
        )

    queryset = queryset.order_by("-appointment_date")

    serializer = MedicalHistorySerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_planned_appointments(request):
    user = request.user
    role = getattr(user, "role", None)
    now = timezone.now()

    queryset = (
        ReceptionLog.objects.select_related("patient_id", "doctor_id")
        .filter(appointment_date__gte=now)
        .exclude(status="COMPLETED")
    )

    if role == "PATIENT":
        patient_profile = getattr(user, "patient_profile", None)
        if not patient_profile:
            return Response([], status=status.HTTP_200_OK)
        queryset = queryset.filter(patient_id=patient_profile)

    elif role == "DOCTOR":
        doctor_profile = getattr(user, "doctor_profile", None)
        if not doctor_profile:
            return Response([], status=status.HTTP_200_OK)
        queryset = queryset.filter(doctor_id=doctor_profile)

        patient_id = request.query_params.get("patient_id")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
    else:
        return Response(
            {"detail": "Доступ запрещен."}, status=status.HTTP_403_FORBIDDEN
        )

    queryset = queryset.order_by("-appointment_date")

    serializer = AppointmentSerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_appointments(request):
    user = request.user
    role = getattr(user, "role", None)

    queryset = ReceptionLog.objects.select_related("patient_id", "doctor_id").all()
    date = request.query_params.get("date")
    if role == "PATIENT":
        patient_profile = getattr(user, "patient_profile", None)
        doctor_id = request.query_params.get("doctor_id")
        if not patient_profile:
            return Response([], status=status.HTTP_200_OK)
        queryset = queryset.filter(patient_id=patient_profile)
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

    elif role == "DOCTOR":
        doctor_profile = getattr(user, "doctor_profile", None)
        if not doctor_profile:
            return Response([], status=status.HTTP_200_OK)
        queryset = queryset.filter(doctor_id=doctor_profile)

        patient_id = request.query_params.get("patient_id")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

    elif role in ["ADMIN", "REGISTRAR"]:
        patient_id = request.query_params.get("patient_id")
        doctor_id = request.query_params.get("doctor_id")

        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

    else:
        return Response(
            {"detail": "Доступ запрещен."}, status=status.HTTP_403_FORBIDDEN
        )

    if date:
        try:
            selected_date = datetime.strptime(
                date,
                "%Y-%m-%d",
            ).date()
        except ValueError:
            return Response(
                {"detail": ("Неверный формат даты. Ожидается YYYY-MM-DD.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_tz = timezone.get_current_timezone()

        start_datetime = timezone.make_aware(
            datetime.combine(
                selected_date,
                time.min,
            ),
            current_tz,
        )

        end_datetime = start_datetime + timedelta(days=1)

        queryset = queryset.filter(
            appointment_date__gte=start_datetime,
            appointment_date__lt=end_datetime,
        )

    queryset = queryset.order_by("-appointment_date")

    serializer = AppointmentSerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
