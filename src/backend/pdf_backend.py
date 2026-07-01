### File: backend/pdf_backend.py

import os
from PyPDF2 import PdfMerger, PdfReader, PdfWriter

class PDFBackend:
    """Handles PDF operations: merging, deleting, rotating."""

    @staticmethod
    def merge_pdfs(pdf_list, output_path):
        merger = PdfMerger()
        for pdf in pdf_list:
            merger.append(pdf)
        merger.write(output_path)
        merger.close()
        return output_path

    @staticmethod
    def delete_pdfs(pdf_list):
        deleted_files = []
        for pdf in pdf_list:
            if os.path.exists(pdf):
                os.remove(pdf)
                deleted_files.append(pdf)
        return deleted_files

    @staticmethod
    def rotate_pdf(pdf_path, rotation_angle=90):
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        for page in reader.pages:
            page.rotate(rotation_angle)
            writer.add_page(page)

        output_path = "rotated_" + os.path.basename(pdf_path)
        with open(output_path, "wb") as output_file:
            writer.write(output_file)
        return output_path

