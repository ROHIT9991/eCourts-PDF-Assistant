import os
import fitz
import tempfile

class ReorderBackend:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.temp_files = []

    def split_pdf_into_pages(self):
        self.temp_files = []
        doc = fitz.open(self.pdf_path)
        for i in range(len(doc)):
            temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf", prefix="temp_page_")
            os.close(temp_fd)
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=i, to_page=i)
            new_doc.save(temp_path)
            new_doc.close()
            self.temp_files.append(temp_path)
        return self.temp_files

    def merge_pages(self, output_path):
        new_doc = fitz.open()
        for page_file in self.temp_files:
            doc = fitz.open(page_file)
            new_doc.insert_pdf(doc)
            doc.close()
        new_doc.save(output_path)
        new_doc.close()

    def cleanup_temp_files(self):
        for file in self.temp_files:
            if os.path.exists(file):
                os.remove(file)
        self.temp_files = []