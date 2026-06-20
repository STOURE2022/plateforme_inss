from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import IsAgentOrAdmin
from apps.accounts.models import UserRole
from apps.notifications.services import NotificationService
from apps.notifications.models import NotificationType

from .models import (
    Claim,
    ClaimMessage,
    ClaimDocument,
    ClaimStatusHistory,
    ClaimStatus,
    ClaimPriority,
    VALID_TRANSITIONS,
)
from .serializers import (
    ClaimListSerializer,
    ClaimDetailSerializer,
    ClaimCreateSerializer,
    ClaimMessageSerializer,
    ClaimDocumentSerializer,
    ClaimAgentActionSerializer,
)


class ClaimViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Claims (Réclamations / Litiges).
    - Citizens: create, list/retrieve their own claims, add public messages, upload docs
    - Agents/Admins: list all, retrieve any, update status, add internal/public messages
    """

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "claim_type", "priority"]

    def get_queryset(self):
        qs = Claim.objects.select_related(
            "filed_by",
            "affiliate",
            "employer",
            "assigned_to",
        ).prefetch_related("messages", "documents", "history")

        user = self.request.user
        if user.role == UserRole.CITIZEN:
            qs = qs.filter(filed_by=user)
        return qs.order_by("-submitted_at")

    def get_serializer_class(self):
        if self.action == "list":
            return ClaimListSerializer
        if self.action == "create":
            return ClaimCreateSerializer
        if self.action in (
            "take_charge", "resolve", "reject", "request_info", "escalate"
        ):
            return ClaimAgentActionSerializer
        if self.action == "add_message":
            return ClaimMessageSerializer
        if self.action == "upload_document":
            return ClaimDocumentSerializer
        return ClaimDetailSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        if self.action in ("create", "add_message", "upload_document", "rate_satisfaction"):
            return [IsAuthenticated()]
        return [IsAgentOrAdmin()]

    def perform_create(self, serializer):
        user = self.request.user
        affiliate = None
        employer = None

        if user.role == UserRole.CITIZEN:
            try:
                affiliate = user.affiliate
            except Exception:
                pass
        elif user.role == UserRole.EMPLOYER:
            try:
                employer = user.employer
            except Exception:
                pass

        claim = serializer.save(
            filed_by=user,
            affiliate=affiliate,
            employer=employer,
            status=ClaimStatus.OPEN,
        )

        ClaimStatusHistory.objects.create(
            claim=claim,
            old_status="",
            new_status=ClaimStatus.OPEN,
            changed_by=user,
            comment="Reclamação submetida.",
        )

    def _transition(self, request, pk, new_status, extra_fields=None):
        """Helper to perform a validated status transition."""
        obj = get_object_or_404(Claim, pk=pk)

        if not obj.can_transition_to(new_status):
            return Response(
                {"detail": f"Transição inválida: {obj.get_status_display()} → {dict(ClaimStatus.choices).get(new_status, new_status)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ClaimAgentActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        old_status = obj.status
        obj.status = new_status

        if new_status == ClaimStatus.UNDER_REVIEW and old_status == ClaimStatus.OPEN:
            obj.assigned_to = request.user
            obj.review_started_at = timezone.now()
        if new_status in (ClaimStatus.RESOLVED, ClaimStatus.REJECTED):
            obj.resolved_at = timezone.now()
        if new_status == ClaimStatus.RESOLVED:
            obj.resolution_notes = data.get("resolution_notes", "")
        if new_status == ClaimStatus.REJECTED:
            obj.rejection_reason = data.get("rejection_reason", "")

        if extra_fields:
            for k, v in extra_fields.items():
                setattr(obj, k, v)

        obj.save()

        ClaimStatusHistory.objects.create(
            claim=obj,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            comment=data.get("comment", ""),
        )

        # Notify the filer
        self._notify_filer(obj, new_status, request)

        serializer_out = ClaimDetailSerializer(obj, context={"request": request})
        return Response(serializer_out.data)

    def _notify_filer(self, obj, new_status, request):
        """Send notification to the claim filer on status change."""
        status_messages = {
            ClaimStatus.UNDER_REVIEW: (
                "Reclamação em análise",
                f"A sua reclamação {obj.reference} está a ser analisada por um agente INSS.",
                NotificationType.INFO,
            ),
            ClaimStatus.RESOLVED: (
                "Reclamação resolvida",
                f"A sua reclamação {obj.reference} foi resolvida. {obj.resolution_notes}",
                NotificationType.SUCCESS,
            ),
            ClaimStatus.REJECTED: (
                "Reclamação rejeitada",
                f"A sua reclamação {obj.reference} foi rejeitada. Motivo: {obj.rejection_reason}",
                NotificationType.ERROR,
            ),
            ClaimStatus.ADDITIONAL_INFO: (
                "Informação adicional solicitada",
                f"O agente INSS solicita informação adicional para a sua reclamação {obj.reference}.",
                NotificationType.WARNING,
            ),
            ClaimStatus.ESCALATED: (
                "Reclamação escalada",
                f"A sua reclamação {obj.reference} foi escalada para supervisão.",
                NotificationType.INFO,
            ),
        }
        if new_status in status_messages:
            title, message, notif_type = status_messages[new_status]
            NotificationService.notify(
                recipient=obj.filed_by,
                title=title,
                message=message,
                notification_type=notif_type,
                resource=obj,
                resource_url=f"/portal/citizen/claims/{obj.pk}/",
            )

    @action(detail=True, methods=["post"], url_path="take-charge")
    def take_charge(self, request, pk=None):
        """POST /api/v1/claims/{pk}/take-charge/ — OPEN → UNDER_REVIEW, assign to self."""
        return self._transition(request, pk, ClaimStatus.UNDER_REVIEW)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """POST /api/v1/claims/{pk}/resolve/"""
        return self._transition(request, pk, ClaimStatus.RESOLVED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """POST /api/v1/claims/{pk}/reject/"""
        return self._transition(request, pk, ClaimStatus.REJECTED)

    @action(detail=True, methods=["post"], url_path="request-info")
    def request_info(self, request, pk=None):
        """POST /api/v1/claims/{pk}/request-info/ — ask citizen for more info."""
        return self._transition(request, pk, ClaimStatus.ADDITIONAL_INFO)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        """POST /api/v1/claims/{pk}/escalate/"""
        return self._transition(request, pk, ClaimStatus.ESCALATED)

    @action(detail=True, methods=["post"], url_path="add-message")
    def add_message(self, request, pk=None):
        """POST /api/v1/claims/{pk}/add-message/ — add a message to the claim thread."""
        obj = get_object_or_404(Claim, pk=pk)
        user = request.user

        # Citizens can only message their own claims
        if user.role == UserRole.CITIZEN and obj.filed_by_id != user.pk:
            return Response({"detail": "Sem permissão."}, status=status.HTTP_403_FORBIDDEN)

        is_internal = request.data.get("is_internal", False)
        # Citizens cannot create internal notes
        if user.role == UserRole.CITIZEN:
            is_internal = False

        body = request.data.get("body", "").strip()
        if not body:
            return Response({"body": "O corpo da mensagem é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        msg = ClaimMessage.objects.create(
            claim=obj,
            author=user,
            body=body,
            is_internal=is_internal,
        )

        # If citizen replies to ADDITIONAL_INFO, auto-transition to UNDER_REVIEW
        if (
            user.role == UserRole.CITIZEN
            and obj.status == ClaimStatus.ADDITIONAL_INFO
        ):
            old_status = obj.status
            obj.status = ClaimStatus.UNDER_REVIEW
            obj.save(update_fields=["status", "updated_at"])
            ClaimStatusHistory.objects.create(
                claim=obj,
                old_status=old_status,
                new_status=ClaimStatus.UNDER_REVIEW,
                changed_by=user,
                comment="Cidadão forneceu informação adicional.",
            )

        # Notify filer if agent sends a public message
        if user.role in ("AGENT", "ADMIN") and not is_internal:
            NotificationService.notify(
                recipient=obj.filed_by,
                title="Nova mensagem na reclamação",
                message=f"O agente INSS adicionou uma mensagem à sua reclamação {obj.reference}.",
                notification_type=NotificationType.INFO,
                resource=obj,
                resource_url=f"/portal/citizen/claims/{obj.pk}/",
            )

        serializer = ClaimMessageSerializer(msg)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="upload-document")
    def upload_document(self, request, pk=None):
        """POST /api/v1/claims/{pk}/upload-document/ — attach a file."""
        obj = get_object_or_404(Claim, pk=pk)
        user = request.user

        if user.role == UserRole.CITIZEN and obj.filed_by_id != user.pk:
            return Response({"detail": "Sem permissão."}, status=status.HTTP_403_FORBIDDEN)

        name = request.data.get("name", "").strip()
        file = request.FILES.get("file")

        if not name or not file:
            return Response(
                {"detail": "Nome e ficheiro são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doc = ClaimDocument.objects.create(
            claim=obj,
            name=name,
            file=file,
            uploaded_by=user,
        )
        serializer = ClaimDocumentSerializer(doc)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="rate-satisfaction")
    def rate_satisfaction(self, request, pk=None):
        """POST /api/v1/claims/{pk}/rate-satisfaction/ — citizen rates a resolved claim."""
        obj = get_object_or_404(Claim, pk=pk)
        user = request.user

        if obj.filed_by_id != user.pk:
            return Response({"detail": "Sem permissão."}, status=status.HTTP_403_FORBIDDEN)

        if obj.status != ClaimStatus.RESOLVED:
            return Response(
                {"detail": "Só é possível avaliar reclamações resolvidas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rating = request.data.get("satisfaction_rating")
        try:
            rating = int(rating)
            if not (1 <= rating <= 5):
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"satisfaction_rating": "A avaliação deve ser um número entre 1 e 5."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj.satisfaction_rating = rating
        obj.satisfaction_comment = request.data.get("satisfaction_comment", "")
        obj.save(update_fields=["satisfaction_rating", "satisfaction_comment", "updated_at"])

        serializer = ClaimDetailSerializer(obj, context={"request": request})
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Reclamações não podem ser eliminadas."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
