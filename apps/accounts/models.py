from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from .managers import UserManager


class UserRole(models.TextChoices):
    CITIZEN = "CITIZEN", "Cidadão"
    DEPENDENT = "DEPENDENT", "Dependente"
    EMPLOYER = "EMPLOYER", "Empregador"
    AGENT = "AGENT", "Agente INSS"
    PROVIDER = "PROVIDER", "Prestador de Cuidados"
    ADMIN = "ADMIN", "Administrador"


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name="Email")
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CITIZEN,
        verbose_name="Função",
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    is_staff = models.BooleanField(default=False, verbose_name="Staff")
    mfa_enabled = models.BooleanField(default=False, verbose_name="MFA ativado")
    # Stored encrypted in production via Django field encryption or at DB level
    mfa_secret = models.CharField(max_length=64, blank=True, verbose_name="Segredo MFA")
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "Utilizador"
        verbose_name_plural = "Utilizadores"

    def __str__(self) -> str:
        return self.email

    @property
    def is_citizen(self) -> bool:
        return self.role == UserRole.CITIZEN

    @property
    def is_agent(self) -> bool:
        return self.role == UserRole.AGENT

    @property
    def is_admin_role(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_provider(self) -> bool:
        return self.role == UserRole.PROVIDER

    @property
    def is_employer_role(self) -> bool:
        return self.role == UserRole.EMPLOYER
