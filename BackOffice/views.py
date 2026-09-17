from datetime import timedelta
import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.db.models import Sum
from Products.models import Product
from Stocks.models import StockItem
from Pos.models import Order, OrderItem # 🌟 อย่าลืม import OrderItem
from django.http import JsonResponse
from django.utils import timezone

User = get_user_model()

# เช็กว่าเป็น Admin
def is_admin(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, 'role', '') == "admin")

@user_passes_test(is_admin, login_url='/login/')
def admin_dashboard(request):
    total_platform_sales = Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_shops = User.objects.filter(is_superuser=False).count()
    
    shops = User.objects.filter(is_superuser=False)
    shop_data = []
    for shop in shops:
        sales = Order.objects.filter(created_by=shop).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        shop_data.append({
            'id': shop.id,  # 🌟 ส่ง ID ไปให้เทมเพลตเพื่อใช้ทำลิงก์
            'username': shop.username,
            'sales': sales
        })
        
    shop_data = sorted(shop_data, key=lambda x: x['sales'], reverse=True)

    context = {
        'total_platform_sales': total_platform_sales,
        'total_shops': total_shops,
        'shop_data': shop_data,
    }
    return render(request, 'BackOffice/dashboard.html', context)

# ==================================================
# 🌟 ระบบเจาะดูข้อมูลและจัดการแต่ละสาขา (Shop Manage)
# ==================================================
@user_passes_test(is_admin, login_url='/login/')
def shop_manage(request, shop_id):
    shop = get_object_or_404(User, id=shop_id)

    # หากมีการกด เพิ่ม/ลบ/แก้ไข ข้อมูลจากหน้าเว็บ
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # --- 📦 จัดการสินค้า (Products) ---
        if action == 'add_product':
            Product.objects.create(
                name=request.POST.get('name'),
                selling_price=request.POST.get('price', 0),
                stock_quantity=request.POST.get('stock_quantity', 0),
                created_by=shop
            )
        elif action == 'edit_product':
            prod = get_object_or_404(Product, id=request.POST.get('product_id'), created_by=shop)
            prod.name = request.POST.get('name')
            prod.selling_price = request.POST.get('price', 0)
            prod.stock_quantity = request.POST.get('stock_quantity', 0)
            prod.save()
        elif action == 'delete_product':
            Product.objects.filter(id=request.POST.get('product_id'), created_by=shop).delete()
            
        # --- 🛒 จัดการสต๊อก (Stocks) ---
        elif action == 'add_stock':
            StockItem.objects.create(
                name=request.POST.get('name'),
                quantity=request.POST.get('qty', 0),
                unit=request.POST.get('unit', 'ชิ้น'),
                created_by=shop
            )
        elif action == 'edit_stock':
            stock = get_object_or_404(StockItem, id=request.POST.get('stock_id'), created_by=shop)
            stock.name = request.POST.get('name')
            stock.quantity = request.POST.get('qty', 0)
            stock.unit = request.POST.get('unit', 'ชิ้น')
            stock.save()
        elif action == 'delete_stock':
            StockItem.objects.filter(id=request.POST.get('stock_id'), created_by=shop).delete()

        # ทำเสร็จแล้วให้รีเฟรชหน้าเดิม
        return redirect('backoffice:shop_manage', shop_id=shop.id)

    # ดึงข้อมูลของร้านนี้มาแสดง
    orders = Order.objects.filter(created_by=shop).order_by('-created_at')
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    products = Product.objects.filter(created_by=shop).order_by('-id')
    stocks = StockItem.objects.filter(created_by=shop).order_by('-id')

    context = {
        'shop': shop,
        'total_sales': total_sales,
        'orders': orders[:20], # ดูประวัติ 20 บิลล่าสุด
        'products': products,
        'stocks': stocks,
    }
    return render(request, 'BackOffice/shop_manage.html', context)

@user_passes_test(is_admin, login_url='/login/')
def shop_manage(request, shop_id):
    shop = get_object_or_404(User, id=shop_id)

    # หากมีการกด เพิ่ม/ลบ/แก้ไข ข้อมูลจากหน้าเว็บ
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # --- 📦 จัดการสินค้า (Products) ---
        if action == 'add_product':
            Product.objects.create(
                name=request.POST.get('name'),
                selling_price=request.POST.get('price', 0),
                stock_quantity=request.POST.get('stock_quantity', 0),
                created_by=shop
            )
        elif action == 'edit_product':
            prod = get_object_or_404(Product, id=request.POST.get('product_id'), created_by=shop)
            prod.name = request.POST.get('name')
            prod.selling_price = request.POST.get('price', 0)
            prod.stock_quantity = request.POST.get('stock_quantity', 0)
            prod.save()
        elif action == 'delete_product':
            Product.objects.filter(id=request.POST.get('product_id'), created_by=shop).delete()
            
        # --- 🛒 จัดการสต๊อก (Stocks) ---
        elif action == 'add_stock':
            StockItem.objects.create(
                name=request.POST.get('name'),
                quantity=request.POST.get('qty', 0),
                unit=request.POST.get('unit', 'ชิ้น'),
                created_by=shop
            )
        elif action == 'edit_stock':
            stock = get_object_or_404(StockItem, id=request.POST.get('stock_id'), created_by=shop)
            stock.name = request.POST.get('name')
            stock.quantity = request.POST.get('qty', 0)
            stock.unit = request.POST.get('unit', 'ชิ้น')
            stock.save()
        elif action == 'delete_stock':
            StockItem.objects.filter(id=request.POST.get('stock_id'), created_by=shop).delete()

        return redirect('backoffice:shop_manage', shop_id=shop.id)

    # ดึงข้อมูลของร้านนี้มาแสดง
    orders = Order.objects.filter(created_by=shop).order_by('-created_at')
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    products = list(Product.objects.filter(created_by=shop).order_by('-id'))
    stocks = StockItem.objects.filter(created_by=shop).order_by('-id')

    # 🌟 คำนวณจำนวนชิ้นที่ขายไปแล้วของแต่ละสินค้า
    sold_data = OrderItem.objects.filter(order__created_by=shop).values('product_id').annotate(total_sold=Sum('quantity'))
    sold_dict = {item['product_id']: item['total_sold'] for item in sold_data}
    
    for p in products:
        p.total_sold = sold_dict.get(p.id, 0)
        
    # จัดอันดับสินค้าขายดี (เรียงจากยอดขายมากไปน้อย เอาแค่ 5 อันดับแรก)
    top_products = sorted([p for p in products if p.total_sold > 0], key=lambda x: x.total_sold, reverse=True)[:5]

    context = {
        'shop': shop,
        'total_sales': total_sales,
        'orders': orders[:20],
        'products': products,
        'top_products': top_products, # 🌟 ส่งข้อมูล 5 อันดับแรกไปแสดงผล
        'stocks': stocks,
    }
    return render(request, 'BackOffice/shop_manage.html', context)

@user_passes_test(is_admin, login_url='/login/')
def live_monitor(request):
    # แค่เรนเดอร์หน้าจอเปล่าๆ ส่วนข้อมูลเดี๋ยว Javascript จะดึงมาใส่เอง
    return render(request, 'BackOffice/live_monitor.html')

@user_passes_test(is_admin, login_url='/login/')
def api_live_monitor(request):
    # รับค่าวันที่จากหน้าเว็บ
    days_param = request.GET.get('days', '0')
    date_param = request.GET.get('date', '') 
    
    now_date = timezone.localtime().date()
    
    # 🌟 สังเกตตรงนี้ ต้องไม่มีคำว่า filter(created_at__date=today) แล้วนะครับ
    orders = Order.objects.select_related(
        'created_by', 'delivery_info', 'delivery_info__destination', 'delivery_info__rider'
    ).prefetch_related('items__product').order_by('created_at')

    # ระบบกรองวันที่
    if date_param:
        try:
            target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date=target_date)
        except ValueError:
            orders = orders.filter(created_at__date=now_date)
    elif days_param != 'all':
        try:
            days = int(days_param)
            target_date = now_date - timedelta(days=days)
            orders = orders.filter(created_at__date=target_date)
        except ValueError:
            orders = orders.filter(created_at__date=now_date)

    pending_count = 0; delivering_count = 0; completed_count = 0
    preparing_orders = []; delivering_orders = []; completed_orders = []
    rider_stats = {} 

    for order in orders:
        status = 'COMPLETED'
        dorm_name = '-'
        rider_name = 'ยังไม่ระบุ'
        items_detail = [f"{item.product.name} (x{item.quantity})" for item in order.items.all()]

        if hasattr(order, 'delivery_info') and order.delivery_info:
            d_info = order.delivery_info
            status = d_info.status
            
            if d_info.destination:
                dorm_name = f"[{d_info.destination.zone}] {d_info.destination.name}"
                
            trip_num = getattr(d_info, 'trip_number', 1)

            if d_info.rider:
                rider_name = getattr(d_info.rider, 'name', 'ไรเดอร์')
                if rider_name not in rider_stats:
                    rider_stats[rider_name] = {'delivering': 0, 'completed': 0, 'trips': {}}

            if status == 'PENDING':
                pending_count += 1
                local_time = timezone.localtime(order.created_at)
                preparing_orders.append({
                    'receipt': order.receipt_number,
                    'shop': order.created_by.username,
                    'time': local_time.strftime('%H:%M'),
                    'created_at_iso': order.created_at.isoformat(),
                    'dorm': dorm_name,
                    'items': items_detail
                })
                
            elif status in ['GOING', 'DELIVERING', 'STARTED']:
                delivering_count += 1
                start_time = timezone.localtime(d_info.started_at).strftime('%H:%M') if d_info.started_at else '-'
                if d_info.rider:
                    rider_stats[rider_name]['delivering'] += 1
                    if trip_num not in rider_stats[rider_name]['trips']:
                        rider_stats[rider_name]['trips'][trip_num] = {'orders': 0, 'status': 'DELIVERING', 'start': [], 'end': []}
                    rider_stats[rider_name]['trips'][trip_num]['orders'] += 1
                    rider_stats[rider_name]['trips'][trip_num]['status'] = 'DELIVERING'
                    if d_info.started_at: rider_stats[rider_name]['trips'][trip_num]['start'].append(d_info.started_at)
                delivering_orders.append({
                    'receipt': order.receipt_number,
                    'shop': order.created_by.username,
                    'start_time': start_time,
                    'started_at_iso': d_info.started_at.isoformat() if d_info.started_at else None,
                    'dorm': dorm_name,
                    'rider': rider_name,
                    'items': items_detail
                })
                
            elif status in ['DELIVERED', 'COMPLETED']:
                completed_count += 1
                completed_time = timezone.localtime(d_info.completed_at).strftime('%H:%M') if d_info.completed_at else '-'
                if d_info.rider:
                    rider_stats[rider_name]['completed'] += 1
                    if trip_num not in rider_stats[rider_name]['trips']:
                        rider_stats[rider_name]['trips'][trip_num] = {'orders': 0, 'status': 'COMPLETED', 'start': [], 'end': []}
                    rider_stats[rider_name]['trips'][trip_num]['orders'] += 1
                    if d_info.started_at: rider_stats[rider_name]['trips'][trip_num]['start'].append(d_info.started_at)
                    if d_info.completed_at: rider_stats[rider_name]['trips'][trip_num]['end'].append(d_info.completed_at)
                completed_orders.append({
                    'receipt': order.receipt_number,
                    'shop': order.created_by.username,
                    'dorm': dorm_name,
                    'rider': rider_name,
                    'items': items_detail,
                    'completed_time': completed_time,
                    'duration': d_info.duration_minutes if d_info.duration_minutes else '-',
                    'total': float(order.total_amount)
                })
        else:
            completed_count += 1 
            completed_orders.append({
                'receipt': order.receipt_number,
                'shop': order.created_by.username,
                'dorm': 'รับหน้าร้าน (ไม่มีจัดส่ง)',
                'rider': '-',
                'items': items_detail,
                'completed_time': timezone.localtime(order.created_at).strftime('%H:%M'),
                'duration': '-',
                'total': float(order.total_amount)
            })

    completed_orders.reverse()

    final_rider_stats = []
    for r_name, stats in rider_stats.items():
        trips_list = []
        for t_num, t_data in sorted(stats['trips'].items()):
            duration = '-'
            if t_data['start']:
                min_s = min(t_data['start'])
                if t_data['status'] == 'COMPLETED' and t_data['end']:
                    max_e = max(t_data['end'])
                    duration = int((max_e - min_s).total_seconds() / 60)
                else:
                    duration = int((timezone.now() - min_s).total_seconds() / 60)
            trips_list.append({'trip': t_num, 'status': t_data['status'], 'orders': t_data['orders'], 'duration': duration})
        final_rider_stats.append({'name': r_name, 'completed': stats['completed'], 'delivering': stats['delivering'], 'trips': trips_list})

    return JsonResponse({
        'pending_count': pending_count,
        'delivering_count': delivering_count,
        'completed_count': completed_count,
        'preparing_orders': preparing_orders,
        'delivering_orders': delivering_orders,
        'completed_orders': completed_orders,
        'rider_stats': final_rider_stats
    })

from django.views.decorators.csrf import csrf_exempt
import json
from Riders.models import DeliveryTask

@csrf_exempt
def force_clear_pending_api(request):
    """ API สำหรับแอดมิน ล้างออเดอร์ PENDING ที่ตกค้างลึกๆ ทิ้งทั้งหมด """
    if request.method == 'POST':
        try:
            tasks = DeliveryTask.objects.filter(status='PENDING')
            count = tasks.count()
            
            for task in tasks:
                task.status = 'DELIVERED' # ปิดงานทิ้ง
                task.completed_at = task.order.created_at # ย้อนเวลากลับไปอดีต
                
                if not task.started_at:
                    task.duration_minutes = None # ไม่เอามาคิดเป็นสถิติ
                    
                task.save()
                
            return JsonResponse({"status": "success", "cleared_count": count})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "invalid method"}, status=405)

from django.db.models import Sum
# ถ้ายังไม่ได้ import timezone กับ Order ให้แน่ใจว่าด้านบนมี 2 ตัวนี้แล้ว
# from django.utils import timezone
# from Pos.models import Order

@user_passes_test(is_admin, login_url='/login/')
def financial_dashboard(request):
    # ดึงออเดอร์ที่จัดส่งสำเร็จแล้วทั้งหมด
    completed_orders = Order.objects.filter(
        delivery_info__status__in=['DELIVERED', 'COMPLETED']
    )
    
    # คำนวณรายรับรวมทั้งหมด
    total_income = sum(order.total_amount for order in completed_orders)
    
    # 🌟 สมมติรายจ่าย (เช่น ค่าไรเดอร์ ต้นทุนของร้าน) = 30% ของรายรับ
    # (ถ้ามี Model บันทึกรายจ่าย สามารถ Query มาใส่ตรงนี้ได้เลย)
    total_expense = float(total_income) * 0.30 
    
    # กำไรสุทธิ
    net_profit = float(total_income) - total_expense

    context = {
        'total_income': float(total_income),
        'total_expense': total_expense,
        'net_profit': net_profit,
    }
    
    return render(request, 'BackOffice/financial_dashboard.html', context)