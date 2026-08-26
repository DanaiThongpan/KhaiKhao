from django.contrib import admin
from .models import Order, OrderItem

# =====================================================
# ตั้งค่าให้แสดงรายการสินค้า (OrderItem) ซ้อนอยู่ในหน้าของบิล (Order)
# =====================================================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0  # ไม่ต้องแสดงช่องว่างๆ เผื่อไว้
    readonly_fields = ['subtotal'] # ล็อคช่องยอดรวมไว้ไม่ให้แก้ ป้องกันคำนวณพลาด
    
    # กำหนดคอลัมน์ที่จะแสดงในตารางย่อย
    fields = ['product', 'price', 'quantity', 'subtotal']

# =====================================================
# ตั้งค่าหน้าแสดงผลหลักของบิล (Order)
# =====================================================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # คอลัมน์ที่จะแสดงในหน้ารวมบิล
    list_display = ['receipt_number', 'total_amount', 'created_by', 'created_at']
    
    # เพิ่มกล่องค้นหา (ค้นหาด้วยเลขที่บิล)
    search_fields = ['receipt_number']
    
    # เพิ่มตัวกรองด้านขวามือ (กรองตามวันที่ หรือ พนักงานขาย)
    list_filter = ['created_at', 'created_by']
    
    # แสดงเมนูแยกตามเดือน/ปี ไว้ด้านบนสุด
    date_hierarchy = 'created_at'
    
    # ล็อคฟิลด์ที่ระบบสร้างอัตโนมัติไม่ให้เผลอไปแก้
    readonly_fields = ['receipt_number', 'total_amount', 'created_at']
    
    # นำรายการสินค้า (Inline) มาต่อท้ายบิล
    inlines = [OrderItemInline]

# หมายเหตุ: หากต้องการให้ Admin แก้ไขฟิลด์ที่ถูก Lock ไว้ได้ ให้เอาออกจาก readonly_fields ครับ