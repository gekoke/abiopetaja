from __future__ import annotations

import random

from sympy import Expr, S, solveset, sympify
from sympy.printing.latex import latex

from app.models import Problem, ProblemKind


def make_plus_or_minus():
    return random.choice(["+", "-"])


def make_comparison_operator(allow_eq: bool = True):
    """
    allow_eq: Whether to allow generating the '=' operator
    """
    return random.choice(["<", "<=", ">=", ">"] + (["="] if allow_eq else []))


def make_quadratic() -> Expr:
    def make_coeffiecient():
        return random.randint(-12, 12)

    a, b, c = make_coeffiecient(), make_coeffiecient(), make_coeffiecient()
    op1, op2 = make_plus_or_minus(), make_plus_or_minus()
    return sympify(f"{a}*x**2 {op1} {b}*x {op2} {c}", evaluate=False)


def make_linear_inequality_problem() -> Problem:
    """
    Example:
    `2(x - 3) - 1 > 3(x - 2) - 4(x + 1)`
    """

    def make_coefficient():
        return random.randint(2, 5)

    c1, c2, c3, c4, c5, c6, c7 = (make_coefficient() for _ in range(7))
    o1, o2, o3, o4, o5 = (make_plus_or_minus() for _ in range(5))
    comparison = make_comparison_operator(allow_eq=False)

    problem_definition = sympify(
        f"{c1}*(x {o1} {c2}) {o2} {c3} {comparison} {c4}*(x {o3} {c5}) {o4} {c6}*(x {o5} {c7})",
        evaluate=False,
    )
    problem_solution = solveset(problem_definition, "x", S.Reals)

    problem = Problem()
    problem.definition = latex(problem_definition)
    problem.solution = latex(problem_solution)
    problem.kind = ProblemKind.QUADRATIC_INEQUALITY
    return problem


def make_quadratic_inequality_problem() -> Problem:
    """
    Example:
    `-5x**2 + 9x + 2 > 0`
    """
    quadratic = make_quadratic()
    comparison = make_comparison_operator(allow_eq=False)

    problem_definition = sympify(f"{quadratic} {comparison} 0")
    problem_solution = solveset(problem_definition, "x", S.Reals)

    problem = Problem()
    problem.definition = latex(problem_definition)
    problem.solution = latex(problem_solution)
    problem.kind = ProblemKind.QUADRATIC_INEQUALITY
    return problem
