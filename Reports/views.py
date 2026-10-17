from datetime import datetime, timedelta
import json
import zoneinfo

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import (
    ExtractHour,
    TruncDate,
    TruncDay,
    TruncHour,
    TruncMonth,
    TruncWeek,
    TruncYear,
)
from django.shortcuts import render
from django.utils import timezone

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

    if filter_type in ["realtime", "today"]:
        if hasattr(period_val, "hour"):
            return f"{period_val.hour:02d}:00 น."
        elif isinstance(period_val, str) and len(period_val) >= 13:
            try:
                hour = int(period_val[11:13])
                return f"{hour:02d}:00 น."
            except ValueError:
                return str(period_val)
        return str(period_val)

    if hasattr(period_val, "date"):
        d = period_val.date()
    elif isinstance(period_val, datetime):
        d = period_val.date()
    elif isinstance(period_val, str):
        try:
            d = datetime.strptime(period_val[:10], "%Y-%m-%d").date()
        except ValueError:
            return str(period_val)
    else:
        d = period_val

    if filter_type == "year":
        return f"{d.year}"
    elif filter_type == "month":
        return f"{THAI_MONTHS_SHORT[d.month]} {d.year}"
    elif filter_type == "week":
        return f"สัปดาห์ {d.day} {THAI_MONTHS_SHORT[d.month]}"
    elif filter_type == "all":
        return f"{d.day} {THAI_MONTHS_SHORT[d.month]} {str(d.year)[2:]}"
    else:  # day
        return f"{d.day} {THAI_MONTHS_SHORT[d.month]}"


@login_required
def reports_home(request):
    """
    หน้าแสดงรายงานยอดขายและสถิติกราฟแยกตามร้านค้า (Stacked Bar Chart)
    รองรับตัวกรอง 6 รูปแบบ:
    1. เรียลไทม์ (realtime / วันนี้)
    2. รายวัน (day)
    3. รายสัปดาห์ (week)
    4. รายเดือน (month)
    5. รายปี (year)
    6. ทั้งหมดทุกออเดอร์ (all)
    พร้อมการวิเคราะห์ช่วงเวลาพีค (Peak Sales Hours: 00:00 - 23:00 น.)
    """
    # 1. รับค่าตัวกรองจาก Request
    selected_user_id = request.GET.get("user", "")
    filter_type = request.GET.get("filter", "day")
    selected_month = request.GET.get("month_picker", "")  # รูปแบบ: YYYY-MM

    # หากผู้ใช้เลือก month_picker ขณะอยู่ใน realtime หรือ all ให้เปลี่ยน filter_type เป็น day
    if selected_month and filter_type in ["realtime", "all"]:
        filter_type = "day"

    # ถ้าเลือก realtime หรือ all ให้เคลียร์ selected_month ออก
    if filter_type in ["realtime", "all"]:
        selected_month = ""

    today = timezone.localdate()

    # 2. ตั้งค่า QuerySet พื้นฐานสำหรับสรุปตารางสถิติด้านล่าง (Historical Tables)
    base_orders_qs = Order.objects.all()
    if selected_user_id:
        base_orders_qs = base_orders_qs.filter(created_by_id=selected_user_id)

    if selected_month:
        try:
            year, month = map(int, selected_month.split("-"))
            base_orders_qs = base_orders_qs.filter(created_at__year=year, created_at__month=month)
        except ValueError:
            pass

    tz = timezone.get_current_timezone()

    # ตารางสรุปสถิติ 4 รูปแบบ (Daily 10 วันล่าสุด, Weekly, Monthly, Yearly)
    daily_sales = (
        base_orders_qs.annotate(period=TruncDay("created_at", tzinfo=tz))
        .values("period")
        .annotate(total=Sum("total_amount"), order_count=Count("id", distinct=True))
        .order_by("-period")[:10]
    )

    weekly_sales = (
        base_orders_qs.annotate(period=TruncWeek("created_at", tzinfo=tz))
        .values("period")
        .annotate(total=Sum("total_amount"), order_count=Count("id", distinct=True))
        .order_by("-period")[:10]
    )

    monthly_sales = (
        base_orders_qs.annotate(period=TruncMonth("created_at", tzinfo=tz))
        .values("period")
        .annotate(total=Sum("total_amount"), order_count=Count("id", distinct=True))
        .order_by("-period")[:12]
    )

    yearly_sales = (
        base_orders_qs.annotate(period=TruncYear("created_at", tzinfo=tz))
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

    # 4. กำหนด QuerySet ตามช่วงเวลาที่ผู้ใช้เลือกกรอง (Filter Scope)
    orders_qs = Order.objects.all()
    items_qs = OrderItem.objects.all()

    if selected_user_id:
        orders_qs = orders_qs.filter(created_by_id=selected_user_id)
        items_qs = items_qs.filter(order__created_by_id=selected_user_id)

    if filter_type in ["realtime", "today"]:
        orders_qs = orders_qs.filter(created_at__date=today)
        items_qs = items_qs.filter(order__created_at__date=today)
        trunc_fn = TruncHour("order__created_at", tzinfo=tz)
        chart_title = "⚡ สถิติยอดขายวันนี้ (เรียลไทม์)"
        summary_label = "ยอดขายสะสมวันนี้ (เรียลไทม์)"
    elif filter_type == "week":
        if selected_month:
            try:
                year, month = map(int, selected_month.split("-"))
                orders_qs = orders_qs.filter(created_at__year=year, created_at__month=month)
                items_qs = items_qs.filter(order__created_at__year=year, order__created_at__month=month)
            except ValueError:
                pass
        trunc_fn = TruncWeek("order__created_at", tzinfo=tz)
        chart_title = "📆 สถิติยอดขายรายสัปดาห์ (แยกตามร้านค้า)"
        summary_label = "ยอดขายสะสมตามช่วงเวลาที่กรอง"
    elif filter_type == "month":
        if selected_month:
            try:
                year, month = map(int, selected_month.split("-"))
                orders_qs = orders_qs.filter(created_at__year=year, created_at__month=month)
                items_qs = items_qs.filter(order__created_at__year=year, order__created_at__month=month)
            except ValueError:
                pass
        trunc_fn = TruncMonth("order__created_at", tzinfo=tz)
        chart_title = "📈 สถิติยอดขายรายเดือน (แยกตามร้านค้า)"
        summary_label = "ยอดขายสะสมตามช่วงเวลาที่กรอง"
    elif filter_type == "year":
        trunc_fn = TruncYear("order__created_at", tzinfo=tz)
        chart_title = "🏆 สถิติยอดขายรายปี (แยกตามร้านค้า)"
        summary_label = "ยอดขายสะสมตามช่วงเวลาที่กรอง"
    elif filter_type == "all":
        trunc_fn = TruncDate("order__created_at", tzinfo=tz)
        chart_title = "🌐 สถิติยอดขายทั้งหมดทุกออเดอร์ (แยกตามร้านค้า)"
        summary_label = "ยอดขายสะสมทั้งหมดทุกออเดอร์ (All-Time)"
    else:  # day
        filter_type = "day"
        if selected_month:
            try:
                year, month = map(int, selected_month.split("-"))
                orders_qs = orders_qs.filter(created_at__year=year, created_at__month=month)
                items_qs = items_qs.filter(order__created_at__year=year, order__created_at__month=month)
            except ValueError:
                pass
        trunc_fn = TruncDate("order__created_at", tzinfo=tz)
        chart_title = "📅 สถิติยอดขายรายวัน (แยกตามร้านค้า)"
        summary_label = "ยอดขายสะสมตามช่วงเวลาที่กรอง"

    if selected_month and filter_type in ["day", "week", "month"]:
        try:
            m_dt = datetime.strptime(selected_month, "%Y-%m")
            chart_title += f" (ประจำเดือน {THAI_MONTHS_SHORT[m_dt.month]} {m_dt.year})"
            summary_label = f"ยอดขายสะสมประจำเดือน {THAI_MONTHS_SHORT[m_dt.month]} {m_dt.year}"
        except ValueError:
            pass

    # ยอดขายสะสมตามเงื่อนไขการกรอง (Grand Total)
    grand_total = orders_qs.aggregate(total=Sum("total_amount"))["total"] or 0

    # 5. Query ข้อมูลกราฟทั้งหมดเพียงครั้งเดียว (Single Query via OrderItem ORM)
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

    # =========================================================
    # 🌟 9. วิเคราะห์ช่วงเวลาพีคของการขาย (Peak Sales Hours) 🌟
    # แปลงเวลาเฉพาะกราฟนี้เป็นเวลาประเทศไทย (Asia/Bangkok: UTC+7) ตามคำสั่งพิเศษ
    # นำช่วงเวลาเที่ยงคืน (00:00 น.) ไว้ตรงกลางของแกน X (เรียงลำดับ: 12:00 -> 23:00 -> 00:00 -> 11:00)
    # =========================================================
    thai_tz = zoneinfo.ZoneInfo("Asia/Bangkok")
    hourly_stats = (
        orders_qs.annotate(
            hour=ExtractHour("created_at", tzinfo=thai_tz)
        )
        .values("hour")
        .annotate(
            total_sales=Sum("total_amount"),
            order_count=Count("id")
        )
        .order_by("hour")
    )

    hour_map = {row["hour"]: row for row in hourly_stats if row["hour"] is not None}

    # จัดเรียงลำดับ 24 ชั่วโมงโดยให้เที่ยงคืน (00:00 น.) อยู่ตรงกลาง (12:00 ถึง 11:00 น.)
    ordered_hours = [(h % 24) for h in range(12, 36)]
    peak_hours_labels = [f"{h:02d}:00 น." for h in ordered_hours]
    peak_hours_sales = [
        float(hour_map[h]["total_sales"] or 0) if h in hour_map else 0.0
        for h in ordered_hours
    ]
    peak_hours_orders = [
        int(hour_map[h]["order_count"] or 0) if h in hour_map else 0
        for h in ordered_hours
    ]

    # สรุปช่วงเวลาที่ขายดีที่สุด (Peak Rush Hour)
    max_peak_sales = max(peak_hours_sales) if peak_hours_sales else 0.0
    max_hour_idx = peak_hours_sales.index(max_peak_sales) if max_peak_sales > 0 else 0
    peak_summary = {
        "hour": peak_hours_labels[max_hour_idx],
        "sales": max_peak_sales,
        "orders": peak_hours_orders[max_hour_idx],
    }

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
        "summary_label": summary_label,
        "filter_type": filter_type,
        "selected_month": selected_month,
        "all_users": all_users,
        "selected_user_id": selected_user_id,
        # 🌟 ตัวแปรช่วงเวลาพีคส่งให้ Chart.js 🌟
        "peak_hours_labels_json": json.dumps(peak_hours_labels, ensure_ascii=False),
        "peak_hours_sales_json": json.dumps(peak_hours_sales),
        "peak_hours_orders_json": json.dumps(peak_hours_orders),
        "peak_summary": peak_summary,
    }

    return render(request, "Reports/home.html", context)
