from django.db import models
from django.conf import settings  # <--- เพิ่มบรรทัดนี้ เพื่อดึงระบบ User ของ Django มาใช้

# Create your models here.

class ProductCategory(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="ชื่อหมวดหมู่"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="เปิดใช้งาน"
    )

    # ==========================================
    # [เพิ่มใหม่] เก็บข้อมูลผู้สร้าง
    # ==========================================
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # ถ้า User ถูกลบ หมวดหมู่จะไม่ถูกลบตาม แต่จะกลายเป็นค่าว่าง
        null=True,
        blank=True,
        verbose_name="ผู้สร้าง",
        related_name="created_categories"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "product_categories"
        verbose_name = "หมวดหมู่สินค้า"
        verbose_name_plural = "หมวดหมู่สินค้า"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):

    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="หมวดหมู่"
    )

    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="รหัสสินค้า"
    )

    name = models.CharField(
        max_length=200,
        verbose_name="ชื่อสินค้า"
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="รายละเอียด"
    )

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="ราคาทุน"
    )

    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="ราคาขาย"
    )

    stock_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="จำนวนคงเหลือ"
    )

    min_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="จำนวนขั้นต่ำ"
    )

    unit = models.CharField(
        max_length=50,
        default="ชิ้น",
        verbose_name="หน่วย"
    )

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
        verbose_name="รูปสินค้า"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="เปิดขาย"
    )

    # ==========================================
    # [เพิ่มใหม่] เก็บข้อมูลผู้สร้าง
    # ==========================================
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="ผู้สร้าง",
        related_name="created_products"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "products"
        verbose_name = "สินค้า"
        verbose_name_plural = "สินค้า"
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.code} - {self.name}"