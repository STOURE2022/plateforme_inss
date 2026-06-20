from django.urls import path
from . import html_views

urlpatterns = [
    path("", html_views.ProviderDashboardView.as_view(), name="provider-dashboard"),
    path("verify/", html_views.ProviderVerifyView.as_view(), name="provider-verify"),
    path("verify/by-number/", html_views.ProviderVerifyByNumberView.as_view(), name="provider-verify-by-number"),
    path("verify/register-act/", html_views.ProviderRegisterActView.as_view(), name="provider-register-act"),
    path("my-acts/", html_views.ProviderMyActsView.as_view(), name="provider-my-acts"),
    path("my-acts/<int:pk>/", html_views.ProviderActDetailView.as_view(), name="provider-act-detail"),
    path("profile/", html_views.ProviderProfileView.as_view(), name="provider-profile"),
    path("history/", html_views.ProviderHistoryView.as_view(), name="provider-history"),
]
