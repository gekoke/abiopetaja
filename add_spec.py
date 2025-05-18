"""
add_spec.py
-----------
Convert every entry in problems.json to include a structured `spec`.
Writes problems_with_spec.json
"""
import json, sys, sympy as sp
from pathlib import Path
from sympy.parsing.latex import parse_latex

SRC  = Path("problems.json")
DEST = Path("problems_with_spec.json")

def to_sym(tex: str) -> str:
    """Remove outer $...$ and convert LaTeX → SymPy string."""
    return str(parse_latex(tex.strip().lstrip("$").rstrip("$")))

def extract_expr(sentence: str) -> str:
    """Take the substring after the last colon (:) and strip spaces."""
    return sentence.split(":")[-1].strip()

def build_spec(entry: dict) -> dict:
    # pick whichever wording key exists
    tex_sentence = (
        entry.get("definition_et")
        or entry.get("definition")
        or entry.get("definition_en")
    )
    if not tex_sentence:
        raise ValueError("No definition_* key found")

    expr_tex = extract_expr(tex_sentence)
    ans_tex  = entry["solution"]

    return {
        "type": "simplify",
        "expr": to_sym(expr_tex),
        "answer_expr": to_sym(ans_tex),
    }

def main():
    if not SRC.exists():
        sys.exit(f"File {SRC} not found")

    data = json.loads(SRC.read_text(encoding="utf-8"))

    failures = 0
    for topic_block in data.values():
        for diff_list in topic_block.values():
            for obj in diff_list:
                try:
                    obj["spec"] = build_spec(obj)
                except Exception as e:
                    failures += 1
                    print("\nFAILED ON OBJECT:\n", json.dumps(obj, ensure_ascii=False, indent=2),
                          "\nReason:", e, file=sys.stderr)

    DEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {DEST}  ({failures} failures)")

if __name__ == "__main__":
    main()
