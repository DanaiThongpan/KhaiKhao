from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, username, password=None, role="owner"):
        if not username:
            raise ValueError("กรุณาระบุชื่อผู้ใช้")

        user = self.model(username=username, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None):
        user = self.create_user(username=username, password=password, role="admin")
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ("admin", "ผู้ดูแลระบบ"),
        ("owner", "เจ้าของร้าน"),
        ("employee", "พนักงาน"),
    )

    # ข้อมูลผู้ใช้งาน
    username = models.CharField(max_length=150, unique=True, verbose_name="ชื่อผู้ใช้")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="owner", verbose_name="บทบาท")

    # สถานะและสิทธิ์การเข้าถึง (Django Admin)
    is_active = models.BooleanField(default=True, verbose_name="เปิดใช้งาน")
    is_staff = models.BooleanField(default=False, verbose_name="เจ้าหน้าที่ระบบ")
    is_superuser = models.BooleanField(default=False, verbose_name="ผู้ดูแลสูงสุด")

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username

    # ========================================================
    # Permissions (จำเป็นสำหรับการใช้งาน Django Admin)
    # ========================================================
    def has_perm(self, perm, obj=None):
        """ผู้ใช้คนนี้มีสิทธิ์ที่ระบุหรือไม่?"""
        return self.is_superuser

    def has_module_perms(self, app_label):
        """ผู้ใช้คนนี้มีสิทธิ์ดูแอปพลิเคชันที่ระบุหรือไม่?"""
        return self.is_superuser