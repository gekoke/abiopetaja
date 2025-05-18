# validators.py  ─── add at top
from sympy import Eq, S, simplify, solveset, symbols
from sympy.parsing.sympy_parser import parse_expr
import logging
import random
# … keep your existing imports …

# ───────────────── helpers ─────────────────
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


# ───────────────── main verifier ─────────────────
def verify(spec: dict) -> tuple[bool, str]:
    logger = logging.getLogger(__name__)
    """
    Return (is_ok, kind).  Supports: simplify, evaluate, simplify_then_evaluate,
    solve, simplify_then_solve … extend further as you add more types.
    """
    kind = spec.get("type")
    logger.debug(">> verify START: kind=%r, spec=%r", kind, spec)
    try:
        # 1)  Simplify  ────────────────────────────
        if  kind == "evaluate":
            ans_expr = spec.get("answer_expr")
            expr = spec.get("expr")
            diff = simplify(_to_expr(expr) - _to_expr(ans_expr))
            logger.debug(" evaluate: expr=%r  ans_expr=%r diff=%r", expr, ans_expr, diff)
            ok = diff == 0
        elif kind == "simplify" or kind == "simplify_then_evaluate":
            expr = _to_expr(spec["expr"])
            ref  = _to_expr(spec["answer_expr"])
            ok   = _expressions_equal(expr, ref)
            logger.debug(" %r: expr=%r  ans_expr=%r diff=%r", kind, expr, ref, ok)



        # 3)  Simplify → Evaluate  ─────────────────
        

        # 4)  Solve linear/quad/etc. equations  ────

        else:
            ok = False

        return ok, kind

    except Exception as e:
        return False, f"Exception: {e}"

"""elif kind == "simplify_then_evaluate":
            # 3 a) algebraic part
            simplified = simplify(_to_expr(spec["expr"]))
            ans_expr = spec.get("answer_expr")
            ok1 = simplify(simplified - _to_expr(ans_expr)) == 0

            # 3 b) numeric part — two possible schemas
            if "vars" in spec and "answer" in spec:
                subs = {symbols(k): _to_expr(v) for k, v in spec["vars"].items()}
                num_val = simplified.subs(subs).evalf()
                ok2 = simplify(num_val - _to_expr(spec["answer"])) == 0
            elif "follow_up" in spec:
                fu_expr = _to_expr(spec["follow_up"]["expr"])
                fu_ans  = _to_expr(spec["follow_up"]["answer"])
                ok2 = simplify(fu_expr.evalf() - fu_ans) == 0
            else:          # only the simplification was requested
                ok2 = True

            ok = ok1 and ok2"""