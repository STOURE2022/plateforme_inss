"""
Tests do Lote 1 — Affiliate, Employer, Contribution
Mínimo 20 testes cobrindo CRUD, permissões, cálculos e unicidade.
"""
import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserRole
from apps.affiliates.models import Affiliate, Dependent
from apps.employers.models import Employer
from apps.contributions.models import Contribution

from .factories import (
    AffiliateFactory,
    DependentFactory,
    EmployerProfileFactory,
    ContributionFactory,
    CitizenUserFactory,
    EmployerUserFactory,
)
from apps.accounts.tests.factories import AgentFactory, AdminFactory, EmployerFactory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth_client(user):
    """Retorna APIClient autenticado com JWT para o utilizador fornecido."""
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


# ---------------------------------------------------------------------------
# Tests — Affiliates
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAffiliateCreation:
    """Testa criação de afiliados."""

    def test_agent_can_create_affiliate(self):
        """Agente INSS pode criar um afiliado."""
        agent = AgentFactory()
        citizen = CitizenUserFactory()
        client = auth_client(agent)
        payload = {
            "user": citizen.pk,
            "niss": "GW000000000001",
            "full_name": "João Silva",
            "birth_date": "1980-01-15",
            "gender": "M",
            "nationality": "GW",
        }
        response = client.post("/api/v1/affiliates/", payload, format="json")
        assert response.status_code == 201
        assert Affiliate.objects.filter(niss="GW000000000001").exists()

    def test_citizen_cannot_create_affiliate(self):
        """Cidadão não pode criar afiliados (403)."""
        citizen = CitizenUserFactory()
        another_citizen = CitizenUserFactory()
        client = auth_client(citizen)
        payload = {
            "user": another_citizen.pk,
            "niss": "GW000000000002",
            "full_name": "Maria Santos",
            "birth_date": "1990-05-20",
            "gender": "F",
        }
        response = client.post("/api/v1/affiliates/", payload, format="json")
        assert response.status_code == 403

    def test_unauthenticated_cannot_create_affiliate(self):
        """Utilizador não autenticado recebe 401."""
        client = APIClient()
        response = client.post("/api/v1/affiliates/", {}, format="json")
        assert response.status_code == 401

    def test_admin_can_create_affiliate(self):
        """Admin pode criar um afiliado."""
        admin = AdminFactory()
        citizen = CitizenUserFactory()
        client = auth_client(admin)
        payload = {
            "user": citizen.pk,
            "niss": "GW000000000099",
            "full_name": "Admin Test",
            "birth_date": "1975-03-10",
            "gender": "M",
        }
        response = client.post("/api/v1/affiliates/", payload, format="json")
        assert response.status_code == 201

    def test_niss_uniqueness_constraint(self):
        """Não é possível criar dois afiliados com o mesmo NISS."""
        agent = AgentFactory()
        citizen1 = CitizenUserFactory()
        citizen2 = CitizenUserFactory()
        client = auth_client(agent)
        niss = "GW000000000077"
        AffiliateFactory(niss=niss, user=citizen1)
        payload = {
            "user": citizen2.pk,
            "niss": niss,
            "full_name": "Duplicado",
            "birth_date": "1985-01-01",
            "gender": "M",
        }
        response = client.post("/api/v1/affiliates/", payload, format="json")
        assert response.status_code == 400

    def test_non_citizen_user_cannot_be_affiliate(self):
        """Utilizador com role!=CITIZEN não pode ser afiliado."""
        agent_user = AgentFactory()
        registering_agent = AgentFactory()
        client = auth_client(registering_agent)
        payload = {
            "user": agent_user.pk,
            "niss": "GW000000000088",
            "full_name": "Agente Afiliado",
            "birth_date": "1980-01-01",
            "gender": "M",
        }
        response = client.post("/api/v1/affiliates/", payload, format="json")
        assert response.status_code == 400


@pytest.mark.django_db
class TestAffiliateMe:
    """Testa o endpoint me/ dos afiliados."""

    def test_citizen_can_see_own_profile(self):
        """Cidadão autenticado vê o seu próprio perfil via me/."""
        affiliate = AffiliateFactory()
        client = auth_client(affiliate.user)
        response = client.get("/api/v1/affiliates/me/")
        assert response.status_code == 200
        assert response.data["niss"] == affiliate.niss
        assert response.data["full_name"] == affiliate.full_name

    def test_citizen_without_affiliate_gets_404(self):
        """Cidadão sem perfil de afiliado recebe 404."""
        citizen = CitizenUserFactory()
        client = auth_client(citizen)
        response = client.get("/api/v1/affiliates/me/")
        assert response.status_code == 404

    def test_agent_cannot_access_me_endpoint(self):
        """Agente não tem acesso ao me/ de afiliados (403)."""
        agent = AgentFactory()
        client = auth_client(agent)
        response = client.get("/api/v1/affiliates/me/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestAffiliateListAndRetrieve:
    """Testa listagem e consulta de afiliados."""

    def test_agent_can_list_affiliates(self):
        """Agente pode listar afiliados."""
        agent = AgentFactory()
        AffiliateFactory.create_batch(3)
        client = auth_client(agent)
        response = client.get("/api/v1/affiliates/")
        assert response.status_code == 200
        assert len(response.data) >= 3

    def test_only_admin_can_delete_affiliate(self):
        """Apenas admin pode eliminar um afiliado."""
        agent = AgentFactory()
        affiliate = AffiliateFactory()
        client = auth_client(agent)
        response = client.delete(f"/api/v1/affiliates/{affiliate.pk}/")
        assert response.status_code == 403

    def test_admin_can_delete_affiliate(self):
        """Admin pode eliminar um afiliado."""
        admin = AdminFactory()
        affiliate = AffiliateFactory()
        client = auth_client(admin)
        response = client.delete(f"/api/v1/affiliates/{affiliate.pk}/")
        assert response.status_code == 204


@pytest.mark.django_db
class TestDependents:
    """Testa operações sobre dependentes."""

    def test_agent_can_add_dependent(self):
        """Agente pode adicionar dependente a um afiliado."""
        agent = AgentFactory()
        affiliate = AffiliateFactory()
        client = auth_client(agent)
        payload = {
            "full_name": "Filho do Afiliado",
            "birth_date": "2010-06-01",
            "relationship": "CHILD",
            "is_active": True,
        }
        response = client.post(f"/api/v1/affiliates/{affiliate.pk}/dependents/", payload, format="json")
        assert response.status_code == 201
        assert Dependent.objects.filter(affiliate=affiliate, full_name="Filho do Afiliado").exists()

    def test_agent_can_list_dependents(self):
        """Agente pode listar dependentes de um afiliado."""
        agent = AgentFactory()
        affiliate = AffiliateFactory()
        DependentFactory.create_batch(2, affiliate=affiliate)
        client = auth_client(agent)
        response = client.get(f"/api/v1/affiliates/{affiliate.pk}/dependents/")
        assert response.status_code == 200
        assert len(response.data) == 2


# ---------------------------------------------------------------------------
# Tests — Employers
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEmployerMe:
    """Testa o endpoint me/ dos empregadores."""

    def test_employer_can_see_own_profile(self):
        """Empregador vê a sua própria ficha via me/."""
        employer_profile = EmployerProfileFactory()
        client = auth_client(employer_profile.user)
        response = client.get("/api/v1/employers/me/")
        assert response.status_code == 200
        assert response.data["nuit"] == employer_profile.nuit
        assert response.data["company_name"] == employer_profile.company_name

    def test_agent_cannot_access_employer_me(self):
        """Agente não tem acesso ao me/ de empregadores (403)."""
        agent = AgentFactory()
        client = auth_client(agent)
        response = client.get("/api/v1/employers/me/")
        assert response.status_code == 403

    def test_nuit_uniqueness_constraint(self):
        """Não é possível criar dois empregadores com o mesmo NUIT."""
        agent = AgentFactory()
        employer_user1 = EmployerFactory()
        employer_user2 = EmployerFactory()
        client = auth_client(agent)
        nuit = "NUITDUPLICADO001"
        EmployerProfileFactory(nuit=nuit, user=employer_user1)
        payload = {
            "user": employer_user2.pk,
            "company_name": "Empresa Duplicada",
            "nuit": nuit,
            "sector": "PRIVATE",
            "address": "Rua Teste",
            "phone": "+245 900000000",
        }
        response = client.post("/api/v1/employers/", payload, format="json")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Tests — Contributions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestContributionCreation:
    """Testa criação e cálculo automático de contribuições."""

    def test_contribution_auto_calculates_amounts(self):
        """Criação de contribuição calcula automaticamente os montantes."""
        affiliate = AffiliateFactory()
        employer_profile = EmployerProfileFactory()
        agent = AgentFactory()
        client = auth_client(agent)
        payload = {
            "affiliate": affiliate.pk,
            "employer": employer_profile.pk,
            "period_year": 2024,
            "period_month": 3,
            "salary_base": "1000000.00",
            "employee_rate": "0.0400",
            "employer_rate": "0.0800",
            "status": "PENDING",
        }
        response = client.post("/api/v1/contributions/", payload, format="json")
        assert response.status_code == 201
        contrib = Contribution.objects.get(pk=response.data["id"])
        assert contrib.employee_amount == Decimal("40000.00")
        assert contrib.employer_amount == Decimal("80000.00")
        assert contrib.total_amount == Decimal("120000.00")

    def test_contribution_reference_auto_generated(self):
        """Referência da contribuição é gerada automaticamente."""
        affiliate = AffiliateFactory(niss="GW000000000042")
        agent = AgentFactory()
        contrib = ContributionFactory(affiliate=affiliate, period_year=2024, period_month=5, created_by=agent)
        assert contrib.reference == f"COTT-202405-GW000000000042"

    def test_contribution_unique_per_period(self):
        """Não é possível criar duas contribuições para o mesmo afiliado/período."""
        agent = AgentFactory()
        affiliate = AffiliateFactory()
        employer_profile = EmployerProfileFactory()
        ContributionFactory(affiliate=affiliate, period_year=2024, period_month=6, created_by=agent)
        client = auth_client(agent)
        payload = {
            "affiliate": affiliate.pk,
            "employer": employer_profile.pk,
            "period_year": 2024,
            "period_month": 6,
            "salary_base": "500000.00",
        }
        response = client.post("/api/v1/contributions/", payload, format="json")
        assert response.status_code == 400

    def test_citizen_cannot_create_contribution(self):
        """Cidadão não pode criar contribuições (403)."""
        affiliate = AffiliateFactory()
        citizen = affiliate.user
        client = auth_client(citizen)
        payload = {
            "affiliate": affiliate.pk,
            "period_year": 2024,
            "period_month": 7,
            "salary_base": "300000.00",
        }
        response = client.post("/api/v1/contributions/", payload, format="json")
        assert response.status_code == 403

    def test_agent_can_mark_contribution_paid(self):
        """Agente pode atualizar o estado de uma contribuição para PAID."""
        agent = AgentFactory()
        contrib = ContributionFactory(created_by=agent, status="PENDING")
        client = auth_client(agent)
        response = client.patch(
            f"/api/v1/contributions/{contrib.pk}/",
            {"status": "PAID", "payment_date": "2024-03-15"},
            format="json",
        )
        assert response.status_code == 200
        contrib.refresh_from_db()
        assert contrib.status == "PAID"


@pytest.mark.django_db
class TestContributionFilters:
    """Testa filtros nas contribuições."""

    def test_filter_contributions_by_status(self):
        """Filtro por status funciona corretamente."""
        agent = AgentFactory()
        affiliate = AffiliateFactory()
        ContributionFactory(affiliate=affiliate, period_month=1, created_by=agent, status="PENDING")
        ContributionFactory(affiliate=affiliate, period_month=2, created_by=agent, status="PAID")
        ContributionFactory(affiliate=affiliate, period_month=3, created_by=agent, status="LATE")
        client = auth_client(agent)
        response = client.get("/api/v1/contributions/?status=PAID")
        assert response.status_code == 200
        assert all(c["status"] == "PAID" for c in response.data)

    def test_filter_contributions_by_year(self):
        """Filtro por ano funciona corretamente."""
        agent = AgentFactory()
        affiliate = AffiliateFactory()
        ContributionFactory(affiliate=affiliate, period_year=2023, period_month=1, created_by=agent)
        ContributionFactory(affiliate=affiliate, period_year=2024, period_month=2, created_by=agent)
        client = auth_client(agent)
        response = client.get("/api/v1/contributions/?year=2023")
        assert response.status_code == 200
        assert all(c["period_year"] == 2023 for c in response.data)


@pytest.mark.django_db
class TestContributionSummary:
    """Testa o endpoint summary das contribuições."""

    def test_agent_can_see_affiliate_summary(self):
        """Agente pode ver o resumo de contribuições de um afiliado."""
        agent = AgentFactory()
        affiliate = AffiliateFactory()
        ContributionFactory(affiliate=affiliate, period_month=1, created_by=agent, salary_base="500000.00")
        ContributionFactory(affiliate=affiliate, period_month=2, created_by=agent, salary_base="500000.00")
        client = auth_client(agent)
        response = client.get(f"/api/v1/contributions/affiliate/{affiliate.pk}/summary/")
        assert response.status_code == 200
        assert response.data["months_contributed"] == 2
        assert response.data["affiliate_id"] == affiliate.pk
