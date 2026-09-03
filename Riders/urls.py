from django.urls import path
from . import views

app_name = 'riders'

urlpatterns = [
    path('', views.rider_dashboard, name='home'),
    path('track/<int:order_id>/', views.rider_tracking_page, name='tracking_page'),
    path('api/update/<int:order_id>/', views.update_location_api, name='update_api'),
    path('api/get/<int:order_id>/', views.get_location_api, name='get_api'),
]