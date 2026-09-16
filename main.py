"""
รายรับ-รายจ่ายครัวเรือน + โครงการ "ไทยช่วยไทย พลัส"

จุดเริ่มต้นของแอป — ทำหน้าที่แค่ "ประกอบร่าง" หน้าจอจาก component ต่าง ๆ
และผูกกลไก refresh_all() ที่ทุก component เรียกใช้ร่วมกันเมื่อข้อมูลเปลี่ยน
ตรรกะจริงของแต่ละส่วนอยู่ใน constants.py / utils.py / db.py / components/*.py
"""
import flet as ft

from components.add_transaction_tab import AddTransactionTab
from components.budget_banner import BudgetBanner
from components.history_tab import HistoryTab
from components.summary_tab import SummaryTab
from constants import PAGE_BG, SEED_COLOR
from db import init_db


def main(page: ft.Page):
    page.title = "รายรับ-รายจ่าย + ไทยช่วยไทย พลัส"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=SEED_COLOR)
    page.bgcolor = PAGE_BG
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    init_db()

    # ----- ประกอบ component หลักแต่ละชิ้น -----
    budget_banner = BudgetBanner()
    add_tab = AddTransactionTab(page, on_saved=lambda: refresh_all())
    history_tab = HistoryTab(on_deleted=lambda: refresh_all())
    summary_tab = SummaryTab()

    def refresh_all():
        """เรียกทุกครั้งที่ข้อมูลเปลี่ยน (บันทึก/ลบรายการ) เพื่อให้ทุก component แสดงผลตรงกัน"""
        budget_banner.refresh()
        add_tab.refresh_payment_options()
        history_tab.refresh()
        summary_tab.refresh()

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
                    controls=[add_tab, history_tab, summary_tab],
                ),
            ],
        ),
    )

    header = ft.Container(
        content=ft.Row(
            [
                ft.Image(src="thaihelp_logo.png", width=40, height=40, fit="contain"),
                ft.Column(
                    [
                        ft.Text("รายรับ-รายจ่ายครัวเรือน", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text("โครงการไทยช่วยไทย พลัส", size=13,
                                color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE)),
                    ],
                    spacing=2,
                ),
            ],
            spacing=12,
        ),
        padding=ft.Padding.symmetric(horizontal=24, vertical=18),
        bgcolor=SEED_COLOR,
    )

    body = ft.Container(
        content=ft.Column([budget_banner, tabs_view], spacing=16, expand=True),
        padding=20,
        expand=True,
    )

    page.add(ft.Column([header, body], spacing=0, expand=True))

    refresh_all()


if hasattr(ft, "run"):
    ft.run(main, assets_dir="assets")
else:  # เผื่อรันบน Flet เวอร์ชันเก่ากว่า 1.0
    ft.app(target=main, assets_dir="assets")
