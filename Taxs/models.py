from django.db import models
from Accounts.models import User

class TaxRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ผู้ใช้งาน")
    tax_year = models.IntegerField(verbose_name="ปีภาษี (พ.ศ./ค.ศ.)")
    total_income = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="รายได้ทั้งปี")
    total_expenses_deduction = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="ค่าใช้จ่ายและค่าลดหย่อน")
    net_income = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="เงินได้สุทธิ")
    tax_to_pay = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="ภาษีที่ต้องชำระ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่บันทึก")

    def __str__(self):
        return f"ภาษีปี {self.tax_year} - {self.user.username} (ยอดชำระ: ฿{self.tax_to_pay})"