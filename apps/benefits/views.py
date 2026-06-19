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
    BenefitType,
    BenefitRequest,
    BenefitDocument,
    BenefitPayment,
    BenefitStatusHistory,
    BenefitRequestStatus,
)
from .serializers import (
    BenefitTypeSerializer,
    BenefitRequestListSerializer,
    BenefitRequestDetailSerializer,
    BenefitRequestCreateSerializer,
    BenefitRequestReviewSerializer,
    BenefitDocumentSerializer,
    BenefitPaymentSerializer,
)


class BenefitTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for benefit types.
    - list/retrieve: all authenticated users
    - create/update/destroy: AGENT or ADMIN only
    """

    queryset = BenefitType.objects.all()
    serializer_class = BenefitTypeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["category", "is_active"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAgentOrAdmin()]

    def get_queryset(self):
        qs = BenefitType.objects.all()
        # Citizens only see active types
        user = self.request.user
        if user.role == UserRole.CITIZEN:
            qs = qs.filter(is_active=True)
        return qs


class BenefitRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for benefit requests.
    - Citizens: list/retrieve/create their own requests
    - Agents/Admins: list all, retrieve, update status
    """

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "benefit_type__category", "benefit_type"]

    def get_queryset(self):
        qs = BenefitRequest.objects.select_related(
            "affiliate",
            "benefit_type",
            "reviewed_by",
            "created_by",
        ).prefetch_related("documents", "payments", "history")

        user = self.request.user
        if user.role == UserRole.CITIZEN:
            try:
                qs = qs.filter(affiliate__user=user)
            except Exception:
                return BenefitRequest.objects.none()

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return BenefitRequestListSerializer
        if self.action == "create":
            return BenefitRequestCreateSerializer
        if self.action in ("review_action", "submit", "start_review", "approve", "reject", "request_additional_docs"):
            return BenefitRequestReviewSerializer
        return BenefitRequestDetailSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        if self.action == "create":
            return [IsAuthenticated()]
        if self.action in ("submit",):
            return [IsAuthenticated()]
        return [IsAgentOrAdmin()]

    def perform_create(self, serializer):
        user = self.request.user
        try:
            affiliate = user.affiliate
        except Exception:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Precisa de um perfil de afiliado para fazer uma solicitação.")

        benefit_type = serializer.validated_data["benefit_type"]

        request_obj = serializer.save(
            affiliate=affiliate,
            applicant_name=affiliate.full_name,
            applicant_niss=affiliate.niss,
            applicant_birth_date=affiliate.birth_date,
            status=BenefitRequestStatus.DRAFT,
            created_by=user,
        )

        BenefitStatusHistory.objects.create(
            request=request_obj,
            old_status="",
            new_status=BenefitRequestStatus.DRAFT,
            changed_by=user,
            comment="Solicitação criada.",
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        POST /api/v1/benefits/{pk}/submit/
        Citizen submits a DRAFT request.
        """
        obj = get_object_or_404(BenefitRequest, pk=pk)
        user = request.user

        # Only the owner citizen can submit
        if user.role == UserRole.CITIZEN:
            if not hasattr(user, "affiliate") or obj.affiliate.user_id != user.pk:
                return Response(
                    {"detail": "Sem permissão para submeter esta solicitação."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if obj.status != BenefitRequestStatus.DRAFT:
            return Response(
                {"detail": f"Só é possível submeter solicitações em rascunho. Estado atual: {obj.get_status_display()}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = obj.status
        obj.status = BenefitRequestStatus.SUBMITTED
        obj.submitted_at = timezone.now()
        obj.save(update_fields=["status", "submitted_at", "updated_at"])

        # Compute eligibility on submission
        obj.compute_eligibility()

        BenefitStatusHistory.objects.create(
            request=obj,
            old_status=old_status,
            new_status=BenefitRequestStatus.SUBMITTED,
            changed_by=user,
            comment="Solicitação submetida pelo requerente.",
        )

        # Notify agents (no specific recipient here — just confirm to citizen)
        NotificationService.notify(
            recipient=user,
            title="Solicitação de prestação submetida",
            message=(
                f"A sua solicitação {obj.reference} foi submetida com sucesso e está a aguardar revisão."
            ),
            notification_type=NotificationType.SUCCESS,
            resource=obj,
            resource_url=f"/portal/citizen/benefits/{obj.pk}/",
        )

        serializer = BenefitRequestDetailSerializer(obj, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="start-review")
    def start_review(self, request, pk=None):
        """
        POST /api/v1/benefits/{pk}/start-review/
        Agent starts review of a SUBMITTED request.
        """
        obj = get_object_or_404(BenefitRequest, pk=pk)

        if obj.status != BenefitRequestStatus.SUBMITTED:
            return Response(
                {"detail": f"Só é possível iniciar revisão de solicitações submetidas. Estado atual: {obj.get_status_display()}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = obj.status
        obj.status = BenefitRequestStatus.UNDER_REVIEW
        obj.reviewed_by = request.user
        obj.review_started_at = timezone.now()
        obj.save(update_fields=["status", "reviewed_by", "review_started_at", "updated_at"])

        BenefitStatusHistory.objects.create(
            request=obj,
            old_status=old_status,
            new_status=BenefitRequestStatus.UNDER_REVIEW,
            changed_by=request.user,
            comment=f"Revisão iniciada pelo agente {request.user.email}.",
        )

        # Notify citizen
        NotificationService.notify(
            recipient=obj.affiliate.user,
            title="Solicitação em revisão",
            message=(
                f"A sua solicitação {obj.reference} está a ser analisada pelo agente INSS."
            ),
            notification_type=NotificationType.INFO,
            resource=obj,
            resource_url=f"/portal/citizen/benefits/{obj.pk}/",
        )

        serializer = BenefitRequestDetailSerializer(obj, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """
        POST /api/v1/benefits/{pk}/approve/
        Agent approves request.
        """
        obj = get_object_or_404(BenefitRequest, pk=pk)

        if obj.status not in (BenefitRequestStatus.UNDER_REVIEW, BenefitRequestStatus.ADDITIONAL_DOCS):
            return Response(
                {"detail": f"Não é possível aprovar neste estado: {obj.get_status_display()}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BenefitRequestReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        old_status = obj.status

        obj.status = BenefitRequestStatus.APPROVED
        obj.decided_at = timezone.now()
        obj.decision_notes = data.get("decision_notes", "")

        # Use overridden amount if provided, else compute
        if data.get("approved_monthly_amount") is not None:
            obj.approved_monthly_amount = data["approved_monthly_amount"]
        else:
            obj.compute_eligibility()

        obj.save(update_fields=["status", "decided_at", "decision_notes", "approved_monthly_amount", "updated_at"])

        BenefitStatusHistory.objects.create(
            request=obj,
            old_status=old_status,
            new_status=BenefitRequestStatus.APPROVED,
            changed_by=request.user,
            comment=data.get("comment") or data.get("decision_notes", "Aprovada."),
        )

        # Notify citizen
        NotificationService.notify(
            recipient=obj.affiliate.user,
            title="Solicitação de prestação aprovada",
            message=(
                f"A sua solicitação {obj.reference} foi aprovada! "
                f"Montante mensal: {obj.approved_monthly_amount} XOF."
            ),
            notification_type=NotificationType.SUCCESS,
            resource=obj,
            resource_url=f"/portal/citizen/benefits/{obj.pk}/",
        )

        serializer_out = BenefitRequestDetailSerializer(obj, context={"request": request})
        return Response(serializer_out.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """
        POST /api/v1/benefits/{pk}/reject/
        Agent rejects request.
        """
        obj = get_object_or_404(BenefitRequest, pk=pk)

        if obj.status not in (
            BenefitRequestStatus.SUBMITTED,
            BenefitRequestStatus.UNDER_REVIEW,
            BenefitRequestStatus.ADDITIONAL_DOCS,
        ):
            return Response(
                {"detail": f"Não é possível rejeitar neste estado: {obj.get_status_display()}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BenefitRequestReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        if not data.get("rejection_reason"):
            return Response(
                {"rejection_reason": "O motivo de rejeição é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = obj.status
        obj.status = BenefitRequestStatus.REJECTED
        obj.decided_at = timezone.now()
        obj.decision_notes = data.get("decision_notes", "")
        obj.rejection_reason = data.get("rejection_reason", "")
        obj.save(update_fields=["status", "decided_at", "decision_notes", "rejection_reason", "updated_at"])

        BenefitStatusHistory.objects.create(
            request=obj,
            old_status=old_status,
            new_status=BenefitRequestStatus.REJECTED,
            changed_by=request.user,
            comment=data.get("comment") or f"Rejeitada: {obj.rejection_reason}",
        )

        # Notify citizen
        NotificationService.notify(
            recipient=obj.affiliate.user,
            title="Solicitação de prestação rejeitada",
            message=(
                f"A sua solicitação {obj.reference} foi rejeitada. "
                f"Motivo: {obj.rejection_reason}."
            ),
            notification_type=NotificationType.ERROR,
            resource=obj,
            resource_url=f"/portal/citizen/benefits/{obj.pk}/",
        )

        serializer_out = BenefitRequestDetailSerializer(obj, context={"request": request})
        return Response(serializer_out.data)

    @action(detail=True, methods=["post"], url_path="request-additional-docs")
    def request_additional_docs(self, request, pk=None):
        """
        POST /api/v1/benefits/{pk}/request-additional-docs/
        Agent requests additional documents.
        """
        obj = get_object_or_404(BenefitRequest, pk=pk)

        if obj.status != BenefitRequestStatus.UNDER_REVIEW:
            return Response(
                {"detail": f"Só é possível solicitar documentos adicionais em revisão. Estado: {obj.get_status_display()}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BenefitRequestReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        old_status = obj.status
        obj.status = BenefitRequestStatus.ADDITIONAL_DOCS
        obj.save(update_fields=["status", "updated_at"])

        BenefitStatusHistory.objects.create(
            request=obj,
            old_status=old_status,
            new_status=BenefitRequestStatus.ADDITIONAL_DOCS,
            changed_by=request.user,
            comment=data.get("comment", "Documentos adicionais solicitados."),
        )

        # Notify citizen
        NotificationService.notify(
            recipient=obj.affiliate.user,
            title="Documentos adicionais necessários",
            message=(
                f"O agente INSS solicitou documentos adicionais para a sua solicitação {obj.reference}. "
                f"Por favor, carregue os documentos necessários."
            ),
            notification_type=NotificationType.WARNING,
            resource=obj,
            resource_url=f"/portal/citizen/benefits/{obj.pk}/documents/",
        )

        serializer_out = BenefitRequestDetailSerializer(obj, context={"request": request})
        return Response(serializer_out.data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        # Only allow deletion of drafts by the owner or admin
        if obj.status != BenefitRequestStatus.DRAFT:
            return Response(
                {"detail": "Só é possível eliminar solicitações em rascunho."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user.role == UserRole.CITIZEN:
            if not hasattr(request.user, "affiliate") or obj.affiliate.user_id != request.user.pk:
                return Response(
                    {"detail": "Sem permissão para eliminar esta solicitação."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        return super().destroy(request, *args, **kwargs)


class BenefitDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for benefit documents.
    - Citizens: upload/list docs for their own requests
    - Agents: list all, upload to any request
    """

    serializer_class = BenefitDocumentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["request", "document_type"]

    def get_queryset(self):
        qs = BenefitDocument.objects.select_related(
            "request", "uploaded_by"
        ).all()

        user = self.request.user
        if user.role == UserRole.CITIZEN:
            try:
                qs = qs.filter(request__affiliate__user=user)
            except Exception:
                return BenefitDocument.objects.none()
        return qs

    def get_permissions(self):
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        user = self.request.user
        request_obj = serializer.validated_data["request"]

        # Citizens can only upload to their own requests
        if user.role == UserRole.CITIZEN:
            if not hasattr(user, "affiliate") or request_obj.affiliate.user_id != user.pk:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Sem permissão para carregar documentos nesta solicitação.")

        serializer.save(uploaded_by=user)

    def destroy(self, request, *args, **kwargs):
        if request.user.role == UserRole.CITIZEN:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Não é possível eliminar documentos.")
        return super().destroy(request, *args, **kwargs)


class BenefitPaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for benefit payments.
    - Citizens: read-only, own payments only
    - Agents: full CRUD
    """

    serializer_class = BenefitPaymentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["request", "status", "period_year", "period_month"]

    def get_queryset(self):
        qs = BenefitPayment.objects.select_related("request").all()

        user = self.request.user
        if user.role == UserRole.CITIZEN:
            try:
                qs = qs.filter(request__affiliate__user=user)
            except Exception:
                return BenefitPayment.objects.none()
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAgentOrAdmin()]
