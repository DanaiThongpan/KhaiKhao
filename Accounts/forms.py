from django import forms

from .models import User


class RegisterForm(forms.ModelForm):

    password = forms.CharField(
        label="รหัสผ่าน",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "กรอกรหัสผ่าน",
                "autocomplete": "new-password",
            }
        )
    )

    password_confirm = forms.CharField(
        label="ยืนยันรหัสผ่าน",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "กรอกรหัสผ่านอีกครั้ง",
                "autocomplete": "new-password",
            }
        )
    )

    role = forms.ChoiceField(
        label="บทบาท",
        choices=(
            ("owner", "เจ้าของร้าน"),
            ("employee", "พนักงาน"),
        ),
        widget=forms.Select(
            attrs={
                "class": "form-input",
            }
        )
    )

    class Meta:

        model = User

        fields = [
            "username",
            "role",
            "bank_name",
            "bank_account_number",
            "bank_account_name",
            "promptpay_number",
        ]

        labels = {
            "username": "ชื่อผู้ใช้",
            "bank_name": "ชื่อธนาคาร",
            "bank_account_number": "เลขที่บัญชีธนาคาร",
            "bank_account_name": "ชื่อบัญชี (เจ้าของบัญชี)",
            "promptpay_number": "หมายเลขพร้อมเพย์ / แม่มณี (เบอร์โทร หรือ เลขผู้เสียภาษี)",
        }

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "กรอกชื่อผู้ใช้",
                    "autocomplete": "username",
                }
            ),
            "bank_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "เช่น กสิกรไทย, ไทยพาณิชย์",
                }
            ),
            "bank_account_number": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "กรอกเลขที่บัญชีธนาคาร",
                }
            ),
            "bank_account_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "กรอกชื่อ-นามสกุล เจ้าของบัญชี",
                }
            ),
            "promptpay_number": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "กรอกเบอร์มือถือ หรือ เลขผู้เสียภาษี สำหรับ QR พร้อมเพย์",
                }
            ),
        }

    # ========================================================
    # Username
    # ========================================================

    fn = clean_username = lambda self: self.cleaned_data.get("username") # (ย่อเพื่อความสะอาด)

    def clean_username(self):

        username = self.cleaned_data["username"].strip()

        if User.objects.filter(
            username=username
        ).exists():

            raise forms.ValidationError(
                "ชื่อผู้ใช้นี้มีอยู่ในระบบแล้ว"
            )

        return username

    # ========================================================
    # Password
    # ========================================================

    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get(
            "password_confirm"
        )

        if password and password_confirm:

            if password != password_confirm:

                raise forms.ValidationError(
                    "รหัสผ่านไม่ตรงกัน"
                )

        return cleaned_data

    # ========================================================
    # Save
    # ========================================================

    def save(self, commit=True):

        user = super().save(commit=False)

        # รับเฉพาะ Role ที่อนุญาต
        role = self.cleaned_data["role"]

        if role not in [
            "owner",
            "employee",
        ]:
            role = "owner"

        user.role = role

        # เข้ารหัส Password
        user.set_password(
            self.cleaned_data["password"]
        )

        # ผู้สมัครทั่วไปไม่มีสิทธิ์ Admin
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False

        if commit:
            user.save()

        return user