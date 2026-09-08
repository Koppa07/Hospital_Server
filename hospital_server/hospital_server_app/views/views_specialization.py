from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Specialization
from ..serializers.action_serializers import SpecializationSerializer
from ..serializers.update_serializers import SpecializationUpdateSerializer


@api_view(["GET", "POST"])
def specializations(request):
    if request.method == "GET":
        specialization = Specialization.objects.all()
        serializer = SpecializationSerializer(specialization, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    if request.method == "POST":
        serializer = SpecializationSerializer(data=request.data)
        if serializer.is_valid():
            return Response(
                {"Добавлена специализация": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT", "PATCH", "DELETE"])
def specialization(request, pk):
    try:
        spec = Specialization.objects.get(pk=pk)
    except Specialization.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method in ("PUT", "PATCH"):
        serializer = SpecializationUpdateSerializer(
            spec, data=request.data, partitial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Обновлена информация о специализации": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        spec.delete()
        return Response("Специализация удалена", status=status.HTTP_204_NO_CONTENT)
