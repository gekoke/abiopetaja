############################ math.py ################################
# Local generation with Qwen/Qwen2.5‑Math‑7B‑Instruct (plain FP16)
# All text **must be English**.
# All mathematics **must be written in LaTeX math mode**, i.e. wrap
#   inline formulas in `$ ... $` and multi‑line in `$$ ... $$` or `\[ ... \]`.
########################################################################

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import List

# import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer

###############################################################################
# Model initialisation (loads once per process)
###############################################################################
_MODEL_NAME = "Qwen/Qwen2.5-Math-7B-Instruct"
_tokenizer = AutoTokenizer.from_pretrained(
    _MODEL_NAME,
    trust_remote_code=True,
)
_model = AutoModelForCausalLM.from_pretrained(
    _MODEL_NAME,
    #  torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True,
)
_streamer = TextStreamer(_tokenizer, skip_prompt=True, skip_special_tokens=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

###############################################################################
# Helper dataclass and JSON example‑loading utilities
###############################################################################


@dataclass
class ProblemExample:
    definition: str
    solution: str


def _read_json(path: str | os.PathLike) -> object | None:
    try:
        with open(path, "r", encoding="utf‑8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Example JSON file '%s' not found", path)
    except json.JSONDecodeError as e:
        logger.error("Malformed JSON in '%s': %s", path, e)
    return None


def get_examples_from_json(
    topic: str,
    difficulty: str,
    json_file_path: str | os.PathLike = "problems.json",
) -> List[ProblemExample]:
    """Return a list of `ProblemExample`s filtered by *topic* and *difficulty*."""
    data = _read_json(json_file_path)
    if data is None:
        return []

    examples: List[ProblemExample] = []

    if isinstance(data, dict):
        topic_entry = data.get(topic)
        if isinstance(topic_entry, dict):
            for item in topic_entry.get(difficulty, []):
                examples.append(
                    ProblemExample(
                        definition=item.get("definition", ""),
                        solution=item.get("solution", ""),
                    )
                )
        else:  # flat dict list per topic
            for item in topic_entry or []:
                if item.get("difficulty") == difficulty:
                    examples.append(
                        ProblemExample(
                            definition=item.get("definition", ""),
                            solution=item.get("solution", ""),
                        )
                    )
    elif isinstance(data, list):  # completely flat
        for item in data:
            if (
                isinstance(item, dict)
                and item.get("topic") == topic
                and item.get("difficulty") == difficulty
            ):
                examples.append(
                    ProblemExample(
                        definition=item.get("definition", ""),
                        solution=item.get("solution", ""),
                    )
                )
    else:
        logger.error("Unexpected JSON schema in '%s'", json_file_path)

    return examples


###############################################################################
# Utility for light post‑processing (optional)
###############################################################################


def format_math_expression(raw_text: str) -> str:
    """Ensure math part is wrapped in `$ ... $` if the problem statement includes a label."""
    if ":" in raw_text:
        label, expr = raw_text.split(":", 1)
        label = label.strip() + ":"
        expr = expr.strip()
    else:
        label, expr = "", raw_text.strip()

    if not (expr.startswith("$") and expr.endswith("$")):
        expr = f"${expr}$"
    return f"{label} {expr}" if label else expr


###############################################################################
# LLM wrapper
###############################################################################


def _generate_with_llm(prompt: str, max_new_tokens: int = 512, temperature: float = 0.7) -> str:
    """Query Qwen model and return decoded text."""
    input_ids = _tokenizer(prompt, return_tensors="pt").to(_model.device).input_ids


#    with torch.no_grad():
#       output_ids = _model.generate(
#          input_ids,
#         max_new_tokens=max_new_tokens,
#        do_sample=True,
#       temperature=temperature,
#      streamer=None,  # not streaming because we need full text
# )
# return _tokenizer.decode(output_ids[0][input_ids.shape[-1] :], skip_special_tokens=True).strip()


###############################################################################
# Public API – generate_problem_with_ai / generate_ai_test_problems
###############################################################################


def _build_prompt(topic: str, difficulty: str, examples: List[ProblemExample]) -> str:
    examples_txt = "\n".join(
        f"### Example {i+1}\nProblem: {ex.definition}\nSolution: {ex.solution}"
        for i, ex in enumerate(examples[:3])
    )
    return (
        "You are a helpful mathematical problem composer. "
        "Create a *new* high‑school mathematics problem and its fully worked solution.\n"
        "Requirements:\n"
        "- **Language:** English only.\n"
        "- **Math:** Every mathematical expression *must* be in LaTeX (math mode).\n"
        "  Use inline `$ ... $` for short expressions and `\\[ ... \\]` for multi‑line when necessary.\n"
        "- Include enough randomness so that consecutive calls differ.\n"
        "- Follow the structural pattern shown in the examples below.\n"
        "- At the end, verify your answer by recomputing. If you find a mistake, correct it before replying.\n"
        "- Output *only* two paragraphs, with no extra commentary:\n"
        "  1️⃣ The problem statement (labelled 'Problem:').\n"
        "  2️⃣ The solution (labelled 'Solution:').\n"
        "### Topic: {topic}\n"
        "### Difficulty: {difficulty}\n"
        "\n"
        f"{examples_txt}\n\n"
        "### Your Turn\n"
        "Problem:"
    )


def generate_problem_with_ai(topic: str, difficulty: str) -> dict[str, str]:
    """Return a dict containing 'definition' and 'solution' generated by Qwen."""
    examples = get_examples_from_json(topic, difficulty)
    prompt = _build_prompt(topic, difficulty, examples)

    logger.info("[LLM‑call] generating problem for topic=%s difficulty=%s", topic, difficulty)
    ai_output = _generate_with_llm(prompt, max_new_tokens=512, temperature=0.7)

    # Capture first occurrence of "Solution:" (case‑insensitive)
    match = re.search(r"(?i)solution:\s*", ai_output)
    if match:
        def_part = ai_output[: match.start()].strip()
        sol_part = ai_output[match.end() :].strip()
    else:
        def_part, sol_part = ai_output, "Solution not generated; please retry."

    # Append to logs for debugging
    try:
        with open("ai_raw_output.txt", "a", encoding="utf‑8") as f:
            f.write(f"Topic: {topic} | Difficulty: {difficulty}\n{ai_output}\n\n")
    except Exception as e:
        logger.error("Failed writing raw output: %s", e)

    return {
        "definition": format_math_expression(def_part),
        "solution": sol_part,
    }


def generate_ai_test_problems(topic: str, difficulty: str, count: int) -> list[dict[str, str]]:
    """Generate *count* problems via `generate_problem_with_ai`."""
    return [generate_problem_with_ai(topic, difficulty) for _ in range(count)]


###############################################################################
# __main__ quick testcase (optional)
###############################################################################

if __name__ == "__main__":
    sample = generate_problem_with_ai("ALGEBRA", "A")
    print("\n# Generated Problem\n", sample["definition"])
    print("\n# Solution\n", sample["solution"])
