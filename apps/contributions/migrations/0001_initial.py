import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("affiliates", "0001_initial"),
        ("employers", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Contribution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "affiliate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="contributions",
                        to="affiliates.affiliate",
                        verbose_name="Afiliado",
                    ),
                ),
                (
                    "employer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="contributions",
                        to="employers.employer",
                        verbose_name="Empregador",
                    ),
                ),
                ("period_year", models.PositiveIntegerField(verbose_name="Ano do período")),
                (
                    "period_month",
                    models.PositiveIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(12),
                        ],
                        verbose_name="Mês do período",
                    ),
                ),
                ("salary_base", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Salário base")),
                (
                    "employee_rate",
                    models.DecimalField(
                        decimal_places=4,
                        default="0.0400",
                        max_digits=5,
                        verbose_name="Taxa do trabalhador",
                    ),
                ),
                (
                    "employer_rate",
                    models.DecimalField(
                        decimal_places=4,
                        default="0.0800",
                        max_digits=5,
                        verbose_name="Taxa do empregador",
                    ),
                ),
                (
                    "employee_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Contribuição do trabalhador",
                    ),
                ),
                (
                    "employer_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Contribuição do empregador",
                    ),
                ),
                (
                    "total_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Total",
                    ),
                ),
                ("payment_date", models.DateField(blank=True, null=True, verbose_name="Data de pagamento")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pendente"),
                            ("PAID", "Pago"),
                            ("LATE", "Em atraso"),
                            ("CANCELLED", "Cancelado"),
                        ],
                        default="PENDING",
                        max_length=10,
                        verbose_name="Estado",
                    ),
                ),
                ("reference", models.CharField(blank=True, max_length=50, unique=True, verbose_name="Referência")),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_contributions",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Criado por",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Criado em")),
                ("notes", models.TextField(blank=True, verbose_name="Notas")),
            ],
            options={
                "verbose_name": "Contribuição",
                "verbose_name_plural": "Contribuições",
                "ordering": ["-period_year", "-period_month"],
                "unique_together": {("affiliate", "period_year", "period_month")},
            },
        ),
    ]
