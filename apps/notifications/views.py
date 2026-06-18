from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Listar as minhas notificações",
        description="Retorna as notificações do utilizador autenticado, não lidas em primeiro.",
        tags=["notifications"],
    ),
    retrieve=extend_schema(
        summary="Detalhe de uma notificação",
        tags=["notifications"],
    ),
    partial_update=extend_schema(
        summary="Marcar notificação como lida",
        tags=["notifications"],
    ),
    destroy=extend_schema(
        summary="Eliminar notificação",
        tags=["notifications"],
    ),
)
class NotificationViewSet(viewsets.ModelViewSet):
    """
    API de notificações.
    Cada utilizador vê apenas as suas próprias notificações.
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).order_by("is_read", "-created_at")

    def partial_update(self, request, *args, **kwargs):
        """PATCH : marquer comme lue."""
        notification = self.get_object()
        if request.data.get("is_read", False):
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @extend_schema(
        summary="Número de notificações não lidas",
        tags=["notifications"],
        responses={200: {"type": "object", "properties": {"count": {"type": "integer"}}}},
    )
    @action(detail=False, methods=["get"], url_path="unread_count")
    def unread_count(self, request):
        """GET /api/v1/notifications/unread_count/ → {"count": N}"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"count": count})
