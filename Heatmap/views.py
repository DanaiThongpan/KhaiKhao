import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from Pos.models import Order

@login_required
def heatmap_dashboard(request):
    filter_type = request.GET.get('filter', 'monthly') # ค่าเริ่มต้นคือรายเดือน
    now = timezone.localtime()

    # 1. คำนวณวันเริ่มต้นตามตัวกรอง
    if filter_type == 'daily':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_type == 'weekly':
        start_date = now - timedelta(days=now.weekday()) # วันจันทร์ของสัปดาห์นี้
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_type == 'yearly':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else: # monthly
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 2. ดึงออเดอร์เฉพาะร้านที่ล็อกอิน + อยู่ในช่วงเวลา + มีหอพักปลายทาง
    # ใช้ select_related เพื่อดึงข้อมูลหอพักมาพร้อมกัน (แก้ปัญหา Query ช้า)
    orders = Order.objects.filter(
        # created_by=request.user,
        created_at__gte=start_date,
        delivery_info__isnull=False,
        delivery_info__destination__isnull=False
    ).select_related('delivery_info__destination')

# 3. จัดกลุ่มนับจำนวนบิลตามหอพัก
    dorm_counts = {}
    for order in orders:
        dest = order.delivery_info.destination
        # 🌟 เปลี่ยนมาเรียกใช้ชื่อฟิลด์แบบเต็มตามโมเดลของคุณ
        if dest.latitude and dest.longitude:
            if dest.id not in dorm_counts:
                dorm_counts[dest.id] = {
                    'name': dest.name,
                    'zone': dest.zone or 'ทั่วไป',
                    'lat': float(dest.latitude),   # 🌟 แก้เป็น .latitude
                    'lng': float(dest.longitude),  # 🌟 แก้เป็น .longitude
                    'count': 0
                }
            dorm_counts[dest.id]['count'] += 1

    # 4. แปลง Dictionary เป็น List เพื่อส่งให้ Javascript วาดแผนที่
    heatmap_data = list(dorm_counts.values())

    context = {
        'heatmap_data_json': json.dumps(heatmap_data),
        'filter_type': filter_type,
    }
    return render(request, 'Heatmap/dashboard.html', context)