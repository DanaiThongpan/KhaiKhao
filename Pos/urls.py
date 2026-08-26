from django.urls import path
from . import views

app_name = "pos"

urlpatterns = [
    path("", views.home, name="home"),
    path('checkout/', views.process_checkout, name='checkout'), # เพิ่มบรรทัดนี้
]