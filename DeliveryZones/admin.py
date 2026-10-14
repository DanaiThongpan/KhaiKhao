from django.contrib import admin
from .models import DeliveryZone

@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'fee', 'color', 'created_by', 'is_active', 'created_at')
    list_filter = ('created_by', 'is_active')
    search_fields = ('name',)
