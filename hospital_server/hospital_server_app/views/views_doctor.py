from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Doctor
from ..serializers.action_serializers import DoctorRegistrationSerializer
from ..serializers.info_serializers import (
    DoctorProfileSerializer,
    UserWithDoctorSerializer,
)
from ..serializers.update_serializers import DoctorUpdateSerializer

User = get_user_model()


class DoctorListView(generics.ListAPIView):
    queryset = Doctor.objects.select_related("user").all()
    serializer_class = DoctorProfileSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]

    filterset_fields = {
        "doctor_name": ["icontains"],
        "spec__spec_title": ["icontains"],
        "dep__dep_title": ["icontains"],
    }


@api_view(["POST"])
def doctors(request):
    serializer = DoctorRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        doctor = serializer.save()
        response_serializer = DoctorProfileSerializer(doctor)
        return Response(
            {"Добавлен врач": response_serializer.data},
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT", "PATCH", "DELETE", "GET"])
def doctor(request, pk):
    try:
        doctor = Doctor.objects.get(pk=pk)
    except Doctor.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = DoctorProfileSerializer(doctor)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ("PUT", "PATCH"):
        serializer = DoctorUpdateSerializer(
            doctor, data=request.data, partial=(request.method == "PATCH")
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Обновлена информация о враче": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        doctor.delete()
        return Response("Сведения о враче удалены", status=status.HTTP_204_NO_CONTENT)


@api_view(["POST", "PUT", "GET"])
def create_or_update_doctor_profile(request):
    user = request.user

    if getattr(user, "role", None) != "DOCTOR":
        return Response(
            {"detail": "Доступ разрешен только врачам."},
            status=status.HTTP_403_FORBIDDEN,
        )

    doctor_profile = getattr(user, "doctor_profile", None)

    if request.method == "GET":
        if not doctor_profile:
            return Response(
                {"detail": "Профиль врача не заполнен."},
                status=404,
            )

        return Response(DoctorProfileSerializer(doctor_profile).data)

    if request.method == "POST" and doctor_profile:
        return Response(
            {"detail": "Профиль врача уже существует. Используйте PUT для обновления."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = DoctorProfileSerializer(
        instance=doctor_profile,
        data=request.data,
        partial=(request.method == "PUT"),
    )

    if serializer.is_valid():
        saved_profile = serializer.save(user=user)
        return Response(
            {
                "message": "Профиль врача успешно сохранен",
                "profile": DoctorProfileSerializer(saved_profile).data,
            },
            status=status.HTTP_201_CREATED
            if not doctor_profile
            else status.HTTP_200_OK,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
