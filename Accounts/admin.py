from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    model = User

    filter_horizontal = ()

    list_display = (
        "username",
        "role",
        "bank_name",
        "promptpay_number",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
    )

    list_filter = (
        "role",
        "bank_name",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    search_fields = (
        "username",
        "bank_account_number",
        "promptpay_number",
    )

    ordering = (
        "username",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "username",
                    "password",
                )
            }
        ),
        (
            "ข้อมูลผู้ใช้",
            {
                "fields": (
                    "role",
                )
            }
        ),
        (
            "ข้อมูลบัญชีธนาคารและพร้อมเพย์",
            {
                "fields": (
                    "bank_name",
                    "bank_account_number",
                    "bank_account_name",
                    "promptpay_number",
                )
            }
        ),
        (
            "สิทธิ์ระบบ",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            }
        ),
        (
            "ข้อมูลการเข้าสู่ระบบ",
            {
                "fields": (
                    "last_login",
                )
            }
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": (
                    "wide",
                ),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "role",
                    "bank_name",
                    "bank_account_number",
                    "bank_account_name",
                    "promptpay_number",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )