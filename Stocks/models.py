from django.db import models
from django.conf import settings

class StockItem(models.Model):
    name = models.CharField(max_length=100, verbose_name="ชื่อของใช้/วัตถุดิบ")
    quantity = models.FloatField(default=0, verbose_name="จำนวนคงเหลือ")
    unit = models.CharField(max_length=50, verbose_name="หน่วยนับ (เช่น ใบ, กก., แพ็ค)")
    alert_level = models.FloatField(default=0, verbose_name="แจ้งเตือนเมื่อต่ำกว่า")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"

class StockLog(models.Model):
    ACTION_CHOICES = (
        ('IN', 'นำเข้า (+)' ),
        ('OUT', 'เบิกออก (-)' ),
    )
    
    item = models.ForeignKey(StockItem, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=3, choices=ACTION_CHOICES)
    amount = models.FloatField(verbose_name="จำนวนที่เข้า/ออก")
    note = models.CharField(max_length=200, blank=True, null=True, verbose_name="หมายเหตุ")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item.name} | {self.action} {self.amount}"