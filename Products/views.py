from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CategoryForm, ProductForm
from .models import Product, ProductCategory


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
            product.created_by = request.user  # ผูก User คนสร้าง
            product.save()
            return redirect("products:list")
    else:
        form = ProductForm()
        # กรองหมวดหมู่ในตัวเลือก ให้แสดงเฉพาะของ User นี้
        form.fields["category"].queryset = ProductCategory.objects.filter(
            created_by=request.user
        )

    return render(
        request, "Products/form.html", {"form": form, "title": "เพิ่มสินค้าใหม่"}
    )


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk, created_by=request.user)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect("products:list")
    else:
        form = ProductForm(instance=product)
        form.fields["category"].queryset = ProductCategory.objects.filter(
            created_by=request.user
        )

    return render(
        request, "Products/form.html", {"form": form, "title": f"แก้ไข: {product.name}"}
    )


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, created_by=request.user)
    product.delete()
    return redirect("products:list")


@login_required
def category_manage(request):
    # สร้างหรือแก้ไขหมวดหมู่แบบรวดเร็ว
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            return redirect("products:category_manage")
    else:
        form = CategoryForm()

    categories = ProductCategory.objects.filter(created_by=request.user)
    return render(
        request,
        "Products/category_manage.html",
        {"form": form, "categories": categories},
    )

import json
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.shortcuts import render
from .models import WebhookLog # อย่าลืม Import Model ที่เพิ่งสร้าง

@csrf_exempt
def facebook_webhook(request):
    VERIFY_TOKEN = "KhaiKhao_Secret_Token_2026" 
    
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return HttpResponse(challenge, status=200)
        else:
            return HttpResponseForbidden('รหัสลับไม่ถูกต้อง', status=403)
            
    elif request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            
            # หาชื่อ Event คร่าวๆ ว่า Facebook ส่งอะไรมา
            event_type = "UNKNOWN EVENT"
            if 'object' in body_data:
                event_type = body_data['object']
            elif 'field' in body_data.get('sample', {}): # กรณีปุ่ม Test จากหน้าเว็บ
                event_type = body_data['sample']['field']
                
            # 🌟 บันทึกข้อมูลดิบลง Database เลยเพื่อเอาไปโชว์ในหน้าทดสอบ
            WebhookLog.objects.create(
                event_type=event_type,
                payload=json.dumps(body_data, indent=4, ensure_ascii=False)
            )
            
            return HttpResponse('EVENT_RECEIVED', status=200)

        except Exception as e:
            print("❌ Webhook Error:", e)
            return HttpResponse('ERROR', status=400)

# ==========================================
# 🌟 เพิ่มฟังก์ชันสำหรับหน้าจอแสดงผล Webhook Test 🌟
# ==========================================
def webhook_test_page(request):
    """ ดึงประวัติ Webhook 50 รายการล่าสุดมาแสดง """
    logs = WebhookLog.objects.all().order_by('-received_at')[:50]
    
    # ถ้ารับค่า action=clear ให้ล้างข้อมูลทั้งหมด (ปุ่มล้างจอ)
    if request.GET.get('action') == 'clear':
        WebhookLog.objects.all().delete()
        logs = []
        
    return render(request, 'Products/webhook_test.html', {'logs': logs})