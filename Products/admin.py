from django.contrib import admin
from .models import ProductCategory, Product

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_by']
    # ล็อคช่องผู้สร้างไว้ ไม่ให้แก้เอง
    readonly_fields = ['created_by'] 

    def save_model(self, request, obj, form, change):
        # ถ้ารายการนี้เพิ่งถูกสร้างใหม่ และยังไม่มีผู้สร้าง
        if not getattr(obj, 'created_by', None):
            obj.created_by = request.user # ยัดชื่อคนที่กำลังล็อกอินเข้าไป
        super().save_model(request, obj, form, change)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'selling_price', 'created_by']
    # ล็อคช่องผู้สร้างไว้ ไม่ให้แก้เอง
    readonly_fields = ['created_by']

    def save_model(self, request, obj, form, change):
        # ถ้ารายการนี้เพิ่งถูกสร้างใหม่ และยังไม่มีผู้สร้าง
        if not getattr(obj, 'created_by', None):
            obj.created_by = request.user # ยัดชื่อคนที่กำลังล็อกอินเข้าไป
        super().save_model(request, obj, form, change)