from django.urls import path
from . import views

app_name = 'history'

urlpatterns = [
    path('', views.history_list, name='home'),
    path('edit/<int:order_id>/', views.edit_order, name='edit_order'), # เพิ่มบรรทัดนี้
]