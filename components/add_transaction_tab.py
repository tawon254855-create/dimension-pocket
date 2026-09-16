"""แท็บ 'บันทึกรายการ' — ฟอร์มเพิ่มรายรับ/รายจ่าย พร้อมตัวเลือกโครงการไทยช่วยไทย พลัส"""
import datetime

import flet as ft

from components.receipt_attach import ReceiptAttach
from constants import CARD_PADDING, CARD_RADIUS, EXPENSE_CATEGORIES, GOV_BUDGET_LIMIT, GOV_SHARE, INCOME_CATEGORIES
from db import compute_split, insert_transaction, total_gov_used
from utils import format_money


class AddTransactionTab(ft.Container):
    def __init__(self, page: ft.Page, on_saved=None):
        """on_saved: callback ที่จะถูกเรียกหลังบันทึกรายการสำเร็จ (ให้แท็บอื่น ๆ รีเฟรชข้อมูลตาม)"""
        self.on_saved = on_saved
        self.receipt_attach = ReceiptAttach(page)

        # ----- ฟิลด์พื้นฐานของฟอร์ม -----
        self.date_field = ft.TextField(
            label="วันที่ (ปปปป-ดด-วว)",
            value=datetime.date.today().isoformat(),
            width=220,
            on_change=lambda e: None,
        )
        self.date_picker = ft.DatePicker(
            first_date=datetime.datetime(2020, 1, 1),
            last_date=datetime.datetime(2035, 12, 31),
            current_date=datetime.datetime.now(),
            on_change=self._on_date_change,
        )
        date_button = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=lambda e: page.show_dialog(self.date_picker),
        )

        self.category_dd = ft.Dropdown(
            label="หมวดหมู่",
            width=260,
            options=[ft.DropdownOption(key=c, text=c) for c in EXPENSE_CATEGORIES],
        )
        self.note_field = ft.TextField(
            label="รายละเอียด / ชื่อร้าน (ถ้ามี)", width=320, on_change=lambda e: None
        )
        self.amount_field = ft.TextField(
            label="จำนวนเงิน (บาท)", width=220, keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._update_preview,
        )

        self.type_group = ft.RadioGroup(
            content=ft.Row([ft.Radio(value="income", label="รายรับ"), ft.Radio(value="expense", label="รายจ่าย")]),
            value="expense",
            on_change=self._on_type_change,
        )

        # ----- ตัวเลือกวิธีชำระเงิน / ไทยช่วยไทย พลัส -----
        self.normal_radio = ft.Radio(value="normal", label="จ่ายปกติ")
        self.thaihelp_radio = ft.Radio(value="thaihelp", label="จ่ายด้วย ไทยช่วยไทย พลัส")
        self.payment_group = ft.RadioGroup(
            content=ft.Column([self.normal_radio, self.thaihelp_radio], spacing=2),
            value="normal",
            on_change=self._update_preview,
        )
        self.budget_full_warning = ft.Text(
            "ใช้งบไทยช่วยไทย พลัส ของเดือนนี้ครบ 1,000 บาทแล้ว ตัวเลือกนี้จึงไม่แสดงให้เลือก "
            "(งบจะรีเซ็ตใหม่เมื่อขึ้นเดือนถัดไป)",
            color=ft.Colors.RED,
            italic=True,
            visible=False,
        )
        self.split_preview = ft.Text(color=ft.Colors.BLUE_700, weight=ft.FontWeight.W_600)

        self.payment_wrap = ft.Container(
            content=ft.Column(
                [
                    ft.Text("วิธีชำระเงิน", weight=ft.FontWeight.BOLD),
                    self.payment_group,
                    self.budget_full_warning,
                    self.split_preview,
                ],
                spacing=6,
            ),
            padding=CARD_PADDING,
            border_radius=CARD_RADIUS,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.GREY_200),
            visible=True,
        )

        self.form_status = ft.Text()
        save_button = ft.Button(content=ft.Text("บันทึกรายการ"), icon=ft.Icons.SAVE, on_click=self._save)

        form_card = ft.Container(
            content=ft.Column(
                [
                    self.type_group,
                    ft.Row([self.date_field, date_button]),
                    self.category_dd,
                    self.note_field,
                    self.amount_field,
                ],
                spacing=14,
            ),
            padding=CARD_PADDING,
            border_radius=CARD_RADIUS,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.GREY_200),
        )

        super().__init__(
            content=ft.Column(
                [
                    self.receipt_attach,
                    form_card,
                    self.payment_wrap,
                    ft.Row([save_button], alignment=ft.MainAxisAlignment.END),
                    self.form_status,
                ],
                spacing=16,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=16,
        )

    # ---------------- event handlers ----------------
    def _on_date_change(self, e):
        self.date_field.value = e.control.value.strftime("%Y-%m-%d")
        self.date_field.update()

    def _on_type_change(self, e):
        is_expense = self.type_group.value == "expense"
        self.category_dd.options = [
            ft.DropdownOption(key=c, text=c) for c in (EXPENSE_CATEGORIES if is_expense else INCOME_CATEGORIES)
        ]
        self.category_dd.value = None
        self.payment_wrap.visible = is_expense
        if is_expense:
            self.refresh_payment_options()
        self.split_preview.value = ""
        self.category_dd.update()
        self.payment_wrap.update()
        self.split_preview.update()

    def refresh_payment_options(self):
        """เรียกทุกครั้งที่งบประมาณอาจเปลี่ยน (บันทึก/ลบรายการจากแท็บใดก็ได้) เพื่อเปิด/ปิดตัวเลือกไทยช่วยไทย พลัส ให้ตรงกับงบที่เหลือจริง"""
        used = total_gov_used()
        remaining = max(0.0, GOV_BUDGET_LIMIT - used)
        available = remaining > 0
        self.thaihelp_radio.visible = available
        self.thaihelp_radio.disabled = not available
        self.thaihelp_radio.label = (
            f"จ่ายด้วย ไทยช่วยไทย พลัส (รัฐช่วย {int(GOV_SHARE * 100)}% • เหลืองบเดือนนี้ {format_money(remaining)} บ.)"
        )
        self.budget_full_warning.visible = not available
        if not available and self.payment_group.value == "thaihelp":
            self.payment_group.value = "normal"
        self.payment_group.update()
        self.budget_full_warning.update()

    def _update_preview(self, e=None):
        if self.payment_group.value == "thaihelp":
            try:
                amt = float(self.amount_field.value)
            except (TypeError, ValueError):
                amt = 0.0
            used = total_gov_used()
            gov_pay, user_pay, capped = compute_split(amt, used)
            txt = f"รัฐช่วยจ่าย {format_money(gov_pay)} บาท • จ่ายเอง {format_money(user_pay)} บาท"
            if capped:
                txt += " (งบไทยช่วยไทย พลัส เหลือไม่พอ 40% เต็ม จึงช่วยให้เท่านี้)"
            self.split_preview.value = txt
        else:
            self.split_preview.value = ""
        self.split_preview.update()

    def _save(self, e):
        errors = []
        if not self.category_dd.value:
            errors.append("กรุณาเลือกหมวดหมู่")
        amt = 0.0
        try:
            amt = float(self.amount_field.value)
            if amt <= 0:
                errors.append("จำนวนเงินต้องมากกว่า 0 บาท")
        except (TypeError, ValueError):
            errors.append("กรุณากรอกจำนวนเงินเป็นตัวเลข")
        if not self.date_field.value:
            errors.append("กรุณาระบุวันที่")

        if errors:
            self.form_status.value = " • ".join(errors)
            self.form_status.color = ft.Colors.RED
            self.form_status.update()
            return

        tx_type = self.type_group.value
        category = self.category_dd.value
        note = self.note_field.value or ""
        tx_date = self.date_field.value

        if tx_type == "expense" and self.payment_group.value == "thaihelp":
            used = total_gov_used()
            gov_pay, user_pay, _capped = compute_split(amt, used)
            payment_method = "thaihelp"
        elif tx_type == "expense":
            gov_pay, user_pay = 0.0, amt
            payment_method = "normal"
        else:
            gov_pay, user_pay = 0.0, 0.0
            payment_method = None

        insert_transaction(
            tx_date, tx_type, category, note, amt, payment_method, gov_pay, user_pay,
            self.receipt_attach.selected_path,
        )

        self.form_status.value = "บันทึกรายการเรียบร้อยแล้ว"
        self.form_status.color = ft.Colors.GREEN
        self.form_status.update()

        self.category_dd.value = None
        self.note_field.value = ""
        self.amount_field.value = ""
        self.payment_group.value = "normal"
        self.split_preview.value = ""
        self.category_dd.update()
        self.note_field.update()
        self.amount_field.update()
        self.payment_group.update()
        self.split_preview.update()
        self.receipt_attach.reset()

        if self.on_saved:
            self.on_saved()
