from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, extend_schema_view
import django_filters

from apps.audit.models import AuditEvent
from apps.audit.serializers import AuditEventSerializer
from apps.audit.filters import AuditEventFilter
from apps.accounts.models import UserRole


class IsAdmin(IsAuthenticated):
    """Permission : ADMIN uniquement."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return getattr(request.user, "role", None) == UserRole.ADMIN


class AuditPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


@extend_schema_view(
    list=extend_schema(
        summary="Listar eventos de auditoria",
        description="Retorna todos os eventos de auditoria. Acesso restrito a administradores.",
        tags=["audit"],
    ),
    retrieve=extend_schema(
        summary="Detalhe de um evento de auditoria",
        tags=["audit"],
    ),
)
class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet readonly pour les événements d'audit. Admin only."""

    queryset = AuditEvent.objects.select_related("user").all()
    serializer_class = AuditEventSerializer
    permission_classes = [IsAdmin]
    pagination_class = AuditPagination
    filterset_class = AuditEventFilter
    filter_backends = [
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["action", "resource_repr", "user_email"]
    ordering_fields = ["timestamp"]
    ordering = ["-timestamp"]
