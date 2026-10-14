from django.conf import settings
from django.db import models

from Products.models import Product


class Order(models.Model):
    receipt_number = models.CharField(
        max_length=20, unique=True, verbose_name="เลขที่บิล"
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="ยอดรวม"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="พนักงาน",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่ขาย")
    payment_status = models.CharField(
        max_length=20, default="PENDING"
    )  # สถานะจ่ายเงิน PENDING / PAID
    transaction_ref = models.CharField(
        max_length=50, null=True, blank=True
    )  # เก็บเลข Ref ของสลิปกันซ้ำ

    class Meta:
        ordering = ["-created_at"]

    @property
    def delivery_fee(self):
        """คำนวณค่าจัดส่งของออเดอร์ (ดึงจาก OrderItem ค่าจัดส่ง)"""
        delivery_item = self.items.filter(
            models.Q(product__code="FEE-DELIVERY") | models.Q(product__name="ค่าจัดส่ง")
        ).first()
        if delivery_item:
            return delivery_item.price
        return 0

    @property
    def is_free_delivery(self):
        """ตรวจสอบว่าออเดอร์นี้เป็นบิลที่ได้รับสิทธิ์ส่งฟรีเนื่องจากจัดส่งล่าช้าหรือไม่"""
        return self.items.filter(
            models.Q(product__code="FREE-DELIVERY-DELAY") |
            models.Q(product__name__icontains="ส่งฟรี")
        ).exists()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาขาย")
    quantity = models.IntegerField(verbose_name="จำนวน")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="รวม")

    @property
    def is_subitem(self):
        """ตรวจสอบว่าเป็น Topping / ตัวเลือกย่อยหรือไม่ (สำหรับย่อหน้า ↳ ในสลิป)"""
        prod_name = (self.product.name or "").lower()
        cat_name = (self.product.category.name if self.product.category else "").lower()

        # สินค้าหลักที่ไม่ใช่ท็อปปิ้ง
        if any(w in prod_name or w in cat_name for w in ["กับข้าว", "น้ำเปล่า", "ข้าวเปล่า", "ข้าวปล่าว"]):
            return False

        # คำที่ระบุว่าเป็นตัวเลือกย่อย หรือ Topping
        keywords = ["topping", "ท็อปปิ้ง", "พิเศษ", "เพิ่มเติม", "ไข่ดาว", "ไข่เจียว", "ไข่เยี่ยวม้า", "เพิ่มข้าว"]
        return any(kw in prod_name or kw in cat_name for kw in keywords)

