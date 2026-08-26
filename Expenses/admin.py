from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "amount",
        "expense_date",
        "category",
        "created_by",  # เพิ่มแสดงผู้บันทึก
        "google_calendar_status",
        "created_at",
    )

    list_filter = (
        "category",
        "expense_date",
        "created_by",  # เพิ่มกรองตามผู้บันทึก
    )

    search_fields = (
        "name",
        "description",
        "google_event_id",
    )

    ordering = (
        "-expense_date",
        "-created_at",
    )

    list_per_page = 25

    readonly_fields = (
        "created_by",  # ป้องกันการเปลี่ยนชื่อคนสร้าง
        "created_at",
        "updated_at",
        "google_event_id",
    )

    fieldsets = (
        (
            "ข้อมูลรายจ่าย",
            {
                "fields": (
                    "name",
                    "amount",
                    "expense_date",
                    "category",
                    "description",
                )
            }
        ),
        (
            "Google Calendar",
            {
                "fields": (
                    "google_event_id",
                )
            }
        ),
        (
            "ข้อมูลระบบ",
            {
                "fields": (
                    "created_by",  # เพิ่มฟิลด์ในส่วนระบบ
                    "created_at",
                    "updated_at",
                )
            }
        ),
    )

    @admin.display(
        description="Google Calendar"
    )
    def google_calendar_status(self, obj):
        if obj.google_event_id:
            return "✓ เชื่อมแล้ว"
        return "✗ ยังไม่เชื่อม"

    # =====================================================
    # จัดการสิทธิ์และผู้สร้าง (Permissions & Save Logic)
    # =====================================================

    def save_model(self, request, obj, form, change):
        # บันทึกชื่อผู้ใช้ที่กำลังล็อกอินใน Admin อัตโนมัติเมื่อสร้างข้อมูลใหม่
        if not obj.pk and request.user.is_authenticated:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        # 1. ถ้าเป็น Admin (Superuser) ให้แก้ไขได้เสมอ
        if request.user.is_superuser:
            return True
        
        # 2. ถ้าผู้ใช้เปิดหน้ารวม (obj เป็น None) ให้แสดงได้
        if obj is None:
            return True
            
        # 3. ถ้าเป็นคนสร้าง (created_by ตรงกับคนที่ล็อกอิน) ให้แก้ไขได้
        if obj.created_by == request.user:
            return True
            
        # 4. นอกนั้นห้ามแก้ไข
        return False

    def has_delete_permission(self, request, obj=None):
        # 1. ถ้าเป็น Admin (Superuser) ให้ลบได้เสมอ
        if request.user.is_superuser:
            return True
            
        # 2. ถ้าผู้ใช้กด action ลบหลายรายการพร้อมกัน (obj เป็น None) อนุญาตให้ผ่านไปเช็กสิทธิ์รายตัว
        if obj is None:
            return True
            
        # 3. ถ้าเป็นคนสร้าง (created_by ตรงกับคนที่ล็อกอิน) ให้ลบได้
        if obj.created_by == request.user:
            return True
            
        # 4. นอกนั้นห้ามลบ
        return False