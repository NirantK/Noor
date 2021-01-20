from io import StringIO
from pathlib import Path
from typing import Bool, List, Union

import requests
import spacy
from pydantic import BaseModel
from tqdm import tqdm

import neuralcoref
import pysbd  # pySBD (Python Sentence Boundary Disambiguation) is a rule-based sentence boundary detection
from pdf_parsing import pdf_to_text

seg = pysbd.Segmenter(language="en", clean=True)

nlp = spacy.load("en")
neuralcoref.add_to_pipe(nlp)


class Chapter(BaseModel):
    number: int
    file_path: Union[Path, str] = ""
    raw_text: str
    space_formatted_text: Union[None, str]
    coref_resolved_text: Union[None, str]
    coref_clusters: Union[None, list]

    def better_sentence_boundaries(self, disable_pysbd: Bool = False) -> None:
        """
        Each paragraph is separated by \n\n so using that
        to remove separate it in paragraphs and then removing \n
        within the paragraphs.

        Also using pySBD to then identify sentences in each
        paragraph. Disabling it converts the para into one single large blob
        """
        clean = []
        for text in self.raw_text.split("\n\n"):
            clean.append(text.replace("\n", " "))
        self.space_formatted_text = "\n".join(clean)
        if not disable_pysbd:
            self.space_formatted_text = "\n".join(seg.segment(self.space_formatted_text))


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
        for file in pdf_files:
            """
            output_io_wrapper is StringIO because TextConverter expect
            StringIOWrapper/TextIOWrapper or similar object as an input.
            This can be replaced by TextIOwrapper when we want to export the
            output directly to the file
            """
            output_io_wrapper = StringIO()
            plain_text = pdf_to_text(file, output_io_wrapper)
            chp = Chapter(
                space_formatted_text=None,
                raw_text=plain_text,
                file_path=file,
                number=int(file.stem[-2:]),
                coref_resolved_text=None,
                coref_clusters=None,
            )
            self.chapters.append(chp)

    def improve_sentence_boundries(self, disable_pysbd: Bool = False):
        for chapter in self.chapters:
            chapter.better_sentence_boundaries(disable_pysbd=disable_pysbd)

    def resolve_coreference(self):
        """Uses spacy pipleline as a base and extends it
        using neuralcoreference to process the coreferences
        in the plain text that you get.

        Saving both resolved text as well as the coreference
        clusters in the chapter.
        """
        for chapter in tqdm(self.chapters):
            if not chapter.space_formatted_text:
                raise ValidationError(
                    "There is no space_formatted_text for the chapter. \
                    Please run book.improve_sentence_boundries or manually add\
                    custom cleaned text by iterating through chapters"
                )
                return
            doc = nlp(chapter.space_formatted_text)
            chapter.coref_resolved_text = doc._.coref_resolved
            chapter.coref_clusters = doc._.coref_clusters
