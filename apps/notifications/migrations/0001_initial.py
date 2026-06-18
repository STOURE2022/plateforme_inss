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
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200, verbose_name="Título")),
                ("message", models.TextField(verbose_name="Mensagem")),
                (
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("INFO", "Informação"),
                            ("WARNING", "Aviso"),
                            ("SUCCESS", "Sucesso"),
                            ("ERROR", "Erro"),
                        ],
                        default="INFO",
                        max_length=20,
                        verbose_name="Tipo",
                    ),
                ),
                ("resource_type", models.CharField(blank=True, max_length=50, verbose_name="Tipo de recurso")),
                ("resource_id", models.CharField(blank=True, max_length=50, verbose_name="ID do recurso")),
                ("resource_url", models.CharField(blank=True, max_length=200, verbose_name="URL do recurso")),
                ("is_read", models.BooleanField(default=False, verbose_name="Lida")),
                ("read_at", models.DateTimeField(blank=True, null=True, verbose_name="Lida em")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Criada em")),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Destinatário",
                    ),
                ),
            ],
            options={
                "verbose_name": "Notificação",
                "verbose_name_plural": "Notificações",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["recipient", "is_read", "created_at"],
                name="notif_recipient_is_read_created_idx",
            ),
        ),
    ]
