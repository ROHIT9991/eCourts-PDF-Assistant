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
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, Rectangle
from kivy.properties import BooleanProperty, NumericProperty
from kivy.clock import Clock
from tkinter import Tk, filedialog
import fitz
from PIL import Image as PILImage
from functools import partial

# Add the backend module to the Python path
sys.path.append(r"C:\Users\ninaw\Downloads\__pycache__\src\backend")
from reorder_backend import ReorderBackend

# ======================
# Color and Window Setup
# ======================
PRIMARY_COLOR = get_color_from_hex("#6200EE")  # Purple
ACCENT_COLOR = get_color_from_hex("#FF0266")   # Pink
BACKGROUND_COLOR = get_color_from_hex("#FFFFFF")  # White
TEXT_COLOR = get_color_from_hex("#000000")     # Black
SELECTED_COLOR = get_color_from_hex("#FFD700") # Gold

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

# ======================
# Custom Widgets
# ======================
class ThumbnailWidget(FloatLayout):
    selected = BooleanProperty(False)
    index = NumericProperty(-1)  # Track the index of the thumbnail

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app  # Reference to the ReorderPDFApp instance
        self.size_hint = (None, None)
        with self.canvas.before:
            self.bg_color = Color(*BACKGROUND_COLOR)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            pos=self.update_rect,
            size=self.update_rect,
            selected=self.on_selected
        )

        # Add image and label
        self.img = Image(
            size_hint=(1, 0.85),
            pos_hint={'top': 1.0, 'x': 0}
        )
        self.add_widget(self.img)

        self.label = Label(
            text="Page",
            size_hint=(1, 0.15),
            pos_hint={'x': 0, 'y': 0},
            color=TEXT_COLOR
        )
        self.add_widget(self.label)

        # Arrow images
        self.arrows = {
            'up': Image(source=r'C:\Users\ninaw\Downloads\__pycache__\src\frontend\ARROWS\Screenshot 2025-03-08 224208.png', size_hint=(None, None)),
            'down': Image(source=r'C:\Users\ninaw\Downloads\__pycache__\src\frontend\ARROWS\Screenshot 2025-03-08 224129.png', size_hint=(None, None)),
            'left': Image(source=r'C:\Users\ninaw\Downloads\__pycache__\src\frontend\ARROWS\Screenshot 2025-03-08 224302.png', size_hint=(None, None)),
            'right': Image(source=r'C:\Users\ninaw\Downloads\__pycache__\src\frontend\ARROWS\Screenshot 2025-03-08 224111.png', size_hint=(None, None))
        }

        # Set arrow sizes
        for arrow in self.arrows.values():
            arrow.size = (40, 40)  # Adjust size as needed

        # Add arrows to the widget
        for arrow in self.arrows.values():
            self.add_widget(arrow)

        # Bind touch events to arrow images
        for direction, arrow in self.arrows.items():
            arrow.bind(on_touch_down=partial(self.on_arrow_touch_down, direction))

        # Hide arrows initially
        self.hide_arrows()

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_selected(self, instance, value):
        self.bg_color.rgba = SELECTED_COLOR if value else BACKGROUND_COLOR
        self.canvas.ask_update()

    def show_arrows(self):
        """Position and show arrow buttons"""
        self.update_arrow_positions()
        for arrow in self.arrows.values():
            arrow.opacity = 1
            arrow.disabled = False

    def hide_arrows(self):
        """Hide arrow buttons"""
        for arrow in self.arrows.values():
            arrow.opacity = 0
            arrow.disabled = True

    def update_arrow_positions(self):
        """Update arrow positions relative to the thumbnail"""
        thumbnail_width, thumbnail_height = self.size
        self.arrows['up'].pos = (self.x + thumbnail_width/2 - 20, self.y + thumbnail_height + 10)
        self.arrows['down'].pos = (self.x + thumbnail_width/2 - 20, self.y - 50)
        self.arrows['left'].pos = (self.x - 50, self.y + thumbnail_height/2 - 20)
        self.arrows['right'].pos = (self.x + thumbnail_width + 10, self.y + thumbnail_height/2 - 20)

    def on_arrow_touch_down(self, direction, instance, touch):
        """Handle arrow image clicks"""
        if instance.collide_point(*touch.pos):
            self.move_page(direction, self.index)
            return True
        return False

    def move_page(self, direction, idx, *args):
        """Move the page in the specified direction"""
        if self.app.selected_page is None:
            return

        current_idx = self.app.page_order.index(idx)
        new_idx = current_idx

        if direction == 'up' and current_idx >= self.app.cols:
            new_idx = current_idx - self.app.cols
        elif direction == 'down' and current_idx < len(self.app.page_order) - self.app.cols:
            new_idx = current_idx + self.app.cols
        elif direction == 'left' and current_idx % self.app.cols != 0:
            new_idx = current_idx - 1
        elif direction == 'right' and (current_idx + 1) % self.app.cols != 0 and current_idx < len(self.app.page_order) - 1:
            new_idx = current_idx + 1

        if 0 <= new_idx < len(self.app.page_order):
            # Reorder pages and refresh
            page = self.app.page_order.pop(current_idx)
            self.app.page_order.insert(new_idx, page)
            self.app.refresh_grid()

# ======================
# Main Application
# ======================
class ReorderPDFApp(App):
    def __init__(self, pdf_path, **kwargs):
        super().__init__(**kwargs)
        self.pdf_path = pdf_path
        self.backend = ReorderBackend(pdf_path)
        self.page_files = []
        self.thumbnail_size = (160, 200)
        self.selected_page = None  # Track the currently selected page
        self.page_order = []
        self.cols = 4
        self.thumbnail_layouts = {}

    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Header
        header = BoxLayout(size_hint=(1, None), height=60)
        self.title_label = Label(text=f"Reordering: {os.path.basename(self.pdf_path)}", 
                               color=TEXT_COLOR, font_size=20, bold=True)
        self.selected_pages_label = Label(text="Selected Page: None", 
                                        color=TEXT_COLOR, font_size=16, bold=True)
        zoom_controls = BoxLayout(size_hint=(None, None), size=(200, 60), spacing=10)
        zoom_in_btn = AnimatedButton(text="Zoom In", size=(80, 40))
        zoom_in_btn.bind(on_press=self.zoom_in)
        zoom_out_btn = AnimatedButton(text="Zoom Out", size=(80, 40))
        zoom_out_btn.bind(on_press=self.zoom_out)
        
        header.add_widget(self.title_label)
        header.add_widget(self.selected_pages_label)
        zoom_controls.add_widget(zoom_in_btn)
        zoom_controls.add_widget(zoom_out_btn)
        header.add_widget(zoom_controls)
        self.layout.add_widget(header)

        # PDF Pages Grid
        self.scroll = ScrollView(size_hint=(1, 1))
        self.grid = GridLayout(cols=self.cols, spacing=20, 
                              size_hint_y=None, size_hint_x=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.grid.bind(minimum_width=self.grid.setter('width'))
        self.scroll.add_widget(self.grid)
        self.layout.add_widget(self.scroll)

        # Action buttons
        action_controls = BoxLayout(size_hint=(1, None), height=60, spacing=20)
        self.save_btn = AnimatedButton(text="Save PDF", background_color=ACCENT_COLOR)
        self.save_btn.bind(on_press=self.save_reordered_pdf)
        self.exit_btn = AnimatedButton(text="Exit", background_color=ACCENT_COLOR)
        self.exit_btn.bind(on_press=self.exit_app)
        action_controls.add_widget(self.save_btn)
        action_controls.add_widget(self.exit_btn)
        self.layout.add_widget(action_controls)

        self.load_pdf_pages()
        return self.layout

    def load_pdf_pages(self):
        self.page_files = self.backend.split_pdf_into_pages()
        self.page_order = list(range(len(self.page_files)))
        
        for idx, page_path in enumerate(self.page_files):
            thumbnail_layout = ThumbnailWidget(app=self, size=self.thumbnail_size)
            thumbnail_layout.index = idx
            
            # Generate thumbnail
            thumbnail = self.generate_thumbnail(page_path)
            thumbnail_layout.img.source = thumbnail
            thumbnail_layout.label.text = f"Page {idx + 1}"
            
            # Bind touch event
            thumbnail_layout.bind(
                on_touch_down=partial(self.on_thumbnail_touch_down, idx)
            )
            
            self.grid.add_widget(thumbnail_layout)
            self.thumbnail_layouts[idx] = thumbnail_layout

    def generate_thumbnail(self, pdf_path):
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap()
        img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
        thumbnail_path = pdf_path.replace(".pdf", "_thumb.png")
        img.save(thumbnail_path)
        return thumbnail_path

    def on_thumbnail_touch_down(self, idx, instance, touch):
        if instance.collide_point(touch.x, touch.y):
            self.select_page(idx)
            return True
        return False

    def select_page(self, idx):
        if self.selected_page is not None:
            # Deselect the previously selected page
            self.thumbnail_layouts[self.selected_page].selected = False
            self.thumbnail_layouts[self.selected_page].hide_arrows()
        
        # Select the new page
        self.selected_page = idx
        self.thumbnail_layouts[idx].selected = True
        self.thumbnail_layouts[idx].show_arrows()
        self.selected_pages_label.text = f"Selected Page: {idx + 1}"

    def refresh_grid(self):
        """Refresh the grid layout"""
        self.grid.clear_widgets()
        for idx in self.page_order:
            self.grid.add_widget(self.thumbnail_layouts[idx])
        
        # Update arrow positions after layout
        if self.selected_page is not None:
            Clock.schedule_once(self.update_arrow_positions)

    def update_arrow_positions(self, *args):
        """Update arrow positions for the selected thumbnail"""
        if self.selected_page is not None:
            self.thumbnail_layouts[self.selected_page].update_arrow_positions()

    def save_reordered_pdf(self, instance):
        reordered_files = [self.page_files[i] for i in self.page_order]
        self.backend.temp_files = reordered_files
        
        Tk().withdraw()
        output_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if output_path:
            self.backend.merge_pages(output_path)
            self.show_popup("Success", f"PDF saved to:\n{output_path}")

    def exit_app(self, instance):
        self.backend.cleanup_temp_files()
        App.get_running_app().stop()

    def show_popup(self, title, message):
        Popup(title=title, 
            content=Label(text=message), 
            size_hint=(0.7, 0.3)).open()

    def zoom_in(self, instance):
        """Increase thumbnail size"""
        self.thumbnail_size = (
            min(300, self.thumbnail_size[0] + 20),  # Limit max width
            min(375, self.thumbnail_size[1] + 25)   # Limit max height
        )
        self.update_grid_layout()

    def zoom_out(self, instance):
        """Decrease thumbnail size"""
        self.thumbnail_size = (
            max(80, self.thumbnail_size[0] - 20),  # Limit min width
            max(100, self.thumbnail_size[1] - 25)  # Limit min height
        )
        self.update_grid_layout()

    def update_grid_layout(self):
        """Update the grid layout based on the current thumbnail size"""
        self.cols = max(1, int(Window.width / (self.thumbnail_size[0] + 20)))
        self.grid.cols = self.cols
        for thumb in self.thumbnail_layouts.values():
            thumb.size = self.thumbnail_size
        self.refresh_grid()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ReorderPDFApp(sys.argv[1]).run()