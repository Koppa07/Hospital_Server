from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Department
from ..serializers.info_serializers import DepartmentSerializer
from ..serializers.update_serializers import DepartmentUpdateSerializer


@api_view(["GET", "POST"])
def departments(request):
    if request.method == "GET":
        department = Department.objects.all()
        serializer = DepartmentSerializer(department, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    if request.method == "POST":
        serializer = DepartmentUpdateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Добавлено отделение": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT", "PATCH", "DELETE"])
def department(request, pk):
    try:
        dep = Department.objects.get(pk=pk)
    except Department.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method in ("PUT", "PATCH"):
        serializer = DepartmentUpdateSerializer(
            dep, data=request.data, partial=(request.method == "PATCH")
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Обновлена информация об отделении": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        dep.delete()
        return Response(
            "Информация об отделении удалена", status=status.HTTP_204_NO_CONTENT
        )
