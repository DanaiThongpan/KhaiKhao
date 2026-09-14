from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import StockItem, StockLog
from Pos.models import Order, OrderItem

User = get_user_model()

@login_required
def stock_list(request):
    items = StockItem.objects.filter(created_by=request.user).order_by('name')
    
    # -----------------------------------------------------
    # ระบบกรองตามช่วงเวลา (Days & Date Range Filter)
    # -----------------------------------------------------
    days = request.GET.get('days', '0')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    now = timezone.localtime()
    today = now.date()
    
    orders_qs = Order.objects.filter(created_by=request.user).order_by('-created_at')
    
    log_qs = StockLog.objects.filter(
        created_by=request.user,
        item__name__icontains='กล่อง',
        action='OUT'
    ).exclude(note__icontains='บิล')

    history_logs_qs = StockLog.objects.filter(created_by=request.user).order_by('-created_at')

    if start_date:
        if end_date:
            orders_qs = orders_qs.filter(created_at__date__range=[start_date, end_date])
            log_qs = log_qs.filter(created_at__date__range=[start_date, end_date])
            history_logs_qs = history_logs_qs.filter(created_at__date__range=[start_date, end_date])
        else:
            orders_qs = orders_qs.filter(created_at__date=start_date)
            log_qs = log_qs.filter(created_at__date=start_date)
            history_logs_qs = history_logs_qs.filter(created_at__date=start_date)
        days = '' 
    else:
        if days == '0':
            orders_qs = orders_qs.filter(created_at__date=today)
            log_qs = log_qs.filter(created_at__date=today)
            history_logs_qs = history_logs_qs.filter(created_at__date=today)
        elif days in ['1', '2', '3', '4', '5', '10', '20', '30']:
            s_date = today - timedelta(days=int(days))
            orders_qs = orders_qs.filter(created_at__date__gte=s_date)
            log_qs = log_qs.filter(created_at__date__gte=s_date)
            history_logs_qs = history_logs_qs.filter(created_at__date__gte=s_date)
        elif days == 'all':
            pass 
        
    today_orders_count = orders_qs.count()
    
    # -----------------------------------------------------
    # คำนวณข้อมูลการขายและการใช้กล่อง
    # -----------------------------------------------------
    exclude_keywords = ["topping", "ท็อปปิ้ง", "กับข้าว", "พิเศษ", "เครื่องดื่ม", "โปรโมชั่น", "เพิ่มเติม", "ของทานเล่น", "ค่าจัดส่ง", "โปรโมชั่นส่วนลด"]
    
    order_items_qs = OrderItem.objects.filter(order__in=orders_qs).select_related('product', 'product__category', 'order')
    
    boxes_from_orders = 0
    sold_by_order = {}

    for item in order_items_qs:
        order_id = item.order.id
        receipt = item.order.receipt_number
        
        p_name = item.product.name if item.product else "ไม่ระบุ"
        c_name = item.product.category.name.lower() if item.product and item.product.category else ""
        
        is_excluded = any(kw in c_name or kw in p_name.lower() for kw in exclude_keywords)
        boxes_used = 0 if is_excluded else item.quantity
        
        boxes_from_orders += boxes_used
        
        if order_id not in sold_by_order:
            sold_by_order[order_id] = {
                'receipt': receipt,
                'time': item.order.created_at,
                'items': [],
                'order_total_boxes': 0,
                'order_total_qty': 0
            }
        
        sold_by_order[order_id]['items'].append({
            'name': p_name,
            'qty': item.quantity,
            'boxes': boxes_used
        })
        sold_by_order[order_id]['order_total_boxes'] += boxes_used
        sold_by_order[order_id]['order_total_qty'] += item.quantity
        
    today_sold_items = sorted(sold_by_order.values(), key=lambda x: x['time'], reverse=True)
        
    manual_boxes_out = log_qs.aggregate(Sum('amount'))['amount__sum'] or 0
    today_boxes_used = boxes_from_orders + manual_boxes_out

    other_shops = User.objects.exclude(id=request.user.id).order_by('username')

    context = {
        'items': items,
        'today_orders_count': today_orders_count,
        'today_boxes_used': today_boxes_used,
        'today_sold_items': today_sold_items,
        'history_logs': history_logs_qs,
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
        'other_shops': other_shops,
    }
    
    return render(request, 'Stocks/stock_list.html', context)

@login_required
def add_stock(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        quantity = request.POST.get('quantity', 0)
        unit = request.POST.get('unit')
        alert_level = request.POST.get('alert_level', 0)
        
        if name and unit:
            StockItem.objects.create(
                name=name, quantity=float(quantity), unit=unit, alert_level=float(alert_level), created_by=request.user
            )
            messages.success(request, f"เพิ่ม {name} เข้าระบบสำเร็จ")
    return redirect('stocks:list')

@login_required
def add_log(request, item_id):
    item = get_object_or_404(StockItem, id=item_id, created_by=request.user)
    
    days = request.GET.get('days', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    if request.method == 'POST':
        action = request.POST.get('action') 
        amount = float(request.POST.get('amount', 0))
        note = request.POST.get('note', '')
        
        if amount > 0:
            if action == 'OUT' and amount > item.quantity:
                messages.error(request, f"ไม่สามารถเบิกได้! {item.name} มีสต๊อกคงเหลือเพียง {item.quantity} {item.unit}")
                return redirect(f"/stocks/?days={days}&start_date={start_date}&end_date={end_date}")
            
            StockLog.objects.create(item=item, action=action, amount=amount, note=note, created_by=request.user)
            
            if action == 'IN':
                item.quantity += amount
                messages.success(request, f"นำเข้า {item.name} จำนวน {amount} {item.unit} สำเร็จ")
            elif action == 'OUT':
                item.quantity -= amount
                messages.success(request, f"เบิก {item.name} จำนวน {amount} {item.unit} สำเร็จ")
                
            item.save()
            
    return redirect(f"/stocks/?days={days}&start_date={start_date}&end_date={end_date}")

@login_required
def delete_stock(request, item_id):
    item = get_object_or_404(StockItem, id=item_id, created_by=request.user)
    if request.method == 'POST':
        item_name = item.name
        item.delete()
        messages.success(request, f"ลบ {item_name} ออกจากระบบแล้ว")
    return redirect('stocks:list')

@login_required
@transaction.atomic 
def transfer_stock(request, item_id):
    item = get_object_or_404(StockItem, id=item_id, created_by=request.user)
    
    if request.method == 'POST':
        amount = float(request.POST.get('amount', 0))
        target_shop_id = request.POST.get('target_shop_id')
        note = request.POST.get('note', '')
        
        if not target_shop_id:
            messages.error(request, "กรุณาเลือกร้านปลายทาง")
            return redirect('stocks:list')
            
        target_shop = get_object_or_404(User, id=target_shop_id)
        
        if amount > 0:
            if amount > item.quantity:
                messages.error(request, f"โอนไม่ได้! สต๊อก {item.name} ของคุณมีเพียง {item.quantity} {item.unit}")
                return redirect('stocks:list')
            
            item.quantity -= amount
            item.save()
            StockLog.objects.create(
                item=item, action='OUT', amount=amount, 
                note=f"โอนไปยังร้าน {target_shop.username} | {note}", 
                created_by=request.user
            )
            
            target_item, created = StockItem.objects.get_or_create(
                name=item.name,
                created_by=target_shop,
                defaults={
                    'quantity': 0,
                    'unit': item.unit,
                    'alert_level': item.alert_level
                }
            )
            target_item.quantity += amount
            target_item.save()
            StockLog.objects.create(
                item=target_item, action='IN', amount=amount, 
                note=f"รับโอนจากร้าน {request.user.username} | {note}", 
                created_by=target_shop
            )
            
            messages.success(request, f"โอน {item.name} จำนวน {amount} {item.unit} ไปยังร้าน {target_shop.username} สำเร็จ")
            
    return redirect('stocks:list')

@login_required
@transaction.atomic
def cancel_stock_log(request, log_id):
    log = get_object_or_404(StockLog, id=log_id, created_by=request.user)
    item = log.item
    
    if request.method == 'POST':
        if log.action == 'OUT' and log.note and 'โอนไปยังร้าน' in log.note:
            try:
                target_username = log.note.split('โอนไปยังร้าน ')[1].split(' |')[0].strip()
                target_shop = User.objects.get(username=target_username)
                
                target_log = StockLog.objects.filter(
                    created_by=target_shop, 
                    action='IN', 
                    amount=log.amount,
                    item__name=item.name,
                    created_at__date=log.created_at.date()
                ).order_by('-created_at').first()
                
                if target_log:
                    target_item = target_log.item
                    target_item.quantity -= log.amount 
                    target_item.save()
                    target_log.delete()
            except Exception as e:
                pass 
                
        if log.action == 'IN':
            item.quantity -= log.amount
        elif log.action == 'OUT':
            item.quantity += log.amount
            
        item.save()
        messages.success(request, f"ยกเลิกรายการ {item.name} และคืนค่าสต๊อกเรียบร้อยแล้ว")
        log.delete()
        
    days = request.GET.get('days', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    return redirect(f"/stocks/?days={days}&start_date={start_date}&end_date={end_date}")