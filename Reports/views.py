from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from Pos.models import Order

@login_required
def reports_home(request):
    # กรองเฉพาะบิลของ User ที่กำลังล็อกอินอยู่
    user_orders = Order.objects.filter(created_by=request.user)

    # รับค่าตัวกรองสำหรับกราฟ (ค่าเริ่มต้นเป็นรายวัน)
    filter_type = request.GET.get('filter', 'day')

    # ข้อมูลสำหรับแสดงในกราฟตามปุ่มที่กด
    if filter_type == 'year':
        chart_data = user_orders.annotate(period=TruncYear('created_at')).values('period').annotate(total=Sum('total_amount')).order_by('period')
        chart_label = "กราฟแสดงยอดขายรายปี"
    elif filter_type == 'month':
        chart_data = user_orders.annotate(period=TruncMonth('created_at')).values('period').annotate(total=Sum('total_amount')).order_by('period')[:12]
        chart_label = "กราฟแสดงยอดขายรายเดือน (12 เดือนล่าสุด)"
    else:
        chart_data = user_orders.annotate(period=TruncDay('created_at')).values('period').annotate(total=Sum('total_amount')).order_by('period')[:15]
        chart_label = "กราฟแสดงยอดขายรายวัน (15 วันล่าสุด)"

    # ข้อมูลสำหรับตารางสรุปทั้ง 4 แบบ
    daily_sales = user_orders.annotate(period=TruncDay('created_at')).values('period').annotate(total=Sum('total_amount')).order_by('-period')[:10]
    weekly_sales = user_orders.annotate(period=TruncWeek('created_at')).values('period').annotate(total=Sum('total_amount')).order_by('-period')[:8]
    monthly_sales = user_orders.annotate(period=TruncMonth('created_at')).values('period').annotate(total=Sum('total_amount')).order_by('-period')[:12]
    yearly_sales = user_orders.annotate(period=TruncYear('created_at')).values('period').annotate(total=Sum('total_amount')).order_by('-period')[:5]

    grand_total = user_orders.aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        "chart_data": chart_data,
        "filter_type": filter_type,
        "chart_label": chart_label,
        "daily_sales": daily_sales,
        "weekly_sales": weekly_sales,
        "monthly_sales": monthly_sales,
        "yearly_sales": yearly_sales,
        "grand_total": grand_total,
    }

    return render(request, "Reports/home.html", context)