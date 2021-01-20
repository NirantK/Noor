from io import StringIO
from typing import List

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser


def pdf_to_text(file: str, output_io_wrapper: object) -> List[str]:
    """
    Converts the pdf to text using pdfminer.six Using PDFParser to fetch PDF objects from a file stream.

    This is then passed to PDF document to cooperate with a PDF parser in order to dynamically import the data as
    processing goes

    ResourceManager facilitates reuse of shared resources such as fonts and images so that large objects are not
    allocated multiple times.

    Used line_margin=0.7 because anything below that was considering a paragraph break as a different text blob(bounding box?)
    """

    with open(file, "rb") as in_file:
        parser = PDFParser(in_file)
        doc = PDFDocument(parser)
        resource_manager = PDFResourceManager()
        test_converter = TextConverter(resource_manager, output_io_wrapper, laparams=LAParams(line_margin=0.7))
        interpreter = PDFPageInterpreter(resource_manager, test_converter)
        # Processor for the content of a PDF page

        for page in PDFPage.create_pages(doc):
            interpreter.process_page(page)

    return output_io_wrapper.getvalue()
