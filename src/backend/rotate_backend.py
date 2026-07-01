import os
import fitz
import tempfile
import shutil

class RotateBackend:
    @staticmethod
    def split_pdf_into_pages(pdf_path):
        temp_dir = tempfile.mkdtemp()
        doc = fitz.open(pdf_path)
        page_files = []
        
        for i in range(len(doc)):
            temp_path = os.path.join(temp_dir, f"page_{i+1}.pdf")
            subdoc = fitz.open()
            subdoc.insert_pdf(doc, from_page=i, to_page=i)
            subdoc.save(temp_path)
            page_files.append(temp_path)
        
        return page_files

    @staticmethod
    def rotate_page(page_path, angle):
        doc = fitz.open(page_path)
        page = doc.load_page(0)
        page.set_rotation(angle)
        doc.saveIncr()

    @staticmethod
    def merge_pages(page_paths, output_path):
        merged = fitz.open()
        for path in page_paths:
            doc = fitz.open(path)
            merged.insert_pdf(doc)
        merged.save(output_path)
        merged.close()

    @staticmethod
    def cleanup_temp_files(page_paths):
        temp_dir = os.path.dirname(page_paths[0])
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

