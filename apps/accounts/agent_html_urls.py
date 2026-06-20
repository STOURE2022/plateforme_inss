from django.urls import path
from apps.affiliates import html_views as affiliate_views
from apps.employers import html_views as employer_views
from apps.verification import html_views as verification_views

urlpatterns = [
    # Dashboard
    path("", affiliate_views.AgentDashboardView.as_view(), name="agent-dashboard"),

    # Afiliados — lista
    path("affiliates/", affiliate_views.AgentAffiliateListView.as_view(), name="agent-affiliates"),

    # Afiliados — criar (dois nomes: link de navegação vs action do formulário)
    path("affiliates/new/", affiliate_views.AgentAffiliateCreateView.as_view(), name="agent-affiliate-new"),
    path("affiliates/create/", affiliate_views.AgentAffiliateCreateView.as_view(), name="agent-affiliate-create"),

    # Afiliados — detalhe
    path("affiliates/<int:pk>/", affiliate_views.AgentAffiliateDetailView.as_view(), name="agent-affiliate-detail"),

    # Carta de saúde
    path("affiliates/<int:pk>/card/", affiliate_views.AgentCardView.as_view(), name="agent-affiliate-card"),
    path("affiliates/<int:pk>/card/new/", affiliate_views.AgentCardCreateView.as_view(), name="agent-card-create"),

    # Empregadores — lista
    path("employers/", employer_views.AgentEmployerListView.as_view(), name="agent-employers"),

    # Empregadores — criar (dois nomes: link de navegação vs action do formulário)
    path("employers/new/", employer_views.AgentEmployerCreateView.as_view(), name="agent-employer-new"),
    path("employers/create/", employer_views.AgentEmployerCreateView.as_view(), name="agent-employer-create"),

    # Logs de verificação
    path("verification-logs/", affiliate_views.AgentVerificationLogView.as_view(), name="agent-verification-logs"),

    # Actos médicos
    path("medical-acts/", verification_views.AgentMedicalActListView.as_view(), name="agent-medical-act-list"),
    path("medical-acts/<int:pk>/", verification_views.AgentMedicalActReviewView.as_view(), name="agent-medical-act-review"),
]
