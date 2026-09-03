import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from Pos.models import Order
from .models import DeliveryTask

@login_required
def rider_dashboard(request):
    orders = Order.objects.filter(created_by=request.user).order_by('-created_at')[:30]
    for o in orders:
        DeliveryTask.objects.get_or_create(order=o)
    return render(request, 'Riders/dashboard.html', {'orders': orders})

def rider_tracking_page(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    task, _ = DeliveryTask.objects.get_or_create(order=order)
    return render(request, 'Riders/tracking.html', {'order': order, 'task': task})

@csrf_exempt
def update_location_api(request, order_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order = get_object_or_404(Order, id=order_id)
            task, _ = DeliveryTask.objects.get_or_create(order=order)
            task.latitude = data.get('lat')
            task.longitude = data.get('lng')
            task.last_location_update = timezone.now()
            task.save()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "invalid method"}, status=405)

@login_required
def get_location_api(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    task, _ = DeliveryTask.objects.get_or_create(order=order)
    return JsonResponse({
        "lat": task.latitude,
        "lng": task.longitude,
        "last_update": timezone.localtime(task.last_location_update).strftime("%H:%M:%S") if task.last_location_update else "ยังไม่เริ่มแชร์พิกัด"
    })