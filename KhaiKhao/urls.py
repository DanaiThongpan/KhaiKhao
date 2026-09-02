"""
URL configuration for KhaiKhao project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Pos.urls')),
    path('accounts/', include('Accounts.urls')),
    path('products/', include('Products.urls')),
    path('expenses/', include('Expenses.urls')),
    path('reports/', include('Reports.urls')),
    path('taxs/', include('Taxs.urls')),
    path('history/', include('History.urls')),
    path('stocks/', include('Stocks.urls')),
]
