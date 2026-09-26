from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("", views.product_list, name="list"),
    path("create/", views.product_create, name="create"),
    path("<int:pk>/edit/", views.product_edit, name="edit"),
    path("<int:pk>/delete/", views.product_delete, name="delete"),
    path("categories/", views.category_manage, name="category_manage"),
    path('webhook-test/', views.webhook_test_page, name='webhook_test_page'),
    path('api/facebook-webhook/', views.facebook_webhook, name='facebook_webhook'),
]
