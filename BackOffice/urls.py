from django.urls import path
from . import views

app_name = 'backoffice'

urlpatterns = [
    path('', views.admin_dashboard, name='home'),
    path('shop/<int:shop_id>/', views.shop_manage, name='shop_manage'), # 🌟 เพิ่มบรรทัดนี้
    path('live-monitor/', views.live_monitor, name='live_monitor'),
    path('api/live-monitor/', views.api_live_monitor, name='api_live_monitor'),
]