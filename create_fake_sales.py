import os
import django
from decimal import Decimal

# ตั้งค่าสภาพแวดล้อม Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KhaiKhao.settings')
django.setup()

from Pos.models import Order
from Accounts.models import User

def generate_fake_order():
    # เลือก User ที่จะให้เป็นเจ้าของยอดขายนี้ (เปลี่ยนชื่อ username ให้ตรงกับที่คุณใช้งาน เช่น P184 หรือ M053)
    target_username = "P184"  # หรือใส่ชื่อ user ของคุณ
    user = User.objects.filter(username=target_username).first()
    
    if not user:
        # ถ้าหา user ไม่เจอ ให้ดึงตัวแรกในระบบมาใช้แทน
        user = User.objects.first()
    
    if not user:
        print("❌ ไม่พบ User ในระบบ กรุณาสร้าง User ก่อนรันสคริปต์นี้")
        return

    # เลขที่บิลจำลอง
    receipt_no = "REC-TAX-TEST"
    
    # ยอดเงินจำลองที่ต้องการ (170,500 บาท)
    fake_amount = Decimal("600000.00")

    # ตรวจสอบว่ามีบิลนี้อยู่แล้วหรือยัง ถ้ามีให้ลบทิ้งก่อนเพื่อสร้างใหม่สดๆ
    Order.objects.filter(receipt_number=receipt_no).delete()

    # สร้างข้อมูล Order จำลอง
    order = Order.objects.create(
        receipt_number=receipt_no,
        total_amount=fake_amount,
        created_by=user
    )

    print(f"✅ สร้างยอดขายจำลองสำเร็จ!")
    print(f"👤 ผู้ใช้งาน: {user.username}")
    print(f"🧾 เลขที่บิล: {order.receipt_number}")
    print(f"💰 ยอดขายรวม: ฿{order.total_amount:,.2f}")
    print(f"📅 วันที่: {order.created_at}")

if __name__ == "__main__":
    generate_fake_order()