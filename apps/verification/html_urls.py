from django.urls import path
from . import html_views

urlpatterns = [
    path("", html_views.ProviderDashboardView.as_view(), name="provider-dashboard"),
    path("verify/", html_views.ProviderVerifyView.as_view(), name="provider-verify"),
    path("history/", html_views.ProviderHistoryView.as_view(), name="provider-history"),
]
