import json
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Prefetch, Q
from django.contrib.auth.decorators import login_required

from Products.models import Product, ProductCategory
from Expenses.models import Expense
from .models import Order, OrderItem
from Stocks.models import StockItem, StockLog 

# 🌟 นำเข้า DeliveryTask และ Dormitory จากแอป Riders ให้ครบ
from Riders.models import Dormitory, DeliveryTask 

@login_required 
def home(request):
    my_products = Product.objects.filter(is_active=True, created_by=request.user)
    dorms = Dormitory.objects.all().order_by('zone', 'name')

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

    # รับค่าวันที่จาก HTML เพื่อค้นหายอดขาย
    selected_date_str = request.GET.get('date') 
    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    else:
        selected_date = timezone.localdate()

    # กรองยอดขายตามวันที่เลือก
    daily_sales = Order.objects.filter(
        created_at__date=selected_date,
        created_by=request.user
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # =====================================================
    # ดึงบิลค้างจ่าย (สำหรับโชว์ในกระดิ่งแจ้งเตือน)
    # =====================================================
    today = timezone.localdate()
    raw_unpaid = Expense.objects.filter(is_paid=False).order_by('expense_date')
    unpaid_expenses = []
    
    for exp in raw_unpaid:
        days_diff = (exp.expense_date - today).days
        unpaid_expenses.append({
            'id': exp.id,
            'name': exp.name,
            'amount': exp.amount,
            'days_left': days_diff,
        })

    context = {
        "categories": categories,
        "products": my_products, 
        "daily_sales": daily_sales,
        "selected_date": selected_date,
        "unpaid_expenses": unpaid_expenses,
        "shop_promptpay": request.user.promptpay_number or "", 
        'dorms': dorms, # 🌟 ส่งตัวแปรหอพักไปให้หน้า POS เลือก
    }

    return render(request, "Pos/home.html", context)


# =====================================================
# API สำหรับ Modal เทียบรายได้-รายจ่าย (แสดงเฉพาะบิลค้างจ่าย)
# =====================================================
@login_required
def api_compare_profit(request):
    start_date_str = request.GET.get('start')
    end_date_str = request.GET.get('end')
    
    if not start_date_str or not end_date_str:
        return JsonResponse({'error': 'กรุณาระบุวันที่ให้ครบถ้วน'}, status=400)
        
    try:
        start_dt = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'รูปแบบวันที่ไม่ถูกต้อง'}, status=400)
        
    sales = Order.objects.filter(
        created_at__date__gte=start_dt,
        created_at__date__lte=end_dt,
        created_by=request.user
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    expenses_qs = Expense.objects.filter(
        is_paid=False
    ).order_by('expense_date')
    
    expenses_list = []
    for exp in expenses_qs:
        expenses_list.append({
            'id': exp.id,
            'name': exp.name,
            'amount': float(exp.amount),
            'date': exp.expense_date.strftime('%d/%m/%Y'),
            'category': f"{exp.get_category_display()} (ยังไม่จ่าย)"
        })
        
    return JsonResponse({
        'sales_total': float(sales),
        'expenses': expenses_list
    })

# =====================================================
# API มาร์ครายจ่ายว่า "จ่ายแล้ว"
# =====================================================
@login_required
def mark_expense_paid(request, expense_id):
    if request.method == "POST":
        try:
            exp = Expense.objects.get(id=expense_id)
            exp.is_paid = True
            exp.save()
            return JsonResponse({"status": "success", "message": "อัปเดตสถานะสำเร็จ!"})
        except Expense.DoesNotExist:
            return JsonResponse({"status": "error", "message": "ไม่พบบิลนี้"}, status=404)
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


# =====================================================
# ระบบชำระเงินหน้า POS (สร้างออเดอร์, ตัดสต๊อกกล่อง, และส่งไปแอป Riders)
# =====================================================
@login_required
def process_checkout(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cart_items = data.get('cart', [])
            dormitory_id = data.get('dormitory_id', '') # 🌟 รับ ID หอพักที่ไรเดอร์ต้องไปส่ง
            
            if not cart_items:
                return JsonResponse({"status": "error", "message": "ตะกร้าว่างเปล่า"}, status=400)

            local_now = timezone.localtime()
            date_str = local_now.strftime('%Y%m%d')
            
            shop_code = request.user.username.upper()
            prefix = f"INV-{shop_code}-{date_str}-"
            
            last_order = Order.objects.filter(
                created_by=request.user,
                receipt_number__startswith=prefix
            ).order_by('receipt_number').first()

            if last_order:
                try:
                    last_number = int(last_order.receipt_number.split('-')[-1])
                    new_number = last_number - 1
                except (ValueError, IndexError):
                    new_number = 9999
            else:
                new_number = 9999
                
            receipt_number = f"{prefix}{new_number:04d}"

            while Order.objects.filter(receipt_number=receipt_number).exists():
                new_number -= 1
                if new_number < 1: 
                    new_number = 9999
                receipt_number = f"{prefix}{new_number:04d}"

            total_amount = sum(item['price'] * item['qty'] for item in cart_items)

            # 1. บันทึกข้อมูลบิล (Order)
            order = Order.objects.create(
                receipt_number=receipt_number,
                total_amount=total_amount,
                created_by=request.user
            )

            boxes_to_deduct = 0
            exclude_keywords = ["topping", "ท็อปปิ้ง", "กับข้าว", "พิเศษ", "เครื่องดื่ม"]

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
                
                product.stock_quantity -= qty
                product.save()

                cat_name = product.category.name.lower() if product.category else ""
                prod_name = product.name.lower()
                
                is_excluded = any(kw in cat_name or kw in prod_name for kw in exclude_keywords)
                if not is_excluded:
                    boxes_to_deduct += qty

            # ==========================================
            # 🌟 2. แมปข้อมูลไปฝั่งแอป Riders ทันที!
            # สร้าง DeliveryTask ผูกกับ Order และ Dormitory 
            # ==========================================
            if dormitory_id:
                try:
                    dorm = Dormitory.objects.get(id=dormitory_id)
                    # สร้างงานส่งของพร้อมระบุจุดหมาย
                    DeliveryTask.objects.create(order=order, destination=dorm, status='PENDING')
                except Dormitory.DoesNotExist:
                    DeliveryTask.objects.create(order=order, status='PENDING')
            else:
                # กรณีไม่ได้เลือกหอพัก (ลูกค้ากินหน้าร้าน) สร้างเป็นงานลอยๆ ไว้
                DeliveryTask.objects.create(order=order, status='PENDING')

            # ==========================================
            # ตัดยอดสต๊อก "กล่อง" ในแอป Stocks แบบอัตโนมัติ
            # ==========================================
            if boxes_to_deduct > 0:
                box_stock = StockItem.objects.filter(
                    created_by=request.user, 
                    name__icontains='กล่อง'
                ).first()
                
                if box_stock:
                    if box_stock.quantity >= boxes_to_deduct:
                        box_stock.quantity -= boxes_to_deduct
                    else:
                        box_stock.quantity = 0
                    box_stock.save()
                    
                    StockLog.objects.create(
                        item=box_stock,
                        action='OUT',
                        amount=boxes_to_deduct,
                        note=f'ขายหน้าร้านบิล {receipt_number}',
                        created_by=request.user
                    )

            return JsonResponse({"status": "success", "message": "บันทึกสำเร็จ!", "receipt": receipt_number})
            
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)