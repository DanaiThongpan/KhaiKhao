from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from .models import StockItem, StockLog
from Pos.models import Order, OrderItem

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
    
    # ดึงประวัติการเบิกกล่องออกด้วยมือ (Manual)
    log_qs = StockLog.objects.filter(
        created_by=request.user,
        item__name__icontains='กล่อง',
        action='OUT'
    ).exclude(note__icontains='บิล')

    if start_date:
        if end_date:
            orders_qs = orders_qs.filter(created_at__date__range=[start_date, end_date])
            log_qs = log_qs.filter(created_at__date__range=[start_date, end_date])
        else:
            orders_qs = orders_qs.filter(created_at__date=start_date)
            log_qs = log_qs.filter(created_at__date=start_date)
        days = '' # ล้างค่า days หากผู้ใช้เลือกวันที่เอง
    else:
        if days == '0':
            orders_qs = orders_qs.filter(created_at__date=today)
            log_qs = log_qs.filter(created_at__date=today)
        elif days in ['1', '2', '3', '4', '5', '10', '20', '30']:
            s_date = today - timedelta(days=int(days))
            orders_qs = orders_qs.filter(created_at__date__gte=s_date)
            log_qs = log_qs.filter(created_at__date__gte=s_date)
        elif days == 'all':
            pass 
        
    today_orders_count = orders_qs.count()
    
    # -----------------------------------------------------
    # คำนวณข้อมูลการขายและการใช้กล่อง
    # -----------------------------------------------------
    exclude_keywords = ["topping", "ท็อปปิ้ง", "กับข้าว", "พิเศษ", "เครื่องดื่ม"]
    
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

    context = {
        'items': items,
        'today_orders_count': today_orders_count,
        'today_boxes_used': today_boxes_used,
        'today_sold_items': today_sold_items,
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
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
    return redirect('stocks:list')

@login_required
def add_log(request, item_id):
    item = get_object_or_404(StockItem, id=item_id, created_by=request.user)
    
    # รับค่าตัวกรองกลับมาใช้เพื่อรักษาหน้าจอ
    days = request.GET.get('days', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    if request.method == 'POST':
        action = request.POST.get('action') 
        amount = float(request.POST.get('amount', 0))
        note = request.POST.get('note', '')
        
        if amount > 0:
            StockLog.objects.create(item=item, action=action, amount=amount, note=note, created_by=request.user)
            if action == 'IN':
                item.quantity += amount
            elif action == 'OUT':
                if item.quantity >= amount:
                    item.quantity -= amount
                else:
                    item.quantity = 0 
            item.save()
            
    return redirect(f"/stocks/?days={days}&start_date={start_date}&end_date={end_date}")

@login_required
def delete_stock(request, item_id):
    item = get_object_or_404(StockItem, id=item_id, created_by=request.user)
    if request.method == 'POST':
        item.delete()
    return redirect('stocks:list')