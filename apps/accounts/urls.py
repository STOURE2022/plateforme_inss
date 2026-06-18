from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path("login/", views.login_view, name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("mfa/verify/", views.mfa_verify_view, name="auth-mfa-verify"),
    path("me/", views.me_view, name="auth-me"),
]
