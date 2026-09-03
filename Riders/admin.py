from django.contrib import admin
from .models import RiderProfile, DeliveryTask

@admin.register(DeliveryTask)
class DeliveryTaskAdmin(admin.ModelAdmin):
    
    list_display = (
        'order', 
        'rider', 
        'status', 
        'dormitory_name', 
        'latitude', 
        'longitude', 
        'last_location_update'
    )
    
    list_filter = (
        'status', 
        'rider',
    )
    
    search_fields = (
        'order__receipt_number', 
        'rider__name', 
        'dormitory_name'
    )
    
    readonly_fields = (
        'latitude', 
        'longitude', 
        'last_location_update'
    )
    
    list_per_page = 20
    
    ordering = (
        '-last_location_update',
    )