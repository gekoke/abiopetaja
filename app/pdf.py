import logging
import os
from dataclasses import dataclass
from subprocess import CalledProcessError, TimeoutExpired, run
from tempfile import TemporaryDirectory

logger = logging.getLogger(__name__)

type PDFCompilationError = Timeout | FailedUnexpectedly


class Timeout:
    pass


class FailedUnexpectedly:
    pass


@dataclass
class PDF:
    data: bytes


def compile_pdf(latex_source: str) -> PDFCompilationError | PDF:
    """Compile a PDF file from Latex source."""
    with TemporaryDirectory() as tmp_dir:
        tex_file = os.path.join(tmp_dir, "template.tex")
        pdf_file = os.path.join(tmp_dir, "template.pdf")
        with open(tex_file, "w") as file:
            file.write(latex_source)

        try:
            run(["pdflatex", tex_file], cwd=tmp_dir, timeout=5, check=True)
        except TimeoutExpired:
            logger.error("pdflatex timed out")
            return Timeout()
        except CalledProcessError as e:
            logger.error(f"pdflatex failed: {e}")
            return FailedUnexpectedly()

        try:
            with open(pdf_file, "rb") as file:
                return PDF(file.read())
        except FileNotFoundError:
            logger.error("pdflatex did not produce a PDF")
            return FailedUnexpectedly()
