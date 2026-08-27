from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Product, ProductCategory
from .forms import ProductForm, CategoryForm

@login_required
def product_list(request):
    # กรองเอาเฉพาะหมวดหมู่และสินค้าของผู้ใช้ที่ล็อกอินเท่านั้น
    categories = ProductCategory.objects.filter(
        is_active=True, created_by=request.user
    ).prefetch_related("products")

    context = {
        "categories": categories,
        "products": Product.objects.filter(created_by=request.user),
    }
    return render(request, "Products/list.html", context)

@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user # ผูก User คนสร้าง
            product.save()
            return redirect('products:list')
    else:
        form = ProductForm()
        # กรองหมวดหมู่ในตัวเลือก ให้แสดงเฉพาะของ User นี้
        form.fields['category'].queryset = ProductCategory.objects.filter(created_by=request.user)

    return render(request, "Products/form.html", {"form": form, "title": "เพิ่มสินค้าใหม่"})

@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk, created_by=request.user)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('products:list')
    else:
        form = ProductForm(instance=product)
        form.fields['category'].queryset = ProductCategory.objects.filter(created_by=request.user)

    return render(request, "Products/form.html", {"form": form, "title": f"แก้ไข: {product.name}"})

@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, created_by=request.user)
    product.delete()
    return redirect('products:list')

@login_required
def category_manage(request):
    # สร้างหรือแก้ไขหมวดหมู่แบบรวดเร็ว
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            return redirect('products:category_manage')
    else:
        form = CategoryForm()
        
    categories = ProductCategory.objects.filter(created_by=request.user)
    return render(request, "Products/category_manage.html", {"form": form, "categories": categories})