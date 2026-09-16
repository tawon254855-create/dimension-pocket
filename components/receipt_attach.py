"""กล่องแนบไฟล์รูปใบเสร็จเก็บไว้เป็นหลักฐาน (ไม่บังคับ) — จัดการ FilePicker และสถานะไฟล์ที่เลือกในตัวเอง"""
import flet as ft

from constants import CARD_PADDING, CARD_RADIUS


class ReceiptAttach(ft.Container):
    def __init__(self, page: ft.Page):
        self.selected_path = None

        self._picker = ft.FilePicker()
        page.services.append(self._picker)

        self._file_name_text = ft.Text(size=13, weight=ft.FontWeight.BOLD)
        self._status_text = ft.Text(size=12)
        self._clear_button = ft.IconButton(
            icon=ft.Icons.CLOSE,
            tooltip="ลบไฟล์ที่แนบไว้",
            visible=False,
            on_click=self._clear,
        )
        attach_button = ft.Button(
            content=ft.Text("แนบรูปใบเสร็จ"),
            icon=ft.Icons.ATTACH_FILE,
            on_click=self._pick,
        )

        super().__init__(
            content=ft.Column(
                [
                    ft.Row(
                        [ft.Icon(ft.Icons.RECEIPT_LONG, color=ft.Colors.BLUE_600, size=20),
                         ft.Text("แนบรูปใบเสร็จเก็บไว้เป็นหลักฐาน (ไม่บังคับ)", size=14, weight=ft.FontWeight.BOLD)],
                        spacing=8,
                    ),
                    ft.Row([attach_button, self._file_name_text, self._clear_button]),
                    self._status_text,
                ],
                spacing=6,
            ),
            padding=CARD_PADDING,
            border_radius=CARD_RADIUS,
            bgcolor=ft.Colors.BLUE_50,
            border=ft.Border.all(1, ft.Colors.BLUE_100),
        )

    async def _pick(self, e):
        files = await self._picker.pick_files(
            dialog_title="เลือกไฟล์ใบเสร็จ",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["jpg", "jpeg", "png", "webp", "pdf"],
            allow_multiple=False,
        )
        if not files:
            return
        picked = files[0]
        if not picked.path:
            self._status_text.value = "ไม่พบตำแหน่งไฟล์จริงบนเครื่อง กรุณาลองเลือกไฟล์ใหม่อีกครั้ง"
            self._status_text.color = ft.Colors.RED
            self._status_text.update()
            return
        self.selected_path = picked.path
        self._file_name_text.value = picked.name
        self._status_text.value = "แนบไฟล์นี้ไว้แล้ว จะถูกบันทึกเป็นหลักฐานพร้อมรายการนี้เมื่อกด \"บันทึกรายการ\""
        self._status_text.color = ft.Colors.GREEN
        self._clear_button.visible = True
        self.update()

    def _clear(self, e=None):
        self.selected_path = None
        self._file_name_text.value = ""
        self._status_text.value = ""
        self._clear_button.visible = False
        self.update()

    def reset(self):
        """เรียกหลังบันทึกรายการสำเร็จ เพื่อล้างไฟล์ที่แนบไว้ก่อนกรอกรายการถัดไป"""
        self._clear()
