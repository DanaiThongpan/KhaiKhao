from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from Products.models import Product, ProductCategory

class Command(BaseCommand):
    help = "Import all products for User P184"

    all_products = {
        # --- เมนูหมูทอด ---
        "เมนูหมูทอด": [
            ("P184-001", "ข้าวหมูทอด", 55),
            ("P184-002", "ข้าวหมูทอดกระเทียม", 55),
            ("P184-003", "ข้าวหมูทอดกระเทียมพริก", 55),
            ("P184-004", "ข้าวยำหมูแซ่บ", 55),
            ("P184-005", "ข้าวหมูทอดราดชีส", 55),
            ("P184-006", "ข้าวหมูทอดราดซอสซาวครีม", 55),
            ("P184-007", "ข้าวหมูทอดราดซอสซาวครีมหัวหอม", 55),
        ],

        # --- เมนูไก่ทอด ---
        "เมนูไก่ทอด": [
            ("P184-008", "ข้าวไก่ทอดกระเทียม", 50),
            ("P184-009", "ข้าวไก่ทอดกระเทียมพริก", 50),
            ("P184-010", "ข้าวยำไก่แซ่บ", 50),
            ("P184-011", "ข้าวไก่ทอดราดชีส", 50),
            ("P184-012", "ข้าวไก่ทอดราดซอสซาวครีม", 50),
            ("P184-013", "ข้าวไก่ทอดราดซอสซาวครีมหัวหอม", 55),
        ],

        # --- เมนูสามชั้นทอด ---
        "เมนูสามชั้นทอด": [
            ("P184-014", "ข้าวสามชั้นทอด", 55),
            ("P184-015", "ข้าวสามชั้นทอดกระเทียม", 55),
            ("P184-016", "ข้าวสามชั้นทอดกระเทียมพริก", 55),
            ("P184-017", "ข้าวยำสามชั้นทอดแซ่บ", 55),
        ],

        # --- Topping ---
        "Topping": [
            ("P184-T01", "ไข่ดาว", 10),
            ("P184-T02", "ไข่เจียว", 10),
        ],

        # --- เครื่องดื่ม ---
        "เครื่องดื่ม": [
            ("P184-D01", "น้ำเปล่า", 10),
        ],

        # --- เพิ่มเติม ---
        "เพิ่มเติม": [
            ("P184-E01", "พิเศษ", 10),
        ],
    }

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            creator = User.objects.get(username="P184")
        except User.DoesNotExist:
            raise CommandError('ไม่พบผู้ใช้งานชื่อ "P184" ในระบบ กรุณาสร้าง User นี้ผ่านหน้า Admin ก่อน')

        total = 0

        for category_name, product_list in self.all_products.items():
            # สร้างหรือดึงหมวดหมู่ของ P184
            category, created = ProductCategory.objects.get_or_create(
                name=category_name,
                defaults={
                    "is_active": True,
                    "created_by": creator,
                }
            )
            # เผื่อหมวดหมู่มีอยู่แล้วแต่เป็นของคนอื่น ให้บังคับเปลี่ยนเจ้าของเป็น P184
            if category.created_by != creator:
                category.created_by = creator
                category.save()

            for code, name, selling_price in product_list:
                # สร้างหรืออัปเดตสินค้าโดยผูกกับ P184 เสมอ
                product, created = Product.objects.update_or_create(
                    code=code,
                    defaults={
                        "category": category,
                        "name": name,
                        "cost_price": 0,
                        "selling_price": selling_price,
                        "stock_quantity": 0,
                        "min_stock": 0,
                        "unit": "จาน",
                        "is_active": True,
                        "created_by": creator,
                    }
                )
                total += 1
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  + เพิ่ม: {code} | {name}"))
                else:
                    self.stdout.write(self.style.WARNING(f"  ↻ อัปเดต: {code} | {name}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"นำเข้าข้อมูลทั้งหมด {total} รายการ ให้กับผู้ใช้ P184 สำเร็จ!"))