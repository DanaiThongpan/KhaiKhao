import os
import httplib2
from datetime import timedelta
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
TARGET_CALENDAR_ID = "teew8888@gmail.com"  # อีเมลที่จะรับข้อมูล

def get_calendar_service():
    credentials_file = os.path.join(settings.BASE_DIR, "service_account.json")

    if not os.path.exists(credentials_file):
        raise FileNotFoundError(f"ไม่พบไฟล์: {credentials_file}")

    credentials = service_account.Credentials.from_service_account_file(
        credentials_file, scopes=SCOPES
    )

    # -------------------------------------------------------------
    # แก้ไขปัญหา Network is unreachable สำหรับบัญชีฟรี PythonAnywhere
    # -------------------------------------------------------------
    # ตรวจสอบว่าเซิร์ฟเวอร์บังคับใช้ Proxy หรือไม่
    if os.environ.get('http_proxy') or os.environ.get('HTTP_PROXY'):
        proxy_info = httplib2.ProxyInfo(
            proxy_type=httplib2.socks.PROXY_TYPE_HTTP,
            proxy_host='proxy.server',
            proxy_port=3128
        )
        http = httplib2.Http(proxy_info=proxy_info)
    else:
        # ถ้ารันในคอมพิวเตอร์ตัวเอง หรือเป็นบัญชีเสียเงิน ให้วิ่งปกติ
        http = httplib2.Http()

    # ผสม Proxy เข้ากับกุญแจ Service Account แล้วส่งให้ Google
    authed_http = AuthorizedHttp(credentials, http=http)
    return build("calendar", "v3", http=authed_http)


def create_expense_event(expense):
    service = get_calendar_service()
    category = expense.get_category_display()

    description = f"รายการรายจ่าย: {expense.name}\nจำนวนเงิน: ฿{expense.amount:,.2f}\nหมวดหมู่: {category}\n"

    if expense.description:
        description += f"รายละเอียด: {expense.description}\n"

    description += "\nสร้างโดย KhaiKhao POS"

    start_date = expense.expense_date
    end_date = start_date + timedelta(days=1)

    event = {
        "summary": f"💵 รายจ่าย: {expense.name}",
        "description": description,
        "start": {"date": start_date.isoformat()},
        "end": {"date": end_date.isoformat()},
    }

    return service.events().insert(calendarId=TARGET_CALENDAR_ID, body=event).execute()

def update_expense_event(expense):
    """ฟังก์ชันสำหรับอัปเดตกิจกรรมใน Google Calendar"""
    if not expense.google_event_id:
        return None

    service = get_calendar_service()
    category = expense.get_category_display()

    description = f"รายการรายจ่าย: {expense.name}\nจำนวนเงิน: ฿{expense.amount:,.2f}\nหมวดหมู่: {category}\n"
    if expense.description:
        description += f"รายละเอียด: {expense.description}\n"
    description += "\n🔄 แก้ไขโดย KhaiKhao POS"

    start_date = expense.expense_date
    end_date = start_date + timedelta(days=1)

    event = {
        "summary": f"💵 รายจ่าย: {expense.name}",
        "description": description,
        "start": {"date": start_date.isoformat()},
        "end": {"date": end_date.isoformat()},
    }

    try:
        # สั่งอัปเดตโดยอ้างอิงจาก google_event_id เดิม
        return service.events().update(
            calendarId=TARGET_CALENDAR_ID,
            eventId=expense.google_event_id,
            body=event
        ).execute()
    except Exception as e:
        print(f"ไม่สามารถอัปเดต Calendar ได้: {e}")
        return None

def delete_expense_event(event_id):
    """ฟังก์ชันสำหรับลบกิจกรรมใน Google Calendar"""
    if not event_id:
        return

    service = get_calendar_service()
    try:
        # สั่งลบโดยใช้ event_id
        service.events().delete(
            calendarId=TARGET_CALENDAR_ID,
            eventId=event_id
        ).execute()
    except Exception as e:
        print(f"ไม่สามารถลบ Calendar ได้ (อาจถูกลบไปแล้ว): {e}")