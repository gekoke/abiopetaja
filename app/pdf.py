import logging
import os
from subprocess import CalledProcessError, TimeoutExpired, run
from tempfile import TemporaryDirectory

from django.conf import settings

logger = logging.getLogger(__name__)

type PDFCompilationError = Timeout | FailedUnexpectedly


class Timeout:
    pass


class FailedUnexpectedly:
    pass


def compile_pdf(latex_source: str) -> PDFCompilationError | bytes:
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
            os.makedirs(os.path.dirname(f"{settings.MEDIA_ROOT}/media"), exist_ok=True)
            with open(pdf_file, "rb") as file:
                return file.read()
        except FileNotFoundError:
            logger.error("pdflatex did not produce a PDF")
            return FailedUnexpectedly()
