from datetime import datetime, timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear

from Pos.models import Order, OrderItem
from Accounts.models import User

@login_required
def reports_home(request):
    # 1. รับค่าตัวกรองจาก Request
    selected_user_id = request.GET.get('user', '')
    filter_type = request.GET.get('filter', 'day') 
    selected_month = request.GET.get('month_picker', '') # รูปแบบ: YYYY-MM

    # 2. ตั้งค่า QuerySet เริ่มต้น
    orders_qs = Order.objects.all()

    # กรองร้าน/ผู้ใช้งาน
    if selected_user_id:
        orders_qs = orders_qs.filter(created_by_id=selected_user_id)

    # กรองเฉพาะเดือนที่เลือก
    if selected_month:
        try:
            year, month = map(int, selected_month.split('-'))
            orders_qs = orders_qs.filter(created_at__year=year, created_at__month=month)
        except ValueError:
            pass

    # 3. ยอดขายสะสมรวมทั้งหมด (Grand Total)
    grand_total = orders_qs.aggregate(total=Sum('total_amount'))['total'] or 0

    # 4. ข้อมูลตารางสรุปแต่ละประเภท
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

    # 5. ข้อมูลสำหรับกราฟ
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
    elif filter_type == 'week': 
        chart_data_qs = (
            orders_qs.annotate(period=TruncWeek('created_at'))
            .values('period')
            .annotate(total=Sum('total_amount'), order_count=Count('id', distinct=True))
            .order_by('-period')
        )
        chart_label = 'สถิติยอดขายรายสัปดาห์'
    else:  
        chart_data_qs = (
            orders_qs.annotate(period=TruncDay('created_at'))
            .values('period')
            .annotate(total=Sum('total_amount'), order_count=Count('id', distinct=True))
            .order_by('-period')
        )
        chart_label = 'สถิติยอดขายรายวัน'

    if selected_month:
        chart_label += f" (ประจำเดือน {datetime.strptime(selected_month, '%Y-%m').strftime('%B %Y')})"

    chart_data = list(chart_data_qs)

    # คีย์เวิร์ดที่ไม่นับรวมเป็น "กล่อง"
    exclude_keywords = [
        "topping", "ท็อปปิ้ง", "กับข้าว", "พิเศษ", "เครื่องดื่ม", 
        "โปรโมชั่น", "เพิ่มเติม", "ของทานเล่น", "ค่าจัดส่ง", "โปรโมชั่นส่วนลด"
    ]
    
    exclude_q = Q()
    for kw in exclude_keywords:
        exclude_q |= Q(product__name__icontains=kw) | Q(product__category__name__icontains=kw)

    for row in chart_data:
        period_val = row['period']
        
        if filter_type == 'year':
            period_orders = orders_qs.filter(created_at__year=period_val.year)
        elif filter_type == 'month':
            period_orders = orders_qs.filter(created_at__year=period_val.year, created_at__month=period_val.month)
        elif filter_type == 'week':
            start_date = period_val.date() if hasattr(period_val, 'date') else period_val
            end_date = start_date + timedelta(days=6)
            period_orders = orders_qs.filter(created_at__date__range=[start_date, end_date])
        else:
            if hasattr(period_val, 'date'):
                period_orders = orders_qs.filter(created_at__date=period_val.date())
            else:
                period_orders = orders_qs.filter(created_at__date=period_val)
        
        qty_sum = OrderItem.objects.filter(order__in=period_orders).exclude(exclude_q).aggregate(total_qty=Sum('quantity'))['total_qty']
        
        row['item_qty'] = qty_sum or 0

    chart_data = sorted(chart_data, key=lambda x: x['period'])

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
        'selected_month': selected_month, 
        'all_users': all_users,
        'selected_user_id': selected_user_id,
    }

    return render(request, 'Reports/home.html', context)