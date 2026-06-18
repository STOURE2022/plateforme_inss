from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_email", models.CharField(blank=True, max_length=254, verbose_name="Email (snapshot)")),
                ("user_role", models.CharField(blank=True, max_length=20, verbose_name="Função (snapshot)")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True, verbose_name="Endereço IP")),
                ("user_agent", models.TextField(blank=True, verbose_name="User Agent")),
                ("action", models.CharField(max_length=100, verbose_name="Ação")),
                ("resource_type", models.CharField(blank=True, max_length=50, verbose_name="Tipo de recurso")),
                ("resource_id", models.CharField(blank=True, max_length=50, verbose_name="ID do recurso")),
                ("resource_repr", models.CharField(blank=True, max_length=200, verbose_name="Representação do recurso")),
                ("details", models.JSONField(blank=True, default=dict, verbose_name="Detalhes")),
                ("old_values", models.JSONField(blank=True, null=True, verbose_name="Valores anteriores")),
                ("new_values", models.JSONField(blank=True, null=True, verbose_name="Novos valores")),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Timestamp")),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_events",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Utilizador",
                    ),
                ),
            ],
            options={
                "verbose_name": "Evento de Auditoria",
                "verbose_name_plural": "Eventos de Auditoria",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["action", "timestamp"], name="audit_audit_action_timestamp_idx"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["resource_type", "resource_id"], name="audit_audit_resource_type_id_idx"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["user", "timestamp"], name="audit_audit_user_timestamp_idx"),
        ),
    ]
