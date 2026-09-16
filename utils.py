"""ฟังก์ชันช่วยเหลือทั่วไป: วันที่ไทย, จัดรูปแบบเงิน, เปิดไฟล์ด้วยโปรแกรมเริ่มต้นของเครื่อง"""
import datetime
import os
import subprocess
import sys

from constants import THAI_MONTHS


def current_month_key():
    """คืนค่าเดือนปัจจุบันรูปแบบ YYYY-MM (อิงตามวันที่ของเครื่องตอนนี้เสมอ ไม่อิงวันที่ในฟอร์ม)"""
    return datetime.date.today().isoformat()[:7]


def thai_month_label(month_key=None):
    """แปลง YYYY-MM เป็นข้อความเดือนภาษาไทย เช่น 'กันยายน 2569'"""
    month_key = month_key or current_month_key()
    try:
        year, month = month_key.split("-")
        return f"{THAI_MONTHS[int(month) - 1]} {int(year) + 543}"
    except (ValueError, IndexError):
        return month_key


def format_money(v):
    try:
        return f"{v:,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def open_file_external(path):
    """เปิดไฟล์หลักฐานด้วยโปรแกรมเริ่มต้นของเครื่อง (รองรับ Windows/Mac/Linux)"""
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: F821  (มีเฉพาะบน Windows)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
