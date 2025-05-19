import json
import logging
import time
from dataclasses import dataclass
from typing import Dict, List
from app.models import get_short_lang
from openai import OpenAI
import os
# SymPy‑powered verification helper
from .validators import verify

logger = logging.getLogger(__name__)

# ─────────────── CONFIG ───────────────
OPENAI_API_KEY      = os.environ.get("MY_API_KEY")                         # put in .env in production!
OPENAI_MODEL        = "gpt-4.1-mini"
# gpt-4.1-mini , gpt-4o-mini, gpt-4.1-nano,
PROBLEMS_JSON_PATH  = "problems.json"             # seed examples
RAW_LOG_PATH        = "ai_raw_output2.txt"        # full AI reply
PROMPT_LOG_PATH     = "ai_example2.txt"           # prompt snippet

client = OpenAI(api_key=OPENAI_API_KEY)
# ───────────────────────────────────────


# ────────────────────────── helpers ──────────────────────────
@dataclass
class ProblemExample:
    definition_et: str = ""
    definition_en: str = ""
    solution: str = ""
    spec: dict | None = None


def _load_examples(
    topic: str,
    difficulty: str,
    json_file_path: str = PROBLEMS_JSON_PATH,
    max_examples: int = 10,
) -> List[ProblemExample]:
    """Pull up to `max_examples` rows for the prompt."""
    try:
        with open(json_file_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Failed loading JSON examples: %s", e)
        return []

    raw_list = (
        data.get(topic, {}).get(difficulty, []) if isinstance(data, dict) else []
    )
    from random import shuffle

    shuffle(raw_list)

    examples = []
    for item in raw_list[:max_examples]:
        examples.append(
            ProblemExample(
                definition_et=item.get("definition_et", ""),
                definition_en=item.get("definition_en", ""),
                solution=item.get("solution", ""),
                spec=item.get("spec"),          # may be None
            )
        )
    return examples


# ────────────────────────── generator ──────────────────────────

def generate_mixed_difficulty_problems(
    topic: str,
    counts: Dict[str, int],  # e.g. {"A": 3, "B": 3, "C": 3}
    max_examples_per_diff: int = 2,
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 4500,
    lang: str | None = None 
) -> List[Dict[str, str]]:
    """
    Return a verified list of problem dicts, each carrying:
        {"spec": ..., "definition_et": ..., "definition_en": ..., "difficulty": ...}

    The caller can specify `lang` – "et" or "en" – to indicate which language
    should be used for the problem wording.  Only that language will be shown
    in the few‑shot examples and the AI will be instructed to output the
    wording in the same language (filling only the corresponding definition
    field and leaving the other empty).
    """

    logger.debug("AI-generator language detected by get_short_lang(): %s", lang)
    language_name = "Estonian" if lang == "et" else "English"

    model = model or OPENAI_MODEL
    total = sum(counts.values())

    # 1)  Few‑shot examples
    example_chunks: list[str] = []
    diff_labels = {"A": "easy", "B": "medium", "C": "hard"}

    for diff in "ABC":
        need = counts.get(diff, 0)
        if need == 0:
            continue

        exs = _load_examples(topic, diff, max_examples=max_examples_per_diff)
        if exs:
            chunk: list[str] = [f"# {diff_labels[diff]} EXAMPLES"]
            for e in exs:
                # Only keep the examples in the desired language
                if lang == "et":
                    chunk.append(f" definition:  {e.definition_et}")
                else:
                    chunk.append(f" definition:  {e.definition_en}")
                chunk.append(f" solution: {e.solution}")
                if e.spec:
                    chunk.append(f" spec: {json.dumps(e.spec, ensure_ascii=False)}")
            example_chunks.append("\n".join(chunk))

    examples_text = "\n\n".join(example_chunks)

    # 2)  Log the few‑shot block

    # 3)  Build the prompt
    prompt = f"""
### TASK
Generate {total} new **high‑school mathematics problems** on the topic \"{topic}\" based on the examples given below.

### LANGUAGE
Write the *definition* in **{language_name}**. **Wrap the entire definition and solution in exactly one pair of `$` characters.**

### DIFFICULTY DISTRIBUTION (must match exactly)
A (easy): {counts.get('A',0)}  B (medium): {counts.get('B',0)}  C (hard): {counts.get('C',0)}

### SOLUTION 
You must solve the problems you generated step by step and show the result in solutions. SHOW THE STEPS MATHEMATICALLY, NO TEXTUAL EXPLANATIONS OR WORDS. the steps in solution should be short.
Wrap the *whole derivation* in one pair of `$` as in this example:
"$5*3x+2=15x+2$"
– For evaluation tasks, avoid approximations; compute symbolic/numeric values exactly.
MOST IMPORTANT.MAKE SURE THE ANSWER IS CORRECT.

The spec fields must be sympy parsable, for verification. Use the keys from the examples.
### OUTPUT – ONE JSON OBJECT PER LINE
{{
  "difficulty": "A" | "B" | "C",
  "definition": "$…$",  # problem wording in {language_name}
  "solution"  : "$…$",  # derivation as described above
  "spec": {{
      "type"       : string,           

  }}
}}

### STRICT RULES
1. **Start and end both `definition` and `solution` with `$`.**. Use \\text for text in math mode.
2. **Return only JSON lines – no Markdown, no back‑ticks, no extra commentary.**
3. Use `*` for multiplication and `**` for powers inside `spec` (never `^`).
4. Write every backslash as `\\` in the JSON output for python to parse it correctly. DO ONLY DOUBLE BACKSLASHES

### Make your problems similiar to the examples below. 
{examples_text}
"""

    # 4)  OpenAI call
    try:
        t_ai0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        raw_text = resp.choices[0].message.content.strip()
        t_ai1 = time.perf_counter()
    except Exception as e:
        logger.error("OpenAI error: %s", e)
        raise

    # 5)  Save raw model reply

    # 6)  Parse & verify
    problems: list[dict] = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            ok, _msg = verify(obj["spec"])
        except Exception as e:
            logger.error("verify() crashed: %s", e)
            ok = False

        if not ok:
            logger.warning("Failed verification, skipping: %s", line[:120])
            continue

        # Make sure language rule is respected; if not, fix keys to always exist
        problems.append(obj)
        t_verify_done = time.perf_counter()
        logger.info(
            "TIMES ai=%4.1fs verify=%4.1fs",
            t_ai1 - t_ai0,
            t_verify_done - t_ai1,
        )
    if len(problems) < total:
        logger.warning(
            "Needed %d problems, validated %d (raw lines %d)",
            total, len(problems), len(raw_text.splitlines())
        )

    return problems


# ─────────────────── compatibility wrappers ───────────────────

def generate_problems_with_ai(
    topic: str,
    difficulty: str,
    count: int,
    max_examples: int = 3,
    model: str | None = None,
    temperature: float = 0.6,
    max_tokens: int = 2000,
    *,
    lang: str = "et",
) -> List[Dict[str, str]]:
    """Legacy single‑difficulty wrapper."""
    return generate_mixed_difficulty_problems(
        topic=topic,
        counts={difficulty: count},
        max_examples_per_diff=max_examples,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        lang=lang,
    )


def generate_ai_test_problems(topic: str, difficulty: str, count: int, *, lang: str = "et"):
    """Old alias kept alive for imports that haven’t migrated."""
    return generate_problems_with_ai(topic, difficulty, count, lang=lang)
