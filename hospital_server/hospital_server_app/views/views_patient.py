from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Patient, ReceptionLog
from ..serializers.action_serializers import PatientRegistrationSerializer
from ..serializers.info_serializers import MedicalHistorySerializer, PatientSerializer
from ..serializers.update_serializers import PatientUpdateSerializer

User = get_user_model()


@api_view(["POST"])
def register_patient(request):
    serializer = PatientRegistrationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT register_new_patient(%s, %s, %s, %s);",
                [
                    data["patient_name"],
                    data["birth_date"],
                    data["address"],
                    data["insurance"],
                ],
            )

            new_card_number = cursor.fetchone()[0]

        return Response(
            {
                "message": "Пациент успешно зарегистрирован",
                "card_number": new_card_number,
            },
            status=status.HTTP_201_CREATED,
        )
    except DatabaseError as e:
        error_message = str(e).split("CONTEXT:")[0].strip()
        return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)


class PatientListView(generics.ListAPIView):
    queryset = Patient.objects.select_related(
        "patient_name", "insurance", "card_number"
    ).all()
    serializer_class = PatientSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]

    search_fields = [
        "patient_name",
        "card_number",
        "insurance",
    ]


@api_view(["PUT", "PATCH", "DELETE"])
def patient(request, pk):
    try:
        patient = Patient.objects.get(pk=pk)
    except Patient.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method in ("PUT", "PATCH"):
        serializer = PatientUpdateSerializer(patient, data=request.data, partitial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Обновлена информация о пациенте": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        patient.delete()
        return Response(
            "Сведения о пациенте удалены", status=status.HTTP_204_NO_CONTENT
        )


@api_view(["GET"])
def medical_history(request, patient_id):
    if request.user.role == "PATIENT":
        patient_profile = getattr(request.user, "patient_profile", None)
        if not patient_profile or patient_profile.card_number != patient_id:
            return Response(
                {
                    "detail": "У вас нет прав для просмотра истории болезни этого пациента."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

    completed_receptions = (
        ReceptionLog.objects.filter(patient_id=patient_id, status="COMPLETED")
        .select_related("doctor_id__spec", "disease_id", "pres_id")
        .prefetch_related("pres_id__prescriptiondrug_set__drug_id")
        .order_by("-appointment_date")
    )

    serializer = MedicalHistorySerializer(completed_receptions, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
