from pathlib import Path
from typing import List, Union

import requests
from pydantic import BaseModel


class Chapter(BaseModel):
    number: int
    page_text: List[str]  # text from each page is a str in a list


class Book(BaseModel):
    id: int
    subject = "History"
    class_or_grade: int = None
    url: str = ""
    title: str = ""
    origin: str = ''
    zip_file_path: str = ""
    extract_to_path: str = ""

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
            raise AssertionError(
                f"Please download the file or set the zip_file_path variable"
            )
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
