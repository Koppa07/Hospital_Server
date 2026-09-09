from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Doctor
from ..serializers.action_serializers import DoctorRegistrationSerializer
from ..serializers.update_serializers import DoctorUpdateSerializer
from ..serializers.info_serializers import DoctorProfileSerializer


class DoctorListView(generics.ListAPIView):
    queryset = Doctor.objects.select_related("spec", "dep", "room").all()
    serializer_class = DoctorProfileSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]

    filterset_fields = ["spec", "dep"]

    search_fields = [
        "doctor_name",
        "spec__spec_title",
        "dep__dep_title",
    ]


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


@api_view(["PUT", "PATCH", "DELETE"])
def doctor(request, pk):
    try:
        doctor = Doctor.objects.get(pk=pk)
    except Doctor.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method in ("PUT", "PATCH"):
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
