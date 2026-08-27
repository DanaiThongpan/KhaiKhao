import traceback
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth.decorators import login_required

from .models import Expense
from .google_calendar import create_expense_event, update_expense_event, delete_expense_event

@login_required
def expense_home(request):

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        amount = request.POST.get("amount", "").strip()
        expense_date = request.POST.get("expense_date", "").strip()
        category = request.POST.get("category", "").strip()
        description = request.POST.get("description", "").strip()
        
        is_paid_str = request.POST.get("is_paid", "True")
        is_paid = (is_paid_str == "True")

        if not name or not amount or not expense_date or not category:
            messages.error(request, "กรุณากรอกข้อมูลที่จำเป็นให้ครบถ้วน")
            return redirect("expenses:home")

        try:
            amount_value = float(amount)
            if amount_value <= 0: raise ValueError
        except ValueError:
            messages.error(request, "จำนวนเงินไม่ถูกต้อง")
            return redirect("expenses:home")

        try:
            expense_date_obj = datetime.strptime(expense_date, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "รูปแบบวันที่ไม่ถูกต้อง")
            return redirect("expenses:home")

        try:
            expense = Expense.objects.create(
                name=name,
                amount=amount_value,
                expense_date=expense_date_obj,
                category=category,
                description=description,
                is_paid=is_paid,
                created_by=request.user
            )
        except Exception as e:
            messages.error(request, f"บันทึกรายจ่ายลงระบบไม่สำเร็จ: {e}")
            return redirect("expenses:home")

        try:
            created_event = create_expense_event(expense)
            event_id = created_event.get("id")

            if event_id:
                expense.google_event_id = event_id
                expense.save(update_fields=["google_event_id"])

            messages.success(request, "บันทึกรายจ่ายและส่งเข้าปฏิทินเรียบร้อยแล้ว!")

        except Exception as e:
            print("=" * 70)
            print("GOOGLE CALENDAR ERROR")
            print("=" * 70)
            traceback.print_exc()
            print("=" * 70)
            messages.warning(request, "บันทึกรายจ่ายลงระบบแล้ว แต่ส่งเข้าปฏิทินไม่สำเร็จ")

        return redirect("expenses:home")

    # ====================================================
    # GET Request 
    # ====================================================
    expenses = Expense.objects.filter(created_by=request.user).order_by("-expense_date", "-id")
    today = timezone.now().date()

    # ดึงบิลค้างจ่ายและคำนวณวันคงเหลือ
    upcoming_limit = today + timedelta(days=3)
    upcoming_bills_qs = expenses.filter(
        is_paid=False, 
        expense_date__lte=upcoming_limit
    ).order_by('expense_date')

    upcoming_bills = list(upcoming_bills_qs)
    for bill in upcoming_bills:
        bill.days_left = (bill.expense_date - today).days
        bill.overdue_days = abs(bill.days_left)

    # ตัวกรองข้อมูล 
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        expenses = expenses.filter(expense_date__gte=start_of_week)
    elif filter_type == 'this_month':
        expenses = expenses.filter(expense_date__year=today.year, expense_date__month=today.month)

    total_expense = expenses.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        "expenses": expenses,
        "categories": Expense.CATEGORY_CHOICES,
        "total_expense": total_expense,
        "google_connected": True,
        "upcoming_bills": upcoming_bills,
        "today": today,
    }

    return render(request, "Expenses/expense.html", context)


@login_required
def expense_edit(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, created_by=request.user)
    if request.method == "POST":
        expense.name = request.POST.get('name')
        expense.amount = float(request.POST.get('amount'))
        expense.expense_date = request.POST.get('expense_date')
        expense.category = request.POST.get('category')
        expense.description = request.POST.get('description')

        expense.save()
        expense.refresh_from_db()

        if expense.google_event_id:
            update_expense_event(expense)

        messages.success(request, f"แก้ไขรายการ '{expense.name}' เรียบร้อยแล้ว!")
        return redirect('expenses:home')

    return render(request, 'Expenses/expense_edit.html', {
        'expense': expense,
        'categories': Expense.CATEGORY_CHOICES,
    })


@login_required
def expense_delete(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, created_by=request.user)
    name = expense.name
    event_id_to_delete = expense.google_event_id
    expense.delete()

    if event_id_to_delete:
        delete_expense_event(event_id_to_delete)

    messages.success(request, f"ลบรายการ '{name}' เรียบร้อยแล้ว!")
    return redirect('expenses:home')


@login_required
def expense_toggle_status(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, created_by=request.user)
    expense.is_paid = not expense.is_paid
    expense.save()
    
    status_text = "จ่ายแล้ว" if expense.is_paid else "ยังไม่จ่าย"
    messages.success(request, f"เปลี่ยนสถานะ '{expense.name}' เป็น '{status_text}' เรียบร้อย!")
    return redirect('expenses:home')