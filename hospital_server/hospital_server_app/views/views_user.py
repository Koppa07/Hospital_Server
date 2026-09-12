from django.contrib.auth import get_user_model
from hospital_server_app.models import *
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from ..serializers.info_serializers import UserSerializer

User = get_user_model()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    user = request.user

    if user.role == "PATIENT" and hasattr(user, "patient_profile"):
        patient = user.patient_profile
        return Response(
            {
                "user_id": user.id,
                "username": user.username,
                "card_number": patient.card_number,
                "patient_name": patient.patient_name,
                "birth_date": patient.birth_date,
                "insurance": patient.insurance,
                "address": patient.address,
            }
        )

    return Response(
        {"detail": "Профиль не найден для текущего аккаунта."},
        status=status.HTTP_404_NOT_FOUND,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {"detail": "Имя пользователя и пароль обязательны."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.filter(username=username).first()

    if user is None or not user.check_password(password):
        return Response(
            {"detail": "Неверное имя пользователя или пароль."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    refresh = RefreshToken.for_user(user)
    serializer = UserSerializer(instance=user)
    return Response(
        {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Refresh токен не предоставлен."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response(
            {"detail": "Успешный выход из системы."}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"detail": "Недействительный токен или ошибка при выходе."},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
def get_users(request):
    user = User.objects.all()

    serializer = UserSerializer(user, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
