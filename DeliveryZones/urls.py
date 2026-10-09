from django.urls import path
from . import views

app_name = 'delivery_zones'

urlpatterns = [
    path('', views.dashboard, name='home'),
    path('api/save/', views.save_zone, name='save_zone'),
    path('api/delete/<int:zone_id>/', views.delete_zone, name='delete_zone'),
]
