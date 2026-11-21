from pathlib import Path #to determine file paths
import re
import pymupdf #python library for parsing pdfs

#function for extracting pdf text
def extract_pdf_text(pdf_path):
    """
    This function extracts readable text from a PDF.
    It returns a plain string, matching the output type of the existing
    HTML extract_text() function.
    """

    pdf_path = Path(pdf_path)
    pages_text = []

    #first open the pdf
    with pymupdf.open(pdf_path) as doc:
        #extract text from each page
        for page in doc:
            text = page.get_text("text")
            if text.strip():
                pages_text.append(text)

    #combine text from all pages
    combined_text = " ".join(pages_text)

    #remove any whitspace in the text
    cleaned_text = re.sub(r"\s+", " ", combined_text).strip()

    return cleaned_text