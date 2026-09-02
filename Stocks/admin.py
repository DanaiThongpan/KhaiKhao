from django.contrib import admin
from .models import StockItem, StockLog

@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'unit', 'alert_level', 'created_by', 'updated_at')
    list_filter = ('created_by',)
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(StockLog)
class StockLogAdmin(admin.ModelAdmin):
    list_display = ('item', 'action', 'amount', 'note', 'created_by', 'created_at')
    list_filter = ('action', 'created_at', 'created_by')
    search_fields = ('item__name', 'note')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'