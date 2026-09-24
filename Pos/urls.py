from django.urls import path
from . import views

app_name = 'pos'

urlpatterns = [
    path('', views.home, name='home'),
    path('checkout/', views.process_checkout, name='checkout'),
    path('mark-paid/<int:expense_id>/', views.mark_expense_paid, name='mark_paid'), 
    path('api/compare/', views.api_compare_profit, name='api_compare'), # <--- เพิ่มบรรทัดนี้
    path('check-slips/', views.check_slips, name='check_slips'),
    path('api/check-slips/', views.api_check_slips, name='api_check_slips'),
    path('confirm-slips/', views.confirm_matched_slips, name='confirm_slips'),
    path('mark-unpaid/', views.mark_order_unpaid, name='mark_unpaid'),
    path('reset-slip/', views.reset_slip_ref, name='reset_slip_ref'),
    path('api-process-single-slip/', views.api_process_single_slip, name='api_process_single_slip'),
    path('voice-order/', views.voice_order_page, name='voice_order'),
    path('api/voice-order/', views.api_save_voice_order, name='api_save_voice_order'),
]