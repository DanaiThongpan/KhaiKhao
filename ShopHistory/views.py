import calendar
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ShopSession
from Pos.models import Order

@login_required
def history_page(request):
    """ หน้าแสดงตารางประวัติการเปิด-ปิดร้าน พร้อมคำนวณชั่วโมง """
    sessions = ShopSession.objects.filter(user=request.user)
    
    # 🌟 คำนวณระยะเวลา (จำนวนชั่วโมง) ก่อนส่งไป HTML
    for s in sessions:
        if s.close_time and s.open_time:
            diff = s.close_time - s.open_time
            total_seconds = int(diff.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            s.duration_str = f"{hours} ชม. {minutes} นาที"
        else:
            s.duration_str = None

    current_session = sessions.filter(is_open=True).first()
    is_currently_open = current_session is not None

    return render(request, 'ShopHistory/history.html', {
        'sessions': sessions,
        'is_currently_open': is_currently_open,
    })

# ==========================================
# API สำหรับ แก้ไข และ ลบ ประวัติ
# ==========================================
@login_required
def edit_session(request, session_id):
    if request.method == 'POST':
        session = ShopSession.objects.get(id=session_id, user=request.user)
        open_time_str = request.POST.get('open_time')
        close_time_str = request.POST.get('close_time')

        if open_time_str:
            session.open_time = datetime.strptime(open_time_str, '%Y-%m-%dT%H:%M')
            
        if close_time_str:
            session.close_time = datetime.strptime(close_time_str, '%Y-%m-%dT%H:%M')
            session.is_open = False
        else:
            session.close_time = None
            session.is_open = True
            
        session.save()
    return redirect('shop_history:home')

@csrf_exempt
@login_required
def delete_session(request, session_id):
    if request.method == 'POST':
        try:
            session = ShopSession.objects.get(id=session_id, user=request.user)
            session.delete()
            return JsonResponse({"status": "success"})
        except:
            return JsonResponse({"status": "error"})
    return JsonResponse({"status": "invalid"}, status=400)

@csrf_exempt
@login_required
def toggle_shop_status(request):
    """ API สำหรับกดปุ่ม เปิด/ปิด ร้าน """
    if request.method == 'POST':
        # หาเซสชันที่กำลังเปิดอยู่
        current_session = ShopSession.objects.filter(user=request.user, is_open=True).first()
        
        if current_session:
            # ถ้าร้านเปิดอยู่ -> ให้ทำการปิดร้าน
            current_session.is_open = False
            current_session.close_time = timezone.now()
            current_session.save()
            return JsonResponse({"status": "success", "state": "CLOSED", "message": "ปิดร้านเรียบร้อยแล้ว"})
        else:
            # ถ้าร้านปิดอยู่ -> ให้ทำการเปิดร้านใหม่
            ShopSession.objects.create(user=request.user, is_open=True)
            return JsonResponse({"status": "success", "state": "OPEN", "message": "เปิดร้านสำเร็จ! พร้อมรับออเดอร์"})
            
    return JsonResponse({"status": "invalid method"}, status=405)

@login_required
def closure_history_page(request):
    """ หน้าแสดงประวัติการหยุดร้าน (คำนวณจากเวลาปิดรอบก่อนหน้า ถึง เวลาเปิดรอบถัดไป) """
    # ดึงประวัติทั้งหมดของ user นี้ เรียงจากเก่าไปใหม่ เพื่อคำนวณเวลาที่ต่อเนื่องกัน
    sessions = list(ShopSession.objects.filter(user=request.user).order_by('open_time'))
    
    closures = []
    now = timezone.now()

    for i in range(len(sessions)):
        current_session = sessions[i]
        
        # ถ้ารอบนี้มีการกด "ปิดร้าน" ถึงจะเริ่มนับเป็น 1 ช่วงเวลาหยุด
        if current_session.close_time:
            closed_at = current_session.close_time
            
            # เช็กว่ามีรอบเปิดร้านถัดไปหรือไม่
            if i + 1 < len(sessions):
                next_session = sessions[i+1]
                opened_at = next_session.open_time
                status = "กลับมาเปิดแล้ว"
            else:
                # ถ้ายังไม่มีรอบถัดไป แปลว่า "ปัจจุบันกำลังหยุดร้านอยู่"
                opened_at = now
                status = "กำลังหยุดร้าน"
            
            # ป้องกันข้อมูลบั๊ก (ถ้าเปิดก่อนปิด)
            if opened_at >= closed_at:
                diff = opened_at - closed_at
                days = diff.days
                hours, remainder = divmod(diff.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                duration_str = []
                if days > 0: duration_str.append(f"{days} วัน")
                if hours > 0: duration_str.append(f"{hours} ชม.")
                if minutes > 0: duration_str.append(f"{minutes} นาที")
                
                closures.append({
                    'closed_at': closed_at,
                    'opened_at': opened_at if status == "กลับมาเปิดแล้ว" else None, # ถ้ากำลังหยุด ไม่ต้องโชว์เวลาเปิด
                    'duration': " ".join(duration_str) if duration_str else "ไม่ถึง 1 นาที",
                    'status': status
                })
                
    # กลับด้านให้ข้อมูลล่าสุดขึ้นก่อน
    closures.reverse()

    return render(request, 'ShopHistory/closure_history.html', {'closures': closures})

# ... (ฟังก์ชันเดิม history_page, toggle_shop_status, closure_history_page) ...

@login_required
def calendar_dashboard(request):
    """ แดชบอร์ดสรุปปฏิทิน เช็กจากประวัติการขาย พร้อมสรุปยอดขายรายวัน """
    now = timezone.localtime()
    
    # รับค่าเดือนและปีจาก URL
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    
    # คำนวณเดือนก่อนหน้า - ถัดไป
    prev_month = 12 if month == 1 else month - 1
    prev_year = year - 1 if month == 1 else year
    next_month = 1 if month == 12 else month + 1
    next_year = year + 1 if month == 12 else year
        
    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdatescalendar(year, month)
    
    orders = Order.objects.filter(
        created_at__year=year,
        created_at__month=month
    )
    # 🌟 คำนวณยอดขายรายวัน และแยกวันที่ร้านเปิด
    sales_dict = {}
    for order in orders:
        local_date = timezone.localtime(order.created_at).date()
        if local_date not in sales_dict:
            sales_dict[local_date] = 0
        sales_dict[local_date] += order.total_amount
        
    open_dates = set(sales_dict.keys())
    monthly_total_sales = sum(sales_dict.values()) # 🌟 ยอดขายรวมทั้งเดือน
    
    # คำนวณสถิติวันเปิด/ปิด
    total_days_in_month = calendar.monthrange(year, month)[1]
    
    if year == now.year and month == now.month:
        days_passed = now.day
    elif year > now.year or (year == now.year and month > now.month):
        days_passed = 0
    else:
        days_passed = total_days_in_month
        
    open_count = len(open_dates)
    closed_count = max(0, days_passed - open_count)
    open_percent = (open_count / days_passed * 100) if days_passed > 0 else 0
    
    # เตรียมข้อมูลใส่ตารางปฏิทิน
    calendar_data = []
    for week in weeks:
        week_data = []
        for d in week:
            is_current_month = (d.month == month)
            is_future = (d > now.date())
            
            day_sales = 0 # สร้างตัวแปรเก็บยอดขายรายวัน
            
            if not is_current_month:
                status = 'other_month'
            elif is_future:
                status = 'future'
            elif d in open_dates:
                status = 'open'
                day_sales = sales_dict[d] # 🌟 ดึงยอดขายของวันนั้นมาใส่
            else:
                status = 'closed'
                
            week_data.append({
                'day': d.day,
                'status': status,
                'sales': day_sales # 🌟 ส่งยอดขายเข้าไปใน HTML
            })
        calendar_data.append(week_data)
        
    month_names = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
        
    context = {
        'month_name': f"{month_names[month]} {year + 543}",
        'year': year, 'month': month,
        'prev_year': prev_year, 'prev_month': prev_month,
        'next_year': next_year, 'next_month': next_month,
        'calendar_data': calendar_data,
        'open_count': open_count,
        'closed_count': closed_count,
        'open_percent': open_percent,
        'monthly_total_sales': monthly_total_sales, # 🌟 ส่งยอดรวมรายเดือนไปที่เทมเพลต
    }
    return render(request, 'ShopHistory/calendar_dashboard.html', context)