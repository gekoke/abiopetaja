from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext

from app.models import (
    Problem,
    Test,
    TestVersion,
)


def _make_document(source: str) -> str:
    return f"""
    \\documentclass[20pt]{{article}}
    \\usepackage{{amsfonts}}
    \\usepackage{{geometry}}
    \\geometry{{
        left=20mm,
        right=20mm,
        top=20mm,
    }}
    \\linespread{{1.5}}
    \\begin{{document}}
    {source}
    \\end{{document}}
    """


def _render_problems(problems: list[Problem]) -> str:
    problem_kind_set = {problem.kind for problem in problems}
    problems_by_kind = {
        problem_kind: [problem for problem in problems if problem.kind == problem_kind]
        for problem_kind in problem_kind_set
    }

    return f"""
    {"\n".join(_render_problem_kind(problems_by_kind[kind]) for kind in problems_by_kind)}
    """


def _render_problem_kind(problems: list[Problem]) -> str:
    assert len(set(problem.kind for problem in problems)) == 1
    problem_text = problems[0].problem_text

    return f"""
    \\noindent
    {problem_text}\\newline
    {"\\newline".join(f"${problem.definition}$" for problem in problems)}
    """


def _render_header(title: str, version: int | None) -> str:
    return f"""
    \\begin{{center}}
    {"" if title == "" else f"{{\\Large \\textbf{{{title}}}}}"}

    {"" if version is None else f"{_("Version")} {version}"}
    \\end{{center}}
    """


def render_test_version(version: TestVersion) -> str:
    test = version.test
    problems = list(version.problem_set.all())

    latex = _make_document(
        f"""
        {_render_header(test.title, version.version_number)}
        {_render_problems(problems)}
        """
    )

    return latex


def _render_answer(problem: Problem) -> str:
    return f"\n\\textbf{{{pgettext("for a math problem", "Solution")}}}: ${problem.solution}$\n"


def _render_test_version_answers(version: TestVersion) -> str:
    version_label = _("Version") + f" {version.version_number}"
    return f"""
    \\subsection*{{{version_label}}}
    {"\\newline".join(_render_answer(problem) for problem in version.problem_set.all())}
    """


def render_answer_key(test: Test) -> str:
    latex = _make_document(
        f"""
        {_render_header(test.title, version=None)}
        {"\n".join(_render_test_version_answers(version) for version in test.versions)}
        """
    )

    return latex
