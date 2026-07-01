import os
import sys
import threading
import tempfile
import shutil
from tkinter import Tk, filedialog
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.uix.modalview import ModalView
from kivy.animation import Animation
from kivy.graphics import Color, Line
from kivy.utils import get_color_from_hex

# Add the backend module to the Python path
sys.path.append(r"C:\Users\ninaw\Downloads\__pycache__\src\backend")
from automate_backend import AutomateBackend

# ======================
# Color and Window Setup
# ======================
PRIMARY_COLOR = get_color_from_hex("#6200EE")
ACCENT_COLOR = get_color_from_hex("#FF0266")
BACKGROUND_COLOR = get_color_from_hex("#FFFFFF")
TEXT_COLOR = get_color_from_hex("#000000")

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
# Loading Components
# ======================
class Spinner(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (100, 100)
        self._angle = 0
        Clock.schedule_interval(self.update, 0.05)

    def update(self, dt):
        self._angle += 10
        with self.canvas:
            self.canvas.clear()
            Color(*PRIMARY_COLOR)
            Line(circle=(self.center_x, self.center_y, 40, self._angle, self._angle + 70), width=2)

class LoadingPopup(ModalView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (300, 200)
        self.background = ''
        self.background_color = [0, 0, 0, 0]
        
        content = BoxLayout(orientation='vertical', spacing=10, padding=20)
        self.spinner = Spinner()
        self.progress_label = Label(text="0%", font_size=20, color=TEXT_COLOR)
        self.status_label = Label(text="Processing...", color=TEXT_COLOR)
        
        content.add_widget(self.spinner)
        content.add_widget(self.progress_label)
        content.add_widget(self.status_label)
        self.add_widget(content)

# ======================
# Main Application
# ======================
class AutomatePDFApp(App):
    def __init__(self, pdf_paths, **kwargs):
        super().__init__(**kwargs)
        self.pdf_paths = pdf_paths
        self.page_files = []
        self.processed_pdfs = []
        self.thumbnail_size = (160, 200)
        self.processed_dir = None
        self.is_processing = False  # Flag to track if processing is ongoing

    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Header
        header = BoxLayout(size_hint=(1, None), height=60)
        self.title_label = Label(
            text=f"Processing {len(self.pdf_paths)} PDF files", 
            color=TEXT_COLOR, font_size=20, bold=True
        )
        
        # Zoom controls
        zoom_controls = BoxLayout(size_hint=(None, None), size=(200, 60), spacing=10)
        zoom_in_btn = Button(text="Zoom In", size_hint=(None, None), size=(80, 40))
        zoom_in_btn.bind(on_press=self.zoom_in)
        zoom_out_btn = Button(text="Zoom Out", size_hint=(None, None), size=(80, 40))
        zoom_out_btn.bind(on_press=self.zoom_out)
        
        zoom_controls.add_widget(zoom_in_btn)
        zoom_controls.add_widget(zoom_out_btn)
        header.add_widget(self.title_label)
        header.add_widget(zoom_controls)
        self.layout.add_widget(header)

        # PDF Pages Grid
        self.scroll = ScrollView(size_hint=(1, 1))
        self.grid = GridLayout(cols=4, spacing=20, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scroll.add_widget(self.grid)
        self.layout.add_widget(self.scroll)

        # Control Buttons
        controls = BoxLayout(size_hint=(1, None), height=60, spacing=20)
        self.process_btn = AnimatedButton(text="Process PDF", background_color=ACCENT_COLOR)
        self.process_btn.bind(on_press=self.start_processing)
        self.save_btn = AnimatedButton(text="Save PDF", disabled=True)  # Disabled by default
        self.save_btn.bind(on_press=self.save_pdf)
        self.exit_btn = AnimatedButton(text="Exit")
        self.exit_btn.bind(on_press=self.exit_app)
        
        controls.add_widget(self.process_btn)
        controls.add_widget(self.save_btn)
        controls.add_widget(self.exit_btn)
        self.layout.add_widget(controls)

        self.load_pdf_pages()
        return self.layout

    def zoom_in(self, instance):
        self.thumbnail_size = (
            int(self.thumbnail_size[0] * 1.2),
            int(self.thumbnail_size[1] * 1.2)
        )
        self.reload_thumbnails()

    def zoom_out(self, instance):
        self.thumbnail_size = (
            max(100, int(self.thumbnail_size[0] * 0.8)),
            max(125, int(self.thumbnail_size[1] * 0.8))
        )
        self.reload_thumbnails()

    def reload_thumbnails(self):
        self.grid.clear_widgets()
        for page_path in self.page_files:
            thumbnail = AutomateBackend.generate_thumbnail(page_path, self.thumbnail_size)
            img = Image(
                source=thumbnail,
                size_hint=(None, None),
                size=self.thumbnail_size
            )
            self.grid.add_widget(img)

    def load_pdf_pages(self):
        self.grid.clear_widgets()
        self.page_files = []
        
        for pdf_path in self.pdf_paths:
            page_paths = AutomateBackend.split_pdf_into_pages(pdf_path)
            self.page_files.extend(page_paths)
            
            for page_path in page_paths:
                thumbnail = AutomateBackend.generate_thumbnail(page_path, self.thumbnail_size)
                img = Image(
                    source=thumbnail,
                    size_hint=(None, None),
                    size=self.thumbnail_size
                )
                self.grid.add_widget(img)
        
        self.title_label.text = f"Loaded {len(self.page_files)} pages from {len(self.pdf_paths)} PDFs"

    def start_processing(self, instance):
        if self.is_processing:
            return  # Prevent double-clicking

        self.is_processing = True
        self.process_btn.disabled = True  # Disable the "Process PDF" button
        self.save_btn.disabled = True  # Ensure "Save PDF" is disabled during processing

        self.loading_popup = LoadingPopup()
        self.loading_popup.open()
        self.processed_dir = tempfile.mkdtemp()
        threading.Thread(target=self.process_pdfs).start()

    def process_pdfs(self):
        try:
            for idx, page_path in enumerate(self.page_files):
                output_path = os.path.join(self.processed_dir, f"processed_page_{idx+1}.pdf")
                AutomateBackend.ocr_pdf_to_searchable_pdf(page_path, output_path)
                self.processed_pdfs.append(output_path)
                
                progress = (idx + 1) / len(self.page_files) * 100
                Clock.schedule_once(lambda dt, p=progress: self.update_progress(p))
            
            Clock.schedule_once(lambda dt: self.on_process_complete())
        except Exception as e:
            Clock.schedule_once(lambda dt, err=str(e): self.show_popup("Error", err))
        finally:
            Clock.schedule_once(lambda dt: self.loading_popup.dismiss())
            self.is_processing = False  # Reset processing flag

    def on_process_complete(self):
        self.show_popup("Success", "PDF processing completed. You can now save the PDF.")
        self.save_btn.disabled = False  # Enable the "Save PDF" button after processing

    def save_pdf(self, instance):
        # Hide the main Kivy window temporarily
        Window.hide()

        # Create a Tkinter root window (hidden)
        root = Tk()
        root.withdraw()  # Hide the root window

        # Open the native Windows save file dialog
        output_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            title="Save PDF As"
        )

        # Destroy the Tkinter root window
        root.destroy()

        # Show the Kivy window again
        Window.show()

        # If the user canceled the dialog, return
        if not output_path:
            return

        # Show loading popup and start saving
        self.loading_popup = LoadingPopup()
        self.loading_popup.open()
        threading.Thread(target=lambda: self.finalize_save(output_path)).start()

    def finalize_save(self, output_path):
        try:
            AutomateBackend.merge_pdfs(
                self.processed_pdfs,
                output_path,
                progress_callback=lambda p: Clock.schedule_once(lambda dt: self.update_progress(p))
            )
            Clock.schedule_once(lambda dt: self.on_save_complete(output_path))
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_popup("Error", str(e)))
        finally:
            Clock.schedule_once(lambda dt: self.loading_popup.dismiss())

    def update_progress(self, progress):
        self.loading_popup.progress_label.text = f"{progress:.2f}%"

    def on_save_complete(self, output_path):
        self.show_popup("Success", f"PDF saved successfully at:\n{output_path}")

    def exit_app(self, instance):
        AutomateBackend.cleanup_temp_files(self.page_files)
        if self.processed_dir and os.path.exists(self.processed_dir):
            shutil.rmtree(self.processed_dir)
        App.get_running_app().stop()

    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', spacing=10)
        message_label = Label(text=message, color=TEXT_COLOR)
        close_button = Button(text="Close", size_hint=(None, None), size=(100, 40))
        popup = Popup(title=title, content=content, size_hint=(0.6, 0.4))

        close_button.bind(on_release=popup.dismiss)
        content.add_widget(message_label)
        content.add_widget(close_button)
        popup.open()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_paths = sys.argv[1:]
        AutomatePDFApp(pdf_paths).run()
    else:
        print("Drag and drop PDF files onto the executable.")