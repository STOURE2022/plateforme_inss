from django.urls import path
from . import html_views

urlpatterns = [
    path("login/", html_views.HTMLLoginView.as_view(), name="html-login"),
    path("logout/", html_views.HTMLLogoutView.as_view(), name="html-logout"),
    path("mfa/", html_views.HTMLMFAVerifyView.as_view(), name="html-mfa"),
    path("mfa/setup/", html_views.HTMLMFASetupView.as_view(), name="html-mfa-setup"),
    path("mfa/disable/", html_views.HTMLMFADisableView.as_view(), name="html-mfa-disable"),
    path("settings/security/", html_views.HTMLSecuritySettingsView.as_view(), name="html-security-settings"),
    path("register/", html_views.HTMLRegisterView.as_view(), name="html-register"),
]
