from django.urls import path
from . import views

app_name = 'shop_history'

urlpatterns = [
    path('', views.history_page, name='home'),
    path('api/toggle-status/', views.toggle_shop_status, name='toggle_status'),
    path('closures/', views.closure_history_page, name='closures'),
    path('calendar/', views.calendar_dashboard, name='calendar'),
    
    # 🌟 2 บรรทัดที่ต้องเพิ่มสำหรับ Edit และ Delete
    path('edit/<int:session_id>/', views.edit_session, name='edit_session'),
    path('delete/<int:session_id>/', views.delete_session, name='delete_session'),
]