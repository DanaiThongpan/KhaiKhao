from datetime import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear

from Pos.models import Order
from Accounts.models import User  # นำเข้า Model User สำหรับทำตัวกรองเลือกผู้ใช้งาน/ร้านค้า

@login_required
def reports_home(request):
    # 1. รับค่าตัวกรองจาก Request (เลือกผู้ใช้งาน และ ประเภทของกราฟ)
    selected_user_id = request.GET.get('user', '')
    filter_type = request.GET.get('filter', 'day') # ค่าเริ่มต้นเป็นรายวัน ('day')

    # 2. ตั้งค่า QuerySet เริ่มต้นของ Order
    orders_qs = Order.objects.all()

    # ถ้ามีการเลือกดูเฉพาะร้าน/ผู้ใช้งานที่กำหนด
    if selected_user_id:
        orders_qs = orders_qs.filter(created_by_id=selected_user_id)

    # 3. คำนวณยอดขายสะสมรวมทั้งหมด (Grand Total) ตามเงื่อนไขที่เลือก
    grand_total = orders_qs.aggregate(total=Sum('total_amount'))['total'] or 0

    # 4. ดึงข้อมูลสำหรับตารางสรุปแต่ละประเภท (ใช้ Query แยกเพื่อความชัวร์และไม่ตีกัน)
    # 4.1 รายวัน (10 วันล่าสุด)
    daily_sales = (
        orders_qs.annotate(period=TruncDay('created_at'))
        .values('period')
        .annotate(total=Sum('total_amount'))
        .order_by('-period')[:10]
    )

    # 4.2 รายสัปดาห์
    weekly_sales = (
        orders_qs.annotate(period=TruncWeek('created_at'))
        .values('period')
        .annotate(total=Sum('total_amount'))
        .order_by('-period')[:10]
    )

    # 4.3 รายเดือน
    monthly_sales = (
        orders_qs.annotate(period=TruncMonth('created_at'))
        .values('period')
        .annotate(total=Sum('total_amount'))
        .order_by('-period')[:12]
    )

    # 4.4 รายปี
    yearly_sales = (
        orders_qs.annotate(period=TruncYear('created_at'))
        .values('period')
        .annotate(total=Sum('total_amount'))
        .order_by('-period')[:5]
    )

    # 5. จัดเตรียมข้อมูลสำหรับแสดงผลบน Chart.js ตาม Tab ที่ผู้ใช้กดเลือก
    if filter_type == 'year':
        chart_data = (
            orders_qs.annotate(period=TruncYear('created_at'))
            .values('period')
            .annotate(total=Sum('total_amount'))
            .order_by('period')
        )
        chart_label = 'สถิติยอดขายรายปี'
    elif filter_type == 'month':
        chart_data = (
            orders_qs.annotate(period=TruncMonth('created_at'))
            .values('period')
            .annotate(total=Sum('total_amount'))
            .order_by('period')
        )
        chart_label = 'สถิติยอดขายรายเดือน'
    else:  # ค่าเริ่มต้น 'day'
        chart_data = (
            orders_qs.annotate(period=TruncDay('created_at'))
            .values('period')
            .annotate(total=Sum('total_amount'))
            .order_by('-period')[:14]  # เอา 14 วันล่าสุดมาแสดงกราฟสวยๆ
        )
        # เรียงกลับให้น้อยไปมากเพื่อแสดงกราฟซ้ายไปขวา
        chart_data = sorted(list(chart_data), key=lambda x: x['period'])
        chart_label = 'สถิติยอดขายรายวัน (14 วันล่าสุด)'

    # 6. ดึงรายชื่อผู้ใช้ทั้งหมด เพื่อส่งไปให้ Dropdown ใน HTML
    all_users = User.objects.filter(is_active=True)

    # 7. ส่งตัวแปรทั้งหมดไปที่หน้า Template
    context = {
        'grand_total': grand_total,
        'daily_sales': daily_sales,
        'weekly_sales': weekly_sales,
        'monthly_sales': monthly_sales,
        'yearly_sales': yearly_sales,
        'chart_data': chart_data,
        'chart_label': chart_label,
        'filter_type': filter_type,
        'all_users': all_users,
        'selected_user_id': selected_user_id,
    }

    return render(request, 'Reports/home.html', context)