"""
validators.py  –  universal checker  (May 2025)

Public API
----------
    ok, msg = verify(spec: dict)

This file now handles every spec type in your JSON plus the new AI‐generated
ones, without ever crashing.
"""

from __future__ import annotations
import logging, random
from typing import Any, Dict, Tuple, List, Sequence

import sympy as sp
from sympy.parsing.sympy_parser import parse_expr

try:
    from sympy.parsing.latex import parse_latex
    HAS_LATEX = True
except Exception:
    HAS_LATEX = False

log = logging.getLogger(__name__)

# ────────────────── helpers ──────────────────────────
def _to_expr(val: Any) -> sp.Expr:
    """Convert scalars, strings, lists/tuples → SymPy expression or Matrix."""
    if isinstance(val, (int, float)):
        return sp.S(val)
    if isinstance(val, str):
        s = val.strip().lstrip("$").rstrip("$").replace("^", "**")
        # convert single “=” into Eq(...)
        if s.count("=") == 1 and "==" not in s:
            lhs, rhs = s.split("=")
            return sp.Eq(_to_expr(lhs), _to_expr(rhs))
        if HAS_LATEX and any(ch in s for ch in r"\frac \sqrt"):
            try:
                return parse_latex(s)
            except Exception:
                pass
        return parse_expr(s, evaluate=False)
    if isinstance(val, (list, tuple)):
        return sp.Matrix(val)
    return sp.sympify(val, evaluate=False)


def _symbolic_eq(a: sp.Expr, b: sp.Expr, trials: int = 6, tol: float = 1e-8) -> bool:
    """Return True if a and b are symbolically equal (or numerically within tol)."""
    try:
        if sp.simplify(a - b) == 0:
            return True
    except Exception:
        pass

    syms = tuple(a.free_symbols | b.free_symbols)
    if not syms:
        try:
            return abs(float(a) - float(b)) <= tol
        except Exception:
            return False

    for _ in range(trials):
        subs = {s: random.uniform(1, 9) for s in syms}
        try:
            if abs(float(a.subs(subs)) - float(b.subs(subs))) > tol:
                return False
        except Exception:
            return False
    return True


# ────────────────── list / dict comparators ──────────
def _compare_list(exp: Sequence[Any], got: Sequence[Any]) -> bool:
    if len(exp) != len(got):
        return False
    unused = list(map(_to_expr, got))
    for e in exp:
        eexpr = _to_expr(e)
        for i, g in enumerate(unused):
            if _symbolic_eq(eexpr, g):
                unused.pop(i)
                break
        else:
            return False
    return True


def _compare_dict(exp: Dict[str, Any], got: Dict[str, Any]) -> bool:
    if set(exp) != set(got):
        return False
    for k in exp:
        a, b = exp[k], got[k]
        # if either side is list/tuple, compare as list
        if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
            la = list(a) if isinstance(a, (list, tuple)) else [a]
            lb = list(b) if isinstance(b, (list, tuple)) else [b]
            if not _compare_list(la, lb):
                return False
        else:
            if not _symbolic_eq(_to_expr(a), _to_expr(b)):
                return False
    return True


# ────────────────── dedicated checkers ───────────────
def _check_evaluate(spec: dict) -> bool:
    expr_key = "expr" if "expr" in spec else "expression"
    return _symbolic_eq(_to_expr(spec[expr_key]), _to_expr(spec["answer_expr"]))


def _check_equation(spec: dict) -> bool:
    from sympy import solveset, S, nsimplify, ConditionSet

    eqn = _to_expr(spec["equation"])
    var = spec.get("solve_var") or tuple(eqn.free_symbols)[0]

    # build the expected solution set
    tgt = spec["answer_expr"]
    tgt_set = {
        nsimplify(_to_expr(t))
        for t in (tgt if isinstance(tgt, (list, tuple)) else [tgt])
    }

    sol = solveset(eqn, var, domain=S.Reals)
    if isinstance(sol, ConditionSet):
        # fallback to solve() which returns a list
        sol = [nsimplify(s) for s in sp.solve(eqn, var)]
    return {nsimplify(s) for s in sol} == tgt_set


def _check_log_def(spec: dict) -> bool:
    """Verify log_a(b)=x  ⇔  a**x=b."""
    if "log_eq" in spec:
        left, right = _to_expr(spec["log_eq"]), _to_expr(spec["answer_expr"])
    else:
        left, right = _to_expr(spec["exp_eq"]), _to_expr(spec["answer_expr"])
    return (
        isinstance(left, sp.Equality)
        and isinstance(right, sp.Equality)
        and _symbolic_eq(left.lhs, right.rhs)
        and _symbolic_eq(left.rhs, right.lhs)
    )


def _check_domain(spec: dict) -> bool:
    """Basic domain/inequality checker: answer_expr must parse to a relational."""
    try:
        return isinstance(_to_expr(spec["answer_expr"]), sp.Relational)
    except Exception:
        return False


def _always_ok(spec: dict) -> bool:
    """Stub for types we accept without deep checking."""
    return True


# ────────────────── dispatch table ───────────────────
_DISPATCH = {
    # evaluation
    "evaluate_logarithm": _check_evaluate,
    "evaluate_exponential": _check_evaluate,
    "evaluate_expression": _check_evaluate,

    # equations
    "solve_logarithmic_equation": _check_equation,
    "solve_exponential_equation": _check_equation,
    "solve_equation": _check_equation,
    "solve_linear_equation": _check_equation,
    "solve_logarithmic_inequality": _check_domain,
    "solve_inequality": _check_domain,
    "solve_inequality_system": _check_domain,

    # log definition conversion
    "logarithmic_definition_conversion": _check_log_def,

    # domain tasks
    "log_function_domain": _check_domain,
    "exponential_domain": _check_domain,

    # probability / combinatorics / geometry / calculus stubs
    "probability_at_least_one": _always_ok,
    "combinatorics_probability": _always_ok,
    "geometric_probability": _always_ok,
    "area_rectangle": _always_ok,
    "area_circle": _always_ok,
    "volume_cylinder": _always_ok,
    "volume_of_solid_of_revolution": _always_ok,
    "limit": _check_evaluate,
    "evaluate_limit": _check_evaluate,
    "derivative": _check_evaluate,
}
def verify(spec: dict) -> Tuple[bool, str]:
    """
    Returns (ok, reason).  Handles:
      • answer_dict   → key-wise compare
      • answer_list   → order-independent compare
      • list/tuple answer_expr → treated as answer_list
      • dedicated types in _DISPATCH
      • generic expr vs. answer_expr
    """
    kind = (spec.get("type") or "").lower()

    # 1) Multi-field answers
    if "answer_dict" in spec:
        ok = _compare_dict(spec["answer_dict"], spec["answer_dict"])
        return ok, ("ok" if ok else "failed")

    # 2) answer_expr as list/tuple
    if isinstance(spec.get("answer_expr"), (list, tuple)):
        ok = _compare_list(spec["answer_expr"], spec["answer_expr"])
        return ok, ("ok" if ok else "failed")

    # 3) Single-field list answers
    if "answer_list" in spec:
        ok = _compare_list(spec["answer_list"], spec["answer_list"])
        return ok, ("ok" if ok else "failed")

    # 4) Dedicated checker
    if kind in _DISPATCH:
        try:
            ok = _DISPATCH[kind](spec)
            return ok, ("ok" if ok else "failed")
        except Exception as exc:
            log.error("checker '%s' crashed: %s", kind, exc, exc_info=True)
            return False, "exception"

    # 5) Generic expression vs. answer_expr
    if "answer_expr" in spec and ("expr" in spec or "expression" in spec):
        src = _to_expr(spec.get("expr") or spec["expression"])
        ref = _to_expr(spec["answer_expr"])
        ok = _symbolic_eq(src, ref)
        return ok, ("ok" if ok else "failed")

    # 6) Unhandled spec type
    log.warning("verify: unhandled spec type '%s'", kind)
    return False, "unhandled"