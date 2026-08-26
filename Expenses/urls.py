from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('', views.expense_home, name='home'),
    path('edit/<int:expense_id>/', views.expense_edit, name='edit'),
    path('delete/<int:expense_id>/', views.expense_delete, name='delete'),
]