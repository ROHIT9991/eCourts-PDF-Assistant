import os
import sys
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.animation import Animation
from tkinter import Tk, filedialog
import fitz
from PIL import Image as PILImage
from functools import partial

# Add backend to path
sys.path.append(r"C:\Users\ninaw\Downloads\__pycache__\src\backend")
from rotate_backend import RotateBackend

# ======================
# Color and Window Setup
# ======================
PRIMARY_COLOR = get_color_from_hex("#6200EE")  # Purple
ACCENT_COLOR = get_color_from_hex("#FF0266")  # Pink
BACKGROUND_COLOR = get_color_from_hex("#FFFFFF")  # White
TEXT_COLOR = get_color_from_hex("#000000")  # Black

Window.size = (800, 600)
Window.clearcolor = BACKGROUND_COLOR

# ======================
# Custom Animated Button
# ======================
class AnimatedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_color = PRIMARY_COLOR
        self.color = BACKGROUND_COLOR
        self.font_size = 16
        self.bold = True
        self.size_hint = (None, None)
        self.size = (120, 50)
        self.bind(on_press=self.animate_button)

    def animate_button(self, instance):
        anim = Animation(opacity=0.7, duration=0.1) + Animation(opacity=1, duration=0.1)
        anim.start(instance)

# ======================
# Main Rotate UI
# ======================
class RotatePDFApp(App):
    def __init__(self, pdf_path, **kwargs):
        super().__init__(**kwargs)
        self.pdf_path = pdf_path
        self.selected_page = None
        self.rotations = {}  # Store rotation angles for each page
        self.thumbnail_size = (160, 200)  # Default thumbnail size

    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Header
        header = BoxLayout(size_hint=(1, None), height=60)
        self.title_label = Label(text=f"Rotating: {os.path.basename(self.pdf_path)}", 
                               color=TEXT_COLOR, font_size=20, bold=True)
        header.add_widget(self.title_label)

        # Zoom buttons
        controls = BoxLayout(size_hint=(None, None), size=(200, 60), spacing=10)
        zoom_in_btn = Button(text="Zoom In", size_hint=(None, None), size=(80, 40))
        zoom_in_btn.bind(on_press=self.zoom_in)
        zoom_out_btn = Button(text="Zoom Out", size_hint=(None, None), size=(80, 40))
        zoom_out_btn.bind(on_press=self.zoom_out)
        controls.add_widget(zoom_in_btn)
        controls.add_widget(zoom_out_btn)
        header.add_widget(controls)

        self.layout.add_widget(header)

        # PDF Pages Grid
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=True)
        self.grid = GridLayout(cols=4, spacing=20, size_hint_y=None, size_hint_x=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.grid.bind(minimum_width=self.grid.setter('width'))
        self.scroll.add_widget(self.grid)
        self.layout.add_widget(self.scroll)

        # Control Buttons
        controls = BoxLayout(size_hint=(1, None), height=60, spacing=20)
        self.rotate_btn = AnimatedButton(text="Rotate Page", background_color=ACCENT_COLOR)
        self.rotate_btn.bind(on_press=self.rotate_current_page)
        self.save_btn = AnimatedButton(text="Save PDF")
        self.save_btn.bind(on_press=self.save_rotated_pdf)
        self.exit_btn = AnimatedButton(text="Exit")
        self.exit_btn.bind(on_press=self.exit_app)
        
        controls.add_widget(self.rotate_btn)
        controls.add_widget(self.save_btn)
        controls.add_widget(self.exit_btn)
        self.layout.add_widget(controls)

        # Load PDF pages
        self.load_pdf_pages()
        return self.layout

    def load_pdf_pages(self):
        self.page_files = RotateBackend.split_pdf_into_pages(self.pdf_path)
        for idx, page_path in enumerate(self.page_files):
            thumbnail = self.generate_thumbnail(page_path)
            img = Image(source=thumbnail, size_hint=(None, None), size=self.thumbnail_size)
            img.bind(on_touch_down=partial(self.select_page, idx))
            self.grid.add_widget(img)

    def generate_thumbnail(self, pdf_path):
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap()
        img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
        thumbnail_path = pdf_path.replace(".pdf", "_thumb.png")
        img.save(thumbnail_path)
        return thumbnail_path

    def select_page(self, page_num, instance, touch):
        if instance.collide_point(*touch.pos):
            self.selected_page = page_num
            self.title_label.text = f"Selected Page: {page_num + 1}"

    def rotate_current_page(self, instance):
        if self.selected_page is not None:
            current_rotation = self.rotations.get(self.selected_page, 0)
            new_rotation = (current_rotation + 90) % 360
            self.rotations[self.selected_page] = new_rotation
            RotateBackend.rotate_page(self.page_files[self.selected_page], new_rotation)
            self.update_thumbnail(self.selected_page)

    def update_thumbnail(self, page_num):
        thumbnail = self.generate_thumbnail(self.page_files[page_num])
        total_pages = len(self.page_files)
        index = total_pages - 1 - page_num
        self.grid.children[index].source = thumbnail
        self.grid.children[index].reload()

    def save_rotated_pdf(self, instance):
        Tk().withdraw()
        output_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if output_path:
            RotateBackend.merge_pages(self.page_files, output_path)
            self.show_popup("Success", f"PDF saved successfully at:\n{output_path}")

    def exit_app(self, instance):
        RotateBackend.cleanup_temp_files(self.page_files)
        App.get_running_app().stop()

    def show_popup(self, title, message):
        Popup(title=title, content=Label(text=message), size_hint=(0.7, 0.3)).open()

    def zoom_in(self, instance):
        self.thumbnail_size = (self.thumbnail_size[0] + 20, self.thumbnail_size[1] + 25)
        self.reload_thumbnails()

    def zoom_out(self, instance):
        self.thumbnail_size = (max(80, self.thumbnail_size[0] - 20), max(100, self.thumbnail_size[1] - 25))
        self.reload_thumbnails()

    def reload_thumbnails(self):
        for idx, img in enumerate(self.grid.children):
            img.size = self.thumbnail_size
            img.reload()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        RotatePDFApp(sys.argv[1]).run()