# backend/apps/rosca/urls.py

from django.urls import path

from . import views

urlpatterns = [
    path("", views.rosca_index, name="rosca_index"),
    path("register/", views.rosca_register, name="rosca_register"),
    path("account/", views.rosca_account, name="rosca_account"),
    path("deposit/", views.rosca_deposit, name="rosca_deposit"),
    path("receipt/<int:payment_id>/", views.rosca_receipt, name="rosca_receipt"),
    path("admin/draw/", views.rosca_admin_draw, name="rosca_admin_draw"),
]
