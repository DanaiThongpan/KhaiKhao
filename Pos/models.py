from django.db import models
from django.conf import settings
from Products.models import Product

class Order(models.Model):
    receipt_number = models.CharField(max_length=20, unique=True, verbose_name="เลขที่บิล")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ยอดรวม")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="พนักงาน")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่ขาย")

    class Meta:
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาขาย")
    quantity = models.IntegerField(verbose_name="จำนวน")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="รวม")