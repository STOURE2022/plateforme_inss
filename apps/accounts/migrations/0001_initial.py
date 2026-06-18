from django.db import migrations, models
import apps.accounts.managers


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(
                    default=False,
                    help_text="Designates that this user has all permissions without explicitly assigning them.",
                    verbose_name="superuser status",
                )),
                ("email", models.EmailField(max_length=254, unique=True, verbose_name="Email")),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("CITIZEN", "Cidadão"),
                            ("DEPENDENT", "Dependente"),
                            ("EMPLOYER", "Empregador"),
                            ("AGENT", "Agente INSS"),
                            ("PROVIDER", "Prestador de Cuidados"),
                            ("ADMIN", "Administrador"),
                        ],
                        default="CITIZEN",
                        max_length=20,
                        verbose_name="Função",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Ativo")),
                ("is_staff", models.BooleanField(default=False, verbose_name="Staff")),
                ("mfa_enabled", models.BooleanField(default=False, verbose_name="MFA ativado")),
                ("mfa_secret", models.CharField(blank=True, max_length=64, verbose_name="Segredo MFA")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "Utilizador",
                "verbose_name_plural": "Utilizadores",
            },
            managers=[
                ("objects", apps.accounts.managers.UserManager()),
            ],
        ),
    ]
