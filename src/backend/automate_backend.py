import fitz  # PyMuPDF
from PIL import Image
import subprocess
import os
import tempfile
import shutil
import logging
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Custom path to Tesseract-OCR executable
TESSERACT_PATH = r"C:\Users\ninaw\Downloads\__pycache__\Tesseract-OCR\tesseract.exe"

class AutomateBackend:
    @staticmethod
    def split_pdf_into_pages(pdf_path):
        """Splits a PDF into individual page PDFs."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        temp_dir = tempfile.mkdtemp()
        page_files = []

        try:
            with fitz.open(pdf_path) as doc:
                for i in range(len(doc)):
                    page_path = os.path.join(temp_dir, f"page_{i+1}.pdf")
                    subdoc = fitz.open()
                    subdoc.insert_pdf(doc, from_page=i, to_page=i)
                    subdoc.save(page_path)
                    page_files.append(page_path)
                    subdoc.close()
        except Exception as e:
            logging.error(f"Error splitting PDF: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

        return page_files

    @staticmethod
    def generate_thumbnail(pdf_path, thumbnail_size=(200, 200)):
        """Generates a thumbnail from the first page of a PDF."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        temp_dir = tempfile.mkdtemp()
        thumbnail_path = os.path.join(temp_dir, "thumbnail.png")

        try:
            with fitz.open(pdf_path) as doc:
                page = doc.load_page(0)
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img.thumbnail(thumbnail_size)
                img.save(thumbnail_path)
        except Exception as e:
            logging.error(f"Error generating thumbnail: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

        return thumbnail_path

    @staticmethod
    def pdf_to_images(pdf_path, dpi=300):
        """Extracts images from a PDF."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        images = []
        try:
            with fitz.open(pdf_path) as doc:
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    images.append(img)
        except Exception as e:
            logging.error(f"Error extracting images from PDF: {e}")
            raise

        return images

    @staticmethod
    def detect_text_orientation(image_path):
        """Detects text orientation using Tesseract."""
        try:
            # Run Tesseract with orientation detection (--psm 0)
            result = subprocess.run(
                [TESSERACT_PATH, image_path, "stdout", "--psm", "0"],
                capture_output=True,
                text=True,
                check=True,
            )
            # Parse the output to find the rotation angle
            for line in result.stdout.split("\n"):
                if "Rotate:" in line:
                    rotation_angle = int(line.split(":")[1].strip())
                    return rotation_angle
            return 0  # Default to no rotation if angle not found
        except subprocess.CalledProcessError as e:
            logging.error(f"Error detecting text orientation: {e.stderr}")
            return 0  # Assume no rotation if detection fails

    @staticmethod
    def ocr_image(image, page_num, dpi=300, languages="hin+mar+eng"):
        """Performs OCR on an image and returns the path to the searchable PDF."""
        unique_id = uuid.uuid4().hex  # Generate a unique identifier
        temp_image_path = tempfile.mktemp(prefix=f"temp_image_page_{page_num}_{unique_id}_", suffix=".png")
        image.save(temp_image_path, dpi=(dpi, dpi))

        # Detect text orientation
        rotation_angle = AutomateBackend.detect_text_orientation(temp_image_path)
        logging.info(f"Detected rotation angle for page {page_num + 1}: {rotation_angle} degrees")

        # Rotate the image if necessary (180 degrees)
        if rotation_angle == 180:
            logging.info(f"Rotating page {page_num + 1} by 180 degrees")
            rotated_image = image.rotate(180, expand=True)
            rotated_image.save(temp_image_path, dpi=(dpi, dpi))

        temp_ocr_pdf_base_path = tempfile.mktemp(prefix=f"temp_ocr_page_{page_num}_{unique_id}_")
        temp_ocr_pdf_path = temp_ocr_pdf_base_path + ".pdf"

        try:
            logging.info(f"Running Tesseract-OCR on {temp_image_path}...")
            subprocess.run(
                [TESSERACT_PATH, temp_image_path, temp_ocr_pdf_base_path, "-l", languages, "pdf"],
                check=True,
                capture_output=True,
                text=True,
            )
            logging.info(f"OCR completed for {temp_image_path}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Tesseract-OCR failed: {e.stderr}")
            raise RuntimeError(f"OCR failed: {e.stderr}") from e
        finally:
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
                logging.info(f"Deleted temporary image file: {temp_image_path}")

        return temp_ocr_pdf_path

    @staticmethod
    def compress_pdf(pdf_path, output_pdf_path):
        """Compresses a PDF if its size exceeds 20MB."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # Convert to MB
        if file_size > 20:
            try:
                pdf = fitz.open(pdf_path)
                pdf.save(output_pdf_path, garbage=4, deflate=True)
                pdf.close()
                logging.info(f"✅ PDF compressed and saved as: {output_pdf_path}")
            except Exception as e:
                logging.error(f"❌ Error compressing PDF: {e}")
                raise
        else:
            logging.info("✅ PDF size is already below 20MB. No compression needed.")
            shutil.copy(pdf_path, output_pdf_path)

    @staticmethod
    def ocr_pdf_to_searchable_pdf(pdf_path, output_pdf_path, dpi=300, progress_callback=None):
        """Converts a PDF to a searchable PDF using OCR."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        images = AutomateBackend.pdf_to_images(pdf_path, dpi)
        ocr_pdf_document = fitz.open()  # Initialize a new PDF document for OCR output
        temp_files = []  # List to store temporary file paths

        logging.info(f"Processing PDF: {pdf_path} with {len(images)} pages...")

        for i, image in enumerate(images):
            logging.info(f"Processing page {i + 1}...")
            temp_ocr_pdf_path = AutomateBackend.ocr_image(image, i, dpi)
            temp_files.append(temp_ocr_pdf_path)  # Add to temporary files list

            if os.path.exists(temp_ocr_pdf_path):
                with fitz.open(temp_ocr_pdf_path) as temp_ocr_pdf:
                    logging.info(f"Adding {len(temp_ocr_pdf)} pages from {temp_ocr_pdf_path}...")
                    ocr_pdf_document.insert_pdf(temp_ocr_pdf)
            else:
                logging.warning(f"Warning: {temp_ocr_pdf_path} not found. Skipping page {i + 1}.")

            if progress_callback:
                progress = (i + 1) / len(images) * 100
                progress_callback(progress)

        # Verify that the number of pages in the input PDF matches the output PDF
        with fitz.open(pdf_path) as input_pdf:
            input_page_count = len(input_pdf)
            output_page_count = len(ocr_pdf_document)

            if input_page_count != output_page_count:
                logging.error(f"Error: Input PDF has {input_page_count} pages, but output PDF has {output_page_count} pages.")
                ocr_pdf_document.close()
                raise ValueError("Page count mismatch between input and output PDFs.")

        logging.info(f"Final PDF has {len(ocr_pdf_document)} pages.")
        if len(ocr_pdf_document) == 0:
            logging.error("Error: No pages were added to the final PDF.")
        else:
            # Save the OCR-processed PDF temporarily
            temp_ocr_output = tempfile.mktemp(suffix=".pdf")
            ocr_pdf_document.save(temp_ocr_output)
            ocr_pdf_document.close()

            # Compress the PDF if its size exceeds 20MB
            AutomateBackend.compress_pdf(temp_ocr_output, output_pdf_path)
            logging.info(f"OCR-processed PDF saved as {output_pdf_path}")

        # Clean up temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logging.info(f"Deleted temporary file: {temp_file}")

    @staticmethod
    def merge_pdfs(input_paths, output_path, progress_callback=None):
        """Merges multiple PDFs into a single PDF."""
        merged = fitz.open()
        total = len(input_paths)

        try:
            for i, path in enumerate(input_paths):
                if not os.path.exists(path):
                    raise FileNotFoundError(f"PDF file not found: {path}")

                with fitz.open(path) as doc:
                    logging.info(f"Merging {path} with {len(doc)} pages...")
                    merged.insert_pdf(doc)

                if progress_callback:
                    progress = (i + 1) / total * 100
                    progress_callback(progress)
        except Exception as e:
            logging.error(f"Error merging PDFs: {e}")
            raise
        finally:
            merged.save(output_path)
            merged.close()
            logging.info(f"Merged PDF saved as {output_path}")

    @staticmethod
    def cleanup_temp_files(paths):
        """Cleans up temporary directories and files."""
        if paths:
            temp_dir = os.path.dirname(paths[0])
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                logging.info(f"Deleted temporary directory: {temp_dir}")