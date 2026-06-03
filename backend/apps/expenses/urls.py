# apps/expenses/urls.py

from django.urls import path, include
from . import views

urlpatterns = [

    path("", views.home),

    path("dashboard/", views.dashboard),

    path("rosca/", include("apps.rosca.urls")),

    path("login/", views.login_view),

    path("register/", views.register_view),

    path("logout/", views.logout_view),

    path("expenses/", views.expenses_list),

    path("expenses/clear/", views.clear_all_expenses),

    path("expenses/<int:id>/", views.expense_detail),

    path("insights/", views.insights),

    path("financial-insights/", include("apps.ai_insights.urls")),

    path("income/", views.income_view),
    path("income/history/", views.income_history_view),
    path("income/<int:id>/", views.income_detail),

    path("finance-summary/", views.finance_summary),
]