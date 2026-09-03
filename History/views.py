from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from django.urls import reverse
from Pos.models import Order, OrderItem
from Products.models import Product
from Stocks.models import StockItem, StockLog

@login_required
def history_list(request):
    orders = Order.objects.filter(created_by=request.user).prefetch_related('items__product').order_by('-created_at')
    products = Product.objects.filter(is_active=True, created_by=request.user).order_by('category', 'name')
    
    # -----------------------------------------------------
    # ระบบกรองตามช่วงเวลา (Days & Date Range Filter)
    # -----------------------------------------------------
    days = request.GET.get('days', '0')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    now = timezone.localtime()
    today = now.date()
    
    if start_date:
        if end_date:
            orders = orders.filter(created_at__date__range=[start_date, end_date])
        else:
            orders = orders.filter(created_at__date=start_date)
        days = '' # ล้างค่า days หากผู้ใช้เลือกวันที่เอง
    else:
        if days == '0':
            orders = orders.filter(created_at__date=today)
        elif days in ['1', '2', '3', '4', '5', '10', '20', '30']:
            start_d = today - timedelta(days=int(days))
            orders = orders.filter(created_at__date__gte=start_d)
        elif days == 'all':
            pass 
        
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    shop_promptpay = getattr(request.user, 'promptpay_number', "")
    
    context = {
        'orders': orders,
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
        'total_sales': total_sales,
        'products': products,
        'shop_promptpay': shop_promptpay,
    }
    return render(request, 'History/history_list.html', context)

@login_required
def edit_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, created_by=request.user)
    days = request.GET.get('days', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    exclude_keywords = ["topping", "ท็อปปิ้ง", "กับข้าว", "พิเศษ", "เครื่องดื่ม"]

    if request.method == 'POST':
        product_ids = request.POST.getlist('item_product_id[]')
        prices = request.POST.getlist('item_price[]')
        qtys = request.POST.getlist('item_qty[]')
        
        # 1. คืนสต๊อกของเก่าก่อนลบ
        boxes_returned = 0
        for item in order.items.all():
            if item.product:
                item.product.stock_quantity += item.quantity
                item.product.save()
                
                cat_name = item.product.category.name.lower() if item.product.category else ""
                prod_name = item.product.name.lower()
                if not any(kw in cat_name or kw in prod_name for kw in exclude_keywords):
                    boxes_returned += item.quantity
                    
        order.items.all().delete()
        
        # 2. บันทึกรายการใหม่ + ตัดสต๊อกใหม่
        new_total = 0
        boxes_used = 0
        
        for i in range(len(product_ids)):
            try:
                prod = Product.objects.get(id=product_ids[i])
                p_price = float(prices[i])
                p_qty = int(qtys[i])
                sub = p_price * p_qty
                
                OrderItem.objects.create(order=order, product=prod, price=p_price, quantity=p_qty, subtotal=sub)
                new_total += sub
                
                prod.stock_quantity -= p_qty
                prod.save()
                
                cat_name = prod.category.name.lower() if prod.category else ""
                prod_name = prod.name.lower()
                if not any(kw in cat_name or kw in prod_name for kw in exclude_keywords):
                    boxes_used += p_qty
            except:
                pass
                
        new_prod_ids = request.POST.getlist('new_product_id[]')
        new_prices = request.POST.getlist('new_price[]')
        new_qtys = request.POST.getlist('new_qty[]')
        
        for i in range(len(new_prod_ids)):
            if new_prod_ids[i]:
                try:
                    prod = Product.objects.get(id=new_prod_ids[i])
                    p_price = float(new_prices[i])
                    p_qty = int(new_qtys[i])
                    sub = p_price * p_qty
                    
                    OrderItem.objects.create(order=order, product=prod, price=p_price, quantity=p_qty, subtotal=sub)
                    new_total += sub
                    
                    prod.stock_quantity -= p_qty
                    prod.save()
                    
                    cat_name = prod.category.name.lower() if prod.category else ""
                    prod_name = prod.name.lower()
                    if not any(kw in cat_name or kw in prod_name for kw in exclude_keywords):
                        boxes_used += p_qty
                except:
                    pass
        
        order.total_amount = new_total
        order.save()
        
        # 3. คำนวณส่วนต่างของกล่อง และอัปเดตสต๊อก
        box_diff = boxes_used - boxes_returned
        if box_diff != 0:
            box_stock = StockItem.objects.filter(created_by=request.user, name__icontains='กล่อง').first()
            if box_stock:
                if box_diff > 0:
                    if box_stock.quantity >= box_diff:
                        box_stock.quantity -= box_diff
                    else:
                        box_stock.quantity = 0
                    box_stock.save()
                    StockLog.objects.create(item=box_stock, action='OUT', amount=box_diff, note=f'เบิกเพิ่ม แก้ไขบิล {order.receipt_number}', created_by=request.user)
                else:
                    return_amount = abs(box_diff)
                    box_stock.quantity += return_amount
                    box_stock.save()
                    StockLog.objects.create(item=box_stock, action='IN', amount=return_amount, note=f'คืนสต๊อก แก้ไขบิล {order.receipt_number}', created_by=request.user)
            
    return redirect(f"{reverse('history:home')}?days={days}&start_date={start_date}&end_date={end_date}")

@login_required
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, created_by=request.user)
    days = request.GET.get('days', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    exclude_keywords = ["topping", "ท็อปปิ้ง", "กับข้าว", "พิเศษ", "เครื่องดื่ม"]
    
    if request.method == 'POST':
        boxes_returned = 0
        for item in order.items.all():
            if item.product:
                item.product.stock_quantity += item.quantity
                item.product.save()
                
                cat_name = item.product.category.name.lower() if item.product.category else ""
                prod_name = item.product.name.lower()
                if not any(kw in cat_name or kw in prod_name for kw in exclude_keywords):
                    boxes_returned += item.quantity
        
        if boxes_returned > 0:
            box_stock = StockItem.objects.filter(created_by=request.user, name__icontains='กล่อง').first()
            if box_stock:
                box_stock.quantity += boxes_returned
                box_stock.save()
                StockLog.objects.create(item=box_stock, action='IN', amount=boxes_returned, note=f'คืนสต๊อก ลบบิล {order.receipt_number}', created_by=request.user)
                
        order.delete()
        
    return redirect(f"{reverse('history:home')}?days={days}&start_date={start_date}&end_date={end_date}")