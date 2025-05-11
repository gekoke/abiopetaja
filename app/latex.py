from __future__ import annotations

from string import ascii_lowercase

from django.utils.translation import(
     gettext_lazy as _,
     get_language,
)
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import (
        Test,
        TestVersion,
        TestVersionProblem,
    )


def _get_problems_by_group(
    problems: list[TestVersionProblem],
) -> dict[tuple[str, str], list[TestVersionProblem]]:
    groups = {}
    for problem in problems:
        # Group by a tuple of (topic, difficulty)
        key = (problem.topic, problem.get_difficulty_display())
        groups.setdefault(key, []).append(problem)
    return groups


def _make_document(source: str) -> str:
    return f"""
    \\documentclass[20pt]{{article}}
    \\usepackage{{amsfonts}}
    \\usepackage{{geometry}}
    \\usepackage{{amsmath}}
    \\usepackage{{tikz}}
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


def _render_problems(problems: list[TestVersionProblem]) -> str:
    problems_by_group = _get_problems_by_group(problems)
    return "\n\n".join(
        _render_problem_group(group_key, group, idx)
        for idx, (group_key, group) in enumerate(problems_by_group.items())
    )


def _render_problem_group(
    group_key: tuple[str, str], problems: list[TestVersionProblem], group_index: int
) -> str:
    # Render all problems and join them with a blank line between each.
    rendered_problems = "\n\n".join(
        _render_problem(problem, idx) for idx, problem in enumerate(problems)
    )
    # Use plain newlines (or a paragraph break) rather than forcing a newline.
    return f"\\noindent {group_index + 1}){rendered_problems}\n\n"

def generate_latex_grid(cols: int, rows: int, square_size: int = 5) -> str:
    return f"""
    \\begin{{center}}
    \\begin{{tikzpicture}}
    \\draw[step={square_size}mm, gray!30, very thin] (0,0) grid ({cols},{rows});
    \\draw[thick] (0,0) rectangle ({cols},{rows});
    \\end{{tikzpicture}}
    \\end{{center}}
    """

def _render_problem(problem: TestVersionProblem, problem_index: int) -> str:
    # Write each problem as regular text.

    text = problem.definition

    return f" {ascii_lowercase[problem_index]})  {text}\n\n {generate_latex_grid(15, 7)}"


def _render_header(title: str, subtitle: str) -> str:
    header_title = "" if title == "" else f"{{\\Large \\textbf{{{title}}}}}"
    return f"""
    \\begin{{center}}
    {header_title}
    {subtitle}
    \\end{{center}}
    """


def render_test_version(version: TestVersion) -> str:
    test = version.test
    problems = list(version.testversionproblem_set.all())
    latex = _make_document(
        f"""
        {_render_header(test.title, _("Version %(version)s") % {"version": version.version_number})}
        {_render_problems(problems)}
        """
    )
    return latex


# Updated function for rendering answers without explicit "\\newline"
def _render_problem_group_answer(
    group_key: tuple[str, str], problems: list[TestVersionProblem], group_index: int
) -> str:
    topic, difficulty = group_key
    header = f"{topic} - {difficulty}"
    # Join each answer with two newlines.
    answers = "\n\n".join(
        _render_problem_answer(problem, idx) for idx, problem in enumerate(problems)
    )
    return f"\\noindent {group_index + 1}) {header}\n\n{answers}\n\n"

# ───── helper ────────────────────────────────────
def _ensure_dollar_wrapped(text: str) -> str:
    """
    Guarantee the string starts **and** ends with $.
    Handles all four cases:
      $…$   → unchanged
      $…    → add trailing $
      …$    → add leading $
      …     → wrap with $…$
    """
    s = text.strip()
    has_start = s.startswith("$")
    has_end   = s.endswith("$")

    if has_start and has_end:
        return s
    if has_start and not has_end:
        return s + "$"
    if has_end and not has_start:
        return "$" + s
    return f"${s}$"


def _render_problem_answer(problem: TestVersionProblem, problem_index: int) -> str:
    # Ensure solution is in math mode
    sol = _ensure_dollar_wrapped(problem.solution)
    return f"\\noindent {ascii_lowercase[problem_index]}) {sol}\n\n"


def _render_test_version_answers(version: TestVersion) -> str:
    subsection_title = _("Version %(version)s") % {"version": version.version_number}
    groups = _get_problems_by_group(list(version.testversionproblem_set.all()))
    # Join each group's answers with double newlines.
    answers = "\n\n".join(
        _render_problem_group_answer(group_key, group_problems, idx)
        for idx, (group_key, group_problems) in enumerate(groups.items())
    )
    return f"\\subsection*{{{subsection_title}}}\n\n{answers}\n\n"


def render_answer_key(test: Test) -> str:
    return _make_document(
        f"""
        {_render_header(test.title, _("Answer Key"))}
        {"\n\n".join(_render_test_version_answers(version) for version in test.versions)}
        """
    )
