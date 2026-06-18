from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import LoginSerializer, MFAVerifySerializer, UserSerializer
from .services import verify_mfa_code


class LoginThrottle(AnonRateThrottle):
    rate = "5/min"
    scope = "login"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def login_view(request: Request) -> Response:
    """
    POST /api/v1/auth/login/
    Returns JWT tokens. If MFA is enabled, returns mfa_required=true without tokens.
    """
    serializer = LoginSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    user: User = serializer.validated_data["user"]

    if user.mfa_enabled:
        # Store user id in a short-lived pre-auth token
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "mfa_required": True,
                "pre_auth_token": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "mfa_required": False,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mfa_verify_view(request: Request) -> Response:
    """
    POST /api/v1/auth/mfa/verify/
    Verify TOTP code. Caller must send the pre_auth_token as Bearer.
    Returns full JWT tokens on success.
    """
    serializer = MFAVerifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    code: str = serializer.validated_data["code"]
    user: User = request.user  # type: ignore[assignment]

    if not verify_mfa_code(user, code):
        return Response({"detail": "Código MFA inválido."}, status=status.HTTP_400_BAD_REQUEST)

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request: Request) -> Response:
    """GET /api/v1/auth/me/ — current user info."""
    return Response(UserSerializer(request.user).data)
