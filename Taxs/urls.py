from django.urls import path
from . import views

app_name = 'tax'

urlpatterns = [
    path('', views.tax_home_view, name='home'),
]