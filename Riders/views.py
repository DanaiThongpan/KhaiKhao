import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder

from Pos.models import Order
from .models import DeliveryTask, Dormitory, RiderProfile
from datetime import timedelta
from django.db.models import Q

# =========================================================
# 1. หน้า Dashboard สำหรับจัดการออเดอร์
# =========================================================
from django.utils.dateparse import parse_date
from django.contrib.auth import get_user_model

@login_required
def rider_dashboard(request):
    """ แสดงหน้าแดชบอร์ดหลักสำหรับเลือกออเดอร์และดูพิกัด """
    days_filter = request.GET.get('days', '0')
    undelivered_only = request.GET.get('undelivered_only', None)
    
    # 🌟 1. ดึงบัญชี Admin และสร้าง/ดึง RiderProfile ออกมา 🌟
    User = get_user_model()
    admin_user = User.objects.filter(is_superuser=True).first()
    default_rider_profile = None
    
    if admin_user:
        # หา RiderProfile ที่ชื่อ Rider Danai ถ้าไม่มีให้สร้างใหม่ผูกกับบัญชี Admin อัตโนมัติ
        default_rider_profile, created = RiderProfile.objects.get_or_create(
            name="Rider Danai",
            created_by=admin_user,
            defaults={'rider_type': 'INTERNAL'}
        )
    
    # 🌟 2. ดึงออเดอร์ทั้งหมดของ "ทุกร้าน" 🌟
    orders = Order.objects.all()
    now_date = timezone.localtime().date()
    
    # กรองตามวัน
    if days_filter == '0':
        orders = orders.filter(created_at__date=now_date)
    elif days_filter == '1':
        target_date = now_date - timedelta(days=1)
        orders = orders.filter(created_at__date=target_date)
    elif days_filter == 'all':
        pass 
        
    # กรองเฉพาะงานที่ยังไม่ส่ง (แก้ให้ใช้ related_name คือ delivery_info)
    if undelivered_only == '1':
        orders = orders.exclude(delivery_info__status__in=['DELIVERED', 'COMPLETED'])
        
    # เรียงลำดับจากใหม่ไปเก่า
    orders = orders.order_by('-created_at')
    
    # ขยายลิมิตการดึงข้อมูล 
    if days_filter == 'all' or undelivered_only == '1':
        orders = orders[:500] 
    else:
        orders = orders[:50] 
        
    # 🌟 3. ยัดโปรไฟล์ไรเดอร์ (RiderProfile) ใส่ในทุกออเดอร์อัตโนมัติ 🌟
    # for order in orders:
    #     task, created = DeliveryTask.objects.get_or_create(order=order)
    #     if not task.rider and default_rider_profile:
    #         task.rider = default_rider_profile
    #         task.save()
            # 🌟 3. บังคับยัดโปรไฟล์ไรเดอร์ (Rider Danai) ทับใส่ในทุกออเดอร์อัตโนมัติ 🌟
    for order in orders:
        task, created = DeliveryTask.objects.get_or_create(order=order)
        
        # 🚨 เอาเงื่อนไข 'not task.rider' ออก เพื่อบังคับทับชื่อเก่าที่ค้างอยู่ในระบบ
        if default_rider_profile and task.rider != default_rider_profile:
            task.rider = default_rider_profile
            task.save()
    dorms = Dormitory.objects.all().order_by('zone', 'name')
        
    return render(request, 'Riders/dashboard.html', {
        'orders': orders,
        'dorms': dorms,
        'days_filter': days_filter,
        'undelivered_only': undelivered_only,
    })

# =========================================================
# 2. หน้า Tracking สำหรับไรเดอร์ (หน้าสแกน QR Code)
# =========================================================
def rider_tracking_page(request, order_id):
    """ หน้าเว็บสำหรับให้ไรเดอร์ (หรือผู้ส่ง) เปิดเพื่อแชร์พิกัด GPS """
    order = get_object_or_404(Order, id=order_id)
    task, created = DeliveryTask.objects.get_or_create(order=order)
    
    return render(request, 'Riders/tracking.html', {
        'order': order,
        'task': task
    })


# =========================================================
# 3. หน้าจัดการฐานข้อมูลหอพัก (Master Data)
# =========================================================
@login_required
def dormitory_map_page(request):
    """ แสดงหน้าแผนที่สำหรับดูจุดและจัดการหอพักทั้งหมดรอบมอ """
    dorms = Dormitory.objects.all()
    
    # แปลงข้อมูลเป็น JSON เพื่อส่งให้ JavaScript นำไปปักหมุด
    dorms_data = [
        {
            'id': d.id,
            'name': d.name,
            'lat': d.latitude,
            'lng': d.longitude,
            'zone': d.zone,  # ส่งข้อมูลโซนจัดส่งไปด้วย
            'color': getattr(d, 'color', 'blue'), # 🌟 ดึงสีไปให้ HTML
        } for d in dorms
    ]
    
    return render(request, 'Riders/dormitory_map.html', {
        'dorms_json': json.dumps(dorms_data, cls=DjangoJSONEncoder)
    })


# =========================================================
# 4. API สำหรับจัดการพิกัดการจัดส่ง (Delivery Tasks)
# =========================================================
# ค้นหาและแทนที่ฟังก์ชัน 2 ตัวนี้
@csrf_exempt
def save_destination_api(request, order_id):
    """ API สำหรับบันทึกพิกัดจุดหมายและหอพักปลายทาง """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order = get_object_or_404(Order, id=order_id)
            task, _ = DeliveryTask.objects.get_or_create(order=order)
            
            dorm_id = data.get('dormitory_id') # 🌟 รับค่า ID หอพักแทน
            if not dorm_id:
                return JsonResponse({"status": "error", "message": "ไม่พบรหัสหอพัก"}, status=400)
                
            dorm = get_object_or_404(Dormitory, id=dorm_id)
            
            # 🌟 บันทึก ForeignKey แทนการเซฟพิกัดและชื่อดิบๆ
            task.destination = dorm 
            
            if task.status == 'PENDING':
                task.status = 'GOING'
                
            task.save()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "invalid method"}, status=405)


@csrf_exempt
def complete_delivery_api(request, order_id):
    """ API สำหรับกดยืนยันจัดส่งสำเร็จ """
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        task, _ = DeliveryTask.objects.get_or_create(order=order)
        task.status = 'DELIVERED'
        task.save()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "invalid method"}, status=405)


@csrf_exempt
def update_location_api(request, order_id):
    """ API รับตำแหน่ง GPS ปัจจุบันจากมือถือไรเดอร์/ผู้ส่ง """
    if request.method != 'POST':
        return JsonResponse({"status": "invalid method"}, status=405)

    try:
        data = json.loads(request.body)
        lat = data.get('lat')
        lng = data.get('lng')

        if lat is None or lng is None:
            return JsonResponse({"status": "error", "message": "ไม่พบพิกัด GPS"}, status=400)

        lat = float(lat)
        lng = float(lng)

        # 🌟 ถ้ารับค่า order_id = 0 ให้อัปเดตพิกัดของ "ทุกงานที่กำลังวิ่งอยู่" ของไรเดอร์คนนี้
        if str(order_id) == "0":
            tasks = DeliveryTask.objects.filter(
                rider__created_by=request.user, 
                status__in=['GOING', 'DELIVERING', 'STARTED']
            )
            for task in tasks:
                task.latitude = lat
                task.longitude = lng
                task.last_location_update = timezone.now()
                task.save()
        else:
            order = get_object_or_404(Order, id=order_id)
            task, _ = DeliveryTask.objects.get_or_create(order=order)
            task.latitude = lat
            task.longitude = lng
            task.last_location_update = timezone.now()
            task.save()

        return JsonResponse({"status": "success", "lat": lat, "lng": lng})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required
def get_location_api(request, order_id):
    """ API ให้ Dashboard ร้านค้าดึงข้อมูลสถานะและ GPS ปัจจุบัน """
    order = get_object_or_404(Order, id=order_id, created_by=request.user)
    task, _ = DeliveryTask.objects.get_or_create(order=order)

    is_online = False
    if task.last_location_update:
        difference = (timezone.now() - task.last_location_update).total_seconds()
        if difference <= 90:
            is_online = True

    # 🌟 เช็กว่ามี destination ผูกอยู่ไหม ถ้ามีดึงพิกัดจากตาราง Dormitory มา
    dest_lat = task.destination.latitude if task.destination else None
    dest_lng = task.destination.longitude if task.destination else None
    dorm_name = task.destination.name if task.destination else ""

    return JsonResponse({
        "lat": task.latitude,
        "lng": task.longitude,
        "dest_lat": dest_lat,
        "dest_lng": dest_lng,
        "status": task.status,
        "is_online": is_online,
        "dormitory_name": dorm_name,
        "last_update": timezone.localtime(task.last_location_update).strftime("%H:%M:%S") if task.last_location_update else "-"
    })


# =========================================================
# 5. API สำหรับจัดการฐานข้อมูลหอพัก (Add / Edit / Delete)
# =========================================================
@csrf_exempt
def add_dormitory_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            lat, lng = data.get('lat'), data.get('lng')
            zone = data.get('zone', 'ทั่วไป')
            color = data.get('color', 'blue') # 🌟 รับค่าสี

            if not name or lat is None or lng is None:
                return JsonResponse({"status": "error", "message": "ข้อมูลไม่ครบ"}, status=400)

            if Dormitory.objects.filter(name=name).exists():
                return JsonResponse({"status": "error", "message": "ชื่อหอพักซ้ำ"}, status=400)

            dorm = Dormitory.objects.create(name=name, latitude=lat, longitude=lng, zone=zone, color=color) # 🌟 เซฟสี
            
            return JsonResponse({
                "status": "success", "id": dorm.id, "name": dorm.name, 
                "lat": dorm.latitude, "lng": dorm.longitude, "zone": dorm.zone, "color": dorm.color
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "invalid method"}, status=405)


@csrf_exempt
def edit_dormitory_api(request, dorm_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            dorm = get_object_or_404(Dormitory, id=dorm_id)
            
            name = data.get('name', '').strip()
            lat, lng = data.get('lat'), data.get('lng')
            zone = data.get('zone', dorm.zone)
            color = data.get('color', getattr(dorm, 'color', 'blue')) # 🌟 รับค่าสี

            if not name or lat is None or lng is None:
                return JsonResponse({"status": "error", "message": "ข้อมูลไม่ครบ"}, status=400)

            if Dormitory.objects.filter(name=name).exclude(id=dorm_id).exists():
                return JsonResponse({"status": "error", "message": "ชื่อหอพักซ้ำ"}, status=400)

            dorm.name = name
            dorm.latitude = float(lat)
            dorm.longitude = float(lng)
            dorm.zone = zone
            dorm.color = color # 🌟 อัปเดตสี
            dorm.save()
            
            return JsonResponse({
                "status": "success", "id": dorm.id, "name": dorm.name, 
                "lat": dorm.latitude, "lng": dorm.longitude, "zone": dorm.zone, "color": dorm.color
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "invalid method"}, status=405)


@csrf_exempt
def delete_dormitory_api(request, dorm_id):
    """ API สำหรับลบข้อมูลหอพัก """
    if request.method == 'POST':
        try:
            dorm = get_object_or_404(Dormitory, id=dorm_id)
            dorm.delete()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "invalid method"}, status=405)

from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

@csrf_exempt
def start_delivery_api(request, order_id):
    """ API สำหรับกดเริ่มจัดส่ง (บันทึกเวลาเริ่ม) """
    if request.method == 'POST':
        try:
            order = get_object_or_404(Order, id=order_id)
            task, _ = DeliveryTask.objects.get_or_create(order=order)
            
            task.status = 'GOING'
            task.started_at = timezone.now() # บันทึกเวลาเริ่มส่ง
            task.save()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "invalid method"}, status=405)

@csrf_exempt
def complete_delivery_api(request, order_id):
    """ API สำหรับกดยืนยันจัดส่งสำเร็จ (บันทึกเวลาจบ และคำนวณนาที) """
    if request.method == 'POST':
        try:
            order = get_object_or_404(Order, id=order_id)
            task, _ = DeliveryTask.objects.get_or_create(order=order)
            
            task.status = 'DELIVERED'
            task.completed_at = timezone.now() # บันทึกเวลาส่งถึง
            
            # คำนวณเวลาที่ใช้ไปทั้งหมด
            if task.started_at:
                diff = task.completed_at - task.started_at
                task.duration_minutes = int(diff.total_seconds() / 60)
            
            task.save()
            return JsonResponse({
                "status": "success", 
                "duration": task.duration_minutes
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "invalid method"}, status=405)

# ... import เดิม ...

@csrf_exempt
def cut_trip_api(request):
    """ API สำหรับให้ไรเดอร์กดปุ่ม 'ตัดรอบ' """
    if request.method == 'POST':
        # ดึงรอบปัจจุบันขึ้นมา +1
        current_trip = request.session.get('trip_number', 1)
        request.session['trip_number'] = current_trip + 1
        return JsonResponse({"status": "success", "new_trip": current_trip + 1})
    return JsonResponse({"status": "invalid method"}, status=405)

# =======================================================
# 1. แก้ไข API ตัดรอบทีละหลายออเดอร์
# =======================================================
@csrf_exempt
def start_batch_delivery_api(request):
    if request.method == 'POST':
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"status": "error", "message": "เซสชันหลุด กรุณาล็อกอินใหม่"}, status=401)

            data = json.loads(request.body)
            order_ids = data.get('order_ids', [])
            
            if not order_ids:
                return JsonResponse({"status": "error", "message": "ไม่ได้เลือกออเดอร์"}, status=400)

            current_trip = request.session.get('trip_number', 1)

            # 🌟 แก้เป็น created_by ตามโครงสร้าง Database ของคุณ
            rider_profile, created = RiderProfile.objects.get_or_create(
                created_by=request.user, 
                defaults={'name': request.user.username}
            )

            for oid in order_ids:
                order = get_object_or_404(Order, id=oid)
                task, _ = DeliveryTask.objects.get_or_create(order=order)
                
                task.status = 'GOING'
                task.started_at = timezone.now()
                task.rider = rider_profile # ผูกกับ RiderProfile
                
                try:
                    task.trip_number = current_trip
                except Exception:
                    pass
                    
                task.save()
            
            request.session['trip_number'] = current_trip + 1
            return JsonResponse({"status": "success"})
            
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "invalid method"}, status=405)


# =======================================================
# 2. แก้ไข API เริ่มงานรายออเดอร์
# =======================================================
@csrf_exempt
def start_delivery_api(request, order_id):
    if request.method == 'POST':
        try:
            order = get_object_or_404(Order, id=order_id)
            task, _ = DeliveryTask.objects.get_or_create(order=order)
            
            task.status = 'GOING'
            task.started_at = timezone.now()
            
            if hasattr(task, 'trip_number'):
                task.trip_number = request.session.get('trip_number', 1)
                
            # 🌟 แก้เป็น created_by ตามโครงสร้าง Database ของคุณ
            if not task.rider:
                rider_profile, _ = RiderProfile.objects.get_or_create(
                    created_by=request.user,
                    defaults={'name': request.user.username}
                )
                task.rider = rider_profile 
                
            task.save()
            return JsonResponse({"status": "success"})
            
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "invalid method"}, status=405)

@csrf_exempt
def reset_trip_api(request):
    """ API สำหรับรีเซ็ตรอบกลับไปเริ่มที่ 1 ใหม่ """
    if request.method == 'POST':
        request.session['trip_number'] = 1
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "invalid method"}, status=405)

@csrf_exempt
def complete_batch_delivery_api(request):
    """ API สำหรับเคลียร์ออเดอร์ตกค้างทีละหลายๆ บิล (ปิดงานแบบข้ามเวลา ไม่นำมาคิดสถิติ) """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_ids = data.get('order_ids', [])
            
            for oid in order_ids:
                order = get_object_or_404(Order, id=oid)
                task, _ = DeliveryTask.objects.get_or_create(order=order)
                
                task.status = 'DELIVERED' 
                
                # 🌟 1. ดันเวลาเสร็จสิ้น กลับไปเป็นวันเดียวและเวลาเดียวกับที่ลูกค้าสั่ง 
                # (ทำให้มันไม่เด้งมาปนกับยอดของวันนี้แน่นอน)
                task.completed_at = order.created_at
                
                # 🌟 2. ล้างค่าเวลาทิ้ง (None) เพื่อไม่ให้กราฟเอา 0 นาทีไปหารเป็นค่าเฉลี่ยเวลาวิ่งของไรเดอร์
                if not task.started_at:
                    task.duration_minutes = None
                    
                task.save()
                
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "invalid method"}, status=405)

# --- วาง 2 ฟังก์ชันนี้ไว้ด้านบนของไฟล์ ---
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for: return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def get_device_info(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    if 'iPhone' in user_agent: return '📱 iPhone/iOS'
    elif 'iPad' in user_agent: return '📱 iPad/iOS'
    elif 'Android' in user_agent: return '📱 Android'
    elif 'Windows' in user_agent: return '💻 Windows PC'
    elif 'Macintosh' in user_agent: return '🍎 Mac'
    else: return 'ไม่ทราบรุ่น'

# --- แก้ไขฟังก์ชันรับพิกัดเดิม ให้ดักจับและบันทึก IP ด้วย ---
@csrf_exempt
def update_location_api(request, order_id):
    if request.method != 'POST':
        return JsonResponse({"status": "invalid method"}, status=405)

    try:
        data = json.loads(request.body)
        lat = data.get('lat')
        lng = data.get('lng')

        if lat is None or lng is None:
            return JsonResponse({"status": "error", "message": "ไม่พบพิกัด GPS"}, status=400)

        lat = float(lat)
        lng = float(lng)

        # 🌟 แกะ IP และรุ่นมือถือจาก Request 🌟
        current_ip = get_client_ip(request)
        current_device = get_device_info(request)

        if str(order_id) == "0":
            # 🌟 บันทึกข้อมูลเครื่องและ IP ลงโปรไฟล์ไรเดอร์ 🌟
            rider_profile = RiderProfile.objects.filter(created_by=request.user).first()
            if rider_profile:
                rider_profile.client_ip = current_ip
                rider_profile.device_info = current_device
                rider_profile.save()

            tasks = DeliveryTask.objects.filter(
                rider__created_by=request.user, 
                status__in=['GOING', 'DELIVERING', 'STARTED']
            )
            for task in tasks:
                task.latitude = lat
                task.longitude = lng
                task.last_location_update = timezone.now()
                task.save()
        else:
            order = get_object_or_404(Order, id=order_id)
            task, _ = DeliveryTask.objects.get_or_create(order=order)
            
            # บันทึก IP หากเป็นการส่งพิกัดทีละออเดอร์
            if task.rider:
                task.rider.client_ip = current_ip
                task.rider.device_info = current_device
                task.rider.save()

            task.latitude = lat
            task.longitude = lng
            task.last_location_update = timezone.now()
            task.save()

        return JsonResponse({"status": "success", "lat": lat, "lng": lng})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)