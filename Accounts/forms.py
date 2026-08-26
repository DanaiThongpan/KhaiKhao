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
        ]

        labels = {
            "username": "ชื่อผู้ใช้",
        }

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "กรอกชื่อผู้ใช้",
                    "autocomplete": "username",
                }
            ),
        }

    # ========================================================
    # Username
    # ========================================================

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