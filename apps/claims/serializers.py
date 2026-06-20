from rest_framework import serializers

from .models import Claim, ClaimMessage, ClaimDocument, ClaimStatusHistory, ClaimStatus


class ClaimMessageSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = ClaimMessage
        fields = ["id", "author", "author_email", "body", "is_internal", "created_at"]
        read_only_fields = ["id", "author", "author_email", "created_at"]


class ClaimDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = ClaimDocument
        fields = ["id", "name", "file", "uploaded_by", "uploaded_by_email", "uploaded_at"]
        read_only_fields = ["id", "uploaded_by", "uploaded_by_email", "uploaded_at"]


class ClaimStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True)
    old_status_display = serializers.SerializerMethodField()
    new_status_display = serializers.SerializerMethodField()

    class Meta:
        model = ClaimStatusHistory
        fields = [
            "id",
            "old_status",
            "old_status_display",
            "new_status",
            "new_status_display",
            "changed_by",
            "changed_by_email",
            "changed_at",
            "comment",
        ]
        read_only_fields = fields

    def get_old_status_display(self, obj):
        return dict(ClaimStatus.choices).get(obj.old_status, obj.old_status)

    def get_new_status_display(self, obj):
        return dict(ClaimStatus.choices).get(obj.new_status, obj.new_status)


class ClaimListSerializer(serializers.ModelSerializer):
    claim_type_display = serializers.CharField(source="get_claim_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    days_open = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Claim
        fields = [
            "id",
            "reference",
            "claim_type",
            "claim_type_display",
            "subject",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "submitted_at",
            "days_open",
            "is_overdue",
            "due_date",
        ]


class ClaimDetailSerializer(serializers.ModelSerializer):
    claim_type_display = serializers.CharField(source="get_claim_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    days_open = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    filed_by_email = serializers.EmailField(source="filed_by.email", read_only=True)
    assigned_to_email = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()
    documents = ClaimDocumentSerializer(many=True, read_only=True)
    history = ClaimStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Claim
        fields = [
            "id",
            "reference",
            "filed_by",
            "filed_by_email",
            "affiliate",
            "employer",
            "claim_type",
            "claim_type_display",
            "subject",
            "description",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "assigned_to",
            "assigned_to_email",
            "submitted_at",
            "review_started_at",
            "resolved_at",
            "due_date",
            "resolution_notes",
            "rejection_reason",
            "satisfaction_rating",
            "satisfaction_comment",
            "days_open",
            "is_overdue",
            "messages",
            "documents",
            "history",
            "created_at",
            "updated_at",
        ]

    def get_assigned_to_email(self, obj):
        return obj.assigned_to.email if obj.assigned_to else None

    def get_messages(self, obj):
        request = self.context.get("request")
        is_agent = request and request.user.role in ("AGENT", "ADMIN")
        qs = obj.messages.all()
        if not is_agent:
            qs = qs.filter(is_internal=False)
        return ClaimMessageSerializer(qs, many=True).data


class ClaimCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Claim
        fields = [
            "claim_type",
            "subject",
            "description",
            "related_resource_type",
            "related_resource_id",
        ]

    def validate_claim_type(self, value):
        from .models import ReclamationType
        valid = [c[0] for c in ReclamationType.choices]
        if value not in valid:
            raise serializers.ValidationError("Tipo de reclamação inválido.")
        return value


class ClaimAgentActionSerializer(serializers.Serializer):
    new_status = serializers.ChoiceField(choices=ClaimStatus.choices)
    comment = serializers.CharField(required=False, allow_blank=True)
    resolution_notes = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(
        choices=[("LOW", "Baixa"), ("NORMAL", "Normal"), ("HIGH", "Alta"), ("URGENT", "Urgente")],
        required=False,
    )
    assigned_to_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, data):
        new_status = data.get("new_status")
        if new_status == "REJECTED" and not data.get("rejection_reason"):
            raise serializers.ValidationError(
                {"rejection_reason": "O motivo de rejeição é obrigatório."}
            )
        if new_status == "RESOLVED" and not data.get("resolution_notes"):
            raise serializers.ValidationError(
                {"resolution_notes": "As notas de resolução são obrigatórias."}
            )
        return data
