from django.urls import path
from . import html_views

app_name = "citizen_benefits"

urlpatterns = [
    path("list/", html_views.CitizenBenefitListView.as_view(), name="citizen_benefit_list"),
    path("new/", html_views.CitizenBenefitCreateView.as_view(), name="citizen_benefit_create"),
    path("<int:pk>/", html_views.CitizenBenefitDetailView.as_view(), name="citizen_benefit_detail"),
    path("<int:pk>/submit/", html_views.CitizenBenefitSubmitView.as_view(), name="citizen_benefit_submit"),
    path("<int:pk>/documents/", html_views.CitizenBenefitDocumentUploadView.as_view(), name="citizen_benefit_docs"),
]
