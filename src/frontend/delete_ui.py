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
from delete_backend import DeleteBackend

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
# Main Delete UI
# ======================
class DeletePDFApp(App):
    def __init__(self, pdf_path, **kwargs):
        super().__init__(**kwargs)
        self.pdf_path = pdf_path
        self.selected_pages = []  # Track selected pages for deletion
        self.deleted_pages = []  # Track paths of deleted pages to cleanup
        self.thumbnail_size = (160, 200)  # Default thumbnail size

    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Header
        header = BoxLayout(size_hint=(1, None), height=60)
        self.title_label = Label(text=f"Deleting Pages: {os.path.basename(self.pdf_path)}", 
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
        self.delete_btn = AnimatedButton(text="Delete Pages", background_color=ACCENT_COLOR)
        self.delete_btn.bind(on_press=self.delete_selected_pages)
        self.save_btn = AnimatedButton(text="Save PDF")
        self.save_btn.bind(on_press=self.save_modified_pdf)
        self.exit_btn = AnimatedButton(text="Exit")
        self.exit_btn.bind(on_press=self.exit_app)
        
        controls.add_widget(self.delete_btn)
        controls.add_widget(self.save_btn)
        controls.add_widget(self.exit_btn)
        self.layout.add_widget(controls)

        # Load PDF pages
        self.load_pdf_pages()
        return self.layout

    def load_pdf_pages(self):
        self.page_files = DeleteBackend.split_pdf_into_pages(self.pdf_path)
        for idx, page_path in enumerate(self.page_files):
            thumbnail = self.generate_thumbnail(page_path)
            img = Image(source=thumbnail, size_hint=(None, None), size=self.thumbnail_size)
            img.bind(on_touch_down=partial(self.select_page, idx))
            
            # Create a layout to hold the image and the label
            page_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=self.thumbnail_size)
            page_layout.add_widget(img)
            
            # Add the page number label
            page_label = Label(text=f"Page {idx + 1}", size_hint=(None, None), size=(self.thumbnail_size[0], 20), color=TEXT_COLOR)
            page_layout.add_widget(page_label)
            
            self.grid.add_widget(page_layout)

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
            if page_num in self.selected_pages:
                self.selected_pages.remove(page_num)
                instance.opacity = 1  # Reset opacity
            else:
                self.selected_pages.append(page_num)
                instance.opacity = 0.5  # Indicate selection
            self.title_label.text = f"Selected {len(self.selected_pages)} pages"

    def delete_selected_pages(self, instance):
        if not self.selected_pages:
            self.show_popup("Error", "No pages selected.")
            return

        # Sort in reverse order to avoid index shifting
        for page_num in sorted(self.selected_pages, reverse=True):
            # Remove from page_files and track deleted pages
            deleted_path = self.page_files.pop(page_num)
            self.deleted_pages.append(deleted_path)
            # Remove the thumbnail widget from grid
            for widget in self.grid.children:
                if isinstance(widget, BoxLayout):
                    for child in widget.children:
                        if isinstance(child, Image) and child.source == deleted_path.replace(".pdf", "_thumb.png"):
                            self.grid.remove_widget(widget)
                            break

        self.selected_pages = []
        self.title_label.text = f"Deleted {len(self.deleted_pages)} pages. Click Save to apply changes."

    def save_modified_pdf(self, instance):
        if not self.page_files:
            self.show_popup("Error", "No pages remaining to save.")
            return

        Tk().withdraw()
        output_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if output_path:
            DeleteBackend.merge_pages(self.page_files, output_path)
            self.show_popup("Success", f"PDF saved successfully at:\n{output_path}")

    def exit_app(self, instance):
        # Cleanup both remaining and deleted temporary files
        DeleteBackend.cleanup_temp_files(self.page_files + self.deleted_pages)
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
        for widget in self.grid.children:
            if isinstance(widget, BoxLayout):
                for child in widget.children:
                    if isinstance(child, Image):
                        child.size = self.thumbnail_size
                        child.reload()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        DeletePDFApp(sys.argv[1]).run()