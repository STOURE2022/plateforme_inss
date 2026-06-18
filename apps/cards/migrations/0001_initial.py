import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("affiliates", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HealthCard",
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
                    "card_number",
                    models.CharField(
                        blank=True,
                        max_length=20,
                        unique=True,
                        verbose_name="Número do cartão",
                    ),
                ),
                (
                    "issued_date",
                    models.DateField(auto_now_add=True, verbose_name="Data de emissão"),
                ),
                (
                    "expiry_date",
                    models.DateField(
                        blank=True, null=True, verbose_name="Data de validade"
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Ativo"),
                            ("SUSPENDED", "Suspenso"),
                            ("EXPIRED", "Expirado"),
                            ("CANCELLED", "Cancelado"),
                        ],
                        default="ACTIVE",
                        max_length=10,
                        verbose_name="Estado",
                    ),
                ),
                (
                    "current_token_jti",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        verbose_name="JTI do token atual",
                    ),
                ),
                (
                    "token_issued_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Emissão do token"
                    ),
                ),
                (
                    "token_expires_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Expiração do token"
                    ),
                ),
                (
                    "pdf_file",
                    models.FileField(
                        blank=True,
                        null=True,
                        upload_to="cards/pdf/",
                        verbose_name="Ficheiro PDF",
                    ),
                ),
                (
                    "pdf_generated_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="PDF gerado em"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Criado em"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Atualizado em"),
                ),
                (
                    "affiliate",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="health_card",
                        to="affiliates.affiliate",
                        verbose_name="Afiliado",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_cards",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Criado por",
                    ),
                ),
            ],
            options={
                "verbose_name": "Cartão de Saúde",
                "verbose_name_plural": "Cartões de Saúde",
                "ordering": ["-created_at"],
            },
        ),
    ]
