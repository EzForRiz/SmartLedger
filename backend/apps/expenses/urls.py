# apps/expenses/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home),
    path('dashboard/', views.dashboard),
    path('rosca/', views.rosca),
    path('expenses/', views.expenses_list),
    path('expenses/<int:id>/', views.delete_expense),
    path('insights/', views.insights),
]