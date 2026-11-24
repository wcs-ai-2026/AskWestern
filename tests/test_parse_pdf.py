#this file is for testing if the pdf parser is working properly

import unittest
import tempfile
from pathlib import Path
import pymupdf
from src.askwestern.ingest.parse_pdf import extract_pdf_text

class TestPDFParser(unittest.TestCase):
    def setUp(self):
        #create a temp folder for test pdfs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pdf_path = Path(self.temp_dir.name) / "test.pdf"

    def tearDown(self):
        #remove temp files after each test
        self.temp_dir.cleanup()

    def test_single_page_pdf(self):
        #create a one page pdf with sample text
        doc = pymupdf.open()
        page = doc.new_page()

        page.insert_text((72,72), "Western University Academic Advising")

        doc.save(self.pdf_path)
        doc.close()

        #run the parser
        result = extract_pdf_text(self.pdf_path)

        #verify the extracted text
        self.assertEqual(result, "Western University Academic Advising")

    def test_multiple_page_pdf(self):
        #create pdf with two pages
        doc = pymupdf.open()

        page_one = doc.new_page()
        page_one.insert_text((72,72), "Page One Info")

        page_two = doc.new_page()
        page_two.insert_text((72,72), "Page Two Info")

        doc.save(self.pdf_path)
        doc.close()

        result = extract_pdf_text(self.pdf_path)

        self.assertEqual(result, "Page One Info Page Two Info")

    def test_empty_pdf(self):
        #create an empty pdf
        doc = pymupdf.open()
        doc.new_page()
        doc.save(self.pdf_path)
        doc.close()

        result = extract_pdf_text(self.pdf_path)
        self.assertEqual(result,"")

    def test_invalid_pdf(self):
        #write invalid pdf data into a file
        self.pdf_path.write_text("This is not a pdf", encoding="utf-8")

        #verify that invalid pdfs result in an error
        with self.assertRaises(Exception):
            extract_pdf_text(self.pdf_path)

    def test_missing_pdf(self):
        #try to parse file that doesnt exist
        with self.assertRaises(Exception):
            extract_pdf_text(self.pdf_path)

if __name__ == "__main__":
    unittest.main()