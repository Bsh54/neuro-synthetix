"""Extraction de mots-cles cliniques a partir d'un texte libre (multilingue).

Utilise le lexique centralise de conditions.py (EN / FR / hindi translittere).
Simple, rapide, hors-ligne. On pourra brancher un LLM plus tard sans changer
l'interface.
"""
from __future__ import annotations

import re

from .conditions import SYMPTOM_LEXICON


def extract_keywords(text: str) -> list[str]:
    """Retourne la liste des symptomes canoniques detectes dans le texte."""
    if not text:
        return []
    low = " " + re.sub(r"\s+", " ", text.lower()) + " "
    found: list[str] = []
    for canonical, variants in SYMPTOM_LEXICON.items():
        if any(v in low for v in variants):
            found.append(canonical)
    return found
