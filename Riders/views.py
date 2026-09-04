import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder

from Pos.models import Order
from .models import DeliveryTask, Dormitory


# =========================================================
# 1. หน้า Dashboard สำหรับจัดการออเดอร์
# =========================================================
@login_required
def rider_dashboard(request):
    """ แสดงหน้าแดชบอร์ดหลักสำหรับเลือกออเดอร์และดูพิกัด """
    # ดึงออเดอร์ของผู้ใช้ระบบ POS ล่าสุด
    orders = Order.objects.filter(created_by=request.user).order_by('-created_at')[:30]
    
    # ตรวจสอบและสร้าง DeliveryTask ผูกกับออเดอร์อัตโนมัติ
    for order in orders:
        DeliveryTask.objects.get_or_create(order=order)
        
    # ดึงรายชื่อหอพักทั้งหมดมาเผื่อใช้แสดงผลในแดชบอร์ด
    dorms = Dormitory.objects.all().order_by('zone', 'name')
        
    return render(request, 'Riders/dashboard.html', {
        'orders': orders,
        'dorms': dorms
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

        order = get_object_or_404(Order, id=order_id)
        task, _ = DeliveryTask.objects.get_or_create(order=order)

        task.latitude = lat
        task.longitude = lng
        task.last_location_update = timezone.now()
        task.save()

        return JsonResponse({
            "status": "success",
            "lat": lat,
            "lng": lng,
            "last_update": timezone.localtime(task.last_location_update).strftime("%H:%M:%S")
        })

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