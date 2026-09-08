from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Room
from ..serializers.info_serializers import RoomSerializer
from ..serializers.update_serializers import RoomUpdateSerializer


@api_view(["GET", "POST"])
def rooms(request):
    if request.method == "GET":
        room = Room.objects.all()
        serializer = RoomSerializer(room, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    if request.method == "POST":
        serializer = RoomSerializer(data=request.data)
        if serializer.is_valid():
            return Response(
                {"Добавлен кабинет": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT", "PATCH", "DELETE"])
def room(request, pk):
    try:
        room = Room.objects.get(pk=pk)
    except Room.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method in ("PUT", "PATCH"):
        serializer = RoomUpdateSerializer(room, data=request.data, partitial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Обновлена информация о кабинете": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        room.delete()
        return Response("Кабинет удален", status=status.HTTP_204_NO_CONTENT)
