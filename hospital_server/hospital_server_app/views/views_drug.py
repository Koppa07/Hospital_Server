from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Drug
from ..serializers.info_serializers import DrugSerializer
from ..serializers.update_serializers import DrugUpdateSerializer


@api_view(["GET", "POST"])
def drugs(request):
    if request.method == "GET":
        drug = Drug.objects.all()
        serializer = DrugSerializer(drug, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        serializer = DrugUpdateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Добавлен медикамент": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT", "PATCH", "DELETE"])
def drug(request, pk):
    try:
        drug = Drug.objects.get(pk=pk)
    except Drug.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method in ("PUT", "PATCH"):
        serializer = DrugUpdateSerializer(
            drug, data=request.data, partial=(request.method == "PATCH")
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Обновлена информация о медикаменте": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        drug.delete()
        return Response(
            "Информация о медикаменте удалена", status=status.HTTP_204_NO_CONTENT
        )
