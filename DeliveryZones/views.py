import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import DeliveryZone
from Riders.models import Dormitory

@login_required
def dashboard(request):
    # 🌟 ดึงเฉพาะสโคปโซนจัดส่งที่ร้านค้านี้วาดขึ้นมาเอง (แยกตามร้านค้า ไม่ปนกัน) 🌟
    zones = DeliveryZone.objects.filter(is_active=True, created_by=request.user)
    zones_data = []
    for z in zones:
        zones_data.append({
            'id': z.id,
            'name': z.name,
            'fee': float(z.fee),
            'color': z.color,
            'polygon_data': z.polygon_data
        })

    # ดึงหอพักทั้งหมดมาแสดงเป็นจุดอ้างอิงบนแผนที่ช่วยในการวาดสโคป
    dorms = Dormitory.objects.all()
    dorms_data = []
    for d in dorms:
        dorms_data.append({
            'id': d.id,
            'name': d.name,
            'lat': d.latitude,
            'lng': d.longitude,
            'zone': d.zone,
            'color': getattr(d, 'color', 'blue')
        })

    context = {
        'zones_json': json.dumps(zones_data),
        'dorms_json': json.dumps(dorms_data)
    }
    return render(request, 'DeliveryZones/dashboard.html', context)

@login_required
@csrf_exempt
def save_zone(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            zone_id = data.get('id')
            name = data.get('name')
            fee = data.get('fee', 0)
            color = data.get('color', '#3b82f6')
            polygon_data = data.get('polygon_data')

            if zone_id:
                # แก้ไขเฉพาะโซนของร้านตัวเองเท่านั้น
                zone = get_object_or_404(DeliveryZone, id=zone_id, created_by=request.user)
                zone.name = name
                zone.fee = fee
                zone.color = color
                zone.polygon_data = polygon_data
                zone.save()
            else:
                # สร้างโซนใหม่โดยผูกกับร้านค้าที่กำลังใช้งาน (request.user)
                zone = DeliveryZone.objects.create(
                    name=name,
                    fee=fee,
                    color=color,
                    polygon_data=polygon_data,
                    created_by=request.user
                )
            return JsonResponse({'status': 'success', 'id': zone.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

@login_required
@csrf_exempt
def delete_zone(request, zone_id):
    if request.method == 'POST':
        try:
            # ลบได้เฉพาะโซนที่เป็นของร้านตัวเองเท่านั้น
            zone = get_object_or_404(DeliveryZone, id=zone_id, created_by=request.user)
            zone.delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)
