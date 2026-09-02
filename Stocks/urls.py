from django.urls import path
from . import views

app_name = 'stocks'

urlpatterns = [
    path('', views.stock_list, name='list'),
    path('add/', views.add_stock, name='add_stock'),
    path('log/<int:item_id>/', views.add_log, name='add_log'),
    path('delete/<int:item_id>/', views.delete_stock, name='delete_stock'),
]