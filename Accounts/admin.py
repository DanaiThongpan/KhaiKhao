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
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
    )

    list_filter = (
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    search_fields = (
        "username",
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
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )