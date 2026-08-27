import json
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Prefetch
from django.contrib.auth.decorators import login_required
from Products.models import Product, ProductCategory
from .models import Order, OrderItem
from datetime import datetime

@login_required 
def home(request):
    my_products = Product.objects.filter(is_active=True, created_by=request.user)

    raw_categories = ProductCategory.objects.filter(
        is_active=True, created_by=request.user
    ).prefetch_related(Prefetch("products", queryset=my_products))

    def sort_category(category):
        back_keywords = ["topping", "ท็อปปิ้ง", "กับข้าว", "เครื่องดื่ม", "เพิ่มเติม"]
        for keyword in back_keywords:
            if keyword in category.name.lower():
                return 1 
        return 0 

    categories = list(raw_categories)
    categories.sort(key=lambda c: (sort_category(c), c.name))

    # ==========================================
    # ส่วนที่เพิ่ม: รับค่าวันที่จาก HTML เพื่อค้นหาตาม created_at
    # ==========================================
    selected_date_str = request.GET.get('date') # รับวันที่มาจากหน้าเว็บ
    if selected_date_str:
        # ถ้ามีการเลือกวันที่ ให้แปลงข้อความเป็น Date
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    else:
        # ถ้าไม่ได้เลือก ให้ใช้วันที่ปัจจุบัน
        selected_date = timezone.localdate()

    # กรองยอดขาย (ตัดยอด) ตาม created_at ที่เลือก
    daily_sales = Order.objects.filter(
        created_at__date=selected_date,  # <--- ค้นหาจากวันที่สร้างบิล
        created_by=request.user
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        "categories": categories,
        "products": my_products, 
        "daily_sales": daily_sales,
        "selected_date": selected_date, # ส่งวันที่กลับไปแสดงบน HTML
    }

    return render(request, "Pos/home.html", context)

# ==========================================
# 2. ระบบชำระเงิน ตัดสต๊อก และรันเลขบิลรายวัน
# ==========================================
def process_checkout(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cart_items = data.get('cart', [])
            
            if not cart_items:
                return JsonResponse({"status": "error", "message": "ตะกร้าว่างเปล่า"}, status=400)

            # -----------------------------------------------------
            # ระบบรันเลขที่บิลรายวัน (INV-YYYYMMDD-XXXX)
            # -----------------------------------------------------
            local_now = timezone.localtime()
            date_str = local_now.strftime('%Y%m%d') # เช่น 20260827
            prefix = f"INV-{date_str}-"
            
            # ค้นหาบิลล่าสุดของวันนี้
            last_order = Order.objects.filter(
                receipt_number__startswith=prefix
            ).order_by('-receipt_number').first()

            if last_order:
                # เอา 4 หลักสุดท้ายมาบวก 1
                last_number = int(last_order.receipt_number.split('-')[-1])
                new_number = last_number + 1
            else:
                # ถ้ายังไม่มีบิลเลย เริ่มที่ 1
                new_number = 1
                
            receipt_number = f"{prefix}{new_number:04d}" # ตัวอย่าง: INV-20260827-0001
            # -----------------------------------------------------

            # คำนวณยอดรวมสุทธิ
            total_amount = sum(item['price'] * item['qty'] for item in cart_items)

            # สร้างหัวบิล (Order)
            # created_at จะถูกสร้างอัตโนมัติตาม auto_now_add=True ใน models.py
            order = Order.objects.create(
                receipt_number=receipt_number,
                total_amount=total_amount,
                created_by=request.user if request.user.is_authenticated else None
            )

            # บันทึกสินค้าในตะกร้า (OrderItem) และตัดสต๊อก
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

            return JsonResponse({
                "status": "success", 
                "message": "บันทึกบิลและตัดสต๊อกสำเร็จ!", 
                "receipt": receipt_number
            })
            
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)