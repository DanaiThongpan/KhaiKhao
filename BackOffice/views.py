from datetime import timedelta
import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.db.models import Sum
from Expenses.models import Expense
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

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, 'role', '') == "admin")

@user_passes_test(is_admin, login_url='/login/')
def financial_dashboard(request):
    # ==========================================
    # 1. 💰 คำนวณรายรับ (Income) - ดึงจากบิลทั้งหมด
    # ==========================================
    # ไม่กรอง Delivery แล้ว ดึงจากยอดบิลทั้งหมดที่ขายได้เลย
    total_income_agg = Order.objects.aggregate(total=Sum('total_amount'))
    total_income = float(total_income_agg['total'] or 0)
    
    # ดึงยอดขาย "แยกตามร้านค้าแต่ละร้าน"
    shop_sales = Order.objects.values('created_by__username').annotate(
        total_sales=Sum('total_amount')
    ).order_by('-total_sales')

    # ==========================================
    # 2. 📉 คำนวณรายจ่ายของจริง (Expense)
    # ==========================================
    # ดึงรายจ่ายทั้งหมดที่เป็น is_paid=True (จ่ายแล้ว)
    expense_agg = Expense.objects.filter(is_paid=True).aggregate(total=Sum('amount'))
    total_expense = float(expense_agg['total'] or 0)
    
    # ==========================================
    # 3. ✨ สรุปกำไรสุทธิและเปอร์เซ็นต์
    # ==========================================
    net_profit = total_income - total_expense

    income_pct = 100.0 if total_income > 0 else 0.0
    if total_income > 0:
        expense_pct = (total_expense / total_income) * 100
        profit_pct = (net_profit / total_income) * 100
    else:
        expense_pct = 0.0
        profit_pct = 0.0

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'net_profit': net_profit,
        'income_pct': income_pct,
        'expense_pct': expense_pct,
        'profit_pct': profit_pct,
        'shop_sales': shop_sales, # 🌟 ส่งข้อมูลยอดขายแยกสาขาไปที่หน้าเว็บ
    }
    
    return render(request, 'BackOffice/financial_dashboard.html', context)

@user_passes_test(is_admin, login_url='/login/')
def rider_map(request):
    """ แสดงผลหน้าจอแผนที่ติดตามไรเดอร์ """
    return render(request, 'BackOffice/rider_map.html')

@user_passes_test(is_admin, login_url='/login/')
def api_rider_locations(request):
    """ API ส่งข้อมูลพิกัดและออเดอร์ที่ไรเดอร์แต่ละคนกำลังถืออยู่ """
    # ดึงเฉพาะงานที่กำลังวิ่งอยู่ (DELIVERING/GOING)
    tasks = DeliveryTask.objects.filter(status__in=['GOING', 'DELIVERING', 'STARTED']).select_related('rider', 'order', 'destination')
    
    riders_data = {}
    for t in tasks:
        if not t.rider: continue
        
        r_id = t.rider.id
        r_name = getattr(t.rider, 'name', getattr(t.rider, 'username', f"ไรเดอร์ #{r_id}"))
        
        if r_id not in riders_data:
            # 📍 ค้นหาพิกัด (ถ้าไม่มีใน DB ให้จำลองพิกัด ม.อุบล ก่อน)
            lat = getattr(t.rider, 'latitude', getattr(t.rider, 'lat', 15.1186 + (r_id * 0.0005)))
            lng = getattr(t.rider, 'longitude', getattr(t.rider, 'lng', 104.9046 + (r_id * 0.0005)))
            
            riders_data[r_id] = {
                'id': r_id,
                'name': r_name,
                'lat': lat,
                'lng': lng,
                'orders': [],
            }
        
        # ⏱️ คำนวณเวลาว่าหิ้วออกไปกี่นาทีแล้ว
        duration_str = "เพิ่งเริ่ม"
        if t.started_at:
            diff = (timezone.now() - t.started_at).total_seconds()
            mins = int(diff // 60)
            if mins >= 60:
                h = mins // 60
                m = mins % 60
                duration_str = f"{h} ชม. {m} นาที"
            else:
                duration_str = f"{mins} นาที"

        dorm_name = t.destination.name if t.destination else "ไม่ได้ระบุหอพัก"
        
        riders_data[r_id]['orders'].append({
            'receipt': t.order.receipt_number,
            'dorm': dorm_name,
            'duration': duration_str
        })
        
    return JsonResponse({"status": "success", "riders": list(riders_data.values())})

import math # 🌟 เพิ่มบรรทัดนี้เพื่อใช้คำนวณระยะทาง

@user_passes_test(is_admin, login_url='/login/')
def api_rider_locations(request):
    """ API ส่งข้อมูลพิกัด จัดลำดับคิว และรวมออเดอร์ทุกร้านให้อยู่ในรถคันเดียว """
    tasks = DeliveryTask.objects.filter(status__in=['GOING', 'DELIVERING', 'STARTED']).select_related('rider', 'order', 'destination', 'order__created_by')
    
    riders_data = {}
    for t in tasks:
        if not t.rider: continue
        
        r_id = t.rider.id
        r_name = getattr(t.rider, 'name', getattr(t.rider, 'username', f"ไรเดอร์ #{r_id}"))
        
        if r_id not in riders_data:
            # 🌟 1. ดึงข้อมูล IP และรุ่นมือถือ 🌟
            rider_ip = getattr(t.rider, 'client_ip', None) or 'ไม่ทราบ IP'
            rider_device = getattr(t.rider, 'device_info', None) or 'ไม่ทราบรุ่นมือถือ'

            # ดึงพิกัดตั้งต้น (กรณีไม่มีข้อมูลเลย)
            default_lat = getattr(t.rider, 'latitude', getattr(t.rider, 'lat', 15.1186 + (r_id * 0.0005)))
            default_lng = getattr(t.rider, 'longitude', getattr(t.rider, 'lng', 104.9046 + (r_id * 0.0005)))
            try: default_lat, default_lng = float(default_lat), float(default_lng)
            except: default_lat, default_lng = 15.1186, 104.9046

            riders_data[r_id] = {
                'id': r_id, 'name': r_name, 
                'lat': default_lat, 
                'lng': default_lng, 
                'orders': [],
                'rider_ip': rider_ip,
                'rider_device': rider_device,
                'last_update': None # ตัวแปรช่วยเช็กเวลาว่าพิกัดไหนใหม่สุด
            }
        
        # 🌟 2. จุดสำคัญ: ดึงพิกัดล่าสุดที่มือถือไรเดอร์ (หน้า /riders/) ยิงเข้ามา 🌟
        if t.latitude and t.longitude:
            try:
                t_lat, t_lng = float(t.latitude), float(t.longitude)
                # ถ้าออเดอร์นี้มีพิกัดที่อัปเดต "ใหม่กว่า" ให้อัปเดตตำแหน่งไรเดอร์บนแผนที่ทันที
                if not riders_data[r_id]['last_update'] or (t.last_location_update and t.last_location_update > riders_data[r_id]['last_update']):
                    riders_data[r_id]['lat'] = t_lat
                    riders_data[r_id]['lng'] = t_lng
                    riders_data[r_id]['last_update'] = t.last_location_update
            except Exception:
                pass
        
        duration_str = "เพิ่งเริ่ม"
        if t.started_at:
            diff = (timezone.now() - t.started_at).total_seconds()
            mins = int(diff // 60)
            if mins >= 60: duration_str = f"{mins // 60} ชม. {mins % 60} นาที"
            else: duration_str = f"{mins} นาที"

        dorm_name = t.destination.name if t.destination else "ไม่ได้ระบุหอพัก"
        dorm_zone = getattr(t.destination, 'zone', 'อื่นๆ') if t.destination else 'อื่นๆ'
        
        shop_name = t.order.created_by.username if t.order.created_by else "ไม่ระบุร้าน"
        
        # พิกัดเป้าหมาย (ปลายทางหอพัก)
        d_lat, d_lng = riders_data[r_id]['lat'], riders_data[r_id]['lng']
        if t.destination:
            dl = getattr(t.destination, 'latitude', getattr(t.destination, 'lat', d_lat))
            dg = getattr(t.destination, 'longitude', getattr(t.destination, 'lng', d_lng))
            try: d_lat, d_lng = float(dl), float(dg)
            except: pass

        # 🌟 3. ข้อมูล IP ของคนคีย์บิล 🌟
        order_ip = getattr(t.order, 'client_ip', None) or 'ไม่ระบุ'
        order_device = getattr(t.order, 'device_info', None) or 'ไม่ระบุ'

        riders_data[r_id]['orders'].append({
            'receipt': t.order.receipt_number,
            'shop': shop_name, 
            'dorm': dorm_name,
            'zone': dorm_zone,
            'duration': duration_str,
            'lat': d_lat,
            'lng': d_lng,
            'order_ip': order_ip,
            'order_device': order_device
        })

    current_hour = timezone.localtime().hour
    SEQ_CHAIN = ['ประตู 3', 'หวานเย็น', 'หน้า มอ', 'อ.10']

    # =========================================================
    # 🧠 สมองกลจัดเรียงคิว (Dynamic Proximity + Rule Based)
    # =========================================================
    for r_id, data in riders_data.items():
        # ลบค่า last_update ออกก่อนแปลงเป็น JSON เพื่อป้องกัน Error
        if 'last_update' in data:
            del data['last_update']
            
        curr_lat, curr_lng = data['lat'], data['lng']
        all_orders = data['orders']
        if not all_orders: continue

        zones = {}
        for o in all_orders:
            z = o['zone']
            if z not in zones: zones[z] = []
            zones[z].append(o)
            
        unvisited_zones = list(zones.keys())
        ordered_zones = []
        current_zone_context = None

        while unvisited_zones:
            next_zone = None
            if current_zone_context:
                curr_idx = -1
                for i, kw in enumerate(SEQ_CHAIN):
                    if kw in current_zone_context:
                        curr_idx = i
                        break
                if curr_idx != -1:
                    for kw in SEQ_CHAIN[curr_idx+1:]:
                        for uz in unvisited_zones:
                            if kw in uz:
                                next_zone = uz
                                break
                        if next_zone: break

            if not next_zone:
                valid_candidates = []
                for z in unvisited_zones:
                    is_hor_nai = 'หอใน' in z or any('หอใน' in o['dorm'] for o in zones[z])
                    if is_hor_nai and (current_hour >= 22 or current_hour < 4):
                        continue
                    valid_candidates.append(z)
                
                if not valid_candidates:
                    valid_candidates = unvisited_zones 
                    
                min_dist = float('inf')
                for z in valid_candidates:
                    dist = min(math.sqrt((curr_lat - o['lat'])**2 + (curr_lng - o['lng'])**2) for o in zones[z])
                    if dist < min_dist:
                        min_dist = dist
                        next_zone = z
            
            ordered_zones.append(next_zone)
            unvisited_zones.remove(next_zone)
            
            temp_lat, temp_lng = curr_lat, curr_lng
            temp_orders = zones[next_zone].copy()
            while temp_orders:
                closest_o = min(temp_orders, key=lambda o: math.sqrt((temp_lat - o['lat'])**2 + (temp_lng - o['lng'])**2))
                temp_lat, temp_lng = closest_o['lat'], closest_o['lng']
                temp_orders.remove(closest_o)
            
            curr_lat, curr_lng = temp_lat, temp_lng
            current_zone_context = next_zone

        optimized_path = []
        final_curr_lat, final_curr_lng = data['lat'], data['lng'] 
        
        for z in ordered_zones:
            zone_orders = zones[z]
            while zone_orders:
                closest_order = min(zone_orders, key=lambda o: math.sqrt((final_curr_lat - o['lat'])**2 + (final_curr_lng - o['lng'])**2))
                optimized_path.append(closest_order)
                zone_orders.remove(closest_order)
                final_curr_lat, final_curr_lng = closest_order['lat'], closest_order['lng']
                
        data['orders'] = optimized_path

    return JsonResponse({"status": "success", "riders": list(riders_data.values())})