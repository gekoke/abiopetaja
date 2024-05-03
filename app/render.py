import logging
import os
from subprocess import CalledProcessError, TimeoutExpired, run
from tempfile import TemporaryDirectory

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext

from app.models import (
    FailedUnexpectedly,
    File,
    Problem,
    ProblemKind,
    RenderError,
    TestVersion,
    Timeout,
)

logger = logging.getLogger(__name__)


def render(version: TestVersion) -> RenderError | File:
    test = version.test
    latex = _init_latex_doc()

    latex += _render_header(test.title, version.version_number)

    problems = list(version.problem_set.all())
    problems.sort(key=lambda x: x.kind)
    kinds_set = set()

    for problem in problems:
        if problem.kind not in kinds_set:
            latex += f"""
            {ProblemKind.get_problem_text(ProblemKind(problem.kind))}
            """
            kinds_set.add(problem.kind)
        latex += _render_problem(problem)

    latex += "\\end{document}"
    return _render_to_pdf(latex, version)


def render_answer_key(versions: list[TestVersion]) -> RenderError | File:
    test = versions[0].test
    latex = _init_latex_doc()

    latex += _render_header(test.title, None)

    for version in versions:
        version_label = _("Version") + f" {version.version_number}"
        latex += f"""
            \\subsection*{{{version_label}}}
            \\noindent
            """
        for problem in version.problem_set.all():
            latex += _render_answer(problem)

    latex += "\\end{document}"
    return _render_to_pdf(latex, test)


def _render_problem(problem: Problem) -> str:
    latex = f"\n${problem.definition}$\n"
    return latex


def _render_answer(problem: Problem) -> str:
    return f"\n\\textbf{{{pgettext("for a math problem", "Solution")}}}: ${problem.solution}$\n"


def _init_latex_doc() -> str:
    return """
    \\documentclass[20pt]{article}
    \\usepackage{amsfonts}
    \\usepackage{geometry}
    \\geometry{
        left=20mm,
        right=20mm,
        top=20mm,
    }
    \\linespread{1.5}
    \\begin{document}
    """


def _render_header(title: str, version: int | None) -> str:
    header = "\n\\begin{center}\n"
    if title != "":
        header += f"{{\\Large \\textbf{{{title}}}}}\n"
    if version is not None:
        version_label = _("Version") + f" {version}"
        header += f"\n{version_label}\n"
    header += "\\end{center}\n"
    return header


def _render_to_pdf(latex_source: str, reference) -> RenderError | File:
    with TemporaryDirectory() as tmp_dir:
        tex_file = os.path.join(tmp_dir, "template.tex")
        pdf_file = os.path.join(tmp_dir, "template.pdf")
        with open(tex_file, "w") as file:
            file.write(latex_source)

        try:
            run(["pdflatex", tex_file], cwd=tmp_dir, timeout=5, check=True)
        except TimeoutExpired:
            logger.error(f"pdflatex timed out for {reference}")
            return RenderError(reason=Timeout())
        except CalledProcessError as e:
            logger.error(f"pdflatex failed for {reference}, {e}")
            return RenderError(reason=FailedUnexpectedly())

        try:
            with open(pdf_file, "rb") as file:
                pdf_file = File()
                pdf_file.data = file.read()
        except FileNotFoundError:
            logger.error(f"pdflatex did not produce a PDF for {reference}")
            return RenderError(reason=FailedUnexpectedly())

    return pdf_file
