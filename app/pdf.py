import logging
import os
from subprocess import CalledProcessError, TimeoutExpired, run
from tempfile import TemporaryDirectory

from app.models import (
    FailedUnexpectedly,
    File,
    RenderError,
    Test,
    TestVersion,
    Timeout,
)
from app.render import render_answer_key, render_test_version

logger = logging.getLogger(__name__)


def compile_pdf(version: TestVersion) -> RenderError | File:
    return _compile_pdf(render_test_version(version), version)


def compile_answer_key_pdf(test: Test) -> RenderError | File:
    return _compile_pdf(render_answer_key(test), test)


def _compile_pdf(latex_source: str, object_reference: Test | TestVersion) -> RenderError | File:
    """
    Compile a PDF file from Latex source.

    - object_reference: the object the Latex source was generated from. Used for logging purposes.
    """
    with TemporaryDirectory() as tmp_dir:
        tex_file = os.path.join(tmp_dir, "template.tex")
        pdf_file = os.path.join(tmp_dir, "template.pdf")
        with open(tex_file, "w") as file:
            file.write(latex_source)

        try:
            run(["pdflatex", tex_file], cwd=tmp_dir, timeout=5, check=True)
        except TimeoutExpired:
            logger.error(f"pdflatex timed out for {object_reference}")
            return RenderError(reason=Timeout())
        except CalledProcessError as e:
            logger.error(f"pdflatex failed for {object_reference}, {e}")
            return RenderError(reason=FailedUnexpectedly())

        try:
            with open(pdf_file, "rb") as file:
                pdf_file = File()
                pdf_file.data = file.read()
        except FileNotFoundError:
            logger.error(f"pdflatex did not produce a PDF for {object_reference}")
            return RenderError(reason=FailedUnexpectedly())

    return pdf_file
