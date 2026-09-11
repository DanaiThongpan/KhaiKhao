# Create your models here.
from django.db import models
from django.conf import settings
from django.utils import timezone

class ShopSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="พนักงาน/ร้านค้า")
    open_time = models.DateTimeField(default=timezone.now, verbose_name="เวลาเปิดร้าน")
    close_time = models.DateTimeField(null=True, blank=True, verbose_name="เวลาปิดร้าน")
    is_open = models.BooleanField(default=True, verbose_name="สถานะ (เปิด/ปิด)")

    class Meta:
        ordering = ['-open_time']

    def __str__(self):
        return f"{self.user.username} | เปิด: {self.open_time.strftime('%d/%m/%Y %H:%M')}"