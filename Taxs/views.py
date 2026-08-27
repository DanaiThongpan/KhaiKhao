from datetime import datetime
from decimal import Decimal # 1. นำเข้า Decimal มาใช้งาน
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .models import TaxRecord
from Pos.models import Order

def calculate_thai_personal_tax(net_income):
    """
    คำนวณภาษีเงินได้บุคคลธรรมดาตามขั้นบันไดสรรพากรไทย (0% - 35%)
    """
    # แปลงเป็น float ชั่วคราวเพื่อให้คำนวณเปรียบเทียบขั้นบันไดได้ง่าย
    net = float(net_income)
    tax = 0
    if net <= 150000:
        tax = 0
    elif net <= 300000:
        tax = (net - 150000) * 0.05
    elif net <= 500000:
        tax = 7500 + (net - 300000) * 0.10
    elif net <= 750000:
        tax = 27500 + (net - 500000) * 0.15
    elif net <= 1000000:
        tax = 65000 + (net - 750000) * 0.20
    elif net <= 2000000:
        tax = 115000 + (net - 1000000) * 0.25
    elif net <= 5000000:
        tax = 365000 + (net - 2000000) * 0.30
    else:
        tax = 1265000 + (net - 5000000) * 0.35
    return Decimal(str(max(0, tax)))

@login_required
def tax_home_view(request):
    current_year = datetime.now().year
    
    try:
        realtime_orders = Order.objects.filter(
            created_by=request.user, 
            created_at__year=current_year
        )
        realtime_sales = realtime_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    except:
        realtime_sales = Decimal('0')

    # 2. ใช้ Decimal ในการคำนวณค่าใช้จ่ายและลดหย่อนเพื่อไม่ให้ Type ชนกัน
    estimated_expense = realtime_sales * Decimal('0.60')
    personal_deduction = Decimal('60000')
    total_deduction_default = estimated_expense + personal_deduction
    
    realtime_net_income = max(Decimal('0'), realtime_sales - total_deduction_default)
    realtime_tax = calculate_thai_personal_tax(realtime_net_income)

    # 3. คำนวณเพดานยอดขายก่อนเริ่มเสียภาษี
    tax_free_sales_limit = (Decimal('150000') + personal_deduction) / Decimal('0.40')
    sales_until_tax = max(Decimal('0'), tax_free_sales_limit - realtime_sales)

    # ระบบจำลอง (Simulator)
    sim_result = None
    if request.method == "POST" and "simulate" in request.POST:
        try:
            sim_income = Decimal(request.POST.get("sim_income", "0"))
            sim_deduction = Decimal(request.POST.get("sim_deduction", "0"))
            sim_net = max(Decimal('0'), sim_income - sim_deduction)
            sim_tax = calculate_thai_personal_tax(sim_net)
            
            sim_result = {
                'income': sim_income,
                'deduction': sim_deduction,
                'net': sim_net,
                'tax': sim_tax
            }
        except (ValueError, decimal.InvalidOperation):
            messages.error(request, "กรุณากรอกตัวเลขจำลองให้ถูกต้อง")

    # บันทึกผลลงประวัติ
    if request.method == "POST" and "save_record" in request.POST:
        try:
            tax_year = int(request.POST.get("tax_year", current_year))
            total_income = Decimal(request.POST.get("total_income", str(realtime_sales)))
            deduction = Decimal(request.POST.get("deduction", str(total_deduction_default)))
            net_income = max(Decimal('0'), total_income - deduction)
            tax_to_pay = calculate_thai_personal_tax(net_income)

            TaxRecord.objects.create(
                user=request.user,
                tax_year=tax_year,
                total_income=total_income,
                total_expenses_deduction=deduction,
                net_income=net_income,
                tax_to_pay=tax_to_pay
            )
            messages.success(request, "บันทึกประวัติภาษีสำเร็จ!")
            return redirect('tax:home')
        except (ValueError, decimal.InvalidOperation):
            messages.error(request, "ข้อมูลการบันทึกไม่ถูกต้อง")

    history = TaxRecord.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'current_year': current_year,
        'realtime_sales': realtime_sales,
        'realtime_net_income': realtime_net_income,
        'realtime_tax': realtime_tax,
        'sales_until_tax': sales_until_tax,
        'total_deduction_default': total_deduction_default,
        'sim_result': sim_result,
        'history': history,
    }
    return render(request, 'Taxs/tax_home.html', context)