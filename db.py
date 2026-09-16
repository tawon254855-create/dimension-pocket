"""
ชั้นข้อมูล (SQLite) + ตรรกะการคำนวณของโครงการ "ไทยช่วยไทย พลัส"
แยกออกมาจาก UI ทั้งหมด เพื่อให้ทดสอบ/แก้ไขตรรกะได้โดยไม่ต้องยุ่งกับหน้าจอ
"""
import datetime
import sqlite3

from constants import DB_PATH, GOV_BUDGET_LIMIT, GOV_SHARE


def db_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = db_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_date TEXT NOT NULL,
            tx_type TEXT NOT NULL,          -- 'income' | 'expense'
            category TEXT,
            note TEXT,
            amount REAL NOT NULL,
            payment_method TEXT,            -- 'normal' | 'thaihelp' | NULL (income)
            gov_pay REAL NOT NULL DEFAULT 0,
            user_pay REAL NOT NULL DEFAULT 0,
            receipt_path TEXT,              -- path ไฟล์รูปใบเสร็จที่แนบไว้เป็นหลักฐาน (ไม่บังคับ)
            created_at TEXT NOT NULL
        )
        """
    )
    # เผื่อฐานข้อมูลเดิมที่ยังไม่มีคอลัมน์ receipt_path (สร้างก่อนฟีเจอร์นี้จะถูกเพิ่ม)
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(transactions)").fetchall()}
    if "receipt_path" not in existing_cols:
        conn.execute("ALTER TABLE transactions ADD COLUMN receipt_path TEXT")
    conn.commit()
    conn.close()


def insert_transaction(tx_date, tx_type, category, note, amount, payment_method, gov_pay, user_pay,
                        receipt_path=None):
    conn = db_conn()
    conn.execute(
        """
        INSERT INTO transactions
            (tx_date, tx_type, category, note, amount, payment_method, gov_pay, user_pay, receipt_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (tx_date, tx_type, category, note, amount, payment_method, gov_pay, user_pay, receipt_path,
         datetime.datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def delete_transaction(tx_id):
    conn = db_conn()
    conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()


def fetch_all():
    conn = db_conn()
    cur = conn.execute(
        """
        SELECT id, tx_date, tx_type, category, note, amount, payment_method, gov_pay, user_pay, receipt_path
        FROM transactions
        ORDER BY tx_date DESC, id DESC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def total_gov_used(month_key=None):
    """ยอดที่รัฐช่วยจ่ายไปแล้ว "เฉพาะเดือนที่ระบุ" (ค่าเริ่มต้น = เดือนปัจจุบัน) งบจะรีเซ็ตใหม่ทุกเดือน"""
    from utils import current_month_key
    month_key = month_key or current_month_key()
    conn = db_conn()
    cur = conn.execute(
        """
        SELECT COALESCE(SUM(gov_pay), 0) FROM transactions
        WHERE payment_method = 'thaihelp' AND substr(tx_date, 1, 7) = ?
        """,
        (month_key,),
    )
    (total,) = cur.fetchone()
    conn.close()
    return total or 0.0


def distinct_months():
    """คืนค่ารายชื่อเดือน (YYYY-MM) ที่มีรายการอยู่จริง เรียงจากล่าสุดไปเก่าสุด สำหรับใช้ทำตัวกรอง"""
    conn = db_conn()
    cur = conn.execute(
        """
        SELECT DISTINCT substr(tx_date, 1, 7) AS m FROM transactions
        WHERE tx_date IS NOT NULL AND tx_date != ''
        ORDER BY m DESC
        """
    )
    months = [row[0] for row in cur.fetchall()]
    conn.close()
    return months


# ============================================================
#  ตรรกะการคำนวณ ไทยช่วยไทย พลัส
# ============================================================
def compute_split(amount, gov_used_so_far):
    """คืนค่า (รัฐช่วยจ่าย, จ่ายเอง, ถูกจำกัดงบหรือไม่)"""
    remaining = max(0.0, GOV_BUDGET_LIMIT - gov_used_so_far)
    ideal_gov = amount * GOV_SHARE
    gov_pay = min(ideal_gov, remaining)
    user_pay = amount - gov_pay
    capped = gov_pay + 1e-6 < ideal_gov
    return round(gov_pay, 2), round(user_pay, 2), capped


def compute_monthly_summary():
    data = {}
    for (_id, tx_date, tx_type, category, note, amount, payment_method, gov_pay, user_pay,
         _receipt_path) in fetch_all():
        month = (tx_date or "")[:7] or "ไม่ระบุ"
        m = data.setdefault(month, {"income": 0.0, "expense_actual": 0.0, "gov_subsidy": 0.0, "used_scheme": False})
        if tx_type == "income":
            m["income"] += amount
        else:
            actual = user_pay if payment_method == "thaihelp" else amount
            m["expense_actual"] += actual
            m["gov_subsidy"] += gov_pay
            if payment_method == "thaihelp":
                m["used_scheme"] = True
    return dict(sorted(data.items()))
