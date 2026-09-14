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

from Riders.models import Dormitory, DeliveryTask

@login_required
def home(request):
    my_products = Product.objects.filter(is_active=True, created_by=request.user)
    dorms = Dormitory.objects.all().order_by('zone', 'name')

    raw_categories = ProductCategory.objects.filter(
        is_active=True, created_by=request.user
    ).prefetch_related(Prefetch("products", queryset=my_products))

    def sort_category(category):
        back_keywords = ["topping", "ท็อปปิ้ง", "กับข้าว", "พิเศษ", "เครื่องดื่ม", "โปรโมชั่น", "เพิ่มเติม", "ของทานเล่น", "ค่าจัดส่ง", "โปรโมชั่นส่วนลด"]
        for keyword in back_keywords:
            if keyword in category.name.lower():
                return 1
        return 0

    categories = list(raw_categories)
    categories.sort(key=lambda c: (sort_category(c), c.name))

    selected_date_str = request.GET.get('date')
    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    else:
        selected_date = timezone.localdate()

    daily_sales = Order.objects.filter(
        created_at__date=selected_date,
        created_by=request.user
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # =====================================================
    # ดึงบิลค้างจ่าย
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

    # =====================================================
    # 🌟 ดึงข้อมูล "กล่อง" เพื่อไปสร้างเงื่อนไขบล็อกหน้าเว็บ
    # =====================================================
    out_of_stock_items = StockItem.objects.filter(created_by=request.user, quantity__lte=0).order_by('name')
    total_noti_count = len(unpaid_expenses) + out_of_stock_items.count()

    box_item = StockItem.objects.filter(created_by=request.user, name__icontains='กล่อง').first()
    box_quantity = box_item.quantity if box_item else 0
    has_box_item = bool(box_item)

    context = {
        "categories": categories,
        "products": my_products,
        "daily_sales": daily_sales,
        "selected_date": selected_date,
        "unpaid_expenses": unpaid_expenses,
        "out_of_stock_items": out_of_stock_items, 
        "total_noti_count": total_noti_count,
        "shop_promptpay": request.user.promptpay_number or "",
        'dorms': dorms, 
        'box_quantity': box_quantity, # ส่งจำนวนกล่องคงเหลือ
        'has_box_item': has_box_item, # ส่งสถานะว่าร้านมีของชื่อกล่องไหม
    }

    return render(request, "Pos/home.html", context)


# =====================================================
# API เทียบกำไร
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
# มาร์ครายจ่ายว่า "จ่ายแล้ว"
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
# Process Checkout
# =====================================================
@login_required
def process_checkout(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cart_items = data.get('cart', [])
            dormitory_id = data.get('dormitory_id', '')

            if not cart_items:
                return JsonResponse({"status": "error", "message": "ตะกร้าว่างเปล่า"}, status=400)

            # คำนวณจำนวนกล่องที่ต้องใช้ก่อนบันทึกบิล
            boxes_to_deduct = 0
            exclude_keywords = ["topping", "ท็อปปิ้ง", "กับข้าว", "พิเศษ", "เครื่องดื่ม", "โปรโมชั่น", "เพิ่มเติม", "ของทานเล่น", "ค่าจัดส่ง", "โปรโมชั่นส่วนลด"]

            for item in cart_items:
                product = Product.objects.get(id=item['id'])
                qty = item['qty']
                cat_name = product.category.name.lower() if product.category else ""
                prod_name = product.name.lower()

                is_excluded = any(kw in cat_name or kw in prod_name for kw in exclude_keywords)
                if not is_excluded:
                    boxes_to_deduct += qty

            # 🌟 หากต้องใช้กล่อง เช็คสต๊อกกล่องให้แน่ใจก่อนบันทึก Database 🌟
            box_stock = None
            if boxes_to_deduct > 0:
                box_stock = StockItem.objects.filter(created_by=request.user, name__icontains='กล่อง').first()
                if box_stock and box_stock.quantity < boxes_to_deduct:
                    return JsonResponse({"status": "error", "message": f"กล่องไม่พอ! (บิลนี้ต้องใช้ {boxes_to_deduct} ใบ แต่มีกล่องเหลือ {int(box_stock.quantity)} ใบ)"}, status=400)

            # -------------------------------------------------------------------
            # ถ่ากล่องพอ หรือไม่ต้องใช้กล่อง ถึงจะอนุญาตให้เซฟบิลได้
            # -------------------------------------------------------------------
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

            order = Order.objects.create(
                receipt_number=receipt_number,
                total_amount=total_amount,
                created_by=request.user
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

                product.stock_quantity -= qty
                product.save()

            if dormitory_id:
                try:
                    dorm = Dormitory.objects.get(id=dormitory_id)
                    DeliveryTask.objects.create(order=order, destination=dorm, status='PENDING')
                except Dormitory.DoesNotExist:
                    DeliveryTask.objects.create(order=order, status='PENDING')
            else:
                DeliveryTask.objects.create(order=order, status='PENDING')

            # ตัดสต๊อกกล่อง
            if boxes_to_deduct > 0 and box_stock:
                box_stock.quantity -= boxes_to_deduct
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