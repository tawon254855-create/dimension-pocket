"""แท็บ 'รายการทั้งหมด' — ตารางประวัติรายรับ/รายจ่าย กรองตามเดือน/วิธีจ่ายได้ ลบรายการและเปิดดูหลักฐานได้"""
import os

import flet as ft

from constants import CARD_PADDING, CARD_RADIUS
from db import delete_transaction, distinct_months, fetch_all
from utils import format_money, open_file_external, thai_month_label


class HistoryTab(ft.Container):
    def __init__(self, on_deleted=None):
        """on_deleted: callback ที่จะถูกเรียกหลังลบรายการ (ให้แท็บอื่น ๆ รีเฟรชข้อมูลตาม)"""
        self.on_deleted = on_deleted

        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(label=ft.Text("วันที่")),
                ft.DataColumn(label=ft.Text("ประเภท")),
                ft.DataColumn(label=ft.Text("หมวดหมู่")),
                ft.DataColumn(label=ft.Text("รายละเอียด")),
                ft.DataColumn(label=ft.Text("จำนวนเงิน")),
                ft.DataColumn(label=ft.Text("วิธีจ่าย")),
                ft.DataColumn(label=ft.Text("รัฐช่วย")),
                ft.DataColumn(label=ft.Text("จ่ายเอง")),
                ft.DataColumn(label=ft.Text("หลักฐาน")),
                ft.DataColumn(label=ft.Text("")),
            ],
            rows=[],
            heading_row_color=ft.Colors.GREY_100,
            border_radius=CARD_RADIUS,
        )
        self.status_text = ft.Text(size=12)

        self.month_filter_dd = ft.Dropdown(
            label="กรองตามเดือน",
            width=220,
            value="all",
            options=[ft.DropdownOption(key="all", text="ทุกเดือน")],
        )
        self.payment_filter_dd = ft.Dropdown(
            label="กรองตามวิธีจ่าย",
            width=240,
            value="all",
            options=[
                ft.DropdownOption(key="all", text="ทั้งหมด"),
                ft.DropdownOption(key="normal", text="จ่ายปกติ"),
                ft.DropdownOption(key="thaihelp", text="จ่ายด้วยไทยช่วยไทย พลัส"),
            ],
        )
        # หมายเหตุ: ft.Dropdown ใน Flet เวอร์ชันที่ติดตั้งจริง (0.86.5) ไม่มีฟิลด์ on_change
        # อีเวนต์ตอนเลือกค่าใหม่ของ Dropdown คือ on_select เท่านั้น ต้องใช้ชื่อนี้ค่าตัวกรองถึงจะ sync จริง
        self.month_filter_dd.on_select = self._on_filter_change
        self.payment_filter_dd.on_select = self._on_filter_change

        filter_card = ft.Container(
            content=ft.Row([self.month_filter_dd, self.payment_filter_dd], wrap=True),
            padding=CARD_PADDING,
            border_radius=CARD_RADIUS,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.GREY_200),
        )
        table_card = ft.Container(
            content=ft.Column([self.table, self.status_text], scroll=ft.ScrollMode.AUTO),
            padding=CARD_PADDING,
            border_radius=CARD_RADIUS,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.GREY_200),
        )

        super().__init__(
            content=ft.Column([filter_card, table_card], spacing=16, scroll=ft.ScrollMode.AUTO),
            padding=16,
        )

    def _on_filter_change(self, e=None):
        self.refresh()

    def _make_delete_handler(self, row_id):
        def handler(e):
            delete_transaction(row_id)
            self.refresh()
            if self.on_deleted:
                self.on_deleted()

        return handler

    def _make_view_receipt_handler(self, path):
        def handler(e):
            if not path or not os.path.exists(path):
                self.status_text.value = "ไม่พบไฟล์หลักฐานต้นฉบับแล้ว (อาจถูกย้ายหรือลบไปจากเครื่อง)"
                self.status_text.color = ft.Colors.RED
            else:
                try:
                    open_file_external(path)
                    self.status_text.value = ""
                except Exception as ex:
                    self.status_text.value = f"เปิดไฟล์ไม่สำเร็จ: {ex}"
                    self.status_text.color = ft.Colors.RED
            self.status_text.update()

        return handler

    def refresh(self):
        # อัปเดตตัวเลือกในดรอปดาวน์ "กรองตามเดือน" ให้ตรงกับเดือนที่มีข้อมูลจริง
        # (คงค่าที่เลือกไว้เดิมถ้ายังมีอยู่ ไม่งั้นรีเซ็ตเป็น "ทุกเดือน")
        prev_month_value = self.month_filter_dd.value
        self.month_filter_dd.options = [ft.DropdownOption(key="all", text="ทุกเดือน")] + [
            ft.DropdownOption(key=m, text=thai_month_label(m)) for m in distinct_months()
        ]
        valid_keys = {opt.key for opt in self.month_filter_dd.options}
        self.month_filter_dd.value = prev_month_value if prev_month_value in valid_keys else "all"
        self.month_filter_dd.update()

        selected_month = self.month_filter_dd.value or "all"
        selected_payment = self.payment_filter_dd.value or "all"

        rows = []
        for (tid, tx_date, tx_type, category, note, amount, payment_method, gov_pay, user_pay,
             receipt_path) in fetch_all():
            if selected_month != "all" and (tx_date or "")[:7] != selected_month:
                continue
            if selected_payment != "all" and payment_method != selected_payment:
                continue
            type_label = "รายรับ" if tx_type == "income" else "รายจ่าย"
            type_color = ft.Colors.GREEN_700 if tx_type == "income" else ft.Colors.RED_700
            pay_label = "-" if not payment_method else ("ไทยช่วยไทย พลัส" if payment_method == "thaihelp" else "ปกติ")

            receipt_cell = (
                ft.IconButton(
                    icon=ft.Icons.RECEIPT_LONG,
                    tooltip="เปิดดูไฟล์หลักฐาน",
                    on_click=self._make_view_receipt_handler(receipt_path),
                )
                if receipt_path
                else ft.Text("-")
            )

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(tx_date)),
                        ft.DataCell(ft.Text(type_label, color=type_color, weight=ft.FontWeight.W_600)),
                        ft.DataCell(ft.Text(category or "-")),
                        ft.DataCell(ft.Text(note or "-")),
                        ft.DataCell(ft.Text(format_money(amount))),
                        ft.DataCell(ft.Text(pay_label)),
                        ft.DataCell(ft.Text(format_money(gov_pay) if gov_pay else "-")),
                        ft.DataCell(ft.Text(format_money(user_pay) if tx_type == "expense" else "-")),
                        ft.DataCell(receipt_cell),
                        ft.DataCell(ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED,
                                                   on_click=self._make_delete_handler(tid))),
                    ]
                )
            )

        self.table.rows = rows
        self.table.update()
        if not rows:
            self.status_text.value = "ยังไม่มีรายการที่ตรงกับตัวกรองนี้"
            self.status_text.color = ft.Colors.GREY_600
            self.status_text.update()
