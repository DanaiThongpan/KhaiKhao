from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from Pos.models import Order, OrderItem
from Products.models import Product

@login_required
def history_list(request):
    # เปลี่ยนกลับเป็น -created_at เพื่อให้บิลล่าสุดอยู่บรรทัดแรกสุด
    orders = Order.objects.filter(created_by=request.user).prefetch_related('items__product').order_by('-created_at')
    products = Product.objects.filter(is_active=True, created_by=request.user).order_by('category', 'name')
    
    days = request.GET.get('days', '1')
    now = timezone.localtime()
    today = now.date()
    
    if days == '0':
        orders = orders.filter(created_at__date=today)
    elif days == '1':
        start_date = today - timedelta(days=1)
        orders = orders.filter(created_at__date__gte=start_date)
    elif days == '2':
        start_date = today - timedelta(days=2)
        orders = orders.filter(created_at__date__gte=start_date)
    elif days == '3':
        start_date = today - timedelta(days=3)
        orders = orders.filter(created_at__date__gte=start_date)
    elif days == '4':
        start_date = today - timedelta(days=4)
        orders = orders.filter(created_at__date__gte=start_date)
    elif days == '5':
        start_date = today - timedelta(days=5)
        orders = orders.filter(created_at__date__gte=start_date)
    elif days == '10':
        start_date = today - timedelta(days=10)
        orders = orders.filter(created_at__date__gte=start_date)
    elif days == '20':
        start_date = today - timedelta(days=20)
        orders = orders.filter(created_at__date__gte=start_date)
    elif days == '30':
        start_date = today - timedelta(days=30)
        orders = orders.filter(created_at__date__gte=start_date)
    elif days == 'all':
        pass 
        
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    shop_promptpay = getattr(request.user, 'promptpay_number', "")
    
    context = {
        'orders': orders,
        'days': days,
        'total_sales': total_sales,
        'products': products,
        'shop_promptpay': shop_promptpay,
    }
    return render(request, 'History/history_list.html', context)

@login_required
def edit_order(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id, created_by=request.user)
        
        item_ids = request.POST.getlist('item_id[]')
        product_ids = request.POST.getlist('item_product_id[]')
        prices = request.POST.getlist('item_price[]')
        qtys = request.POST.getlist('item_qty[]')
        
        order.items.all().delete()
        
        new_total = 0
        for i in range(len(product_ids)):
            try:
                prod = Product.objects.get(id=product_ids[i])
                p_price = float(prices[i])
                p_qty = int(qtys[i])
                sub = p_price * p_qty
                
                OrderItem.objects.create(
                    order=order, product=prod, price=p_price, quantity=p_qty, subtotal=sub
                )
                new_total += sub
            except Exception as e:
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
                    
                    OrderItem.objects.create(
                        order=order, product=prod, price=p_price, quantity=p_qty, subtotal=sub
                    )
                    new_total += sub
                except Exception as e:
                    pass
        
        order.total_amount = new_total
        order.save()
            
    return redirect('history:home')