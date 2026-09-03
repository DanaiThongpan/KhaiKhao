from django.conf import settings
from django.db import models
from Pos.models import Order

# ลบบรรทัด: from .models import RiderProfile, DeliveryTask ออกไป


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


class DeliveryTask(models.Model):
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name='delivery_info'
    )
    rider = models.ForeignKey(
        'RiderProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
    )

    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    last_location_update = models.DateTimeField(blank=True, null=True)

    dormitory_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, default='PENDING')

    def __str__(self):
        return f'Task for Order: {self.order.receipt_number}'