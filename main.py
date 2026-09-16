import datetime
import os
import sqlite3

import flet as ft

# ============================================================
#  ตั้งค่าโครงการ "ไทยช่วยไทย พลัส"  (ปรับตัวเลขที่นี่ได้ตามจริง)
# ============================================================
GOV_BUDGET_LIMIT = 1000.0       # งบที่รัฐให้ต่อคน/ต่อโครงการ (บาท)
GOV_SHARE = 0.60                # สัดส่วนที่ "รัฐ" ช่วยจ่าย (60%)
USER_SHARE = 1 - GOV_SHARE      # สัดส่วนที่ "จ่ายเอง" (40%)


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")

EXPENSE_CATEGORIES = ["อาหาร", "เดินทาง", "ของใช้ในบ้าน", "ค่าน้ำ/ค่าไฟ/บิล", "ช้อปปิ้ง", "สุขภาพ", "อื่นๆ"]
INCOME_CATEGORIES = ["เงินเดือน", "รายได้เสริม", "โอนเข้า", "อื่นๆ"]


# ============================================================
#  ชั้นข้อมูล (SQLite)
# ============================================================
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
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def insert_transaction(tx_date, tx_type, category, note, amount, payment_method, gov_pay, user_pay):
    conn = db_conn()
    conn.execute(
        """
        INSERT INTO transactions
            (tx_date, tx_type, category, note, amount, payment_method, gov_pay, user_pay, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (tx_date, tx_type, category, note, amount, payment_method, gov_pay, user_pay,
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
        SELECT id, tx_date, tx_type, category, note, amount, payment_method, gov_pay, user_pay
        FROM transactions
        ORDER BY tx_date DESC, id DESC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def total_gov_used():
    conn = db_conn()
    cur = conn.execute(
        "SELECT COALESCE(SUM(gov_pay), 0) FROM transactions WHERE payment_method = 'thaihelp'"
    )
    (total,) = cur.fetchone()
    conn.close()
    return total or 0.0


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


def format_money(v):
    try:
        return f"{v:,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def compute_monthly_summary():
    data = {}
    for (_id, tx_date, tx_type, category, note, amount, payment_method, gov_pay, user_pay) in fetch_all():
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


# ============================================================
#  UI
# ============================================================
def main(page: ft.Page):
    page.title = "รายรับ-รายจ่าย + ไทยช่วยไทย พลัส"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    init_db()

    # ---------- แถบสถานะงบประมาณ (แสดงบนสุดตลอด) ----------
    budget_bar = ft.ProgressBar(width=400, value=0)
    budget_text = ft.Text(weight=ft.FontWeight.BOLD)
    budget_banner = ft.Container(
        content=ft.Column(
            [
                ft.Text("งบประมาณโครงการ ไทยช่วยไทย พลัส", size=14, weight=ft.FontWeight.BOLD),
                budget_bar,
                budget_text,
            ],
            spacing=4,
        ),
        padding=12,
        border_radius=10,
        bgcolor=ft.Colors.AMBER_50,
        border=ft.Border.all(1, ft.Colors.AMBER_200),
    )

    def refresh_budget_banner():
        used = total_gov_used()
        remaining = max(0.0, GOV_BUDGET_LIMIT - used)
        budget_bar.value = min(1.0, used / GOV_BUDGET_LIMIT) if GOV_BUDGET_LIMIT else 0
        budget_bar.color = ft.Colors.RED if remaining <= 0 else ft.Colors.GREEN
        budget_text.value = (
            f"ใช้ไปแล้ว {format_money(used)} / {format_money(GOV_BUDGET_LIMIT)} บาท "
            f"(เหลือ {format_money(remaining)} บาท)"
        )
        budget_banner.update()

    # ================= แท็บ 1: บันทึกรายการ =================
    date_field = ft.TextField(label="วันที่ (YYYY-MM-DD)", value=datetime.date.today().isoformat(), width=220)

    def on_date_change(e):
        date_field.value = e.control.value.strftime("%Y-%m-%d")
        date_field.update()

    date_picker = ft.DatePicker(
        first_date=datetime.datetime(2020, 1, 1),
        last_date=datetime.datetime(2035, 12, 31),
        current_date=datetime.datetime.now(),
        on_change=on_date_change,
    )
    date_button = ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, on_click=lambda e: page.show_dialog(date_picker))

    category_dd = ft.Dropdown(
        label="หมวดหมู่",
        width=260,
        options=[ft.DropdownOption(key=c, text=c) for c in EXPENSE_CATEGORIES],
    )
    note_field = ft.TextField(label="รายละเอียด / ชื่อร้าน (ถ้ามี)", width=320)
    amount_field = ft.TextField(label="จำนวนเงิน (บาท)", width=220, keyboard_type=ft.KeyboardType.NUMBER)

    normal_radio = ft.Radio(value="normal", label="จ่ายปกติ")
    thaihelp_radio = ft.Radio(value="thaihelp", label="จ่ายด้วย ไทยช่วยไทย พลัส")
    payment_group = ft.RadioGroup(
        content=ft.Column([normal_radio, thaihelp_radio], spacing=2),
        value="normal",
    )
    budget_full_warning = ft.Text(
        "ใช้งบไทยช่วยไทย พลัส ครบ 1,000 บาทแล้ว ตัวเลือกนี้จึงไม่แสดงให้เลือก",
        color=ft.Colors.RED,
        italic=True,
        visible=False,
    )
    split_preview = ft.Text(color=ft.Colors.BLUE_700)

    payment_wrap = ft.Column(
        [
            ft.Text("วิธีชำระเงิน", weight=ft.FontWeight.BOLD),
            payment_group,
            budget_full_warning,
            split_preview,
        ],
        visible=True,
        spacing=4,
    )

    form_status = ft.Text()

    def rebuild_payment_options():
        used = total_gov_used()
        remaining = max(0.0, GOV_BUDGET_LIMIT - used)
        available = remaining > 0
        thaihelp_radio.visible = available
        thaihelp_radio.disabled = not available
        thaihelp_radio.label = (
            f"จ่ายด้วย ไทยช่วยไทย พลัส (รัฐช่วย {int(GOV_SHARE * 100)}% • เหลืองบ {format_money(remaining)} บ.)"
        )
        budget_full_warning.visible = not available
        if not available and payment_group.value == "thaihelp":
            payment_group.value = "normal"
        payment_group.update()
        budget_full_warning.update()

    def update_preview(e=None):
        if payment_group.value == "thaihelp":
            try:
                amt = float(amount_field.value)
            except (TypeError, ValueError):
                amt = 0.0
            used = total_gov_used()
            gov_pay, user_pay, capped = compute_split(amt, used)
            txt = f"รัฐช่วยจ่าย {format_money(gov_pay)} บาท • จ่ายเอง {format_money(user_pay)} บาท"
            if capped:
                txt += " (งบไทยช่วยไทย พลัส เหลือไม่พอ 40% เต็ม จึงช่วยให้เท่านี้)"
            split_preview.value = txt
        else:
            split_preview.value = ""
        split_preview.update()

    amount_field.on_change = update_preview
    payment_group.on_change = update_preview

    def on_type_change(e):
        is_expense = type_group.value == "expense"
        category_dd.options = [
            ft.DropdownOption(key=c, text=c) for c in (EXPENSE_CATEGORIES if is_expense else INCOME_CATEGORIES)
        ]
        category_dd.value = None
        payment_wrap.visible = is_expense
        if is_expense:
            rebuild_payment_options()
        split_preview.value = ""
        category_dd.update()
        payment_wrap.update()
        split_preview.update()

    type_group = ft.RadioGroup(
        content=ft.Row([ft.Radio(value="income", label="รายรับ"), ft.Radio(value="expense", label="รายจ่าย")]),
        value="expense",
        on_change=on_type_change,
    )

    def save_transaction(e):
        errors = []
        if not category_dd.value:
            errors.append("กรุณาเลือกหมวดหมู่")
        amt = 0.0
        try:
            amt = float(amount_field.value)
            if amt <= 0:
                errors.append("จำนวนเงินต้องมากกว่า 0 บาท")
        except (TypeError, ValueError):
            errors.append("กรุณากรอกจำนวนเงินเป็นตัวเลข")
        if not date_field.value:
            errors.append("กรุณาระบุวันที่")

        if errors:
            form_status.value = " • ".join(errors)
            form_status.color = ft.Colors.RED
            form_status.update()
            return

        tx_type = type_group.value
        category = category_dd.value
        note = note_field.value or ""
        tx_date = date_field.value

        if tx_type == "expense" and payment_group.value == "thaihelp":
            used = total_gov_used()
            gov_pay, user_pay, _capped = compute_split(amt, used)
            payment_method = "thaihelp"
        elif tx_type == "expense":
            gov_pay, user_pay = 0.0, amt
            payment_method = "normal"
        else:
            gov_pay, user_pay = 0.0, 0.0
            payment_method = None

        insert_transaction(tx_date, tx_type, category, note, amt, payment_method, gov_pay, user_pay)

        form_status.value = "บันทึกรายการเรียบร้อยแล้ว"
        form_status.color = ft.Colors.GREEN
        form_status.update()

        category_dd.value = None
        note_field.value = ""
        amount_field.value = ""
        payment_group.value = "normal"
        split_preview.value = ""
        category_dd.update()
        note_field.update()
        amount_field.update()
        payment_group.update()
        split_preview.update()

        refresh_all()

    save_button = ft.Button(content=ft.Text("บันทึกรายการ"), icon=ft.Icons.SAVE, on_click=save_transaction)

    add_tab_content = ft.Container(
        content=ft.Column(
            [
                ft.Row([date_field, date_button]),
                type_group,
                category_dd,
                note_field,
                amount_field,
                payment_wrap,
                save_button,
                form_status,
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=16,
    )

    # ================= แท็บ 2: รายการทั้งหมด =================
    history_table = ft.DataTable(
        columns=[
            ft.DataColumn(label=ft.Text("วันที่")),
            ft.DataColumn(label=ft.Text("ประเภท")),
            ft.DataColumn(label=ft.Text("หมวดหมู่")),
            ft.DataColumn(label=ft.Text("รายละเอียด")),
            ft.DataColumn(label=ft.Text("จำนวนเงิน")),
            ft.DataColumn(label=ft.Text("วิธีจ่าย")),
            ft.DataColumn(label=ft.Text("รัฐช่วย")),
            ft.DataColumn(label=ft.Text("จ่ายเอง")),
            ft.DataColumn(label=ft.Text("")),
        ],
        rows=[],
    )

    def refresh_history_table():
        rows = []
        for (tid, tx_date, tx_type, category, note, amount, payment_method, gov_pay, user_pay) in fetch_all():
            type_label = "รายรับ" if tx_type == "income" else "รายจ่าย"
            pay_label = "-" if not payment_method else ("ไทยช่วยไทย พลัส" if payment_method == "thaihelp" else "ปกติ")

            def make_delete_handler(row_id=tid):
                def handler(e):
                    delete_transaction(row_id)
                    refresh_all()

                return handler

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(tx_date)),
                        ft.DataCell(ft.Text(type_label)),
                        ft.DataCell(ft.Text(category or "-")),
                        ft.DataCell(ft.Text(note or "-")),
                        ft.DataCell(ft.Text(format_money(amount))),
                        ft.DataCell(ft.Text(pay_label)),
                        ft.DataCell(ft.Text(format_money(gov_pay) if gov_pay else "-")),
                        ft.DataCell(ft.Text(format_money(user_pay) if tx_type == "expense" else "-")),
                        ft.DataCell(ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED,
                                                   on_click=make_delete_handler())),
                    ]
                )
            )
        history_table.rows = rows
        history_table.update()

    history_tab_content = ft.Container(
        content=ft.Column([history_table], scroll=ft.ScrollMode.AUTO),
        padding=16,
    )

    # ================= แท็บ 3: สรุป / เปรียบเทียบ =================
    summary_table = ft.DataTable(
        columns=[
            ft.DataColumn(label=ft.Text("เดือน")),
            ft.DataColumn(label=ft.Text("รายรับ")),
            ft.DataColumn(label=ft.Text("รายจ่ายจริง (จ่ายเอง)")),
            ft.DataColumn(label=ft.Text("รัฐช่วย (บาท)")),
            ft.DataColumn(label=ft.Text("มีโครงการไทยช่วยไทยพลัส?")),
        ],
        rows=[],
    )

    comparison_text = ft.Text(size=14)

    bar_with_label = ft.Text("เดือนที่มีโครงการ")
    bar_with = ft.Container(height=22, bgcolor=ft.Colors.BLUE_400, border_radius=4, width=1)
    bar_without_label = ft.Text("เดือนที่ไม่มีโครงการ")
    bar_without = ft.Container(height=22, bgcolor=ft.Colors.GREY_500, border_radius=4, width=1)

    comparison_chart = ft.Column(
        [
            ft.Row([bar_with_label, bar_with]),
            ft.Row([bar_without_label, bar_without]),
        ],
        spacing=8,
    )

    def refresh_summary():
        monthly = compute_monthly_summary()
        rows = []
        with_scheme = []
        without_scheme = []
        for month, m in monthly.items():
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(month)),
                        ft.DataCell(ft.Text(format_money(m["income"]))),
                        ft.DataCell(ft.Text(format_money(m["expense_actual"]))),
                        ft.DataCell(ft.Text(format_money(m["gov_subsidy"]))),
                        ft.DataCell(ft.Text("มี" if m["used_scheme"] else "ไม่มี")),
                    ]
                )
            )
            (with_scheme if m["used_scheme"] else without_scheme).append(m["expense_actual"])
        summary_table.rows = rows
        summary_table.update()

        avg_with = sum(with_scheme) / len(with_scheme) if with_scheme else None
        avg_without = sum(without_scheme) / len(without_scheme) if without_scheme else None

        lines = []
        if avg_with is not None:
            lines.append(f"เฉลี่ยเดือนที่ใช้โครงการไทยช่วยไทย พลัส: {format_money(avg_with)} บาท/เดือน (จ่ายเองจริง)")
        if avg_without is not None:
            lines.append(f"เฉลี่ยเดือนที่ไม่ได้ใช้โครงการ: {format_money(avg_without)} บาท/เดือน")
        if avg_with is not None and avg_without is not None:
            diff = avg_without - avg_with
            if diff > 0.005:
                lines.append(f"เดือนที่มีโครงการช่วยประหยัดเงินได้เฉลี่ย {format_money(diff)} บาท/เดือน เทียบกับเดือนที่ไม่มีโครงการ")
            elif diff < -0.005:
                lines.append(f"เดือนที่มีโครงการกลับใช้จ่ายจริงมากกว่าเฉลี่ย {format_money(-diff)} บาท/เดือน เทียบกับเดือนที่ไม่มีโครงการ")
            else:
                lines.append("ค่าเฉลี่ยรายจ่ายจริงของทั้งสองกลุ่มเท่ากัน")
        if not lines:
            lines.append("ยังไม่มีข้อมูลเพียงพอสำหรับเปรียบเทียบ (ยังไม่มีรายการรายจ่าย)")
        comparison_text.value = "\n".join(lines)
        comparison_text.update()

        max_val = max(avg_with or 0, avg_without or 0, 1)
        bar_with.width = max(1, 300 * ((avg_with or 0) / max_val))
        bar_without.width = max(1, 300 * ((avg_without or 0) / max_val))
        bar_with.update()
        bar_without.update()

    summary_tab_content = ft.Container(
        content=ft.Column(
            [
                ft.Text("เปรียบเทียบรายจ่ายจริงต่อเดือน (มี vs ไม่มี ไทยช่วยไทย พลัส)", weight=ft.FontWeight.BOLD),
                comparison_chart,
                comparison_text,
                ft.Divider(),
                summary_table,
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=16,
    )

    # ================= รวม refresh ทั้งหมด =================
    def refresh_all():
        refresh_budget_banner()
        rebuild_payment_options()
        refresh_history_table()
        refresh_summary()

    # ================= โครงสร้างแท็บหลัก =================
    tabs_view = ft.Tabs(
        length=3,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="บันทึกรายการ", icon=ft.Icons.ADD_CIRCLE),
                        ft.Tab(label="รายการทั้งหมด", icon=ft.Icons.LIST),
                        ft.Tab(label="สรุป/เปรียบเทียบ", icon=ft.Icons.INSIGHTS),
                    ]
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[add_tab_content, history_tab_content, summary_tab_content],
                ),
            ],
        ),
    )

    page.add(
        ft.Text("รายรับ-รายจ่ายครัวเรือน + โครงการไทยช่วยไทย พลัส", size=22, weight=ft.FontWeight.BOLD),
        budget_banner,
        tabs_view,
    )

    refresh_all()


if hasattr(ft, "run"):
    ft.run(main)
else:  # เผื่อรันบน Flet เวอร์ชันเก่ากว่า 1.0
    ft.app(target=main)