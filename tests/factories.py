import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from datetime import timedelta

from apps.accounts.tests.factories import UserFactory, AgentFactory, AdminFactory, EmployerFactory
from apps.accounts.models import UserRole
from apps.affiliates.models import Affiliate, Dependent, GenderChoices, RelationshipChoices, AffiliateStatus
from apps.employers.models import Employer, SectorChoices, EmployerStatus
from apps.contributions.models import Contribution, ContributionStatus


class CitizenUserFactory(UserFactory):
    role = UserRole.CITIZEN
    email = factory.Sequence(lambda n: f"citizen{n}@einss.gw")


class AffiliateFactory(DjangoModelFactory):
    class Meta:
        model = Affiliate

    user = factory.SubFactory(CitizenUserFactory)
    niss = factory.Sequence(lambda n: f"GW{n:013d}")
    full_name = factory.Sequence(lambda n: f"Cidadão Teste {n}")
    birth_date = "1985-06-15"
    gender = GenderChoices.MALE
    nationality = "GW"
    address = "Rua Principal, Bissau"
    phone = factory.Sequence(lambda n: f"+245 9{n:08d}")
    status = AffiliateStatus.ACTIVE


class DependentFactory(DjangoModelFactory):
    class Meta:
        model = Dependent

    affiliate = factory.SubFactory(AffiliateFactory)
    full_name = factory.Sequence(lambda n: f"Dependente {n}")
    birth_date = "2010-03-20"
    relationship = RelationshipChoices.CHILD
    is_active = True


class EmployerUserFactory(EmployerFactory):
    pass


class EmployerProfileFactory(DjangoModelFactory):
    class Meta:
        model = Employer

    user = factory.SubFactory(EmployerUserFactory)
    company_name = factory.Sequence(lambda n: f"Empresa {n} Lda")
    nuit = factory.Sequence(lambda n: f"NUIT{n:016d}")
    sector = SectorChoices.PRIVATE
    address = "Av. Amílcar Cabral, Bissau"
    phone = factory.Sequence(lambda n: f"+245 3{n:08d}")
    email = factory.Sequence(lambda n: f"empresa{n}@company.gw")
    status = EmployerStatus.ACTIVE
    registered_by = None


class ContributionFactory(DjangoModelFactory):
    class Meta:
        model = Contribution

    affiliate = factory.SubFactory(AffiliateFactory)
    employer = factory.SubFactory(EmployerProfileFactory)
    period_year = 2024
    period_month = 1
    salary_base = "500000.00"
    employee_rate = "0.0400"
    employer_rate = "0.0800"
    status = ContributionStatus.PENDING
    created_by = factory.SubFactory(AgentFactory)
    notes = ""


class HealthCardFactory(DjangoModelFactory):
    class Meta:
        model = "cards.HealthCard"

    affiliate = factory.SubFactory(AffiliateFactory)
    status = "ACTIVE"
    created_by = factory.SubFactory(AgentFactory)
