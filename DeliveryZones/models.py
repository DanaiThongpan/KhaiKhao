from django.db import models
from django.conf import settings

class DeliveryZone(models.Model):
    name = models.CharField(max_length=255, verbose_name="ชื่อโซนจัดส่ง")
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ค่าจัดส่ง (บาท)")
    color = models.CharField(max_length=50, default="#3b82f6", verbose_name="สีพื้นที่ (Hex Code)")
    polygon_data = models.JSONField(verbose_name="ข้อมูลพิกัด (Polygon)", help_text="เก็บข้อมูล GeoJSON หรืออาเรย์พิกัด")
    is_active = models.BooleanField(default=True, verbose_name="เปิดใช้งาน")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="ร้านค้าผู้สร้าง/เจ้าของ",
        related_name="delivery_zones"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        owner_name = f" [{self.created_by.username}]" if self.created_by else ""
        return f"{self.name}{owner_name} - ฿{self.fee}"

    class Meta:
        verbose_name = "สโคปพื้นที่จัดส่ง"
        verbose_name_plural = "สโคปพื้นที่จัดส่ง"
