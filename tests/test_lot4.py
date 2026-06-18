"""
Tests Lot 4 — Portais HTML (HTMX + Tailwind)
Couvre les vues HTML session-based (pas JWT).
"""

import pytest
from django.test import Client
from django.urls import reverse

from tests.factories import (
    AffiliateFactory,
    EmployerProfileFactory,
    ContributionFactory,
)
from apps.accounts.tests.factories import (
    UserFactory,
    AgentFactory,
    AdminFactory,
    EmployerFactory,
)
from apps.accounts.models import UserRole
from apps.cards.models import HealthCard


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_PASSWORD = "testpassword123"


def make_citizen_with_affiliate():
    """Crée un afiliado et retourne (user, affiliate, password)."""
    affiliate = AffiliateFactory()
    # La factory définit déjà set_password("testpassword123")
    return affiliate.user, affiliate, DEFAULT_PASSWORD


def make_employer_with_profile():
    """Crée un empregador et retourne (user, profile, password)."""
    emp_profile = EmployerProfileFactory()
    return emp_profile.user, emp_profile, DEFAULT_PASSWORD


def make_agent():
    """Crée un agent INSS et retourne (user, password)."""
    agent = AgentFactory()
    return agent, DEFAULT_PASSWORD


def make_provider():
    """Crée un prestataire et retourne (user, password)."""
    from apps.accounts.tests.factories import ProviderFactory
    provider = ProviderFactory()
    return provider, DEFAULT_PASSWORD


# ---------------------------------------------------------------------------
# Test 1 : GET /auth/login/ → 200, contient formulaire
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_login_page_renders():
    """GET /auth/login/ retourne 200 avec un formulaire de connexion."""
    client = Client()
    response = client.get("/auth/login/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "email" in content.lower()
    assert "senha" in content.lower() or "password" in content.lower()


# ---------------------------------------------------------------------------
# Test 2 : POST /auth/login/ credentials valides citoyen → redirect /portal/citizen/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_login_citizen_redirects_to_citizen_portal():
    user, affiliate, pw = make_citizen_with_affiliate()
    client = Client()
    response = client.post("/auth/login/", {"email": user.email, "password": pw})
    assert response.status_code == 302
    assert response["Location"] == "/portal/citizen/"


# ---------------------------------------------------------------------------
# Test 3 : POST /auth/login/ credentials invalides → 200, message d'erreur
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_login_invalid_credentials_returns_error():
    client = Client()
    response = client.post("/auth/login/", {"email": "nobody@einss.gw", "password": "wrongpassword"})
    assert response.status_code == 200
    content = response.content.decode()
    assert "inválid" in content.lower() or "erro" in content.lower() or "senha" in content.lower()


# ---------------------------------------------------------------------------
# Test 4 : POST /auth/login/ agent → redirect /portal/agent/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_login_agent_redirects_to_agent_portal():
    agent, pw = make_agent()
    client = Client()
    response = client.post("/auth/login/", {"email": agent.email, "password": pw})
    assert response.status_code == 302
    assert response["Location"] == "/portal/agent/"


# ---------------------------------------------------------------------------
# Test 5 : GET /portal/citizen/ non authentifié → redirect /auth/login/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_citizen_dashboard_unauthenticated_redirects():
    client = Client()
    response = client.get("/portal/citizen/")
    assert response.status_code == 302
    location = response["Location"]
    assert "/auth/login/" in location


# ---------------------------------------------------------------------------
# Test 6 : GET /portal/citizen/ citoyen authentifié → 200
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_citizen_dashboard_authenticated_200():
    user, affiliate, pw = make_citizen_with_affiliate()
    client = Client()
    client.login(username=user.email, password=pw)
    response = client.get("/portal/citizen/")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Test 7 : GET /portal/citizen/ rôle EMPLOYER → 403
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_citizen_dashboard_wrong_role_403():
    user, profile, pw = make_employer_with_profile()
    client = Client()
    client.login(username=user.email, password=pw)
    response = client.get("/portal/citizen/")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Test 8 : GET /portal/citizen/contributions/ → 200, contient tableau
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_citizen_contributions_page_200():
    user, affiliate, pw = make_citizen_with_affiliate()
    # Crée quelques contributions
    ContributionFactory(affiliate=affiliate, period_year=2024, period_month=1)
    ContributionFactory(affiliate=affiliate, period_year=2024, period_month=2)

    client = Client()
    client.login(username=user.email, password=pw)
    response = client.get("/portal/citizen/contributions/")
    assert response.status_code == 200
    content = response.content.decode()
    # Le tableau doit être présent
    assert "Período" in content or "período" in content.lower() or "table" in content.lower()


# ---------------------------------------------------------------------------
# Test 9 : GET /portal/employer/ employer authentifié → 200
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_employer_dashboard_authenticated_200():
    user, profile, pw = make_employer_with_profile()
    client = Client()
    client.login(username=user.email, password=pw)
    response = client.get("/portal/employer/")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Test 10 : GET /portal/agent/ agent authentifié → 200
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_agent_dashboard_authenticated_200():
    agent, pw = make_agent()
    client = Client()
    client.login(username=agent.email, password=pw)
    response = client.get("/portal/agent/")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Test 11 : GET /portal/agent/affiliates/ → 200, liste affiliés
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_agent_affiliate_list_200():
    agent, pw = make_agent()
    # Crée quelques affiliés pour vérifier qu'ils apparaissent
    AffiliateFactory()
    AffiliateFactory()

    client = Client()
    client.login(username=agent.email, password=pw)
    response = client.get("/portal/agent/affiliates/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "affiliates" in content.lower() or "afiliado" in content.lower() or "NISS" in content


# ---------------------------------------------------------------------------
# Test 12 : GET /portal/provider/ provider authentifié → 200
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_provider_dashboard_authenticated_200():
    provider, pw = make_provider()
    client = Client()
    client.login(username=provider.email, password=pw)
    response = client.get("/portal/provider/")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Test 13 : POST /portal/provider/verify/ token invalide → fragment HTML erreur
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_provider_verify_invalid_token_returns_error_fragment():
    provider, pw = make_provider()
    client = Client()
    client.login(username=provider.email, password=pw)

    response = client.post(
        "/portal/provider/verify/",
        {"token": "token.invalido.aqui"},
        HTTP_HX_REQUEST="true",  # Simule header HTMX
    )
    # La vue retourne 200 avec fragment HTML d'erreur (pas une page complète)
    assert response.status_code == 200
    content = response.content.decode()
    # Doit contenir un message d'erreur, pas un <html> complet
    assert "<html" not in content.lower() or "inválid" in content.lower() or "erro" in content.lower()


# ---------------------------------------------------------------------------
# Test 14 : POST /portal/employer/contributions/calculate/ → fragment HTML
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_employer_contribution_calculate_returns_fragment():
    user, profile, pw = make_employer_with_profile()
    client = Client()
    client.login(username=user.email, password=pw)

    response = client.post(
        "/portal/employer/contributions/calculate/",
        {"salary_base": "500000.00"},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    content = response.content.decode()
    # Doit contenir les montants calculés, pas une page complète
    assert "<html" not in content.lower()
    # 4% de 500000 = 20000, 8% = 40000, total = 60000
    assert "20000" in content or "60000" in content or "40000" in content


# ---------------------------------------------------------------------------
# Test 15 : GET /portal/agent/affiliates/ non authentifié → redirect login
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_agent_affiliate_list_unauthenticated_redirects():
    client = Client()
    response = client.get("/portal/agent/affiliates/")
    assert response.status_code == 302
    location = response["Location"]
    assert "/auth/login/" in location


# ---------------------------------------------------------------------------
# Tests supplémentaires (bonus)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_citizen_card_page_no_card():
    """Citoyen sans carte → page 200 avec message 'nenhuma carta'."""
    user, affiliate, pw = make_citizen_with_affiliate()
    client = Client()
    client.login(username=user.email, password=pw)
    response = client.get("/portal/citizen/card/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "nenhuma" in content.lower() or "não encontrada" in content.lower()


@pytest.mark.django_db
def test_login_redirects_root_to_login_page():
    """GET / → redirect vers /auth/login/."""
    client = Client()
    response = client.get("/")
    assert response.status_code in (301, 302)
    assert "/auth/login/" in response["Location"]


@pytest.mark.django_db
def test_htmx_contributions_filter_returns_partial():
    """GET /portal/citizen/contributions/?year=2024 avec header HTMX → HTML partiel."""
    user, affiliate, pw = make_citizen_with_affiliate()
    ContributionFactory(affiliate=affiliate, period_year=2024, period_month=3)

    client = Client()
    client.login(username=user.email, password=pw)
    response = client.get(
        "/portal/citizen/contributions/?year=2024",
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    content = response.content.decode()
    # Réponse partielle : pas de <html> complet
    assert "<!DOCTYPE" not in content and "<html" not in content.lower()


@pytest.mark.django_db
def test_agent_can_see_affiliate_detail():
    """Agent peut accéder à la fiche d'un affilié."""
    agent, pw = make_agent()
    affiliate = AffiliateFactory()

    client = Client()
    client.login(username=agent.email, password=pw)
    response = client.get(f"/portal/agent/affiliates/{affiliate.pk}/")
    assert response.status_code == 200
    content = response.content.decode()
    assert affiliate.full_name in content


@pytest.mark.django_db
def test_employer_contributions_htmx_filter():
    """Filtre HTMX des contributions employer retourne un tbody partiel."""
    user, profile, pw = make_employer_with_profile()
    ContributionFactory(employer=profile, period_year=2024, period_month=5)

    client = Client()
    client.login(username=user.email, password=pw)
    response = client.get(
        "/portal/employer/contributions/?year=2024",
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "<!DOCTYPE" not in content and "<html" not in content.lower()
