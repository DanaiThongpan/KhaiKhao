from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from .forms import RegisterForm


# ============================================================
# Register
# ============================================================
def register(request):
    # ถ้า Login อยู่แล้วให้กลับไปหน้าแรก
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ")
            return redirect("login")
    else:
        form = RegisterForm()

    return render(request, "Accounts/register.html", {"form": form})


# ============================================================
# Login
# ============================================================
def user_login(request):
    # ถ้า Login อยู่แล้วให้กลับไปหน้าแรก
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # ตรวจสอบความถูกต้องของ Username และ Password
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # เข้าสู่ระบบสำเร็จ
            login(request, user)

            # ================================================
            # ตรวจสอบสิทธิ์ (Role) 
            # ================================================
            # เช็คว่าเป็น Admin หรือ Superuser หรือไม่
            if user.is_superuser or getattr(user, 'role', '') == "admin":
                return redirect("/products")  # เปลี่ยน URL ไปหน้า dashboard ของ admin ได้
            
            # เช็คว่าเป็น Owner หรือไม่
            elif getattr(user, 'role', '') == "owner":
                return redirect("/products")  # เปลี่ยน URL ไปหน้า dashboard ของ owner ได้
                
            # เช็คว่าเป็น Employee หรือไม่
            elif getattr(user, 'role', '') == "employee":
                return redirect("/products")  # เปลี่ยน URL ไปหน้า dashboard ของ employee ได้

            # หากไม่ตรงกับสิทธิ์ใดเลย (กันเหนียว)
            else:
                logout(request)
                messages.error(request, "ไม่พบสิทธิ์การใช้งานที่ถูกต้อง")
                return redirect("login")

        else:
            # เข้าสู่ระบบไม่สำเร็จ (รหัสผ่านผิด หรือไม่พบผู้ใช้)
            messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    return render(request, "Accounts/login.html")


# ============================================================
# Logout
# ============================================================
def user_logout(request):
    logout(request)
    messages.success(request, "ออกจากระบบเรียบร้อยแล้ว")
    return redirect("login")