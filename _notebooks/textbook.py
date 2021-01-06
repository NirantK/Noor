from io import StringIO
from pathlib import Path
from typing import List, Union

import pysbd
import requests
from pdf_parsing import pdf_to_text
from pydantic import BaseModel
from tqdm import tqdm

seg = pysbd.Segmenter(language="en", clean=True)


class Chapter(BaseModel):
    number: int
    file_path: Union[Path, str] = ""
    raw_text: str
    clean_text: Union[None, str]


class Book(BaseModel):
    id: int
    subject = "History"
    class_or_grade: int = None
    url: str = ""
    title: str = ""
    origin: str = ""
    zip_file_path: str = ""
    extract_to_path: str = ""
    chapters: List = []

    def download(self, file_path: Path = ".", file_name: Union[None, str] = None):
        """
        Utility function to download
        """
        # TODO: Add zip_file_path if the zip file already exists, without downloading again
        url = self.url
        if file_name is None:
            url_path = Path(url)
            file_name = url_path.name

        path = Path(file_path).resolve()
        path.mkdir(exist_ok=True, parents=True)
        path = path / file_name

        if not path.exists():
            r = requests.get(url)
            with path.open("wb") as f:
                f.write(r.content)

        self.zip_file_path = path
        return path

    def unzip(self, extract_to: Path = "."):
        """"""
        file_path = self.zip_file_path
        try:
            assert self.zip_file_path != ""
        except AssertionError as e:
            raise AssertionError(f"Please download the file or set the zip_file_path variable")
        import zipfile

        extract_to = Path(extract_to)
        extract_to.mkdir(exist_ok=True, parents=True)
        export_to_path = (
            extract_to / f"class_{self.class_or_grade}_{self.subject}"
        )  # export to class_9_History and so on in the data folder
        export_to_path.mkdir(exist_ok=True, parents=True)
        self.extract_to_path = export_to_path
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(export_to_path)

    def make_chapters(self):
        def get_chapter_pdf_for_book(book: Book) -> List:
            """Get paths to all pdf files for each chapter

            Args:
                book (Book): [description]

            Returns:
                List: of all chapter pdf files
            """
            pdf_files = []
            for folder in self.extract_to_path.ls():
                pdf_files.extend(folder.pdfls())
            pdf_files.sort()
            pdf_files = [file for file in pdf_files if file.stem[-2:].isdigit()]  # keep the chapter files, nothing else
            return pdf_files

        pdf_files = get_chapter_pdf_for_book(self)
        for file in tqdm(pdf_files):
            """
            output_io_wrapper is StringIO because TextConverter expect
            StringIOWrapper/TextIOWrapper or similar object as an input.
            This can be replaced by TextIOwrapper when we want to export the
            output directly to the file
            """
            output_io_wrapper = StringIO()
            plain_text = pdf_to_text(file, output_io_wrapper)
            chp = Chapter(
                clean_text=None,
                raw_text=plain_text,
                file_path=file,
                number=int(file.stem[-2:]),
            )
            self.chapters.append(chp)

    def clean_raw_text(self, disable_pysbd=False):
        """pySBD (Python Sentence Boundary Disambiguation)
        is a rule-based sentence boundary detection that
        works out-of-the-box.

        Didn't use the spacy-pipe version of this because it
        is conflicting with the neuralcoref.

        Each paragraph is separated by \n\n so using that
        to remove separate it in paragraphs and then removing \n
        within the paragraphs.
        Also using pySBD to then identify sentences in each
        paragraph. I don't know if we need this so added a disable
        option for this. The difference you can see after disabling
        it is you will be able to see the whole paragraph as one
        blob.
        """
        for chapter in tqdm(self.chapters):
            clean = []
            for text in chapter.raw_text.split("\n\n"):
                clean.append(text.replace("\n", " "))
            clean_text = "\n".join(clean)
            if not disable_pysbd:
                clean_text = "\n".join(seg.segment(clean_text))
            chapter.clean_text = clean_text
