from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Disease
from ..serializers.info_serializers import DiseaseSerializer


@api_view(["GET"])
def diseases(request):
    if request.method == "GET":
        disease = Disease.objects.all()
        serializer = DiseaseSerializer(disease, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def disease(request, pk):
    if request.method == "GET":
        disease = Disease.objects.get(pk=pk)
        serializer = DiseaseSerializer(disease, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
