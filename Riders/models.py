from django.conf import settings
from django.db import models
from Pos.models import Order

# =========================================================
# Master Data: ข้อมูลหอพัก
# =========================================================
# =========================================================
# Master Data: ข้อมูลหอพัก
# =========================================================
class Dormitory(models.Model):
    ZONE_CHOICES = (
        ('โซนอนามัย 10', 'โซนอนามัย 10'),
        ('โซนหน้ามอ', 'โซนหน้ามอ'),
        ('โซนประตู 3', 'โซนประตู 3'),
        ('โซนร้านหวานเย็น', 'โซนร้านหวานเย็น'),
        ('โซนบุญเยี่ยมหรือนอกพื้นที่', 'โซนบุญเยี่ยมหรือนอกพื้นที่'),
    )

    name = models.CharField(max_length=255, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # 🌟 เพิ่มฟิลด์การแบ่งโซน
    zone = models.CharField(max_length=50, default='โซนหน้ามอ')
    # 🌟 เพิ่มฟิลด์สำหรับเก็บสีหมุด (ค่าเริ่มต้นคือสีฟ้า)
    color = models.CharField(max_length=30, default='blue')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.zone}] {self.name}"
# =========================================================
# ข้อมูลโปรไฟล์ไรเดอร์
# =========================================================
class RiderProfile(models.Model):
    RIDER_TYPES = (
        ('INTERNAL', 'ไรเดอร์ของร้านเอง'),
        ('GRAB', 'GrabFood'),
        ('LINEMAN', 'LINE MAN'),
        ('SHOPEE', 'ShopeeFood'),
        ('FOODPANDA', 'Foodpanda'),
    )

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    rider_type = models.CharField(
        max_length=20, choices=RIDER_TYPES, default='INTERNAL'
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )

    def __str__(self):
        return f'{self.name} ({self.get_rider_type_display()})'

# =========================================================
# งานจัดส่ง
# =========================================================
class DeliveryTask(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery_info')
    rider = models.ForeignKey('RiderProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    last_location_update = models.DateTimeField(blank=True, null=True)
    
    destination = models.ForeignKey('Dormitory', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING')

    # 🌟 ฟิลด์ที่เพิ่มใหม่ เพื่อเก็บประวัติการจัดส่ง
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="เวลาเริ่มจัดส่ง")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="เวลาส่งสำเร็จ")
    duration_minutes = models.IntegerField(null=True, blank=True, verbose_name="ใช้เวลาไป (นาที)")

    def __str__(self):
        return f"Task for Order: {self.order.receipt_number}"