# ============================================================
# Expenses/views.py
# ============================================================
import traceback
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib import messages

from .models import Expense
# นำเข้าฟังก์ชันจาก google_calendar.py
# (สมมติว่าไฟล์ google_calendar.py อยู่ในโฟลเดอร์เดียวกับ views.py)
# from .google_calendar import create_expense_event
# แก้ไขบรรทัด import google_calendar ให้มี 3 ตัวนี้
from .google_calendar import create_expense_event, update_expense_event, delete_expense_event

def expense_home(request):

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        amount = request.POST.get("amount", "").strip()
        expense_date = request.POST.get("expense_date", "").strip()
        category = request.POST.get("category", "").strip()
        description = request.POST.get("description", "").strip()

        # Validation เบื้องต้น
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

        # บันทึกลง Database
        try:
            user = request.user if request.user.is_authenticated else None
            expense = Expense.objects.create(
                name=name,
                amount=amount_value,
                expense_date=expense_date_obj,
                category=category,
                description=description,
                created_by=user
            )
        except Exception as e:
            messages.error(request, f"บันทึกรายจ่ายลงระบบไม่สำเร็จ: {e}")
            return redirect("expenses:home")

        # ====================================================
        # ส่งเข้า Google Calendar ผ่าน Bot
        # ====================================================
        try:
            # เรียกใช้ฟังก์ชันที่เราเขียนแยกไว้
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
            messages.warning(
                request,
                "บันทึกรายจ่ายลงระบบแล้ว แต่ส่งเข้าปฏิทินไม่สำเร็จ (ดู log ใน Terminal)"
            )

        return redirect("expenses:home")

    # GET Request
    expenses = Expense.objects.all().order_by("-expense_date", "-id")
    categories = Expense.CATEGORY_CHOICES
    total_expense = sum(expense.amount for expense in expenses)

    context = {
        "expenses": expenses,
        "categories": categories,
        "total_expense": total_expense,
        "google_connected": True,
    }

    return render(request, "Expenses/expense.html", context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Expense

# (โค้ดเก่าที่มีอยู่แล้ว เช่น expense_home ปล่อยไว้เหมือนเดิมครับ)

def expense_edit(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)

    if request.method == "POST":
        expense.name = request.POST.get('name')
        expense.amount = float(request.POST.get('amount'))
        expense.expense_date = request.POST.get('expense_date')
        expense.category = request.POST.get('category')
        expense.description = request.POST.get('description')

        expense.save()

        # === เพิ่มบรรทัดนี้ 1 บรรทัดครับ ===
        # เพื่อแปลงวันที่แบบข้อความ ให้กลายเป็นวันที่แบบ Date Object
        expense.refresh_from_db()
        # ============================

        if expense.google_event_id:
            update_expense_event(expense)

        messages.success(request, f"แก้ไขรายการ '{expense.name}' เรียบร้อยแล้ว!")
        return redirect('expenses:home')

    context = {
        'expense': expense,
        'categories': Expense.CATEGORY_CHOICES,
    }
    return render(request, 'Expenses/expense_edit.html', context)

def expense_delete(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    name = expense.name

    # ----- เพิ่ม 1 บรรทัดนี้: เก็บ ID ปฏิทินไว้ก่อนที่ข้อมูลในเว็บจะถูกลบ -----
    event_id_to_delete = expense.google_event_id

    expense.delete()

    # ----- เพิ่มส่วนนี้: สั่งลบใน Google Calendar -----
    if event_id_to_delete:
        delete_expense_event(event_id_to_delete)
    # --------------------------------------------

    messages.success(request, f"ลบรายการ '{name}' เรียบร้อยแล้ว!")
    return redirect('expenses:home')