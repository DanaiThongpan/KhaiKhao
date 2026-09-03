import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from Pos.models import Order
from .models import DeliveryTask


# =========================================================
# Dashboard ร้านค้า
# =========================================================
@login_required
def rider_dashboard(request):
    orders = Order.objects.filter(created_by=request.user).order_by('-created_at')[:30]
    
    # สร้าง DeliveryTask ถ้ายังไม่มี
    for order in orders:
        DeliveryTask.objects.get_or_create(order=order)
        
    return render(request, 'Riders/dashboard.html', {'orders': orders})


# =========================================================
# หน้าสำหรับไรเดอร์แชร์ GPS
# =========================================================
def rider_tracking_page(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    task, created = DeliveryTask.objects.get_or_create(order=order)
    
    return render(request, 'Riders/tracking.html', {
        'order': order,
        'task': task
    })


# =========================================================
# API สำหรับให้ไรเดอร์บันทึกชื่อหอพัก
# =========================================================
@csrf_exempt
def save_dormitory_api(request, order_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            dorm_name = data.get('dormitory_name', '').strip()
            
            order = get_object_or_404(Order, id=order_id)
            task, _ = DeliveryTask.objects.get_or_create(order=order)
            
            task.dormitory_name = dorm_name
            task.save()
            
            return JsonResponse({"status": "success", "dormitory_name": task.dormitory_name})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    return JsonResponse({"status": "invalid method"}, status=405)


# =========================================================
# API รับตำแหน่ง GPS จากมือถือไรเดอร์
# =========================================================
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

        if not (-90 <= lat <= 90):
            return JsonResponse({"status": "error", "message": "Latitude ไม่ถูกต้อง"}, status=400)
        if not (-180 <= lng <= 180):
            return JsonResponse({"status": "error", "message": "Longitude ไม่ถูกต้อง"}, status=400)

        order = get_object_or_404(Order, id=order_id)
        task, created = DeliveryTask.objects.get_or_create(order=order)

        task.latitude = lat
        task.longitude = lng
        task.last_location_update = timezone.now()

        # เปลี่ยนสถานะอัตโนมัติเมื่อเริ่มส่งพิกัด
        if task.status == 'PENDING':
            task.status = 'GOING'
            
        task.save()

        return JsonResponse({
            "status": "success",
            "lat": lat,
            "lng": lng,
            "last_update": timezone.localtime(task.last_location_update).strftime("%H:%M:%S")
        })

    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"status": "error", "message": "ข้อมูลไม่ถูกต้อง"}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# =========================================================
# API ให้ Dashboard ร้านค้าดึง GPS และชื่อหอพัก
# =========================================================
@login_required
def get_location_api(request, order_id):
    order = get_object_or_404(Order, id=order_id, created_by=request.user)
    task, created = DeliveryTask.objects.get_or_create(order=order)

    is_online = False

    if task.last_location_update:
        now = timezone.now()
        difference = (now - task.last_location_update).total_seconds()
        
        # ถ้าได้รับ GPS ภายใน 90 วินาที ถือว่าออนไลน์
        if difference <= 90:
            is_online = True

    return JsonResponse({
        "lat": task.latitude,
        "lng": task.longitude,
        "status": task.status,
        "is_online": is_online,
        "dormitory_name": task.dormitory_name or "-",
        "last_update": timezone.localtime(task.last_location_update).strftime("%H:%M:%S") if task.last_location_update else "ยังไม่เริ่มแชร์พิกัด"
    })