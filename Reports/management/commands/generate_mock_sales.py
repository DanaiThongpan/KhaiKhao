import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from Products.models import Product
from Pos.models import Order, OrderItem

class Command(BaseCommand):
    help = "Generate distinct test sales data including Aug 26, 2026 for reports testing"

    def handle(self, *args, **options):
        target_username = "P184"
        
        User = get_user_model()
        try:
            user = User.objects.get(username=target_username)
        except User.DoesNotExist:
            raise CommandError(f'ไม่พบผู้ใช้งานชื่อ "{target_username}" ในระบบ กรุณาสร้าง User นี้ก่อน')

        products = list(Product.objects.filter(created_by=user, is_active=True))
        if not products:
            raise CommandError(f'ไม่พบสินค้าของ "{target_username}" กรุณารันคำสั่ง import สินค้าของ User นี้ก่อน')

        self.stdout.write(f"กำลังล้างข้อมูลบิลทดสอบเก่า และสร้างข้อมูลใหม่ให้ผู้ใช้: {user.username}...")

        # (ทางเลือก) ลบข้อมูลบิลเก่าเฉพาะของ P184 ทิ้งก่อน เพื่อให้เริ่มนับยอดใหม่แบบเคลียร์ๆ
        Order.objects.filter(created_by=user).delete()

        # กำหนดวันที่เป้าหมายหลักคือ วันนี้ (Aug 26, 2026)
        today = timezone.datetime(2026, 8, 26, tzinfo=timezone.get_current_timezone())
        total_orders_created = 0

        # สร้างข้อมูลย้อนหลังไป 10 วัน เพื่อให้กราฟมีแท่งสูงต่ำเปรียบเทียบกัน
        for day_offset in range(10, -1, -1):
            target_date = today - timedelta(days=day_offset)
            
            # กำหนดช่วงเวลาขายในแต่ละวันให้แตกต่างกัน เพื่อให้เห็นผลต่างของเวลา
            if day_offset == 0:
                # วันที่ 26 ส.ค. 2026 ใส่เวลาตามที่คุณต้องการเป๊ะๆ
                specific_times = [
                    target_date.replace(hour=9, minute=14, second=0),
                    target_date.replace(hour=11, minute=30, second=15),
                    target_date.replace(hour=14, minute=20, second=10),
                    target_date.replace(hour=17, minute=20, second=30),
                    target_date.replace(hour=20, minute=10, second=0),
                ]
            else:
                # วันอื่นๆ สุ่มเวลาและจำนวนบิลต่างกัน (เพื่อให้ยอดขายแต่ละวันไม่เท่ากัน กราฟจะได้สูงต่ำต่างกัน)
                num_bills = random.randint(2, 6)
                specific_times = [
                    target_date.replace(hour=random.randint(10, 21), minute=random.randint(0, 59), second=0)
                    for _ in range(num_bills)
                ]

            for order_time in specific_times:
                receipt_num = f"V2-{order_time.strftime('%Y%m%d-%H%M%S')}-{random.randint(10, 99)}"

                order = Order.objects.create(
                    receipt_number=receipt_num,
                    total_amount=0,
                    created_by=user
                )

                # บังคับอัปเดตเวลาสร้างบิลให้ตรงตามที่กำหนด
                Order.objects.filter(id=order.id).update(created_at=order_time)

                # สุ่มสินค้าใส่บิล (1 ถึง 4 รายการ)
                num_items = random.randint(1, 4)
                chosen_products = random.sample(products, min(num_items, len(products)))
                
                order_total = 0
                for prod in chosen_products:
                    qty = random.randint(1, 3)
                    subtotal = prod.selling_price * qty
                    order_total += subtotal

                    OrderItem.objects.create(
                        order=order,
                        product=prod,
                        price=prod.selling_price,
                        quantity=qty,
                        subtotal=subtotal
                    )

                order.total_amount = order_total
                order.save()
                total_orders_created += 1

        self.stdout.write(self.style.SUCCESS(f"สร้างข้อมูลสำเร็จทั้งหมด {total_orders_created} บิล! (รวมวันที่ Aug. 26, 2026 เรียบร้อย)"))