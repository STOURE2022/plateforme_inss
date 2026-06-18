import factory
from factory.django import DjangoModelFactory
from apps.accounts.models import User, UserRole


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@einss.gw")
    password = factory.PostGenerationMethodCall("set_password", "testpassword123")
    role = UserRole.CITIZEN
    is_active = True
    mfa_enabled = False


class AgentFactory(UserFactory):
    role = UserRole.AGENT
    email = factory.Sequence(lambda n: f"agent{n}@inss.gw")


class AdminFactory(UserFactory):
    role = UserRole.ADMIN
    is_staff = True
    is_superuser = True
    email = factory.Sequence(lambda n: f"admin{n}@inss.gw")


class ProviderFactory(UserFactory):
    role = UserRole.PROVIDER
    email = factory.Sequence(lambda n: f"provider{n}@health.gw")


class EmployerFactory(UserFactory):
    role = UserRole.EMPLOYER
    email = factory.Sequence(lambda n: f"employer{n}@company.gw")
