from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import IsAgentOrAdmin, IsAdminRole, IsCitizen
from .models import Affiliate, Dependent
from .serializers import AffiliateSerializer, AffiliateCreateSerializer, DependentSerializer
from .filters import AffiliateFilter


class AffiliateViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD para afiliados.

    - list/retrieve: Agente ou Admin
    - create/update: Agente ou Admin
    - destroy: Admin apenas
    - me/: Cidadão autenticado vê o seu próprio perfil
    - {id}/dependents/: Agente ou Admin
    """

    queryset = Affiliate.objects.select_related("user").prefetch_related("dependents").all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = AffiliateFilter

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return AffiliateCreateSerializer
        return AffiliateSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdminRole()]
        if self.action == "me":
            return [IsCitizen()]
        return [IsAgentOrAdmin()]

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """GET /api/v1/affiliates/me/ — Cidadão vê o seu próprio perfil."""
        try:
            affiliate = Affiliate.objects.select_related("user").prefetch_related("dependents").get(
                user=request.user
            )
        except Affiliate.DoesNotExist:
            return Response(
                {"detail": "Perfil de afiliado não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = AffiliateSerializer(affiliate, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"], url_path="dependents")
    def dependents(self, request, pk=None):
        """
        GET  /api/v1/affiliates/{id}/dependents/ — listar dependentes
        POST /api/v1/affiliates/{id}/dependents/ — adicionar dependente
        """
        affiliate = self.get_object()

        if request.method == "GET":
            deps = affiliate.dependents.all()
            serializer = DependentSerializer(deps, many=True, context={"request": request})
            return Response(serializer.data)

        # POST
        serializer = DependentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(affiliate=affiliate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DependentViewSet(viewsets.ModelViewSet):
    """ViewSet CRUD para dependentes (sempre via afiliado pai)."""

    serializer_class = DependentSerializer

    def get_queryset(self):
        return Dependent.objects.filter(affiliate_id=self.kwargs.get("affiliate_pk")).select_related("affiliate")

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdminRole()]
        return [IsAgentOrAdmin()]

    def perform_create(self, serializer):
        from django.shortcuts import get_object_or_404
        affiliate = get_object_or_404(Affiliate, pk=self.kwargs.get("affiliate_pk"))
        serializer.save(affiliate=affiliate)
