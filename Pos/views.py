import json
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
import re
import pytesseract
from PIL import Image, ImageEnhance
from datetime import datetime, timedelta

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

@login_required
def api_check_slips(request):
    if request.method == 'POST' and request.FILES.getlist('slips'):
        files = request.FILES.getlist('slips')
        recent_orders = Order.objects.filter(
            created_by=request.user,
            created_at__gte=timezone.localtime() - timedelta(days=2)
        ).order_by('-created_at')

        results = []
        for f in files:
            try:
                img = Image.open(f.file).convert('L')
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(2.0)
                text = pytesseract.image_to_string(img, lang='eng+tha')

                amount_matches = re.findall(r'\d{1,3}(?:,\d{3})*\.\d{2}', text)
                float_amounts = [float(a.replace(',', '')) for a in amount_matches]
                
                time_matches = re.findall(r'([0-1]?[0-9]|2[0-3]):([0-5][0-9])', text)
                slip_time_str = f"{time_matches[0][0]}:{time_matches[0][1]}" if time_matches else None

                matched_order_id = None
                status = "NOT_FOUND"
                final_amount = max(float_amounts) if float_amounts else None

                if float_amounts:
                    potential_orders = []
                    # 🌟 เทียบค่าที่ได้ทั้งหมดกับบิลเหมือนกัน
                    for amt in sorted(float_amounts, reverse=True):
                        pots = [o for o in recent_orders if abs(float(o.total_amount) - amt) < 0.01]
                        if pots:
                            potential_orders = pots
                            final_amount = amt
                            break

                    if potential_orders:
                        if slip_time_str:
                            slip_time_obj = datetime.strptime(slip_time_str, '%H:%M').time()
                            best_order = None
                            min_diff = float('inf')
                            
                            for order in potential_orders:
                                order_time = timezone.localtime(order.created_at).time()
                                o_mins = order_time.hour * 60 + order_time.minute
                                s_mins = slip_time_obj.hour * 60 + slip_time_obj.minute
                                diff = min((s_mins - o_mins) % 1440, (o_mins - s_mins) % 1440)
                                
                                if diff < min_diff:
                                    min_diff = diff
                                    best_order = order
                                    
                            matched_order_id = best_order.id
                        else:
                            matched_order_id = potential_orders[0].id
                        
                        status = "MATCHED"

                results.append({
                    'filename': f.name,
                    'amount': final_amount,
                    'order_id': matched_order_id,
                    'status': status
                })
            except Exception as e:
                results.append({'filename': f.name, 'status': 'ERROR'})

        return JsonResponse({'status': 'success', 'results': results})
    return JsonResponse({'status': 'error'}, status=400)

from django.views.decorators.http import require_POST

import json
import re
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
# สมมติว่าดึงโมเดลมาครบแล้ว เช่น Order, OrderItem, Dormitory...

@login_required
def check_slips(request):
    results = []
    
    # 1. รับค่าวันที่จากช่องค้นหา (ถ้าไม่ได้เลือก ให้ใช้วันนี้)
    filter_date_str = request.GET.get('filter_date')
    if filter_date_str:
        try:
            selected_date = datetime.strptime(filter_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.localdate()
    else:
        selected_date = timezone.localdate()
    
    # ดึงบิลตามวันที่กรองเฉพาะที่ยังไม่จ่าย
    orders = Order.objects.filter(
        created_by=request.user, 
        created_at__date=selected_date
    ).select_related('delivery_info__destination').prefetch_related('items__product').order_by('-created_at')
    
    if request.method == 'POST' and request.FILES.getlist('slips'):
        files = request.FILES.getlist('slips')
        
        recent_orders = Order.objects.filter(
            created_by=request.user,
            created_at__date=selected_date
        ).select_related('delivery_info__destination').prefetch_related('items__product').order_by('-created_at')

        used_transactions = list(Order.objects.filter(
            created_by=request.user, 
            transaction_ref__isnull=False
        ).exclude(transaction_ref="").values_list('transaction_ref', flat=True))

        for f in files:
            try:
                # 🌟 ส่งไฟล์รูปภาพข้ามไปวิเคราะห์ที่ API Go โดยตรง 🌟
                api_url = "https://48c8-2405-9800-bcb0-61ac-d638-f429-3759-da42.ngrok-free.app/api/v1/scan-slip"
                
                # แนบไฟล์และ Header เจาะทะลุ Ngrok
                files_payload = {'slip_image': (f.name, f.file, f.content_type)}
                headers = {'ngrok-skip-browser-warning': 'true'}
                
                response = requests.post(api_url, files=files_payload, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    res_json = response.json()
                    
                    if res_json.get('success') and 'data' in res_json:
                        slip_data = res_json['data']
                        
                        slip_amount = slip_data.get('amount')
                        if slip_amount is not None:
                            try: slip_amount = float(slip_amount)
                            except: slip_amount = None
                            
                        slip_ref_id = slip_data.get('transaction_ref')
                        raw_date = slip_data.get('date', '')
                        raw_text = slip_data.get('raw_text', '')

                        # แกะเอาแค่เวลา (HH:MM) ออกมาจากข้อมูล date
                        slip_time_str = None
                        time_matches = re.findall(r'([0-1]?[0-9]|2[0-3]):([0-5][0-9])', raw_date)
                        if not time_matches:
                            time_matches = re.findall(r'([0-1]?[0-9]|2[0-3]):([0-5][0-9])', raw_text)
                        
                        if time_matches:
                            slip_time_str = f"{time_matches[-1][0].zfill(2)}:{time_matches[-1][1]}"

                        # ระบบ Matching (จับคู่บิล)
                        matched_order = None
                        match_status = "NOT_FOUND"
                        time_diff_minutes = None
                        possible_matches = []

                        # 1. เช็คสลิปซ้ำ
                        if slip_ref_id and slip_ref_id in used_transactions:
                            match_status = "DUPLICATE"
                        
                        # 2. หาระบบที่ยอดเงินตรงกัน (ถ้าไม่ซ้ำ)
                        elif slip_amount:
                            potential_orders = [o for o in recent_orders if abs(float(o.total_amount) - slip_amount) < 0.01 and o.payment_status != 'PAID']

                            if potential_orders:
                                for po in potential_orders:
                                    d_name = "หน้าร้าน/ไม่ระบุ"
                                    if hasattr(po, 'delivery_info') and po.delivery_info.destination:
                                        d_name = po.delivery_info.destination.name
                                    i_text = [f"{i.product.name} (x{i.quantity})" for i in po.items.all()]
                                    
                                    possible_matches.append({
                                        'id': po.id,
                                        'receipt_number': po.receipt_number,
                                        'dorm_name': d_name,
                                        'items': i_text,
                                        'time': timezone.localtime(po.created_at).strftime('%H:%M')
                                    })

                                if slip_time_str:
                                    best_order = None
                                    min_diff = float('inf')
                                    slip_time_obj = datetime.strptime(slip_time_str, '%H:%M').time()
                                    
                                    for order in potential_orders:
                                        order_time = timezone.localtime(order.created_at).time()
                                        o_mins = order_time.hour * 60 + order_time.minute
                                        s_mins = slip_time_obj.hour * 60 + slip_time_obj.minute
                                        diff = min((s_mins - o_mins) % 1440, (o_mins - s_mins) % 1440)
                                        
                                        if diff < min_diff:
                                            min_diff = diff
                                            best_order = order
                                            
                                    matched_order = best_order
                                    time_diff_minutes = min_diff
                                else:
                                    matched_order = potential_orders[0]

                                if match_status != "DUPLICATE":
                                    match_status = "MATCHED"

                        order_items_text = []
                        dorm_name = "หน้าร้าน/ไม่ระบุ"
                        if matched_order:
                            for item in matched_order.items.all():
                                order_items_text.append(f"{item.product.name} (x{item.quantity})")
                            if hasattr(matched_order, 'delivery_info') and matched_order.delivery_info.destination:
                                dorm_name = matched_order.delivery_info.destination.name

                        results.append({
                            'filename': f.name,
                            'amount': slip_amount,
                            'time': slip_time_str,
                            'transaction_ref': slip_ref_id,
                            'order_id': matched_order.id if matched_order else None,
                            'order_ref': matched_order.receipt_number if matched_order else "-",
                            'dorm_name': dorm_name,
                            'items': order_items_text,
                            'status': match_status,
                            'time_diff': time_diff_minutes,
                            'possible_matches': possible_matches
                        })
                    else:
                        results.append({'filename': f.name, 'status': "ERROR", 'error_msg': res_json.get('message', 'API Return Invalid Data')})
                else:
                    results.append({'filename': f.name, 'status': "ERROR", 'error_msg': f"API Error: {response.status_code}"})

            except Exception as e:
                results.append({'filename': f.name, 'status': "ERROR", 'error_msg': str(e)})

    return render(request, 'Pos/check_slips.html', {
        'results': results, 
        'orders': orders,
        'selected_date': selected_date.strftime('%Y-%m-%d')
    })


@login_required
@require_POST
def mark_order_unpaid(request):
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        if order_id:
            Order.objects.filter(id=order_id, created_by=request.user).update(
                payment_status='PENDING',
                transaction_ref=None
            )
            return JsonResponse({"status": "success", "message": "อัปเดตสถานะเป็นยังไม่จ่ายเรียบร้อยแล้ว"})
        return JsonResponse({"status": "error", "message": "ไม่พบรหัสบิล"}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@require_POST
def reset_slip_ref(request):
    try:
        data = json.loads(request.body)
        ref = data.get('transaction_ref')
        if ref:
            Order.objects.filter(created_by=request.user, transaction_ref=ref).update(
                transaction_ref=None,
                payment_status='PENDING'
            )
            return JsonResponse({"status": "success", "message": "รีเซ็ตสลิปซ้ำเรียบร้อยแล้ว สามารถสแกนใหม่อีกครั้งได้"})
        return JsonResponse({"status": "error", "message": "ไม่พบเลขอ้างอิงสลิป"}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@require_POST
def confirm_matched_slips(request):
    try:
        data = json.loads(request.body)
        matched_items = data.get('matches', [])
        
        updated_count = 0
        for item in matched_items:
            order_id = item.get('order_id')
            ref = item.get('transaction_ref')
            
            if order_id:
                Order.objects.filter(id=order_id, created_by=request.user).update(
                    payment_status='PAID',
                    transaction_ref=ref
                )
                updated_count += 1
                
        return JsonResponse({"status": "success", "message": f"บันทึกยอดเงินสำเร็จ {updated_count} รายการ"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)