import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Employer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="employer",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Utilizador",
                    ),
                ),
                ("company_name", models.CharField(max_length=200, verbose_name="Nome da empresa")),
                ("nuit", models.CharField(help_text="Número de Identificação Fiscal", max_length=20, unique=True, verbose_name="NUIT")),
                (
                    "sector",
                    models.CharField(
                        choices=[
                            ("PUBLIC", "Público"),
                            ("PRIVATE", "Privado"),
                            ("NGO", "ONG"),
                            ("OTHER", "Outro"),
                        ],
                        max_length=10,
                        verbose_name="Sector",
                    ),
                ),
                ("address", models.TextField(verbose_name="Endereço")),
                ("phone", models.CharField(max_length=20, verbose_name="Telefone")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="Email")),
                ("registration_date", models.DateField(auto_now_add=True, verbose_name="Data de registo")),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Ativo"), ("INACTIVE", "Inativo"), ("SUSPENDED", "Suspenso")],
                        default="ACTIVE",
                        max_length=10,
                        verbose_name="Estado",
                    ),
                ),
                (
                    "registered_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="registered_employers",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Registado por",
                    ),
                ),
            ],
            options={
                "verbose_name": "Empregador",
                "verbose_name_plural": "Empregadores",
                "ordering": ["-registration_date"],
            },
        ),
    ]
