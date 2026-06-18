from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsAgentOrAdmin, IsAdminRole
from apps.cards.models import HealthCard
from apps.cards.serializers import HealthCardSerializer, HealthCardCreateSerializer
from apps.cards.services.qr_service import QRTokenService
from apps.cards.services.pdf_service import PDFService
from apps.cards.tasks import generate_card_pdf_task


class HealthCardViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestão de cartões de saúde.

    - list/create : agente ou admin
    - retrieve : agente, admin, ou o próprio cidadão
    - update/partial_update : agente ou admin
    - destroy : admin apenas
    """

    queryset = HealthCard.objects.select_related("affiliate__user", "created_by").all()

    def get_serializer_class(self):
        if self.action == "create":
            return HealthCardCreateSerializer
        return HealthCardSerializer

    def get_permissions(self):
        if self.action in ("list", "create", "update", "partial_update"):
            return [IsAgentOrAdmin()]
        if self.action == "destroy":
            return [IsAdminRole()]
        if self.action in ("retrieve", "qr_code", "download_pdf"):
            # Agentes, admins e o cidadão proprietário
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        # Cidadão só vê o seu próprio cartão
        if user.is_citizen:
            return HealthCard.objects.filter(affiliate__user=user).select_related(
                "affiliate__user", "created_by"
            )
        return super().get_queryset()

    def perform_create(self, serializer):
        card = serializer.save(created_by=self.request.user)
        # Dispara geração de PDF de forma assíncrona
        generate_card_pdf_task.delay(card.pk)

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        user = request.user
        # Cidadão só pode aceder ao seu próprio cartão
        if user.is_citizen and obj.affiliate.user != user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Não tem permissão para aceder a este cartão.")

    # ------------------------------------------------------------------
    # Actions personalizadas
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get"], url_path="qr")
    def qr_code(self, request, pk=None):
        """Retorna a imagem QR PNG do token JWS atual (gera se necessário)."""
        card = self.get_object()
        service = QRTokenService()
        token = service.generate_token(card)
        qr_bytes = service.generate_qr_image(token)
        return HttpResponse(qr_bytes, content_type="image/png")

    @action(detail=True, methods=["get"], url_path="pdf")
    def download_pdf(self, request, pk=None):
        """Descarrega ou regenera o PDF do cartão."""
        card = self.get_object()
        pdf_service = PDFService()

        if not card.pdf_file:
            pdf_service.save_card_pdf(card)

        pdf_bytes = pdf_service.generate_card_pdf(card)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{card.card_number}.pdf"'
        )
        return response

    @action(detail=False, methods=["get"], url_path="me")
    def my_card(self, request):
        """O cidadão consulta o seu próprio cartão."""
        try:
            card = HealthCard.objects.get(affiliate__user=request.user)
        except HealthCard.DoesNotExist:
            return Response(
                {"detalhe": "Não possui cartão de saúde."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = HealthCardSerializer(card)
        return Response(serializer.data)
