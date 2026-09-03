from datetime import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q  # <--- เพิ่ม Q ตรงนี้
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear

from Pos.models import Order, OrderItem
from Accounts.models import User

@login_required
def reports_home(request):
    # 1. รับค่าตัวกรองจาก Request
    selected_user_id = request.GET.get('user', '')
    filter_type = request.GET.get('filter', 'day') 

    # 2. ตั้งค่า QuerySet เริ่มต้นของ Order
    orders_qs = Order.objects.all()

    # ถ้ามีการเลือกดูเฉพาะร้าน/ผู้ใช้งานที่กำหนด
    if selected_user_id:
        orders_qs = orders_qs.filter(created_by_id=selected_user_id)

    # 3. คำนวณยอดขายสะสมรวมทั้งหมด (Grand Total)
    grand_total = orders_qs.aggregate(total=Sum('total_amount'))['total'] or 0

    # 4. ดึงข้อมูลสำหรับตารางสรุปแต่ละประเภท
    daily_sales = (
        orders_qs.annotate(period=TruncDay('created_at'))
        .values('period')
        .annotate(total=Sum('total_amount'), order_count=Count('id', distinct=True))
        .order_by('-period')[:10]
    )

    weekly_sales = (
        orders_qs.annotate(period=TruncWeek('created_at'))
        .values('period')
        .annotate(total=Sum('total_amount'), order_count=Count('id', distinct=True))
        .order_by('-period')[:10]
    )

    monthly_sales = (
        orders_qs.annotate(period=TruncMonth('created_at'))
        .values('period')
        .annotate(total=Sum('total_amount'), order_count=Count('id', distinct=True))
        .order_by('-period')[:12]
    )

    yearly_sales = (
        orders_qs.annotate(period=TruncYear('created_at'))
        .values('period')
        .annotate(total=Sum('total_amount'), order_count=Count('id', distinct=True))
        .order_by('-period')[:5]
    )

    # 5. จัดเตรียมข้อมูลสำหรับแสดงผลบน Chart.js
    if filter_type == 'year':
        chart_data_qs = (
            orders_qs.annotate(period=TruncYear('created_at'))
            .values('period')
            .annotate(total=Sum('total_amount'), order_count=Count('id', distinct=True))
            .order_by('-period')
        )
        chart_label = 'สถิติยอดขายรายปี'
    elif filter_type == 'month':
        chart_data_qs = (
            orders_qs.annotate(period=TruncMonth('created_at'))
            .values('period')
            .annotate(total=Sum('total_amount'), order_count=Count('id', distinct=True))
            .order_by('-period')
        )
        chart_label = 'สถิติยอดขายรายเดือน'
    else:  
        chart_data_qs = (
            orders_qs.annotate(period=TruncDay('created_at'))
            .values('period')
            .annotate(total=Sum('total_amount'), order_count=Count('id', distinct=True))
            .order_by('-period')[:14]  # เอา 14 วันล่าสุด
        )
        chart_label = 'สถิติยอดขายรายวัน (14 วันล่าสุด)'

    # แปลงเป็น List เพื่อนำไปเพิ่ม "จำนวนกล่อง" (item_qty)
    chart_data = list(chart_data_qs)

    # =========================================================
    # คีย์เวิร์ดที่ไม่นับรวมเป็น "กล่อง" (เหมือนกับแอป Stocks)
    # =========================================================
    exclude_keywords = ["topping", "ท็อปปิ้ง", "กับข้าว", "พิเศษ", "เครื่องดื่ม", "เพิ่มเติม"]
    
    # สร้างเงื่อนไข Q เพื่อตรวจสอบว่าชื่อสินค้า หรือ ชื่อหมวดหมู่ มีคำเหล่านี้หรือไม่
    exclude_q = Q()
    for kw in exclude_keywords:
        exclude_q |= Q(product__name__icontains=kw) | Q(product__category__name__icontains=kw)

    # วนลูปเพื่อหาจำนวนชิ้น/กล่อง ที่ขายได้ในแต่ละช่วงเวลา
    for row in chart_data:
        period_val = row['period']
        
        # กรอง Order เฉพาะในรอบเวลานั้นๆ
        if filter_type == 'year':
            period_orders = orders_qs.filter(created_at__year=period_val.year)
        elif filter_type == 'month':
            period_orders = orders_qs.filter(created_at__year=period_val.year, created_at__month=period_val.month)
        else:
            # กรณีเป็นรายวัน
            if hasattr(period_val, 'date'):
                period_orders = orders_qs.filter(created_at__date=period_val.date())
            else:
                period_orders = orders_qs.filter(created_at__date=period_val)
        
        # คำนวณผลรวมจำนวน Quantity จาก OrderItem ของบิลเหล่านั้น 
        # โดย .exclude(exclude_q) จะเตะรายการที่มีคำว่า Topping, เครื่องดื่ม, ฯลฯ ออกไปไม่ให้เอามารวม
        qty_sum = OrderItem.objects.filter(order__in=period_orders).exclude(exclude_q).aggregate(total_qty=Sum('quantity'))['total_qty']
        
        row['item_qty'] = qty_sum or 0

    # เรียงข้อมูลกลับให้น้อยไปมากเพื่อแสดงกราฟซ้ายไปขวา
    chart_data = sorted(chart_data, key=lambda x: x['period'])

    # 6. ดึงรายชื่อผู้ใช้ทั้งหมด
    all_users = User.objects.filter(is_active=True)

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