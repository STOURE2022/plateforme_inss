from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Max
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import IsAgentOrAdmin, IsAdminRole
from apps.accounts.models import UserRole
from .models import Contribution
from .serializers import ContributionSerializer, ContributionCreateSerializer
from .filters import ContributionFilter


class ContributionViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD para contribuições.

    - list: Agente ou Admin (filtros por afiliado, empregador, ano, mês, estado)
    - create: Agente ou Admin
    - retrieve: Agente, Admin ou o próprio afiliado
    - update/partial_update: Agente ou Admin
    - destroy: Admin apenas
    - {affiliate_id}/summary/: Resumo das contribuições de um afiliado
    """

    filter_backends = [DjangoFilterBackend]
    filterset_class = ContributionFilter

    def get_queryset(self):
        qs = Contribution.objects.select_related(
            "affiliate", "employer", "created_by"
        ).all()

        # Cidadão só vê as suas próprias contribuições
        user = self.request.user
        if user.role == UserRole.CITIZEN:
            try:
                qs = qs.filter(affiliate__user=user)
            except Exception:
                return Contribution.objects.none()

        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ContributionCreateSerializer
        return ContributionSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdminRole()]
        if self.action == "retrieve":
            # Agente, Admin ou o próprio afiliado
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated()]
        return [IsAgentOrAdmin()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"], url_path=r"affiliate/(?P<affiliate_id>\d+)/summary")
    def summary(self, request, affiliate_id=None):
        """
        GET /api/v1/contributions/affiliate/{affiliate_id}/summary/
        Resumo das contribuições de um afiliado.
        """
        from apps.affiliates.models import Affiliate
        from django.shortcuts import get_object_or_404

        affiliate = get_object_or_404(Affiliate, pk=affiliate_id)

        # Verificar permissão: agente/admin ou o próprio afiliado
        user = request.user
        if user.role == UserRole.CITIZEN:
            if not hasattr(user, "affiliate") or user.affiliate.pk != affiliate.pk:
                return Response(
                    {"detail": "Sem permissão para ver este resumo."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        qs = Contribution.objects.filter(affiliate=affiliate)
        agg = qs.aggregate(
            total_contributions=Sum("total_amount"),
            months_contributed=Count("id"),
            last_contribution_date=Max("payment_date"),
        )
        last_contribution = qs.order_by("-period_year", "-period_month").first()

        return Response(
            {
                "affiliate_id": affiliate.pk,
                "affiliate_name": affiliate.full_name,
                "niss": affiliate.niss,
                "total_contributions": agg["total_contributions"] or 0,
                "months_contributed": agg["months_contributed"],
                "last_contribution_date": agg["last_contribution_date"],
                "last_period": (
                    f"{last_contribution.period_year}/{last_contribution.period_month:02d}"
                    if last_contribution
                    else None
                ),
            }
        )
