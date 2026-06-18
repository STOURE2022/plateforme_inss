import time

from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.filters import OrderingFilter

from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import IsAgentOrAdmin
from apps.cards.exceptions import HealthCardVerificationError
from apps.cards.models import CardStatus
from apps.cards.services.qr_service import QRTokenService

from .models import VerificationLog, VerificationResult
from .serializers import (
    VerifyRequestSerializer,
    VerificationLogSerializer,
)
from .filters import VerificationLogFilter
from .throttles import VerifyCardThrottle, VerifyCardAuthThrottle


def _get_client_ip(request) -> str | None:
    """Extrai o IP real do cliente a partir dos headers da requisição."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # O primeiro IP da lista é o IP real do cliente
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class VerifyCardView(APIView):
    """
    Endpoint público (autenticação opcional) para verificar um QR code.

    POST /api/v1/verify/
    {
        "token": "<jwt_token_do_qr_code>"
    }

    Retorna 200 se válido, 400 se inválido/expirado/revogado.
    Sempre cria um VerificationLog com o resultado.
    """
    permission_classes = [AllowAny]
    throttle_classes = [VerifyCardThrottle, VerifyCardAuthThrottle]

    def post(self, request, *args, **kwargs):
        start_time = time.monotonic()

        # Valida o corpo da requisição
        serializer = VerifyRequestSerializer(data=request.data)
        if not serializer.is_valid():
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            VerificationLog.objects.create(
                verifier=request.user if request.user.is_authenticated else None,
                verifier_ip=_get_client_ip(request),
                verifier_role=request.user.role if request.user.is_authenticated else "",
                result=VerificationResult.INVALID,
                failure_reason="Token ausente ou inválido no corpo da requisição.",
                response_ms=elapsed_ms,
            )
            return Response(
                {
                    "valid": False,
                    "error": "O campo 'token' é obrigatório.",
                    "error_code": "INVALID",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = serializer.validated_data["token"]
        verifier = request.user if request.user.is_authenticated else None
        verifier_ip = _get_client_ip(request)
        verifier_role = request.user.role if request.user.is_authenticated else ""

        # Inicializa QRTokenService sem chaves (usará as chaves de ficheiro configuradas)
        qr_service = QRTokenService()

        card = None
        card_number = ""
        token_jti = ""

        try:
            payload = qr_service.verify_token(token)
            card_number = payload.get("card_number", "")
            token_jti = payload.get("jti", "")

            # Obtém o cartão
            from apps.cards.models import HealthCard
            try:
                card = HealthCard.objects.select_related("affiliate").get(
                    card_number=card_number
                )
            except HealthCard.DoesNotExist:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                VerificationLog.objects.create(
                    verifier=verifier,
                    verifier_ip=verifier_ip,
                    verifier_role=verifier_role,
                    card_number=card_number,
                    token_jti=token_jti,
                    result=VerificationResult.INVALID,
                    failure_reason="Cartão não encontrado.",
                    response_ms=elapsed_ms,
                )
                return Response(
                    {
                        "valid": False,
                        "error": "Cartão não encontrado.",
                        "error_code": "INVALID",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verifica se o cartão está válido (ACTIVE + não expirado)
            if not card.is_valid():
                elapsed_ms = int((time.monotonic() - start_time) * 1000)

                if card.status == CardStatus.SUSPENDED:
                    error_msg = "Cartão suspenso."
                    error_code = VerificationResult.FAILURE
                elif card.status == CardStatus.CANCELLED:
                    error_msg = "Cartão cancelado."
                    error_code = VerificationResult.REVOKED
                elif card.status == CardStatus.EXPIRED:
                    error_msg = "Cartão expirado."
                    error_code = VerificationResult.EXPIRED
                else:
                    # Cartão ACTIVE mas data de validade ultrapassada
                    error_msg = "Cartão expirado."
                    error_code = VerificationResult.EXPIRED

                VerificationLog.objects.create(
                    verifier=verifier,
                    verifier_ip=verifier_ip,
                    verifier_role=verifier_role,
                    card=card,
                    card_number=card.card_number,
                    token_jti=token_jti,
                    result=error_code,
                    failure_reason=error_msg,
                    response_ms=elapsed_ms,
                )
                return Response(
                    {
                        "valid": False,
                        "error": error_msg,
                        "error_code": error_code,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Sucesso
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            VerificationLog.objects.create(
                verifier=verifier,
                verifier_ip=verifier_ip,
                verifier_role=verifier_role,
                card=card,
                card_number=card.card_number,
                token_jti=token_jti,
                result=VerificationResult.SUCCESS,
                response_ms=elapsed_ms,
            )

            response_data = {
                "valid": True,
                "card_number": card.card_number,
                "status": card.status,
                "affiliate_name": card.affiliate.full_name,
                "expiry_date": card.expiry_date,
                "verified_at": timezone.now(),
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except HealthCardVerificationError as exc:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            error_str = str(exc)

            # Determina o código de erro a partir da mensagem
            if "expirado" in error_str.lower():
                error_code = VerificationResult.EXPIRED
                user_message = "Token expirado."
            elif "revogado" in error_str.lower():
                error_code = VerificationResult.REVOKED
                user_message = "Token revogado."
            else:
                error_code = VerificationResult.INVALID
                user_message = "Token inválido."

            VerificationLog.objects.create(
                verifier=verifier,
                verifier_ip=verifier_ip,
                verifier_role=verifier_role,
                card=card,
                card_number=card_number,
                token_jti=token_jti,
                result=error_code,
                failure_reason=error_str,
                response_ms=elapsed_ms,
            )
            return Response(
                {
                    "valid": False,
                    "error": user_message,
                    "error_code": error_code,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class VerificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Leitura apenas dos logs de verificação.
    - list : IsAgent ou IsAdmin (com filtros)
    - retrieve : IsAgent ou IsAdmin
    """
    serializer_class = VerificationLogSerializer
    permission_classes = [IsAgentOrAdmin]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = VerificationLogFilter
    ordering_fields = ["verified_at", "result"]
    ordering = ["-verified_at"]

    def get_queryset(self):
        return VerificationLog.objects.select_related("verifier", "card").all()


class VerificationStatsView(APIView):
    """
    GET /api/v1/verify/stats/
    Acessível: IsAgent ou IsAdmin

    Retorna estatísticas agregadas de verificações.
    """
    permission_classes = [IsAgentOrAdmin]
    throttle_classes = []

    def get(self, request, *args, **kwargs):
        today = timezone.now().date()
        today_start = timezone.datetime(today.year, today.month, today.day, tzinfo=timezone.get_current_timezone())
        today_end = today_start + timedelta(days=1)

        # Estatísticas do dia
        today_qs = VerificationLog.objects.filter(
            verified_at__gte=today_start,
            verified_at__lt=today_end,
        )
        total_today = today_qs.count()
        success_today = today_qs.filter(result=VerificationResult.SUCCESS).count()
        failure_today = total_today - success_today
        success_rate_today = round((success_today / total_today * 100), 1) if total_today > 0 else 0.0

        # Top motivos de falha hoje
        top_failures = (
            today_qs.exclude(result=VerificationResult.SUCCESS)
            .values("result")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        top_failure_reasons = [
            {"reason": item["result"], "count": item["count"]}
            for item in top_failures
        ]

        # Verificações por dia nos últimos 7 dias
        seven_days_ago = today_start - timedelta(days=6)
        daily_data = []
        for i in range(7):
            day_start = seven_days_ago + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            day_qs = VerificationLog.objects.filter(
                verified_at__gte=day_start,
                verified_at__lt=day_end,
            )
            day_total = day_qs.count()
            day_success = day_qs.filter(result=VerificationResult.SUCCESS).count()
            daily_data.append({
                "date": day_start.date().isoformat(),
                "total": day_total,
                "success": day_success,
            })

        return Response(
            {
                "total_today": total_today,
                "success_today": success_today,
                "failure_today": failure_today,
                "success_rate_today": success_rate_today,
                "top_failure_reasons": top_failure_reasons,
                "verifications_last_7_days": daily_data,
            },
            status=status.HTTP_200_OK,
        )
