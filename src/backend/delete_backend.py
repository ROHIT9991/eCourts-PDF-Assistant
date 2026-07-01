import os
import fitz
from PyPDF2 import PdfWriter, PdfReader
import tempfile

class DeleteBackend:
    @staticmethod
    def split_pdf_into_pages(input_pdf):
        temp_dir = tempfile.mkdtemp()
        page_files = []
        doc = fitz.open(input_pdf)
        for page_num in range(len(doc)):
            output_path = os.path.join(temp_dir, f"page_{page_num}.pdf")
            page = doc.load_page(page_num)
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            new_doc.save(output_path)
            new_doc.close()
            page_files.append(output_path)
        doc.close()
        return page_files

    @staticmethod
    def merge_pages(page_paths, output_pdf):
        pdf_writer = PdfWriter()
        for path in page_paths:
            pdf_reader = PdfReader(path)
            pdf_writer.add_page(pdf_reader.pages[0])
        with open(output_pdf, 'wb') as out:
            pdf_writer.write(out)

    @staticmethod
    def cleanup_temp_files(temp_files):
        for file in temp_files:
            try:
                os.remove(file)
            except:
                pass
        temp_dir = os.path.dirname(temp_files[0])
        try:
            os.rmdir(temp_dir)
        except:
            pass