from __future__ import annotations

import random

from sympy import Expr, S, simplify, solveset, sympify
from sympy.core import UnevaluatedExpr, symbols
from sympy.printing.latex import latex

from app.models import Problem, ProblemKind


def _latex(expr):
    return latex(expr, decimal_separator="comma")


def make_plus_or_minus():
    return random.choice(["+", "-"])


def make_comparison_operator(allow_eq: bool = True):
    """allow_eq: Whether to allow generating the '=' operator."""
    return random.choice(["<", "<=", ">=", ">"] + (["=="] if allow_eq else []))


def make_quadratic() -> Expr:
    def make_coeffiecient():
        return random.randint(-12, 12)

    a, b, c = make_coeffiecient(), make_coeffiecient(), make_coeffiecient()
    op1, op2 = make_plus_or_minus(), make_plus_or_minus()
    return sympify(f"{a}*x**2 {op1} {b}*x {op2} {c}", evaluate=False)


def make_fraction() -> Expr:
    """
    Make a fraction.

    Example:
    -------
    4*(x - 2) / (x + 3)
    """

    def make_coeffiecient():
        return random.randint(1, 8)

    c1, c2, c3 = (make_coeffiecient() for _ in range(3))
    op1, op2 = make_plus_or_minus(), make_plus_or_minus()
    # Use empty string if c1==1 to avoid multiplying by 1.
    c1 = "" if c1 == 1 else f"{c1}*"
    return sympify(f"{c1}(x {op1} {c2}) / (x {op2} {c3})", evaluate=False)


def make_linear_inequality_problem() -> Problem:
    """
    Make a linear inequality problem.

    Example:
    -------
    `2(x - 3) - 1 > 3(x - 2) - 4(x + 1)`.
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
    problem.definition = _latex(problem_definition)
    problem.solution = _latex(problem_solution)
    problem.kind = ProblemKind.LINEAR_INEQUALITY
    return problem


def make_quadratic_inequality_problem() -> Problem:
    """
    Make a quadratic inequality problem.

    Example:
    -------
    `-5x**2 + 9x + 2 > 0`.
    """
    quadratic = make_quadratic()
    comparison = make_comparison_operator(allow_eq=False)

    problem_definition = sympify(f"{quadratic} {comparison} 0")
    problem_solution = solveset(problem_definition, "x", S.Reals)

    problem = Problem()
    problem.definition = _latex(problem_definition)
    problem.solution = _latex(problem_solution)
    problem.kind = ProblemKind.QUADRATIC_INEQUALITY
    return problem


def make_fractional_inequality_problem() -> Problem:
    """
    Make a fractional inequality problem.

    Example:
    -------
    `2*(x - 2) / (x + 2) > 4`.
    """
    fraction = make_fraction()
    comparsion = make_comparison_operator(allow_eq=False)

    problem_definition = sympify(f"{fraction} {comparsion} {random.randint(-9, 9)}", evaluate=False)
    problem_solution = solveset(problem_definition, "x", S.Reals)

    problem = Problem()
    problem.definition = _latex(problem_definition)
    problem.solution = _latex(problem_solution)
    problem.kind = ProblemKind.FRACTIONAL_INEQUALITY
    return problem


def make_exponent_reduction_problem() -> Problem:
    m, n, w, x, y = symbols("m n w x y")

    def variant_1() -> Problem:
        coef_1 = random.randint(10, 50)
        coef_2 = random.randint(10, 50)
        exp_1 = random.randint(2, 9)
        exp_2 = random.randint(2, 9)
        exp_3 = random.randint(2, 9)
        exp_4 = random.randint(2, 9)
        exp_5 = random.randint(2, 9)
        exp_6 = random.randint(2, 9)

        numerator = UnevaluatedExpr(coef_1 * w**exp_1 * x**exp_2 * y**exp_3)
        denominator = coef_2 * w**exp_4 * x**exp_5 * y**exp_6

        problem_definition = numerator / denominator
        problem_solution = simplify(problem_definition)

        problem = Problem()
        problem.definition = _latex(problem_definition)
        problem.solution = _latex(problem_solution)
        problem.kind = ProblemKind.EXPONENT_REDUCTION_PROBLEM
        return problem

    def variant_2() -> Problem:
        coef_1 = random.randint(10, 50)
        coef_2 = random.randint(10, 50)
        exp_1 = random.randint(2, 9)
        exp_2 = random.randint(2, 9)
        exp_4 = random.randint(2, 9)
        exp_5 = random.randint(2, 9)

        numerator = UnevaluatedExpr(coef_1 * m**exp_1 * n**exp_2)
        denominator = coef_2 * m**exp_4 * n**exp_5

        problem_definition = numerator / denominator
        problem_solution = simplify(problem_definition)

        problem = Problem()
        problem.definition = _latex(problem_definition)
        problem.solution = _latex(problem_solution)
        problem.kind = ProblemKind.EXPONENT_REDUCTION_PROBLEM
        return problem

    variants = [
        variant_1,
        variant_2,
    ]
    return random.choice(variants)()


def make_exponent_operation_problem() -> Problem:
    u, v, x, y, z = symbols("u v x y z")

    def variant_1() -> Problem:
        coef_1 = random.choice(list(range(-9, 0)) + list(range(1, 9)))
        coef_2 = random.randint(1, 9)
        exp = random.randint(2, 3)
        numerator = UnevaluatedExpr(coef_1 * x * z)
        denominator = coef_2 * y

        problem_definition = UnevaluatedExpr(numerator / denominator) ** exp
        problem_solution = simplify(problem_definition)

        problem = Problem()
        problem.definition = _latex(problem_definition)
        problem.solution = _latex(problem_solution)
        problem.kind = ProblemKind.EXPONENT_OPERATION_PROBLEM
        return problem

    def variant_2() -> Problem:
        coef_1 = random.choice(list(i / 10 for i in range(1, 10)))
        coef_2 = random.randint(2, 9)
        exp_1 = random.randint(2, 3)
        exp_2 = random.randint(2, 3)
        exp_3 = random.randint(2, 3)

        fact_1 = UnevaluatedExpr(coef_1 * x**exp_1 * y**exp_2)
        fact_2 = coef_2 * x * y**exp_3

        problem_definition = fact_1 * fact_2
        problem_solution = simplify(problem_definition)

        problem = Problem()
        problem.definition = _latex(problem_definition)
        problem.solution = _latex(problem_solution)
        problem.kind = ProblemKind.EXPONENT_OPERATION_PROBLEM
        return problem

    def variant_3() -> Problem:
        coef_1 = random.randint(-4, -2)
        coef_2 = random.randint(2, 6)
        exp_1 = random.randint(2, 4)
        exp_2 = random.randint(2, 4)

        problem_definition = UnevaluatedExpr(coef_1 * u * v**exp_1) / (coef_2 * u * v**exp_2)
        problem_solution = simplify(problem_definition)

        problem = Problem()
        problem.definition = _latex(problem_definition)
        problem.solution = _latex(problem_solution)
        problem.kind = ProblemKind.EXPONENT_OPERATION_PROBLEM
        return problem

    def variant_4() -> Problem:
        exp_1 = random.randint(1, 3)
        exp_2 = random.randint(2, 3)
        exp_3 = random.randint(2, 3)

        problem_definition = (UnevaluatedExpr(x**exp_1 * y**exp_2) ** exp_3) * (-x * y)
        problem_solution = simplify(problem_definition)

        problem = Problem()
        problem.definition = _latex(problem_definition)
        problem.solution = _latex(problem_solution)
        problem.kind = ProblemKind.EXPONENT_OPERATION_PROBLEM
        return problem

    variants = [
        variant_1,
        variant_2,
        variant_3,
        variant_4,
    ]
    return random.choice(variants)()
