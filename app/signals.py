# app/signals.py  –  default templates + topic helpers  (May 2025)
import logging
from typing import Dict, List, Tuple

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from app.models import Template
from app.topics import get_all_topic_choices   # neutral helper → no circular import

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────
# 1.  13 põhikategooriat (mallinimed eesti keeles)
# ────────────────────────────────────────────────────────────────────────────
DEFAULT_TEMPLATE_TOPICS: List[Tuple[str, str]] = [
    "AVALDISED": _("Avaldised"),
    "EKSPONENT/LOGARITM VÕRRANDID JA VÕRRATUSED": _("Eksponent/logaritm võrrandid ja võrratused"),
    "EKSPONENTFUNKTSIOON": _("Eksponentfunktsioon"),
    "LOGARITMI_DEFINITSIOON": _("Logaritmi definitsioon"),
    "MATEMAATIKA RAKENDUSED": _("Matemaatika rakendused"),
    "TRIGONOMEETRIA_II": _("Trigonometria II"),
    "TRIGONOMEETRILISED_AVALDISED": _("Trigonometrilised avaldised"),
    "VÕRRANDID_JA_VÕRRANDISÜSTEEMID": _("Võrrandid ja võrrandisüsteemid"),
]

# ────────────────────────────────────────────────────────────────────────────
# 2.  Märksõnad → grupp (kohanda vastavalt oma problems.json-i koodidele)
# ────────────────────────────────────────────────────────────────────────────
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "AVALDISED": ["AVALDISED"],
    "EKSPONENT- ja LOGARITMFUNKTSIOON": ["EKSPONENT", "LOGARITM", "EKSPONENT/LOGARITM VÕRRANDID JA VÕRRATUSED"],
    "FUNKTSIOONID JA ARVJADAD": ["FUNKTSIOONID", "ARVJADAD"],
    "TRIGONOMEETRILISED I JA II": [
        "TRIGONOMEETRILISED_AVALDISED",
        "TRIGONOMEETRIA",
        "TÄISNURKSE_KOLMNURGA_LAHENDAMINE",
    ],
    "VÕRRANDID JA VÕRRANDISÜSTEEMID": ["VÕRRANDID_JA_VÕRRANDISÜSTEEMID"],
    "VÕRRATUSED JA VÕRRATUSESÜSTEEMID": [
        "VÕRRATUSED",
        "VÕRRATUSESÜSTEEMID",
        
    ],
    "VEKTOR TASANDIL JA JOONE VÕRRAND": ["VEKTOR_TASANDIL", "JOONE_VORRAND"],
    "TRIGONOMEETRILISED FUNKTSIOONID. FUNKTSIOONI PIIRVÄÄRTUS JA TULETIS": [
        "TRIGONOMEETRILISED FUNKTSIOONID",
        "FUNKTSIOONI PIIRVÄÄRTUS JA TULETIS",
    ],
    "TULETISE RAKENDUSED": ["TULETISE RAKENDUSED"],
    "INTEGRAAL ja PLANIMEETRIA": ["INTEGRAAL", "KUJUNDI PINDALA JA RUUMALA"],
    "SIRGE JA TASAND RUUMIS": [
        "SIRGE JA TASAND RUUMIS",
        "PUNKTI KOORDINAADID JA VEKTOR RUUMIS",
    ],
    "STEREOMEETRIA": ["STEREOMEETRIA"],
    "MATEMAATIKA RAKENDUSED, REAALSETE PROTSESSIDE UURIMINE": [
        "MATEMAATIKA RAKENDUSED",
        "TOENAOSUS",
        "STATISTIKA",
        "LIITPROTSENDID",
    ],
}

# ────────────────────────────────────────────────────────────────────────────
# 3.  Abifunktsioon ülesannete jaotamiseks
# ────────────────────────────────────────────────────────────────────────────
def _distribute(total: int, buckets: int) -> List[int]:
    """Jaotab 'total' võimalikult võrdselt 'buckets' hulka.
       Nt total=3, buckets=5  → [1,1,1,0,0]"""
    base, remainder = divmod(total, buckets)
    return [base + 1 if i < remainder else base for i in range(buckets)]


# ────────────────────────────────────────────────────────────────────────────
# 4.  Signaal – loo vaikemallid uuele kasutajale
# ────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender=User)
def add_default_templates(sender, instance: User, created: bool, **kwargs):
    """Iga kategooria saab 3 A + 3 B + 3 C ülesannet kokku."""
    if not created:
        return

    user = instance
    all_codes = get_all_topic_choices()

    for cat_code, cat_label in DEFAULT_TEMPLATE_TOPICS:
        keywords = CATEGORY_KEYWORDS.get(cat_code, [])
        subtopics = [
            code
            for code in all_codes
            if any(kw in code for kw in keywords)
        ] or [cat_code]  # tagavara

        template = Template.objects.create(name=cat_label, title=cat_label, author=user)

        for diff in ("A", "B", "C"):
            # jagame 3 ülesannet sub-teemade vahel
            shares = _distribute(3, len(subtopics))
            for topic_code, cnt in zip(subtopics, shares):
                if cnt:
                    template.add_problem(topic=topic_code, difficulty=diff, count=cnt)

        logger.info(
            "Loodud mall '%s' – %d alamteemat; 9 ülesannet (3+3+3)",
            cat_label,
            len(subtopics),
        )
