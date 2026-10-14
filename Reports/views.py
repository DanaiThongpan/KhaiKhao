from datetime import datetime, timedelta
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import (
    TruncDate,
    TruncDay,
    TruncMonth,
    TruncWeek,
    TruncYear,
)
from django.shortcuts import render

from Accounts.models import User
from Pos.models import Order, OrderItem

# =========================================================
# การตั้งค่าการแสดงผลร้านค้าและพาเลตสี (Color Palette)
# =========================================================
SHOP_CONFIG = {
    "P184": {
        "name": "🔥 ร้านทอดเป่า (P184)",
        "bg_color": "rgba(249, 115, 22, 0.85)",  # สีส้มสว่างสดใส (Brand Color)
        "border_color": "#ea580c",
    },
    "M053": {
        "name": "🐷 ร้านเรื่องของหมู (M053)",
        "bg_color": "rgba(236, 72, 153, 0.85)",  # สีชมพูสดใส (Brand Color)
        "border_color": "#db2777",
    },
}

# ชุดสีสำรองระดับพรีเมียม (เผื่อกรณีมีร้านค้าอื่นๆ เพิ่มเติมในอนาคต)
FALLBACK_COLORS = [
    {"bg_color": "rgba(16, 185, 129, 0.85)", "border_color": "#059669"},  # เขียวมรกต
    {"bg_color": "rgba(59, 130, 246, 0.85)", "border_color": "#2563eb"},  # น้ำเงิน
    {"bg_color": "rgba(139, 92, 246, 0.85)", "border_color": "#7c3aed"},  # ม่วง
    {"bg_color": "rgba(245, 158, 11, 0.85)", "border_color": "#d97706"},  # เหลืองอำพัน
    {"bg_color": "rgba(6, 182, 212, 0.85)", "border_color": "#0891b2"},  # ฟ้าคราม
    {"bg_color": "rgba(239, 68, 68, 0.85)", "border_color": "#dc2626"},  # แดง
    {"bg_color": "rgba(99, 102, 241, 0.85)", "border_color": "#4f46e5"},  # คราม
]

THAI_MONTHS_SHORT = [
    "",
    "ม.ค.",
    "ก.พ.",
    "มี.ค.",
    "เม.ย.",
    "พ.ค.",
    "มิ.ย.",
    "ก.ค.",
    "ส.ค.",
    "ก.ย.",
    "ต.ค.",
    "พ.ย.",
    "ธ.ค.",
]


def format_period_label(period_val, filter_type):
    """ฟังก์ชันจัดรูปแบบแกน X ของกราฟเป็นภาษาไทยตามประเภทการกรอง"""
    if not period_val:
        return ""
    if hasattr(period_val, "date"):
        d = period_val.date()
    elif isinstance(period_val, datetime):
        d = period_val.date()
    else:
        d = period_val

    if filter_type == "year":
        return f"{d.year}"
    elif filter_type == "month":
        return f"{THAI_MONTHS_SHORT[d.month]} {d.year}"
    elif filter_type == "week":
        return f"สัปดาห์ {d.day} {THAI_MONTHS_SHORT[d.month]}"
    else:  # day
        return f"{d.day} {THAI_MONTHS_SHORT[d.month]}"


@login_required
def reports_home(request):
    """
    หน้าแสดงรายงานยอดขายและสถิติกราฟแยกตามร้านค้า (Stacked Bar Chart)
    ดึงข้อมูลทั้งหมดด้วย Django ORM Query เพียงครั้งเดียว ไม่เกิดปัญหา N+1 Query
    """
    # 1. รับค่าตัวกรองจาก Request
    selected_user_id = request.GET.get("user", "")
    filter_type = request.GET.get("filter", "day")
    selected_month = request.GET.get("month_picker", "")  # รูปแบบ: YYYY-MM

    # 2. ตั้งค่า QuerySet สำหรับสรุปตารางสถิติด้านล่าง
    orders_qs = Order.objects.all()
    if selected_user_id:
        orders_qs = orders_qs.filter(created_by_id=selected_user_id)

    if selected_month:
        try:
            year, month = map(int, selected_month.split("-"))
            orders_qs = orders_qs.filter(created_at__year=year, created_at__month=month)
        except ValueError:
            pass

    # ยอดขายสะสมรวมทั้งหมด (Grand Total)
    grand_total = orders_qs.aggregate(total=Sum("total_amount"))["total"] or 0

    # ตารางสรุปสถิติ 4 รูปแบบ
    daily_sales = (
        orders_qs.annotate(period=TruncDay("created_at"))
        .values("period")
        .annotate(total=Sum("total_amount"), order_count=Count("id", distinct=True))
        .order_by("-period")[:10]
    )

    weekly_sales = (
        orders_qs.annotate(period=TruncWeek("created_at"))
        .values("period")
        .annotate(total=Sum("total_amount"), order_count=Count("id", distinct=True))
        .order_by("-period")[:10]
    )

    monthly_sales = (
        orders_qs.annotate(period=TruncMonth("created_at"))
        .values("period")
        .annotate(total=Sum("total_amount"), order_count=Count("id", distinct=True))
        .order_by("-period")[:12]
    )

    yearly_sales = (
        orders_qs.annotate(period=TruncYear("created_at"))
        .values("period")
        .annotate(total=Sum("total_amount"), order_count=Count("id", distinct=True))
        .order_by("-period")[:5]
    )

    # 3. กำหนดเงื่อนไขการตัดคีย์เวิร์ดที่ไม่นับเป็น "กล่อง"
    exclude_keywords = [
        "topping",
        "ท็อปปิ้ง",
        "กับข้าว",
        "พิเศษ",
        "เครื่องดื่ม",
        "โปรโมชั่น",
        "เพิ่มเติม",
        "ของทานเล่น",
        "ค่าจัดส่ง",
        "โปรโมชั่นส่วนลด",
    ]
    exclude_q = Q()
    for kw in exclude_keywords:
        exclude_q |= Q(product__name__icontains=kw) | Q(
            product__category__name__icontains=kw
        )

    # 4. ฟังก์ชันช่วงเวลาสำหรับจัดกลุ่มกราฟ
    if filter_type == "year":
        trunc_fn = TruncYear("order__created_at")
        chart_title = "สถิติยอดขายรายปี (แยกตามร้านค้า)"
    elif filter_type == "month":
        trunc_fn = TruncMonth("order__created_at")
        chart_title = "สถิติยอดขายรายเดือน (แยกตามร้านค้า)"
    elif filter_type == "week":
        trunc_fn = TruncWeek("order__created_at")
        chart_title = "สถิติยอดขายรายสัปดาห์ (แยกตามร้านค้า)"
    else:
        trunc_fn = TruncDate("order__created_at")
        chart_title = "สถิติยอดขายรายวัน (แยกตามร้านค้า)"

    if selected_month:
        try:
            m_dt = datetime.strptime(selected_month, "%Y-%m")
            chart_title += f" (ประจำเดือน {THAI_MONTHS_SHORT[m_dt.month]} {m_dt.year})"
        except ValueError:
            pass

    # 5. Query ข้อมูลกราฟทั้งหมดเพียงครั้งเดียว (Single Query via OrderItem ORM)
    items_qs = OrderItem.objects.all()
    if selected_user_id:
        items_qs = items_qs.filter(order__created_by_id=selected_user_id)
    if selected_month:
        try:
            year, month = map(int, selected_month.split("-"))
            items_qs = items_qs.filter(
                order__created_at__year=year, order__created_at__month=month
            )
        except ValueError:
            pass

    sales_by_shop = (
        items_qs.annotate(
            period=trunc_fn,
            shop=F("order__created_by__username"),
        )
        .values("period", "shop")
        .annotate(
            total_sales=Sum("subtotal"),
            order_count=Count("order_id", distinct=True),
            box_count=Sum("quantity", filter=~exclude_q, default=0),
        )
        .order_by("period", "shop")
    )

    sales_list = list(sales_by_shop)

    # 6. เตรียมข้อมูลแกน X (chart_labels)
    unique_periods = sorted(
        list(set(row["period"] for row in sales_list if row["period"]))
    )
    chart_labels = [format_period_label(p, filter_type) for p in unique_periods]

    # 7. ค้นหาร้านค้าทั้งหมด พร้อมจัดเรียง P184 และ M053 ขึ้นก่อน
    raw_shops = list(set(row["shop"] for row in sales_list if row["shop"]))
    sorted_shops = sorted(
        raw_shops,
        key=lambda s: (0 if s == "P184" else 1 if s == "M053" else 2, str(s)),
    )

    # สร้าง Lookup Map: (period, shop) -> row เพื่อความเร็ว O(1)
    lookup_map = {(row["period"], row["shop"]): row for row in sales_list}

    # 8. สร้าง chart_datasets ให้รองรับ Stacked Bar Chart แยกตามร้านค้า
    chart_datasets = []
    fallback_idx = 0

    for shop in sorted_shops:
        if shop in SHOP_CONFIG:
            cfg = SHOP_CONFIG[shop]
        else:
            palette = FALLBACK_COLORS[fallback_idx % len(FALLBACK_COLORS)]
            fallback_idx += 1
            cfg = {
                "name": f"🛒 ร้าน {shop}",
                "bg_color": palette["bg_color"],
                "border_color": palette["border_color"],
            }

        sales_vals = []
        order_vals = []
        box_vals = []

        for p in unique_periods:
            item = lookup_map.get((p, shop))
            if item:
                sales_vals.append(float(item["total_sales"] or 0))
                order_vals.append(int(item["order_count"] or 0))
                box_vals.append(int(item["box_count"] or 0))
            else:
                sales_vals.append(0.0)
                order_vals.append(0)
                box_vals.append(0)

        chart_datasets.append(
            {
                "label": cfg["name"],
                "shop_id": shop,
                "data": sales_vals,
                "order_counts": order_vals,
                "box_counts": box_vals,
                "backgroundColor": cfg["bg_color"],
                "borderColor": cfg["border_color"],
                "borderWidth": 1.5,
                "borderRadius": 6,
                "stack": "salesStack",  # ตั้งค่า stack ให้ซ้อนแท่งกัน
            }
        )

    all_users = User.objects.filter(is_active=True)

    context = {
        "grand_total": grand_total,
        "daily_sales": daily_sales,
        "weekly_sales": weekly_sales,
        "monthly_sales": monthly_sales,
        "yearly_sales": yearly_sales,
        "chart_labels_json": json.dumps(chart_labels, ensure_ascii=False),
        "chart_datasets_json": json.dumps(chart_datasets, ensure_ascii=False),
        "chart_label": chart_title,
        "filter_type": filter_type,
        "selected_month": selected_month,
        "all_users": all_users,
        "selected_user_id": selected_user_id,
    }

    return render(request, "Reports/home.html", context)
