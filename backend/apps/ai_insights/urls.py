from django.urls import path

from . import views

urlpatterns = [
    path("", views.insights_hub, name="insights_hub"),
    path("api/", views.insights_analysis_api, name="insights_analysis_api"),
]
