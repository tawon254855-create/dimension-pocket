"""การ์ดสถานะงบประมาณโครงการ ไทยช่วยไทย พลัส ของเดือนปัจจุบัน แสดงอยู่บนสุดของหน้าตลอด"""
import flet as ft

from constants import CARD_PADDING, CARD_RADIUS, COLOR_GOV, GOV_BUDGET_LIMIT
from db import total_gov_used
from utils import format_money, thai_month_label


class BudgetBanner(ft.Container):
    def __init__(self):
        self._icon = ft.Image(src="thaihelp_logo.png", width=32, height=32, fit="contain")
        self._title = ft.Text(weight=ft.FontWeight.BOLD, size=15)
        self._badge_text = ft.Text("0%", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self._badge = ft.Container(
            content=self._badge_text,
            bgcolor=COLOR_GOV,
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            border_radius=20,
        )
        self._bar = ft.ProgressBar(value=0, height=10, border_radius=6, bgcolor=ft.Colors.TEAL_50)
        self._detail = ft.Text(size=13, color=ft.Colors.GREY_700)

        header = ft.Row(
            [
                ft.Row([self._icon, self._title], spacing=8),
                self._badge,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        super().__init__(
            content=ft.Column([header, self._bar, self._detail], spacing=10),
            padding=CARD_PADDING,
            border_radius=CARD_RADIUS,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.TEAL_100),
            shadow=ft.BoxShadow(
                blur_radius=14,
                color=ft.Colors.with_opacity(0.06, ft.Colors.BLACK),
                offset=ft.Offset(0, 4),
            ),
        )

    def refresh(self):
        """เรียกใหม่ทุกครั้งที่มีรายการเปลี่ยนแปลง เพื่อดึงยอดใช้งบล่าสุดจากฐานข้อมูล"""
        used = total_gov_used()
        remaining = max(0.0, GOV_BUDGET_LIMIT - used)
        pct = min(1.0, used / GOV_BUDGET_LIMIT) if GOV_BUDGET_LIMIT else 0
        is_full = remaining <= 0
        color = ft.Colors.RED_400 if is_full else COLOR_GOV

        self._title.value = f"งบประมาณ ไทยช่วยไทย พลัส • ประจำเดือน{thai_month_label()}"
        self._bar.value = pct
        self._bar.color = color
        self._badge_text.value = f"{pct * 100:.0f}%"
        self._badge.bgcolor = color
        self._detail.value = (
            f"ใช้ไปแล้ว {format_money(used)} / {format_money(GOV_BUDGET_LIMIT)} บาท "
            f"(เหลือ {format_money(remaining)} บาท) • งบจะรีเซ็ตใหม่ทุกต้นเดือน"
        )
        self.update()
