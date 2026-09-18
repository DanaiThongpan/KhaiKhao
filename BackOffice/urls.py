from django.urls import path
from . import views

app_name = 'backoffice'

urlpatterns = [
    path('', views.admin_dashboard, name='home'),
    path('shop/<int:shop_id>/', views.shop_manage, name='shop_manage'), # 🌟 เพิ่มบรรทัดนี้
    path('live-monitor/', views.live_monitor, name='live_monitor'),
    path('api/live-monitor/', views.api_live_monitor, name='api_live_monitor'),
# ... path เดิมที่มีอยู่แล้ว ...
    path('api/force-clear-pending/', views.force_clear_pending_api, name='force_clear_pending_api'), # 🌟 เพิ่มบรรทัดนี้
# ... path อื่นๆ ...
    path('financial-dashboard/', views.financial_dashboard, name='financial_dashboard'), # 🌟 เพิ่มบรรทัดนี้
    path('rider-map/', views.rider_map, name='rider_map'),
    path('api/rider-locations/', views.api_rider_locations, name='api_rider_locations'),
]