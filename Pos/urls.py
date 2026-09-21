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
    path('confirm-slips/', views.confirm_matched_slips, name='confirm_slips')
]