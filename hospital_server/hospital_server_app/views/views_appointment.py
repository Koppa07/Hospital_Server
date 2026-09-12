from django.db import DatabaseError, connection, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import ReceptionLog, TimeSlot
from ..serializers.action_serializers import (
    AppointmentBookingSerializer,
    CancelOrNoShowSerializer,
    CompleteReceptionSerializer,
    DoctorScheduleCreateSerializer,
)
from ..serializers.info_serializers import AvailableTimeSlotSerializer
from ..services import generate_time_slots_for_schedule


@api_view(["POST"])
def book_appointment(request):
    serializer = AppointmentBookingSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    if request.user.role == "PATIENT":
        patient_profile = getattr(request.user, "patient_profile", None)
        if not patient_profile or patient_profile.card_number != data["patient_id"]:
            return Response(
                {"detail": "Вы можете записывать на прием только себя."},
                status=status.HTTP_403_FORBIDDEN,
            )

    try:
        with transaction.atomic():
            slot = (
                TimeSlot.objects.select_for_update()
                .filter(
                    doctor_id=data["doctor_id"],
                    start_datetime=data["appointment_date"],
                    is_booked=False,
                )
                .first()
            )

            if not slot:
                return Response(
                    {
                        "error": "Выбранное время уже занято или не существует в расписании."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT book_appointment(%s, %s, %s);",
                    [
                        data["doctor_id"],
                        data["patient_id"],
                        data["appointment_date"],
                    ],
                )

            slot.is_booked = True
            slot.save(update_fields=["is_booked"])

        return Response(
            {"message": "Вы успешно записаны на прием!"}, status=status.HTTP_201_CREATED
        )

    except DatabaseError as e:
        error_message = str(e).split("CONTEXT:")[0].replace("ERROR:", "").strip()
        return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)


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
def cancel_or_no_show_appointment(request, pk):
    serializer = CancelOrNoShowSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    new_status = serializer.validated_data["status"]
    user = request.user

    try:
        appointment = ReceptionLog.objects.select_related("patient_id").get(pk=pk)
    except ReceptionLog.DoesNotExist:
        return Response(
            {"detail": "Запись на прием не найдена."}, status=status.HTTP_404_NOT_FOUND
        )

    if user.role == "PATIENT":
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
            "message": status_labels[new_status],
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

    if request.user.role == "DOCTOR":
        doctor_profile = getattr(request.user, "doctor_profile", None)
        if doctor_profile:
            doctor_id = doctor_profile.id

    if not doctor_id:
        return Response(
            {"detail": "Необходимо указать doctor_id."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    queryset = ReceptionLog.objects.filter(
        doctor_id=doctor_id, status__in=["BOOKED", "COMPLETED"]
    ).select_related("patient_id")

    if start_date:
        queryset = queryset.filter(appointment_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(appointment_date__lte=end_date)

    events = []
    for log in queryset:
        events.append(
            {
                "id": log.log_id,
                "title": f"Пациент: {log.patient_id.full_name}",
                "start": log.appointment_date.isoformat(),
                "end": (
                    log.appointment_date + timezone.timedelta(minutes=15)
                ).isoformat(),
                "status": log.status,
                "patient_id": log.patient_id.card_number,
                "doctor_id": log.doctor_id_id,
            }
        )

    return Response(events, status=status.HTTP_200_OK)
