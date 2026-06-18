from django.urls import path
from . import html_views

urlpatterns = [
    path("login/", html_views.HTMLLoginView.as_view(), name="html-login"),
    path("logout/", html_views.HTMLLogoutView.as_view(), name="html-logout"),
    path("mfa/", html_views.HTMLMFAVerifyView.as_view(), name="html-mfa"),
    path("register/", html_views.HTMLRegisterView.as_view(), name="html-register"),
]
