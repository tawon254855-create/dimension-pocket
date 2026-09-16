"""แท็บ 'สรุป/เปรียบเทียบ' — เปรียบเทียบรายจ่ายจริงต่อเดือน ระหว่างเดือนที่มี/ไม่มีโครงการไทยช่วยไทย พลัส"""
import flet as ft

from constants import CARD_PADDING, CARD_RADIUS, COLOR_GOV
from db import compute_monthly_summary
from utils import format_money

BAR_MAX_WIDTH = 320
COLOR_WITHOUT_SCHEME = ft.Colors.GREY_400


class SummaryTab(ft.Container):
    def __init__(self):
        self.summary_table = ft.DataTable(
            columns=[
                ft.DataColumn(label=ft.Text("เดือน")),
                ft.DataColumn(label=ft.Text("รายรับ")),
                ft.DataColumn(label=ft.Text("รายจ่ายจริง (จ่ายเอง)")),
                ft.DataColumn(label=ft.Text("รัฐช่วย (บาท)")),
                ft.DataColumn(label=ft.Text("มีโครงการไทยช่วยไทยพลัส?")),
            ],
            rows=[],
            heading_row_color=ft.Colors.GREY_100,
        )
        self.comparison_text = ft.Text(size=14)

        self._bar_with_value = ft.Text(size=12, weight=ft.FontWeight.BOLD, color=COLOR_GOV)
        self._bar_with = ft.Container(height=22, bgcolor=COLOR_GOV, border_radius=6, width=1)
        self._bar_without_value = ft.Text(size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700)
        self._bar_without = ft.Container(height=22, bgcolor=COLOR_WITHOUT_SCHEME, border_radius=6, width=1)

        chart_card = ft.Container(
            content=ft.Column(
                [
                    ft.Text("เปรียบเทียบรายจ่ายจริงต่อเดือน (มี vs ไม่มี ไทยช่วยไทย พลัส)",
                            weight=ft.FontWeight.BOLD, size=15),
                    ft.Column(
                        [
                            ft.Row([ft.Container(width=140, content=ft.Text("เดือนที่มีโครงการ")),
                                    self._bar_with, self._bar_with_value]),
                            ft.Row([ft.Container(width=140, content=ft.Text("เดือนที่ไม่มีโครงการ")),
                                    self._bar_without, self._bar_without_value]),
                        ],
                        spacing=10,
                    ),
                    self.comparison_text,
                ],
                spacing=14,
            ),
            padding=CARD_PADDING,
            border_radius=CARD_RADIUS,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.GREY_200),
        )

        table_card = ft.Container(
            content=ft.Column([
                ft.Text("รายเดือนทั้งหมด", weight=ft.FontWeight.BOLD, size=15),
                self.summary_table,
            ], spacing=10, scroll=ft.ScrollMode.AUTO),
            padding=CARD_PADDING,
            border_radius=CARD_RADIUS,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.GREY_200),
        )

        super().__init__(
            content=ft.Column([chart_card, table_card], spacing=16, scroll=ft.ScrollMode.AUTO),
            padding=16,
        )

    def refresh(self):
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
        self.summary_table.rows = rows
        self.summary_table.update()

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
        self.comparison_text.value = "\n".join(lines)
        self.comparison_text.update()

        max_val = max(avg_with or 0, avg_without or 0, 1)
        self._bar_with.width = max(1, BAR_MAX_WIDTH * ((avg_with or 0) / max_val))
        self._bar_without.width = max(1, BAR_MAX_WIDTH * ((avg_without or 0) / max_val))
        self._bar_with_value.value = format_money(avg_with) + " บ." if avg_with is not None else "-"
        self._bar_without_value.value = format_money(avg_without) + " บ." if avg_without is not None else "-"
        self._bar_with.update()
        self._bar_without.update()
        self._bar_with_value.update()
        self._bar_without_value.update()
