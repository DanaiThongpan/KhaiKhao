from django.urls import path
from . import views

app_name = 'pos'

urlpatterns = [
    path('', views.home, name='home'),
    path('checkout/', views.process_checkout, name='checkout'),
    path('mark-paid/<int:expense_id>/', views.mark_expense_paid, name='mark_paid'), 
    path('api/compare/', views.api_compare_profit, name='api_compare'), # <--- เพิ่มบรรทัดนี้
]