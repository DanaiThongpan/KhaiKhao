from django.contrib import admin
from .models import TaxRecord

@admin.register(TaxRecord)
class TaxRecordAdmin(admin.ModelAdmin):
    # กำหนดคอลัมน์ที่จะให้แสดงในตารางหน้า Admin
    list_display = ['tax_year', 'user', 'total_income', 'net_income', 'tax_to_pay', 'created_at']
    
    # เพิ่มแถบตัวกรองด้านขวามือ (กรองตามปีภาษี และผู้ใช้งาน)
    list_filter = ['tax_year', 'user']
    
    # เพิ่มช่องค้นหา (ค้นหาจากชื่อผู้ใช้งาน)
    search_fields = ['user__username']
    
    # ล็อคไม่ให้แก้ไขวันที่สร้างย้อนหลัง
    readonly_fields = ['created_at']
    
    # จัดเรียงข้อมูลให้รายการล่าสุดขึ้นมาก่อน
    ordering = ['-tax_year', '-created_at']

    # ฟังก์ชันช่วยบันทึกข้อมูล (กรณีสร้างผ่านหน้า Admin ให้ผูกกับ User อัตโนมัติถ้าลืมเลือก)
    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.user:
            obj.user = request.user
        super().save_model(request, obj, form, change)