import re
import json
import logging
from typing import List, Dict
from dataclasses import dataclass

from openai import OpenAI

logger = logging.getLogger(__name__)

# ─────────────── CONFIG ───────────────
OPENAI_API_KEY = "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"
OPENAI_MODEL   = "gpt-4o-mini" 
PROBLEMS_JSON_PATH = "problems.json"
# ────────────────────────────────────────

client = OpenAI(api_key=OPENAI_API_KEY)

logger = logging.getLogger(__name__)

@dataclass
class ProblemExample:
    definition: str
    solution: str

def get_examples_from_json(
    topic: str,
    difficulty: str,
    json_file_path: str = PROBLEMS_JSON_PATH,
    max_examples: int = 10
) -> List[ProblemExample]:
    """
    Load up to `max_examples` examples from problems.json filtered by topic & difficulty,
    assuming a nested JSON structure:
      {
        "TOPIC1": {
          "A": [ { "definition": "...", "solution": "..." }, … ],
          "B": [ … ],
          "C": [ … ]
        },
        "TOPIC2": { … }
      }
    """
    try:
        with open(json_file_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Failed loading JSON examples: %s", e)
        return []

    examples: List[ProblemExample] = []
    # Only nested dict-of-dicts supported:
    if isinstance(data, dict) and topic in data:
        topic_block = data[topic]
        if isinstance(topic_block, dict):
            raw_list = topic_block.get(difficulty, [])
            from random import shuffle
            shuffle(raw_list)
        else:
            raw_list = []
    else:
        raw_list = []

    for item in raw_list[:max_examples]:
        examples.append(ProblemExample(
            definition=item.get("definition", ""),
            solution=item.get("solution", "")
        ))

    # <— Return after collecting all items, not inside the loop
    return examples





def generate_mixed_difficulty_problems(
    topic: str,
    counts: Dict[str,int],        # e.g. {"A":3, "B":3, "C":3}
    max_examples_per_diff: int = 5,
    model: str | None = None,
    temperature: float = 0.5,
    max_tokens: int = 1200
) -> List[Dict[str,str]]:
    """
    1) Tells GPT exactly Topic + how many A/B/C
    2) Seeds with any examples you have
    3) Falls back if no examples for a diff
    4) Parses and tags each problem with its difficulty
    """
    model = model or OPENAI_MODEL
    total = sum(counts.values())

    # 1) Build the examples blocks & write to ai_example2.txt
    examples_blocks = []
    for diff in ["A","B","C"]:
        cnt = counts.get(diff,0)
        if cnt <= 0:
            continue

        exs = get_examples_from_json(topic, diff, max_examples=max_examples_per_diff)
        labels = {"A": "easy – single idea, 1‑2 steps",
                "B": "medium – multi‑step, combine two ideas",
                "C": "hard – olympiad/insight or proof sketch"}
        if exs:
            block = f"## Examples for difficulty {diff} — {labels[diff]}:\n"
            for ex in exs:
                block += f"Problem: {ex.definition}\nSolution: {ex.solution}\n\n"
        else:
            block = f"## No past examples for difficulty {diff}; please generate {cnt} new { 'easy' if diff=='A' else 'medium' if diff=='B' else 'hard' } problems on the same topic.\n\n"
            logger.warning("No JSON examples for %s/%s", topic, diff)

        examples_blocks.append(block)

    examples_text = "\n".join(examples_blocks)

    # persist seed examples for audit
    try:
        with open("ai_example2.txt","a",encoding="utf-8") as f2:
            f2.write(f"=== Topic: {topic}; Counts: {counts} ===\n")
            f2.write(examples_text + "\n\n")
    except Exception as e:
        logger.error("Failed to write ai_example2.txt: %s", e)

    # 2) Build a super‐explicit prompt
    prompt = f"""
Topic: {topic}

I want a total of {total} problems, broken down by difficulty:
- {counts.get('A',0)} easy (A)
- {counts.get('B',0)} medium (B)
- {counts.get('C',0)} hard (C)

Generate a new, original high school math problem similiar to the examples below with the output formatted in LaTeX and the language in English. The topic is in estonian. 
Calculate the problem and show your calculations step by step and the final answer in the solution. Ensure the answer is correct and also in latex. Add behind each Number the difficulty level of the problem.
Number them 1)…{total} in this format:

1) <definition>
   <solution>

2) <definition>
   <solution>

…through {total}.

Here are past examples or instructions for each difficulty:

{examples_text}

Your response MUST strictly follow the numbering and formatting above, and must only contain the problems and solutions.
"""

    # 3) Call GPT
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"user", "content":prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        raw = resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("OpenAI API error: %s", e)
        raise

    # log raw GPT reply
    try:
        with open("ai_raw_output2.txt","a",encoding="utf-8") as f3:
            f3.write(f"=== Raw AI for {topic} {counts} ===\n")
            f3.write(raw + "\n\n")
    except Exception as e:
        logger.error("Failed to write ai_raw_output.txt: %s", e)

    # 4) Parse & tag
    pieces = re.split(r"^\s*\d+\)\s*", raw, flags=re.MULTILINE)[1:]
    problems: List[Dict[str,str]] = []
    idx = 0
    for diff in ["A","B","C"]:
        n = counts.get(diff,0)
        for _ in range(n):
            if idx >= len(pieces):
                break
            block = pieces[idx].strip()
            idx += 1
            lines = block.split("\n",1)
            problems.append({
                "definition": lines[0].strip(),
                "solution":   (lines[1].strip() if len(lines)>1 else ""),
                "difficulty": diff,
                "topic":      topic,
            })

    if len(problems) < total:
        logger.warning("Expected %d problems but parsed %d.\nRaw:\n%s", total, len(problems), raw)

    return problems


def generate_problems_with_ai(
    topic: str,
    difficulty: str,
    count: int,
    max_examples: int = 3,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 800
) -> List[Dict[str, str]]:
    """
    Back-compat wrapper so old views/models importing generate_problems_with_ai
    continue to work by routing to our mixed-difficulty batcher.
    """
    # Build a single-difficulty dict for the mixed generator:
    counts = {difficulty: count}
    return generate_mixed_difficulty_problems(
        topic=topic,
        counts=counts,
        max_examples_per_diff=max_examples,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

# And if you still have views calling the old alias:
def generate_ai_test_problems(topic: str, difficulty: str, count: int):
    return generate_problems_with_ai(topic, difficulty, count)