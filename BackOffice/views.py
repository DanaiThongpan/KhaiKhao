from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.db.models import Sum
from Pos.models import Order
from Products.models import Product
from Stocks.models import StockItem
from Pos.models import Order, OrderItem # 🌟 อย่าลืม import OrderItem

User = get_user_model()

# เช็กว่าเป็น Admin
def is_admin(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, 'role', '') == "admin")

@user_passes_test(is_admin, login_url='/login/')
def admin_dashboard(request):
    total_platform_sales = Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_shops = User.objects.filter(is_superuser=False).count()
    
    shops = User.objects.filter(is_superuser=False)
    shop_data = []
    for shop in shops:
        sales = Order.objects.filter(created_by=shop).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        shop_data.append({
            'id': shop.id,  # 🌟 ส่ง ID ไปให้เทมเพลตเพื่อใช้ทำลิงก์
            'username': shop.username,
            'sales': sales
        })
        
    shop_data = sorted(shop_data, key=lambda x: x['sales'], reverse=True)

    context = {
        'total_platform_sales': total_platform_sales,
        'total_shops': total_shops,
        'shop_data': shop_data,
    }
    return render(request, 'BackOffice/dashboard.html', context)

# ==================================================
# 🌟 ระบบเจาะดูข้อมูลและจัดการแต่ละสาขา (Shop Manage)
# ==================================================
@user_passes_test(is_admin, login_url='/login/')
def shop_manage(request, shop_id):
    shop = get_object_or_404(User, id=shop_id)

    # หากมีการกด เพิ่ม/ลบ/แก้ไข ข้อมูลจากหน้าเว็บ
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # --- 📦 จัดการสินค้า (Products) ---
        if action == 'add_product':
            Product.objects.create(
                name=request.POST.get('name'),
                selling_price=request.POST.get('price', 0),
                stock_quantity=request.POST.get('stock_quantity', 0),
                created_by=shop
            )
        elif action == 'edit_product':
            prod = get_object_or_404(Product, id=request.POST.get('product_id'), created_by=shop)
            prod.name = request.POST.get('name')
            prod.selling_price = request.POST.get('price', 0)
            prod.stock_quantity = request.POST.get('stock_quantity', 0)
            prod.save()
        elif action == 'delete_product':
            Product.objects.filter(id=request.POST.get('product_id'), created_by=shop).delete()
            
        # --- 🛒 จัดการสต๊อก (Stocks) ---
        elif action == 'add_stock':
            StockItem.objects.create(
                name=request.POST.get('name'),
                quantity=request.POST.get('qty', 0),
                unit=request.POST.get('unit', 'ชิ้น'),
                created_by=shop
            )
        elif action == 'edit_stock':
            stock = get_object_or_404(StockItem, id=request.POST.get('stock_id'), created_by=shop)
            stock.name = request.POST.get('name')
            stock.quantity = request.POST.get('qty', 0)
            stock.unit = request.POST.get('unit', 'ชิ้น')
            stock.save()
        elif action == 'delete_stock':
            StockItem.objects.filter(id=request.POST.get('stock_id'), created_by=shop).delete()

        # ทำเสร็จแล้วให้รีเฟรชหน้าเดิม
        return redirect('backoffice:shop_manage', shop_id=shop.id)

    # ดึงข้อมูลของร้านนี้มาแสดง
    orders = Order.objects.filter(created_by=shop).order_by('-created_at')
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    products = Product.objects.filter(created_by=shop).order_by('-id')
    stocks = StockItem.objects.filter(created_by=shop).order_by('-id')

    context = {
        'shop': shop,
        'total_sales': total_sales,
        'orders': orders[:20], # ดูประวัติ 20 บิลล่าสุด
        'products': products,
        'stocks': stocks,
    }
    return render(request, 'BackOffice/shop_manage.html', context)

@user_passes_test(is_admin, login_url='/login/')
def shop_manage(request, shop_id):
    shop = get_object_or_404(User, id=shop_id)

    # หากมีการกด เพิ่ม/ลบ/แก้ไข ข้อมูลจากหน้าเว็บ
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # --- 📦 จัดการสินค้า (Products) ---
        if action == 'add_product':
            Product.objects.create(
                name=request.POST.get('name'),
                selling_price=request.POST.get('price', 0),
                stock_quantity=request.POST.get('stock_quantity', 0),
                created_by=shop
            )
        elif action == 'edit_product':
            prod = get_object_or_404(Product, id=request.POST.get('product_id'), created_by=shop)
            prod.name = request.POST.get('name')
            prod.selling_price = request.POST.get('price', 0)
            prod.stock_quantity = request.POST.get('stock_quantity', 0)
            prod.save()
        elif action == 'delete_product':
            Product.objects.filter(id=request.POST.get('product_id'), created_by=shop).delete()
            
        # --- 🛒 จัดการสต๊อก (Stocks) ---
        elif action == 'add_stock':
            StockItem.objects.create(
                name=request.POST.get('name'),
                quantity=request.POST.get('qty', 0),
                unit=request.POST.get('unit', 'ชิ้น'),
                created_by=shop
            )
        elif action == 'edit_stock':
            stock = get_object_or_404(StockItem, id=request.POST.get('stock_id'), created_by=shop)
            stock.name = request.POST.get('name')
            stock.quantity = request.POST.get('qty', 0)
            stock.unit = request.POST.get('unit', 'ชิ้น')
            stock.save()
        elif action == 'delete_stock':
            StockItem.objects.filter(id=request.POST.get('stock_id'), created_by=shop).delete()

        return redirect('backoffice:shop_manage', shop_id=shop.id)

    # ดึงข้อมูลของร้านนี้มาแสดง
    orders = Order.objects.filter(created_by=shop).order_by('-created_at')
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    products = list(Product.objects.filter(created_by=shop).order_by('-id'))
    stocks = StockItem.objects.filter(created_by=shop).order_by('-id')

    # 🌟 คำนวณจำนวนชิ้นที่ขายไปแล้วของแต่ละสินค้า
    sold_data = OrderItem.objects.filter(order__created_by=shop).values('product_id').annotate(total_sold=Sum('quantity'))
    sold_dict = {item['product_id']: item['total_sold'] for item in sold_data}
    
    for p in products:
        p.total_sold = sold_dict.get(p.id, 0)
        
    # จัดอันดับสินค้าขายดี (เรียงจากยอดขายมากไปน้อย เอาแค่ 5 อันดับแรก)
    top_products = sorted([p for p in products if p.total_sold > 0], key=lambda x: x.total_sold, reverse=True)[:5]

    context = {
        'shop': shop,
        'total_sales': total_sales,
        'orders': orders[:20],
        'products': products,
        'top_products': top_products, # 🌟 ส่งข้อมูล 5 อันดับแรกไปแสดงผล
        'stocks': stocks,
    }
    return render(request, 'BackOffice/shop_manage.html', context)