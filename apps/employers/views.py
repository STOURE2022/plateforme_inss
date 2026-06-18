from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import IsAgentOrAdmin, IsAdminRole, IsEmployer
from .models import Employer
from .serializers import EmployerSerializer, EmployerCreateSerializer
from .filters import EmployerFilter


class EmployerViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD para empregadores.

    - list/retrieve: Agente ou Admin
    - create/update: Agente ou Admin (registered_by = request.user)
    - destroy: Admin apenas
    - me/: Empregador vê a sua própria ficha
    """

    queryset = Employer.objects.select_related("user", "registered_by").all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmployerFilter

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return EmployerCreateSerializer
        return EmployerSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdminRole()]
        if self.action == "me":
            return [IsEmployer()]
        return [IsAgentOrAdmin()]

    def perform_create(self, serializer):
        serializer.save(registered_by=self.request.user)

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """GET /api/v1/employers/me/ — Empregador vê a sua própria ficha."""
        try:
            employer = Employer.objects.select_related("user", "registered_by").get(user=request.user)
        except Employer.DoesNotExist:
            return Response(
                {"detail": "Perfil de empregador não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = EmployerSerializer(employer, context={"request": request})
        return Response(serializer.data)
