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
            name="Affiliate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="affiliate",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Utilizador",
                    ),
                ),
                ("niss", models.CharField(help_text="Número de Identificação de Segurança Social", max_length=15, unique=True, verbose_name="NISS")),
                ("full_name", models.CharField(max_length=200, verbose_name="Nome completo")),
                ("birth_date", models.DateField(verbose_name="Data de nascimento")),
                (
                    "gender",
                    models.CharField(
                        choices=[("M", "Masculino"), ("F", "Feminino"), ("O", "Outro")],
                        max_length=1,
                        verbose_name="Género",
                    ),
                ),
                ("nationality", models.CharField(default="GW", max_length=3, verbose_name="Nacionalidade")),
                ("address", models.TextField(blank=True, verbose_name="Endereço")),
                ("phone", models.CharField(blank=True, max_length=20, verbose_name="Telefone")),
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
            ],
            options={
                "verbose_name": "Afiliado",
                "verbose_name_plural": "Afiliados",
                "ordering": ["-registration_date"],
            },
        ),
        migrations.CreateModel(
            name="Dependent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "affiliate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dependents",
                        to="affiliates.affiliate",
                        verbose_name="Afiliado",
                    ),
                ),
                ("full_name", models.CharField(max_length=200, verbose_name="Nome completo")),
                ("birth_date", models.DateField(verbose_name="Data de nascimento")),
                (
                    "relationship",
                    models.CharField(
                        choices=[
                            ("SPOUSE", "Cônjuge"),
                            ("CHILD", "Filho/Filha"),
                            ("PARENT", "Pai/Mãe"),
                            ("OTHER", "Outro"),
                        ],
                        max_length=10,
                        verbose_name="Grau de parentesco",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Ativo")),
            ],
            options={
                "verbose_name": "Dependente",
                "verbose_name_plural": "Dependentes",
                "ordering": ["full_name"],
            },
        ),
    ]
