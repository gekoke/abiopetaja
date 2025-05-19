# app/topics.py  –  lightweight helpers for topic codes & labels
#
# Public helpers
# --------------
#     get_all_topic_codes()    -> List[str]
#     get_all_topic_choices()  -> List[Tuple[str, str]]
#
# Both read the top-level keys of problems.json at runtime, so any new
# topic you add to the JSON file appears automatically in forms/admin.

from __future__ import annotations

import json
import logging
import os
from typing import List, Tuple

from django.conf import settings
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------.
# Optional: provide prettier / translated labels for known topic codes.
# If a code is missing, we fall back to a prettified version of the code.
# ---------------------------------------------------------------------------.
DEFAULT_TRANSLATIONS = {
    "AVALDISED": _("Avaldised"),
    "EKSPONENT/LOGARITM VÕRRANDID JA VÕRRATUSED": _("Eksponent/logaritm võrrandid ja võrratused"),
    "EKSPONENTFUNKTSIOON": _("Eksponentfunktsioon"),
    "LOGARITMI_DEFINITSIOON": _("Logaritmi definitsioon"),
    "MATEMAATIKA RAKENDUSED": _("Matemaatika rakendused"),
    "TRIGONOMEETRIA_II": _("Trigonometria II"),
    "TRIGONOMEETRILISED_AVALDISED": _("Trigonometrilised avaldised"),
    "VÕRRANDID_JA_VÕRRANDISÜSTEEMID": _("Võrrandid ja võrrandisüsteemid"),
}
    # add more overrides here if you like


ALLOWED_TOPICS: List[str] = [
    "AVALDISED",
    "EKSPONENT/LOGARITM VÕRRANDID JA VÕRRATUSED",
    "EKSPONENTFUNKTSIOON",
    "LOGARITMI_DEFINITSIOON",
    "MATEMAATIKA RAKENDUSED",
    "TRIGONOMEETRIA_II",
    "TRIGONOMEETRILISED_AVALDISED",
    "VÕRRANDID_JA_VÕRRANDISÜSTEEMID",
]

# ---------------------------------------------------------------------------.
# Internal utility
# ---------------------------------------------------------------------------.
def _load_json_topics() -> List[str]:
    """Load the list of topic codes defined as top-level keys in problems.json."""
    problems_path = os.path.join(settings.BASE_DIR, "problems.json")
    try:
        with open(problems_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return list(data.keys())
    except FileNotFoundError:
        logger.error("File %s not found – returning empty topic list", problems_path)
    except Exception as exc:  # pragma: no cover
        logger.error("Error reading %s: %s", problems_path, exc)
    return []


# ---------------------------------------------------------------------------.
# Public helpers
# ---------------------------------------------------------------------------.
def get_all_topic_codes() -> List[str]:
    """Return every topic code present in problems.json (order as appears)."""
    return ALLOWED_TOPICS


def get_all_topic_choices() -> List[Tuple[str, str]]:
    """Return (code, human-label) tuples for forms & admin `choices=` arguments."""
    codes = get_all_topic_codes()
    choices: List[Tuple[str, str]] = []
    for code in codes:
        label = DEFAULT_TRANSLATIONS.get(code)
        if label is None:
            # fallback: prettify the code – replace underscores, title-case
            label = _(code.replace("_", " ").title())
        choices.append((code, label))
    return choices
