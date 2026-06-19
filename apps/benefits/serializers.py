from rest_framework import serializers

from .models import (
    BenefitType,
    BenefitRequest,
    BenefitDocument,
    BenefitPayment,
    BenefitStatusHistory,
    BenefitRequestStatus,
)


class BenefitTypeSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    calculation_method_display = serializers.CharField(source="get_calculation_method_display", read_only=True)

    class Meta:
        model = BenefitType
        fields = [
            "id",
            "category",
            "category_display",
            "name",
            "description",
            "min_contribution_months",
            "calculation_method",
            "calculation_method_display",
            "fixed_amount",
            "percentage_of_salary",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BenefitDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = BenefitDocument
        fields = [
            "id",
            "request",
            "document_type",
            "document_type_display",
            "name",
            "file",
            "uploaded_by",
            "uploaded_by_email",
            "uploaded_at",
            "notes",
        ]
        read_only_fields = ["id", "uploaded_by", "uploaded_by_email", "uploaded_at"]


class BenefitPaymentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    request_reference = serializers.CharField(source="request.reference", read_only=True)

    class Meta:
        model = BenefitPayment
        fields = [
            "id",
            "request",
            "request_reference",
            "period_year",
            "period_month",
            "amount",
            "status",
            "status_display",
            "scheduled_date",
            "paid_date",
            "payment_reference",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class BenefitStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True)
    old_status_display = serializers.SerializerMethodField()
    new_status_display = serializers.SerializerMethodField()

    class Meta:
        model = BenefitStatusHistory
        fields = [
            "id",
            "request",
            "old_status",
            "old_status_display",
            "new_status",
            "new_status_display",
            "changed_by",
            "changed_by_email",
            "changed_at",
            "comment",
        ]
        read_only_fields = ["id", "changed_by", "changed_at"]

    def get_old_status_display(self, obj):
        return BenefitRequestStatus(obj.old_status).label if obj.old_status else ""

    def get_new_status_display(self, obj):
        try:
            return BenefitRequestStatus(obj.new_status).label
        except ValueError:
            return obj.new_status


class BenefitRequestListSerializer(serializers.ModelSerializer):
    """Compact serializer for list views."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    benefit_type_name = serializers.CharField(source="benefit_type.name", read_only=True)
    benefit_type_category = serializers.CharField(source="benefit_type.get_category_display", read_only=True)

    class Meta:
        model = BenefitRequest
        fields = [
            "id",
            "reference",
            "applicant_name",
            "applicant_niss",
            "benefit_type",
            "benefit_type_name",
            "benefit_type_category",
            "status",
            "status_display",
            "submitted_at",
            "decided_at",
            "approved_monthly_amount",
            "created_at",
        ]
        read_only_fields = fields


class BenefitRequestDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested documents, payments, history."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    benefit_type_detail = BenefitTypeSerializer(source="benefit_type", read_only=True)
    documents = BenefitDocumentSerializer(many=True, read_only=True)
    payments = BenefitPaymentSerializer(many=True, read_only=True)
    history = BenefitStatusHistorySerializer(many=True, read_only=True)
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = BenefitRequest
        fields = [
            "id",
            "reference",
            "affiliate",
            "benefit_type",
            "benefit_type_detail",
            "applicant_name",
            "applicant_niss",
            "applicant_birth_date",
            "status",
            "status_display",
            "justification",
            "requested_start_date",
            "contribution_months_count",
            "average_salary",
            "is_eligible",
            "submitted_at",
            "reviewed_by",
            "reviewed_by_email",
            "review_started_at",
            "decided_at",
            "decision_notes",
            "rejection_reason",
            "approved_monthly_amount",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
            "documents",
            "payments",
            "history",
        ]
        read_only_fields = [
            "id",
            "reference",
            "contribution_months_count",
            "average_salary",
            "is_eligible",
            "submitted_at",
            "review_started_at",
            "decided_at",
            "created_by",
            "created_at",
            "updated_at",
        ]


class BenefitRequestCreateSerializer(serializers.ModelSerializer):
    """For citizen submission — captures benefit_type, justification, requested_start_date."""

    class Meta:
        model = BenefitRequest
        fields = [
            "id",
            "benefit_type",
            "justification",
            "requested_start_date",
        ]
        read_only_fields = ["id"]

    def validate_benefit_type(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Este tipo de prestação não está disponível.")
        return value


class BenefitRequestReviewSerializer(serializers.Serializer):
    """For agent status changes."""

    action = serializers.ChoiceField(choices=[
        ("start_review", "Iniciar revisão"),
        ("approve", "Aprovar"),
        ("reject", "Rejeitar"),
        ("request_additional_docs", "Solicitar documentos adicionais"),
    ])
    decision_notes = serializers.CharField(required=False, allow_blank=True, default="")
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")
    approved_monthly_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        action = attrs.get("action")
        if action == "reject" and not attrs.get("rejection_reason"):
            raise serializers.ValidationError(
                {"rejection_reason": "O motivo de rejeição é obrigatório."}
            )
        return attrs
