import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import DeliveryZone
from Riders.models import Dormitory

def dashboard(request):
    zones = DeliveryZone.objects.filter(is_active=True)
    zones_data = []
    for z in zones:
        zones_data.append({
            'id': z.id,
            'name': z.name,
            'fee': float(z.fee),
            'color': z.color,
            'polygon_data': z.polygon_data
        })

    # ดึงหอพักทั้งหมดมาโชว์เป็นจุดอ้างอิง
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
                zone = DeliveryZone.objects.get(id=zone_id)
                zone.name = name
                zone.fee = fee
                zone.color = color
                zone.polygon_data = polygon_data
                zone.save()
            else:
                zone = DeliveryZone.objects.create(
                    name=name, fee=fee, color=color, polygon_data=polygon_data
                )
            return JsonResponse({'status': 'success', 'id': zone.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

@csrf_exempt
def delete_zone(request, zone_id):
    if request.method == 'POST':
        try:
            zone = DeliveryZone.objects.get(id=zone_id)
            zone.delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)
