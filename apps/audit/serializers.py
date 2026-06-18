from rest_framework import serializers
from apps.audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "user",
            "user_email",
            "user_role",
            "ip_address",
            "user_agent",
            "action",
            "resource_type",
            "resource_id",
            "resource_repr",
            "details",
            "old_values",
            "new_values",
            "timestamp",
        ]
        read_only_fields = fields
