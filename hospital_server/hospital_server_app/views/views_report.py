from datetime import date

from django.db import DatabaseError, connection
from django.db.models import Count, Q
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Doctor, ReceptionLog
from ..reports import (
    generate_analytics_pdf,
    generate_diagnosis_drug_pdf,
    generate_patient_age_pdf,
    generate_appointment_status_pdf,
    generate_doctor_load_pdf,
)


def parse_report_date(value):
    try:
        parsed_date = date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed_date if parsed_date.isoformat() == value else None


def fetch_report_rows(query, params):
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [column[0].lower() for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


@api_view(["GET"])
def export_doctor_analytics(request, doctor_id):
    if request.user.role == "DOCTOR":
        doctor_profile = getattr(request.user, "doctor_profile", None)
        if not doctor_profile or doctor_profile.doctor_id != doctor_id:
            return Response(
                {"detail": "Вы можете скачивать аналитику только по своему профилю."},
                status=status.HTTP_403_FORBIDDEN,
            )

    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")

    if not start_date or not end_date:
        return Response(
            {
                "detail": "Параметры start_date и end_date обязательны (формат YYYY-MM-DD)."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    parsed_start_date = parse_report_date(start_date)
    parsed_end_date = parse_report_date(end_date)
    if not parsed_start_date or not parsed_end_date:
        return Response(
            {"detail": "Даты должны иметь формат YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if parsed_start_date > parsed_end_date:
        return Response(
            {"detail": "Дата начала не может быть позднее даты окончания."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        doctor = Doctor.objects.get(pk=doctor_id)
    except Doctor.DoesNotExist:
        return Response({"detail": "Врач не найден."}, status=status.HTTP_404_NOT_FOUND)

    receptions = ReceptionLog.objects.filter(
        doctor_id=doctor_id,
        appointment_date__date__gte=start_date,
        appointment_date__date__lte=end_date,
    )

    total_count = receptions.count()
    completed_count = receptions.filter(status="COMPLETED").count()
    cancelled_count = receptions.filter(
        Q(status="CANCELLED") | Q(status="NO_SHOW")
    ).count()

    top_diseases_qs = (
        receptions.filter(status="COMPLETED", disease_id__isnull=False)
        .values("disease_id__disease_code", "disease_id__disease_title")
        .annotate(total=Count("disease_id"))
        .order_by("-total")[:5]
    )

    top_diseases = [
        {
            "code": item["disease_id__disease_code"],
            "title": item["disease_id__disease_title"],
            "count": item["total"],
        }
        for item in top_diseases_qs
    ]

    report_data = {
        "doctor_name": doctor.doctor_name,
        "period": f"{start_date} - {end_date}",
        "total_appointments": total_count,
        "completed_count": completed_count,
        "cancelled_count": cancelled_count,
        "top_diseases": top_diseases,
    }

    pdf_buffer = generate_analytics_pdf(report_data)

    filename = f"analytics_doctor_{doctor_id}_{start_date}_{end_date}.pdf"

    return FileResponse(
        pdf_buffer,
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )


@api_view(["GET"])
def export_diagnosis_drugs_analytics(request):
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    if not date_from or not date_to:
        return Response(
            {
                "error": (
                    "Необходимо указать начальную и конечную даты (формат YYYY-MM-DD)"
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    parsed_date_from = parse_report_date(date_from)
    parsed_date_to = parse_report_date(date_to)
    if not parsed_date_from or not parsed_date_to:
        return Response(
            {"error": "Даты должны быть указаны в формате YYYY-MM-DD"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if parsed_date_from > parsed_date_to:
        return Response(
            {"error": "Начальная дата не может быть позднее конечной"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM GET_DIAGNOSIS_DRUG_REPORT(%s, %s)
                """,
                [parsed_date_from, parsed_date_to],
            )

            columns = [col[0].upper() for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        report_data = {
            "period": (
                f"{parsed_date_from.strftime('%d.%m.%Y')} — "
                f"{parsed_date_to.strftime('%d.%m.%Y')}"
            ),
            "records": rows,
        }
        pdf_buffer = generate_diagnosis_drug_pdf(report_data)

    except DatabaseError as e:
        error_message = str(e).split("CONTEXT:")[0].strip()
        return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

    filename = f"diagnosis_drugs_{date_from}_{date_to}.pdf"
    return FileResponse(
        pdf_buffer,
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )


@api_view(["GET"])
def export_patient_age_analytics(request):
    report_date = request.query_params.get("as_of_date", date.today().isoformat())
    if not parse_report_date(report_date):
        return Response(
            {"error": "Некорректный формат даты"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        rows = fetch_report_rows(
            "SELECT * FROM GET_PATIENT_AGE_REPORT(%s)", [report_date]
        )
    except DatabaseError:
        return Response(
            {"error": "Не удалось сформировать отчет о возрасте пациентов."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    report_data = {"as_of_date": report_date, "rows": rows}

    pdf = generate_patient_age_pdf(report_data)

    return FileResponse(
        pdf,
        as_attachment=True,
        filename="patient_age_report.pdf",
        content_type="application/pdf",
    )


@api_view(["GET"])
def export_appointments_status_analytics(request):
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    if not date_from or not date_to:
        return Response(
            {"error": "Необходимо указать date_from и date_to"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    parsed_date_from = parse_report_date(date_from)
    parsed_date_to = parse_report_date(date_to)
    if not parsed_date_from or not parsed_date_to:
        return Response(
            {"error": "Даты должны иметь формат YYYY-MM-DD"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if parsed_date_from > parsed_date_to:
        return Response(
            {"error": "Начальная дата позже конечной"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        rows = fetch_report_rows(
            "SELECT * FROM GET_APPOINTMENT_STATUS_REPORT(%s, %s)",
            [parsed_date_from, parsed_date_to],
        )
    except DatabaseError:
        return Response(
            {"error": "Не удалось сформировать отчет о статусах записей."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    report_data = {"date_from": date_from, "date_to": date_to, "rows": rows}

    pdf = generate_appointment_status_pdf(report_data)

    return FileResponse(
        pdf,
        as_attachment=True,
        filename="appointment_status_report.pdf",
        content_type="application/pdf",
    )


@api_view(["GET"])
def export_doctor_load_analytics(request):
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    if not date_from or not date_to:
        return Response(
            {"error": "Необходимо указать date_from и date_to"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    parsed_date_from = parse_report_date(date_from)
    parsed_date_to = parse_report_date(date_to)
    if not parsed_date_from or not parsed_date_to:
        return Response(
            {"error": "Даты должны иметь формат YYYY-MM-DD"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if parsed_date_from > parsed_date_to:
        return Response(
            {"error": "Начальная дата позже конечной"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        rows = fetch_report_rows(
            "SELECT * FROM GET_DOCTOR_LOAD_REPORT(%s, %s)",
            [parsed_date_from, parsed_date_to],
        )
    except DatabaseError:
        return Response(
            {"error": "Не удалось сформировать отчет о загрузке врачей."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    report_data = {"date_from": date_from, "date_to": date_to, "rows": rows}

    pdf = generate_doctor_load_pdf(report_data)

    return FileResponse(
        pdf,
        as_attachment=True,
        filename="doctor_load_report.pdf",
        content_type="application/pdf",
    )
