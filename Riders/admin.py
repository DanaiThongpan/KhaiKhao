from django.contrib import admin
from .models import RiderProfile, DeliveryTask, Dormitory

@admin.register(Dormitory)
class DormitoryAdmin(admin.ModelAdmin):
    # เพิ่ม zone และ color ในหน้าแอดมินด้วย
    list_display = ('name', 'zone', 'color', 'latitude', 'longitude', 'created_at')
    list_filter = ('zone', 'color')
    search_fields = ('name', 'zone')
    
@admin.register(RiderProfile)
class RiderProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'rider_type', 'is_active', 'created_by')
    list_filter = ('rider_type', 'is_active')
    search_fields = ('name', 'phone')

@admin.register(DeliveryTask)
class DeliveryTaskAdmin(admin.ModelAdmin):
    # 🌟 เพิ่มข้อมูลระยะเวลาการจัดส่ง (duration_minutes) ให้โชว์ในตารางด้วย
    list_display = ('order', 'rider', 'status', 'destination', 'duration_minutes', 'started_at', 'completed_at')
    list_filter = ('status', 'rider')
    search_fields = ('order__receipt_number', 'destination__name')
    # ป้องกันการแก้ไขเวลาเอง
    readonly_fields = ('duration_minutes', 'started_at', 'completed_at', 'last_location_update')