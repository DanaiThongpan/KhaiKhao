from django.db import models
from django.conf import settings  # เปลี่ยนมาใช้บรรทัดนี้แทน
from django.db import models
from django.contrib.auth.models import User

class Expense(models.Model):

    # =====================================================
    # หมวดหมู่รายจ่าย
    # =====================================================

    CATEGORY_CHOICES = [
        ("ingredient", "วัตถุดิบ"),
        ("electricity", "ค่าไฟ"),
        ("water", "ค่าน้ำ"),
        ("rent", "ค่าเช่า"),
        ("transport", "ค่าเดินทาง"),
        ("equipment", "อุปกรณ์"),
        ("salary", "เงินเดือน / ค่าแรง"),
        ("maintenance", "ค่าซ่อมบำรุง"),
        ("other", "อื่น ๆ"),
    ]

    # =====================================================
    # ข้อมูลรายจ่าย
    # =====================================================

    name = models.CharField(
        max_length=255,
        verbose_name="รายการรายจ่าย"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="จำนวนเงิน"
    )

    expense_date = models.DateField(
        verbose_name="วันที่รายจ่าย"
    )

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        verbose_name="หมวดหมู่"
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="รายละเอียด"
    )

    # =====================================================
    # ผู้บันทึก (ให้ Admin หรือคนสร้างลบได้)
    # =====================================================

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # <--- เปลี่ยนตรงนี้
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="ผู้บันทึก"
    )
    # =====================================================
    # Google Calendar
    # =====================================================

    google_event_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Google Calendar Event ID"
    )

    # =====================================================
    # วันที่ระบบ
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="สร้างเมื่อ"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="แก้ไขล่าสุด"
    )

    is_paid = models.BooleanField(default=True, verbose_name="จ่ายแล้ว")

    # =====================================================
    # Meta
    # =====================================================

    class Meta:

        ordering = [
            "-expense_date",
            "-created_at",
        ]

        verbose_name = "รายจ่าย"

        verbose_name_plural = "รายจ่าย"

    # =====================================================
    # String
    # =====================================================

    def __str__(self):

        return f"{self.name} - ฿{self.amount:,.2f}"