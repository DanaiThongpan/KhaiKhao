from django.urls import path
from . import views

app_name = 'riders'

urlpatterns = [
    path('', views.rider_dashboard, name='home'),
    path('track/<int:order_id>/', views.rider_tracking_page, name='tracking_page'),
    path('api/update/<int:order_id>/', views.update_location_api, name='update_api'),
    path('api/get/<int:order_id>/', views.get_location_api, name='get_api'),
    path('api/save-dest/<int:order_id>/', views.save_destination_api, name='save_dest'),
    path('api/complete/<int:order_id>/', views.complete_delivery_api, name='complete_delivery'),
    
    path('dormitories/', views.dormitory_map_page, name='dormitory_map'),
    path('api/add-dormitory/', views.add_dormitory_api, name='add_dormitory'),
    
    # 🌟 เพิ่มบรรทัดนี้: API สำหรับแก้ไขหอพัก
    path('api/edit-dormitory/<int:dorm_id>/', views.edit_dormitory_api, name='edit_dormitory'),
# 🌟 เพิ่มบรรทัดนี้: API สำหรับลบหอพัก
    path('api/delete-dormitory/<int:dorm_id>/', views.delete_dormitory_api, name='delete_dormitory'),
    path('api/start-delivery/<int:order_id>/', views.start_delivery_api, name='start_delivery'),
    path('api/complete-delivery/<int:order_id>/', views.complete_delivery_api, name='complete_delivery'),
]