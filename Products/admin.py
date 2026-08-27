from django.contrib import admin
from .models import ProductCategory, Product

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_by']
    readonly_fields = ['created_by'] 

    # 1. สร้างแถบเมนูด้านขวามือ เพื่อให้กดกรองดูเฉพาะ "ผู้สร้าง" แต่ละคนได้
    list_filter = ['created_by', 'is_active']
    
    # 2. จัดเรียงข้อมูลในตาราง ให้ผู้สร้างคนเดียวกันอยู่ติดกัน (Group by)
    ordering = ['created_by', 'name']

    def save_model(self, request, obj, form, change):
        if not getattr(obj, 'created_by', None):
            obj.created_by = request.user 
        super().save_model(request, obj, form, change)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'selling_price', 'created_by']
    readonly_fields = ['created_by']

    # 1. สร้างแถบเมนูด้านขวามือ เพื่อให้กดกรองดูเฉพาะ "ผู้สร้าง" แต่ละคนได้
    list_filter = ['created_by', 'category']
    
    # 2. จัดเรียงข้อมูลในตาราง ให้ผู้สร้างคนเดียวกันอยู่ติดกัน (Group by)
    ordering = ['created_by', 'category', 'name']

    def save_model(self, request, obj, form, change):
        if not getattr(obj, 'created_by', None):
            obj.created_by = request.user 
        super().save_model(request, obj, form, change)