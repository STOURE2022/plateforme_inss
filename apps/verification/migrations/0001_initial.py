import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("cards", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VerificationLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "verifier_ip",
                    models.GenericIPAddressField(
                        blank=True,
                        null=True,
                        verbose_name="IP do verificador",
                    ),
                ),
                (
                    "verifier_role",
                    models.CharField(
                        blank=True,
                        max_length=20,
                        verbose_name="Função no momento da verificação",
                    ),
                ),
                (
                    "card_number",
                    models.CharField(
                        blank=True,
                        max_length=20,
                        verbose_name="Número do cartão (snapshot)",
                    ),
                ),
                (
                    "token_jti",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        verbose_name="JTI do token apresentado",
                    ),
                ),
                (
                    "result",
                    models.CharField(
                        choices=[
                            ("SUCCESS", "Sucesso"),
                            ("FAILURE", "Falha"),
                            ("EXPIRED", "Expirado"),
                            ("REVOKED", "Revogado"),
                            ("INVALID", "Inválido"),
                        ],
                        max_length=20,
                        verbose_name="Resultado",
                    ),
                ),
                (
                    "failure_reason",
                    models.TextField(
                        blank=True,
                        verbose_name="Motivo da falha",
                    ),
                ),
                (
                    "verified_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Verificado em",
                    ),
                ),
                (
                    "response_ms",
                    models.IntegerField(
                        blank=True,
                        null=True,
                        verbose_name="Tempo de resposta (ms)",
                    ),
                ),
                (
                    "card",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="verification_logs",
                        to="cards.healthcard",
                        verbose_name="Cartão",
                    ),
                ),
                (
                    "verifier",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="verifications",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Verificador",
                    ),
                ),
            ],
            options={
                "verbose_name": "Log de Verificação",
                "verbose_name_plural": "Logs de Verificação",
                "ordering": ["-verified_at"],
            },
        ),
        migrations.AddIndex(
            model_name="verificationlog",
            index=models.Index(
                fields=["card_number", "verified_at"],
                name="verificatio_card_nu_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="verificationlog",
            index=models.Index(
                fields=["verifier", "verified_at"],
                name="verificatio_verifie_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="verificationlog",
            index=models.Index(
                fields=["result", "verified_at"],
                name="verificatio_result_idx",
            ),
        ),
    ]
