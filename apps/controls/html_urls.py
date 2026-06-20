from django.urls import path

from .html_views import (
    ControlAddAssessmentView,
    ControlAddDocumentView,
    ControlAddPaymentView,
    ControlCreateView,
    ControlDetailView,
    ControlListView,
    ControlPVView,
    ControlRemoveAssessmentView,
    ControlStatusActionView,
)

app_name = "agent_controls"

urlpatterns = [
    path(
        "portal/agent/controls/",
        ControlListView.as_view(),
        name="agent-control-list",
    ),
    path(
        "portal/agent/controls/new/",
        ControlCreateView.as_view(),
        name="agent-control-create",
    ),
    path(
        "portal/agent/controls/<int:pk>/",
        ControlDetailView.as_view(),
        name="agent-control-detail",
    ),
    path(
        "portal/agent/controls/<int:pk>/assessment/add/",
        ControlAddAssessmentView.as_view(),
        name="agent-control-add-assessment",
    ),
    path(
        "portal/agent/controls/<int:pk>/assessment/<int:apk>/remove/",
        ControlRemoveAssessmentView.as_view(),
        name="agent-control-remove-assessment",
    ),
    path(
        "portal/agent/controls/<int:pk>/action/",
        ControlStatusActionView.as_view(),
        name="agent-control-action",
    ),
    path(
        "portal/agent/controls/<int:pk>/payment/",
        ControlAddPaymentView.as_view(),
        name="agent-control-add-payment",
    ),
    path(
        "portal/agent/controls/<int:pk>/document/",
        ControlAddDocumentView.as_view(),
        name="agent-control-add-document",
    ),
    path(
        "portal/agent/controls/<int:pk>/pv.pdf/",
        ControlPVView.as_view(),
        name="agent-control-pv-pdf",
    ),
]
