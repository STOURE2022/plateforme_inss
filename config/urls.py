from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf.urls.i18n import set_language
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Page d'accueil publique
    path("", TemplateView.as_view(template_name="landing.html"), name="home"),

    # i18n language switcher
    path("i18n/set-language/", set_language, name="set_language"),

    # Admin Django
    path("admin/", admin.site.urls),

    # API REST (JWT)
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.affiliates.urls")),
    path("api/v1/", include("apps.employers.urls")),
    path("api/v1/", include("apps.contributions.urls")),
    path("api/v1/", include("apps.cards.urls")),
    path("api/v1/", include("apps.verification.urls")),
    path("api/v1/", include("apps.audit.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.benefits.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Portais HTML (sessions Django)
    path("auth/", include("apps.accounts.html_urls")),
    path("portal/citizen/", include("apps.affiliates.html_urls")),
    path("portal/employer/", include("apps.employers.html_urls")),
    path("portal/agent/", include("apps.accounts.agent_html_urls")),
    path("portal/provider/", include("apps.verification.html_urls")),
    path("notifications/", include("apps.notifications.html_urls")),
    path("portal/citizen/benefits/", include("apps.benefits.citizen_html_urls")),
    path("portal/agent/benefits/", include("apps.benefits.agent_html_urls")),
    path("portal/citizen/claims/", include("apps.claims.citizen_html_urls")),
    path("portal/agent/claims/", include("apps.claims.agent_html_urls")),
    path("api/v1/", include("apps.claims.urls")),
    path("", include("apps.contributions.html_urls")),
    path("", include("apps.statistics_dashboard.urls")),
    path("", include("apps.payroll.html_urls")),
]
