from django.shortcuts import render

from Products.models import Product, ProductCategory

# Create your views here.

def product_list(request):
    categories = ProductCategory.objects.filter(
        is_active=True
    ).prefetch_related("products")

    products = Product.objects.filter(
        is_active=True
    ).select_related("category")

    context = {
        "categories": categories,
        "products": products,
    }

    return render(request, "Products/list.html", context)