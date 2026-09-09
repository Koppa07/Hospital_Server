from django.db.models import Count, Q
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..reports import generate_analytics_pdf
from ..models import Doctor, ReceptionLog


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
