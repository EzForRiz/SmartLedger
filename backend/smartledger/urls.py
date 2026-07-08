# backend/smartledger/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.expenses.urls')),
    path('', include('apps.rosca.urls')),
    path('', include('apps.ai_insights.urls')),
]