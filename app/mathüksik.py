import os
import logging
import json
import re
from dataclasses import dataclass
from openai import OpenAI

# Initialize your OpenAI client (replace with your actual key)
client = OpenAI(api_key="YOUR_API_KEY_HERE")

logging.basicConfig(level=logging.INFO)

@dataclass
class ProblemExample:
    definition: str
    solution: str


def get_examples_from_json(
    topic: str,
    difficulty: str,
    json_file_path: str = "problems.json"
) -> list[ProblemExample]:
    """
    Load example problems from a JSON database structured by topic and difficulty.

    Expected structure:
    {
      "TOPIC1": {
        "A": [ {"definition": "...", "solution": "..."}, ... ],
        "B": [...],
        "C": [...]
      },
      ...
    }
    """
    try:
        with open(json_file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception as e:
        logging.error("Failed to load JSON file '%s': %s", json_file_path, e)
        return []

    examples: list[ProblemExample] = []
    if isinstance(data, dict) and topic in data:
        topic_entry = data[topic]
        if isinstance(topic_entry, dict):
            for item in topic_entry.get(difficulty, []):
                examples.append(ProblemExample(
                    definition=item.get("definition", ""),
                    solution=item.get("solution", "")
                ))
    elif isinstance(data, list):
        for item in data:
            if (
                isinstance(item, dict)
                and item.get("topic") == topic
                and item.get("difficulty") == difficulty
            ):
                examples.append(ProblemExample(
                    definition=item.get("definition", ""),
                    solution=item.get("solution", "")
                ))
    else:
        logging.error("Unexpected JSON structure in '%s'.", json_file_path)

    return examples


def format_math_expression(raw_text: str) -> str:
    """
    Wrap the math part of raw_text in LaTeX math delimiters ($...$).

    Splits on the first colon to separate a label if present.
    """
    if ":" in raw_text:
        label, expr = raw_text.split(":", 1)
        label = label.strip() + ":"
        expr = expr.strip()
    else:
        label = ""
        expr = raw_text.strip()

    if not (expr.startswith("$") and expr.endswith("$")):
        expr = f"${expr}$"

    return f"{label} {expr}" if label else expr


def generate_problem_with_ai(topic: str, difficulty: str) -> dict:
    """
    Generate a new, original high school math problem and its solution using GPT.

    Returns:
        { "definition": <latex-formatted problem>, "solution": <latex-formatted solution> }
    """
    # Fetch guidance examples
    examples = get_examples_from_json(topic, difficulty)
    examples_text = "Here are some examples:\n\n"
    for idx, ex in enumerate(examples, start=1):
        examples_text += (
            f"Example {idx}:\n"
            f"  Problem:  {ex.definition}\n"
            f"  Solution: {ex.solution}\n\n"
        )

    # Build AI prompt
    prompt = (
        "Generate a new, original high school math problem and a solution, "
        "with the math formatted in LaTeX and the language in Estonian. "
        "Use only ASCII characters (no special Estonian letters).\n"
        "Include randomness so that the problems differ and follow the same format as the examples.\n\n"
        f"{examples_text}"
        "Now generate a completely new problem for the following parameters:\n"
        f"Topic: {topic}\n"
        f"Difficulty: {difficulty}\n\n"
        "Calculate the answer and include it in the response. Ensure correctness.\n"
        "Return strictly in this format without extra commentary:\n"
        "<definition>\n"
        "<solution>\n"
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7
    )

    ai_output = response.choices[0].message.content.strip()

    # Log raw AI output for auditing
    try:
        with open("ai_raw_output.txt", "a", encoding="utf-8") as f:
            f.write(f"Topic: {topic}, Difficulty: {difficulty}\n{ai_output}\n\n")
    except Exception as e:
        logging.error("Failed to save AI output: %s", e)

    # Split into definition and solution
    if "Solution:" in ai_output:
        parts = ai_output.split("Solution:", 1)
        definition = parts[0].strip()
        solution = parts[1].strip()
    else:
        definition = ai_output
        solution = "Solution not generated; please try again."

    return {
        "definition": format_math_expression(definition),
        "solution": solution
    }


def generate_ai_test_problems(topic: str, difficulty: str, count: int) -> list:
    """
    Generate a list of math problems using GPT for a given topic and difficulty.
    """
    return [generate_problem_with_ai(topic, difficulty) for _ in range(count)]
