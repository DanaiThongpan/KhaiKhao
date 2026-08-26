from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Prefetch
from django.contrib.auth.decorators import login_required
from Products.models import Product, ProductCategory
from .models import Order

# บังคับให้ต้องล็อกอินก่อนถึงจะเข้าหน้านี้ได้ 
# (เพื่อป้องกัน Error เวลาค้นหาของที่เป็นของ request.user)
@login_required 
def home(request):
    # 1. กรองเฉพาะ "สินค้า" ที่สร้างโดยคนที่กำลังล็อกอิน
    my_products = Product.objects.filter(
        is_active=True,
        created_by=request.user
    )

    # 2. กรองเฉพาะ "หมวดหมู่" ที่สร้างโดยคนที่กำลังล็อกอิน
    # พร้อมทั้งนำสินค้า (จากข้อ 1) มายัดใส่หมวดหมู่ให้ตรงกัน
    raw_categories = ProductCategory.objects.filter(
        is_active=True,
        created_by=request.user
    ).prefetch_related(
        Prefetch("products", queryset=my_products)
    )

    # ==========================================
    # 3. จัดเรียงหมวดหมู่ (ดันหมวดที่ระบุไปไว้หลังสุด)
    # ==========================================
    def sort_category(category):
        back_keywords = ["topping", "ท็อปปิ้ง", "กับข้าว", "เครื่องดื่ม", "เพิ่มเติม"]
        for keyword in back_keywords:
            if keyword in category.name.lower():
                return 1 
        return 0 

    categories = list(raw_categories)
    categories.sort(key=lambda c: (sort_category(c), c.name))

    # ==========================================
    # 4. คำนวณยอดขายของ "วันนี้" (กรองเอาเฉพาะบิลที่ User คนนี้เป็นคนขาย)
    # ==========================================
    today = timezone.localdate()
    daily_sales = Order.objects.filter(
        created_at__date=today,
        created_by=request.user  # <--- เพิ่มเงื่อนไขตรงนี้
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        "categories": categories,
        "products": my_products, # ส่งรายการสินค้าของตัวเองไปนับจำนวน
        "daily_sales": daily_sales,
    }

    return render(
        request,
        "Pos/home.html",
        context
    )
# (ส่วนฟังก์ชัน process_checkout ปล่อยไว้เหมือนเดิมครับ)

import json
from django.http import JsonResponse
from django.utils.crypto import get_random_string
from .models import Order, OrderItem
from Products.models import Product

# (ฟังก์ชัน home เดิมปล่อยไว้เหมือนเดิมครับ)

def process_checkout(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cart_items = data.get('cart', [])
            
            if not cart_items:
                return JsonResponse({"status": "error", "message": "ตะกร้าว่างเปล่า"}, status=400)

            receipt_number = "INV-" + get_random_string(8).upper()
            total_amount = sum(item['price'] * item['qty'] for item in cart_items)

            order = Order.objects.create(
                receipt_number=receipt_number,
                total_amount=total_amount,
                created_by=request.user if request.user.is_authenticated else None
            )

            for item in cart_items:
                product = Product.objects.get(id=item['id'])
                qty = item['qty']
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    price=item['price'],
                    quantity=qty,
                    subtotal=item['price'] * qty
                )
                
                # ตัดสต๊อกสินค้า
                product.stock_quantity -= qty
                product.save()

            return JsonResponse({"status": "success", "message": "บันทึกบิลสำเร็จ!", "receipt": receipt_number})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)