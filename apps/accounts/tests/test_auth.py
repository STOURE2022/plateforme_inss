import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.tests.factories import UserFactory, AgentFactory
import pyotp


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory(email="citizen@test.com")


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, client, user):
        url = reverse("auth-login")
        response = client.post(url, {"email": "citizen@test.com", "password": "testpassword123"})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["mfa_required"] is False

    def test_login_wrong_password(self, client, user):
        url = reverse("auth-login")
        response = client.post(url, {"email": "citizen@test.com", "password": "wrongpassword"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_inactive_user(self, client, db):
        inactive = UserFactory(email="inactive@test.com", is_active=False)
        url = reverse("auth-login")
        response = client.post(url, {"email": "inactive@test.com", "password": "testpassword123"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_mfa_required(self, client, db):
        secret = pyotp.random_base32()
        mfa_user = UserFactory(email="mfa@test.com", mfa_enabled=True, mfa_secret=secret)
        url = reverse("auth-login")
        response = client.post(url, {"email": "mfa@test.com", "password": "testpassword123"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["mfa_required"] is True
        assert "pre_auth_token" in response.data
        assert "access" not in response.data


@pytest.mark.django_db
class TestMFAVerify:
    def test_mfa_verify_success(self, client, db):
        secret = pyotp.random_base32()
        mfa_user = UserFactory(email="mfa2@test.com", mfa_enabled=True, mfa_secret=secret)
        # Login first to get pre_auth_token
        login_url = reverse("auth-login")
        login_resp = client.post(login_url, {"email": "mfa2@test.com", "password": "testpassword123"})
        pre_auth_token = login_resp.data["pre_auth_token"]

        # Verify MFA
        totp = pyotp.TOTP(secret)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {pre_auth_token}")
        verify_url = reverse("auth-mfa-verify")
        response = client.post(verify_url, {"code": totp.now()})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_mfa_verify_wrong_code(self, client, db):
        secret = pyotp.random_base32()
        mfa_user = UserFactory(email="mfa3@test.com", mfa_enabled=True, mfa_secret=secret)
        login_url = reverse("auth-login")
        login_resp = client.post(login_url, {"email": "mfa3@test.com", "password": "testpassword123"})
        pre_auth_token = login_resp.data["pre_auth_token"]

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {pre_auth_token}")
        verify_url = reverse("auth-mfa-verify")
        response = client.post(verify_url, {"code": "000000"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTokenRefresh:
    def test_token_refresh(self, client, user):
        login_url = reverse("auth-login")
        login_resp = client.post(login_url, {"email": "citizen@test.com", "password": "testpassword123"})
        refresh_token = login_resp.data["refresh"]

        refresh_url = reverse("auth-refresh")
        response = client.post(refresh_url, {"refresh": refresh_token})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data


@pytest.mark.django_db
class TestMeEndpoint:
    def test_me_authenticated(self, client, user):
        login_url = reverse("auth-login")
        login_resp = client.post(login_url, {"email": "citizen@test.com", "password": "testpassword123"})
        access = login_resp.data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        me_url = reverse("auth-me")
        response = client.get(me_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "citizen@test.com"

    def test_me_unauthenticated(self, client):
        me_url = reverse("auth-me")
        response = client.get(me_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
