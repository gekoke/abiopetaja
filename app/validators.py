from sympy import Eq, S, simplify, solveset, symbols
from sympy.parsing.sympy_parser import parse_expr
import logging, random
from sympy import log, simplify

def _to_expr(value):
    """
    Robustly turn strings / numbers into a SymPy expression.
    Falls back cleanly if `parse_latex` chokes on plain‑text math.
    """
    if isinstance(value, (int, float)):
        return S(value)
    if isinstance(value, str):
        value = value.strip("$ ").replace("^", "**")
        try:                                       # ① try LaTeX first
            return parse_latex(value)
        except Exception:                          # ② plain SymPy syntax
            return parse_expr(value, evaluate=False)
    return S(value)



def _expressions_equal(sym_expr, sym_ref, trials: int = 6, tol=1e-8) -> bool:
    # 1) symbolic attempt
    if simplify(sym_expr - sym_ref) == 0:
        return True

    # 2) numeric fallback
    free_syms = list(sym_expr.free_symbols | sym_ref.free_symbols)
    for _ in range(trials):
        subs = {s: random.uniform(1, 9) for s in free_syms}  # positive reals
        val1 = sym_expr.subs(subs).evalf()
        val2 = sym_ref.subs(subs).evalf()
        if abs(val1 - val2) > tol:
            return False
    return True

def verify(spec: dict) -> tuple[bool,str]:
    kind = spec.get("type")
    try:
        if kind in ("simplify", "simplify_then_evaluate"):
            ok = _verify_simplify(spec)

        elif kind in ("evaluate", "evaluate_expression"):
            ok = _verify_evaluate(spec)

        elif kind == "evaluate_logarithm":
            ok = _verify_evaluate_logarithm(spec)

        elif kind == "evaluate_exponential":
            ok = _verify_evaluate_exponential(spec)

        elif kind in ("solve_equation",
                      "solve_exponential_equation",
                      "solve_logarithmic_equation"):
            ok = _verify_solve(spec)

        else:
            ok = True

        return ok, kind

    except KeyError as e:
        return False, f"Missing field: {e}"
    except Exception as e:
        return False, f"Exception: {e}"

def _verify_solve(spec: dict) -> bool:
    """
    Verifies specs of type solve_equation*, solve_exponential_equation,
    or solve_logarithmic_equation.
    Expects:
      - "equation": a string like "2*x+1=5" or "x**2-4"
      - "solve_var": the variable name as a string, e.g. "x"
      - either "answer_expr" (single solution or list) or "answer" (list)
    """
    eq_str   = spec["equation"]
    var_name = spec["solve_var"]
    sym      = symbols(var_name)

    # build the Sympy Solveset
    if "=" in eq_str:
        lhs, rhs = eq_str.split("=", 1)
        sol_set  = solveset(Eq(_to_expr(lhs), _to_expr(rhs)), sym)
    else:
        sol_set  = solveset(_to_expr(eq_str), sym)

    # pull out expected answers
    raw_ans = spec.get("answer_expr") or spec.get("answer", [])
    if isinstance(raw_ans, (list, tuple)):
        want = { _to_expr(a) for a in raw_ans }
    else:
        want = { _to_expr(raw_ans) }

    # compare sets
    return set(sol_set) == want

def _verify_evaluate_exponential(spec: dict) -> bool:
    """
    Verifies specs of type "evaluate_exponential".
    Expects exactly the schema:
      - "function": a string f(x)
      - "values":  list of numeric x-values
      - "answer_dict": mapping "f(v)" → result
    """
    # sanity check
    required = {"function", "values", "answer_dict"}
    if not required <= spec.keys():
        missing = required - spec.keys()
        raise KeyError(f"Missing fields for evaluate_exponential: {missing}")

    x     = symbols("x")
    f_expr = _to_expr(spec["function"])
    answers = spec["answer_dict"]

    for v in spec["values"]:
        key = f"f({v})"
        if key not in answers:
            raise KeyError(f"No answer_dict entry for {key}")
        expected = _to_expr(answers[key])
        actual   = f_expr.subs({x: v})
        if not _expressions_equal(actual, expected):
            return False
    return True

def _verify_simplify(spec: dict) -> bool:
    """
    Verifies specs of type "simplify" or "simplify_then_evaluate".
    Expects keys:
      - "expr": the original expression to simplify
      - "answer_expr": the proposed simplified form
    """
    # parse both sides to Sympy
    orig = _to_expr(spec["expr"])
    fmt  = _to_expr(spec["answer_expr"])
    # check symbolically or numerically
    return _expressions_equal(orig, fmt)
# ──────────────────────────────────────────────────────────────────────────
def _verify_evaluate_logarithm(spec: dict) -> bool:
    """
    Verifies specs of type "evaluate_logarithm".
    Supports two schemas:
      A) { base, argument, answer }
      B) { expr, answer_expr }
    """
    # Schema A: explicit base & argument
    if {"base", "argument", "answer"} <= spec.keys():
        base = _to_expr(spec["base"])
        arg  = _to_expr(spec["argument"])
        got  = simplify(log(arg, base))
        want = _to_expr(spec["answer"])
        return _expressions_equal(got, want)

    # Schema B: generic diff-check
    if "expr" in spec and "answer_expr" in spec:
        diff = simplify(_to_expr(spec["expr"]) -
                        _to_expr(spec["answer_expr"]))
        return diff == 0

    raise KeyError("evaluate_logarithm needs either (base,argument,answer) or (expr,answer_expr)")

def _verify_evaluate(spec: dict) -> bool:
    """
    Verifies specs of type "evaluate" or "evaluate_expression".
    Expects either:
      - "expr" key, or
      - "expression" key,
    plus:
      - "answer_expr": the proposed numerical/symbolic result
    """
    # pick whichever key is present
    if "expr" in spec:
        raw = spec["expr"]
    elif "expression" in spec:
        raw = spec["expression"]
    else:
        raise KeyError("Missing 'expr' or 'expression' in spec")

    # compute the difference and check if it simplifies to zero
    diff = simplify(_to_expr(raw) - _to_expr(spec["answer_expr"]))
    return diff == 0