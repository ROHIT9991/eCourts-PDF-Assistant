import os
import sys
import subprocess
import logging
import tempfile
import fitz  # PyMuPDF
from PIL import Image as PILImage
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
from kivy.animation import Animation
from tkinter import Tk, filedialog

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Backend configuration
BACKEND_PATH = r"C:\Users\ninaw\Downloads\__pycache__\src\frontend"
sys.path.append(BACKEND_PATH)  # Add backend to Python path

# Color scheme
PRIMARY_COLOR = get_color_from_hex("#6200EE")
SECONDARY_COLOR = get_color_from_hex("#03DAC6")
ACCENT_COLOR = get_color_from_hex("#FF0266")
BACKGROUND_COLOR = get_color_from_hex("#FFFFFF")
TEXT_COLOR = get_color_from_hex("#000000")

class AnimatedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_color = PRIMARY_COLOR
        self.color = BACKGROUND_COLOR
        self.font_size = 18
        self.bold = True
        self.size_hint = (1, None)
        self.height = 50
        self.bind(on_press=self.animate_button)

    def animate_button(self, instance):
        anim = Animation(opacity=0.7, duration=0.05) + Animation(opacity=1, duration=0.05)
        anim.start(instance)

class PDFEditorApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_files = []
        self.thumbnail_dir = tempfile.mkdtemp(prefix="pdf_thumbnails_")
        self.tk_root = Tk()
        self.tk_root.withdraw()

    def build(self):
        Window.size = (800, 600)
        Window.clearcolor = BACKGROUND_COLOR
        
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Status label
        self.status_label = Label(
            text="PDF Editor Pro",
            size_hint=(1, 0.1),
            color=TEXT_COLOR,
            font_size=24,
            bold=True,
            halign='center'
        )
        self.layout.add_widget(self.status_label)

        # File selection button
        self.choose_file_button = AnimatedButton(text="Choose PDF Files")
        self.choose_file_button.bind(on_press=self.show_file_chooser)
        self.layout.add_widget(self.choose_file_button)

        # PDF thumbnails scroll view
        self.scroll_view = ScrollView(size_hint=(1, 1))
        self.pdf_container = GridLayout(cols=3, size_hint_y=None, spacing=20)
        self.pdf_container.bind(minimum_height=self.pdf_container.setter('height'))
        self.scroll_view.add_widget(self.pdf_container)
        self.layout.add_widget(self.scroll_view)

        # Action buttons
        self.create_action_buttons()
        
        Window.bind(on_resize=self.update_grid_columns)
        return self.layout

    def create_action_buttons(self):
        """Create and arrange action buttons"""
        action_grid = GridLayout(cols=2, spacing=15, size_hint=(1, None), height=120)
        
        # Left column
        left_col = BoxLayout(orientation='vertical', spacing=10)
        reorder_button = AnimatedButton(text="Reorder PDF")
        reorder_button.bind(on_press=self.reorder_pdf)
        left_col.add_widget(reorder_button)

        automate_button = AnimatedButton(text="Automate Tasks", background_color=SECONDARY_COLOR)
        automate_button.bind(on_press=self.automate_task)
        left_col.add_widget(automate_button)

        # Right column
        right_col = BoxLayout(orientation='vertical', spacing=10)
        delete_button = AnimatedButton(text="Delete Pages", background_color=ACCENT_COLOR)
        delete_button.bind(on_press=self.open_delete_ui)
        right_col.add_widget(delete_button)

        rotate_button = AnimatedButton(text="Rotate PDF")
        rotate_button.bind(on_press=self.rotate_pdf)
        right_col.add_widget(rotate_button)

        action_grid.add_widget(left_col)
        action_grid.add_widget(right_col)
        self.layout.add_widget(action_grid)

    def show_file_chooser(self, instance):
        """Handle PDF file selection with accumulation"""
        file_paths = filedialog.askopenfilenames(
            title="Select PDF Files",
            filetypes=[("PDF Files", "*.pdf")]
        )
        
        if file_paths:
            new_files = [f for f in file_paths if f not in self.selected_files]
            self.selected_files.extend(new_files)
            self.update_selected_files()
            self.status_label.text = f"Loaded {len(self.selected_files)} PDF files (accumulated)"

    def generate_thumbnail(self, pdf_path):
        """Generate thumbnail from first page of PDF"""
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(0)
            pix = page.get_pixmap()
            img_path = os.path.join(self.thumbnail_dir, f"thumb_{os.path.basename(pdf_path)}.png")
            
            # Convert to PIL Image for format conversion
            pil_image = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
            pil_image.save(img_path, "PNG")
            return img_path
        except Exception as e:
            logging.error(f"Thumbnail generation failed: {e}")
            return None

    def update_selected_files(self):
        """Update UI with selected PDF thumbnails"""
        self.pdf_container.clear_widgets()
        
        for file in self.selected_files:
            thumbnail_path = self.generate_thumbnail(file)
            if thumbnail_path:
                self.add_pdf_thumbnail(file, thumbnail_path)

    def add_pdf_thumbnail(self, pdf_path, thumbnail_path):
        """Add a PDF thumbnail to the container with a 'Back' button"""
        # Create a FloatLayout to overlay the thumbnail and the "Back" button
        thumbnail_layout = FloatLayout(size_hint=(None, None), size=(220, 300))

        # Add the thumbnail image
        thumbnail = Image(
            source=thumbnail_path,
            size_hint=(None, None),
            size=(200, 250),
            pos_hint={'center_x': 0.5, 'center_y': 0.6}
        )
        thumbnail_layout.add_widget(thumbnail)

        # Add the filename label
        filename = Label(
            text=os.path.basename(pdf_path),
            size_hint=(None, None),
            size=(200, 30),
            color=TEXT_COLOR,
            font_size=14,
            halign='center',
            pos_hint={'center_x': 0.5, 'center_y': 0.1}
        )
        thumbnail_layout.add_widget(filename)

        # Add the "Back" button (small "X" button)
        back_button = Button(
            text="X",
            size_hint=(None, None),
            size=(30, 30),
            background_color=ACCENT_COLOR,
            color=BACKGROUND_COLOR,
            bold=True,
            pos_hint={'right': 1, 'top': 1}
        )
        back_button.bind(on_press=lambda instance: self.remove_file(pdf_path))
        thumbnail_layout.add_widget(back_button)

        self.pdf_container.add_widget(thumbnail_layout)

    def remove_file(self, pdf_path):
        """Remove a specific file from the selected files"""
        if pdf_path in self.selected_files:
            self.selected_files.remove(pdf_path)
            self.update_selected_files()
            self.status_label.text = f"Removed file. {len(self.selected_files)} files remaining."

    def get_backend_script(self, script_name):
        """Get full path to backend script"""
        return os.path.join(BACKEND_PATH, script_name)

    def reorder_pdf(self, instance):
        """Handle PDF reordering"""
        if not self.selected_files:
            self.show_message("Error", "No PDF files selected!")
            return
            
        try:
            subprocess.Popen([
                sys.executable,
                self.get_backend_script("reorder_ui.py"),
                *self.selected_files
            ])
            self.status_label.text = f"Reordering {len(self.selected_files)} PDFs"
        except Exception as e:
            self.show_message("Error", f"Failed to reorder PDFs: {str(e)}")

    def rotate_pdf(self, instance):
        """Handle PDF rotation"""
        if not self.selected_files:
            self.show_message("Error", "No PDF selected!")
            return
            
        try:
            subprocess.Popen([
                sys.executable,
                self.get_backend_script("rotate_ui.py"),
                self.selected_files[0]
            ])
            self.status_label.text = f"Rotating: {os.path.basename(self.selected_files[0])}"
        except Exception as e:
            self.show_message("Error", f"Failed to rotate PDF: {str(e)}")

    def open_delete_ui(self, instance):
        """Open Delete Pages interface"""
        if not self.selected_files:
            self.show_message("Error", "Please select a PDF file first!")
            return
            
        if len(self.selected_files) > 1:
            self.show_message("Error", "Select only one PDF for deletion!")
            return

        try:
            subprocess.Popen([
                sys.executable,
                self.get_backend_script("delete_ui.py"),
                self.selected_files[0]
            ])
            self.status_label.text = f"Deleting pages in: {os.path.basename(self.selected_files[0])}"
        except Exception as e:
            self.show_message("Error", f"Failed to delete pages: {str(e)}")

    def automate_task(self, instance):
        """Handle automation workflow"""
        if not self.selected_files:
            self.show_message("Error", "No PDF files selected!")
            return

        try:
            subprocess.Popen([
                sys.executable,
                self.get_backend_script("automate_ui.py"),
                *self.selected_files
            ])
            self.status_label.text = f"Processing: {os.path.basename(self.selected_files[0])}"
        except Exception as e:
            self.show_message("Error", f"Failed to automate tasks: {str(e)}")

    def show_message(self, title, message):
        """Show popup messages"""
        Popup(
            title=title,
            content=Label(text=message),
            size_hint=(0.8, 0.4)
        ).open()

    def update_grid_columns(self, window, width, height):
        """Responsive grid layout"""
        self.pdf_container.cols = max(1, int(width / 250))

    def on_stop(self):
        """Cleanup thumbnails when app closes"""
        try:
            for f in os.listdir(self.thumbnail_dir):
                os.remove(os.path.join(self.thumbnail_dir, f))
            os.rmdir(self.thumbnail_dir)
        except Exception as e:
            logging.error(f"Error cleaning thumbnails: {e}")

if __name__ == "__main__":
    PDFEditorApp().run()