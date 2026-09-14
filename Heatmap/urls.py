from django.urls import path
from . import views

app_name = 'heatmap'

urlpatterns = [
    path('', views.heatmap_dashboard, name='home'),
]