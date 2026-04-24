# urls.py in smartledger folder. note: root folder is SmartLedger which contains all folders such as apps folder, expenses folder, static folder, templates folder etc.


from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('apps.expenses.urls')),
]