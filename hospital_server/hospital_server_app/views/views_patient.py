from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Patient
from ..serializers.action_serializers import PatientRegistrationSerializer
from ..serializers.info_serializers import PatientSerializer, UserWithPatientSerializer
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
    queryset = Patient.objects.select_related("user").all()
    serializer_class = PatientSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]

    search_fields = [
        "patient_name",
        "card_number",
        "insurance",
    ]


@api_view(["PUT", "PATCH", "DELETE", "GET"])
def patient(request, pk):
    try:
        patient = Patient.objects.get(pk=pk)
    except Patient.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = PatientSerializer(patient)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ("PUT", "PATCH"):
        serializer = PatientUpdateSerializer(
            patient, data=request.data, partial=(request.method == "PATCH")
        )
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


@api_view(["POST", "PUT"])
def create_or_update_patient_profile(request):
    user = request.user

    if getattr(user, "role", None) != "PATIENT":
        return Response(
            {
                "detail": "Только пользователи с ролью PATIENT могут создавать профиль пациента."
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    patient_profile = getattr(user, "patient_profile", None)

    if request.method == "POST" and patient_profile:
        return Response(
            {
                "detail": "Профиль пациента уже существует. Используйте PUT для обновления."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = PatientSerializer(
        instance=patient_profile,
        data=request.data,
        partial=(request.method == "PUT"),
    )

    if serializer.is_valid():
        saved_profile = serializer.save(user=user)
        return Response(
            {
                "message": "Профиль пациента успешно сохранен",
                "profile": PatientSerializer(saved_profile).data,
            },
            status=status.HTTP_201_CREATED
            if not patient_profile
            else status.HTTP_200_OK,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
