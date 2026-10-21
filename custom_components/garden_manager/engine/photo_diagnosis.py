"""Photo diagnosis (2.1): what to ask an AI model about a plant photo, and how to read its answer.

The model only chooses from the pests and diseases Hortulus knows (the crops' own tags first), so the
answer always leads to the organic advice in the knowledge base - an answer outside the list is kept
as "other" with the model's own words.  Pure: the Home Assistant side sends the request through an
``ai_task`` entity.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .i18n import normalize_lang
from .plantdb import PlantDatabase
from .qa_kb import DISEASES, PESTS

HEALTHY = "healthy"
OTHER = "other"
LANGUAGE_NAMES = {"en": "English", "nl": "Dutch", "fr": "French", "de": "German"}


def _text(table: Mapping[str, Mapping[str, str]], key: str, lang: str) -> str:
    entry = table.get(key, {})
    return entry.get(lang) or entry.get("en") or ""


def label(problem_id: str, lang: str | None) -> str:
    """The problem's name: the knowledge base writes "Name: advice"."""
    lang = normalize_lang(lang)
    text = _text(PESTS, problem_id, lang) or _text(DISEASES, problem_id, lang)
    return text.split(":", 1)[0].strip() if text else problem_id.replace("_", " ")


def remedy(problem_id: str, lang: str | None) -> str:
    lang = normalize_lang(lang)
    text = _text(PESTS, problem_id, lang) or _text(DISEASES, problem_id, lang)
    return text.split(":", 1)[1].strip() if ":" in text else text


def candidates(db: PlantDatabase, plant_ids: Iterable[str], lang: str | None) -> list[dict[str, Any]]:
    """The problems the model may choose from: the crops' own pests and diseases first, then the rest."""
    own: list[str] = []
    for pid in plant_ids:
        plant = db.get(pid)
        if plant is None:
            continue
        own += [tag for tag in (*plant.pests, *plant.diseases) if tag in PESTS or tag in DISEASES]
    ordered = list(dict.fromkeys(own)) + sorted(k for k in (*PESTS, *DISEASES) if k not in own)
    return [
        {"id": key, "name": label(key, "en"), "kind": "pest" if key in PESTS else "disease", "likely": key in own}
        for key in ordered
    ]


def instructions(crops: list[str], options: list[dict[str, Any]], lang: str | None) -> str:
    """The question for the model (in English, answered in the gardener's language)."""
    language = LANGUAGE_NAMES.get(normalize_lang(lang), "English")
    likely = ", ".join(o["id"] for o in options if o.get("likely")) or "none"
    listing = "\n".join(f"- {o['id']}: {o['name']} ({o['kind']})" for o in options)
    return (
        "You look at a photo from a vegetable garden and say what is wrong with the plant, if anything.\n"
        f"Crops growing here: {', '.join(crops) or 'unknown'}.\n"
        f"Most likely for these crops: {likely}.\n"
        f"Choose problem_id from this list, or '{HEALTHY}' when the plant looks healthy, or '{OTHER}' when "
        "it is something else (nutrient shortage, drought, sunburn, frost damage ...):\n"
        f"{listing}\n"
        "Give confidence 0-100. Explain in one or two short sentences what you see that points to it. "
        f"Write explanation and other_problem in {language}. Do not guess wildly: a blurry or unclear photo "
        "gets a low confidence."
    )


def structure() -> dict[str, Any]:
    """The answer's fields (ai_task ``structure``)."""
    return {
        "problem_id": {
            "description": "An id from the list, 'healthy' or 'other'",
            "required": True,
            "selector": {"text": {}},
        },
        "confidence": {"description": "0-100", "required": True, "selector": {"number": {"min": 0, "max": 100}}},
        "explanation": {"description": "What in the photo points to it", "required": True, "selector": {"text": {}}},
        "other_problem": {"description": "Name of the problem when problem_id is 'other'", "selector": {"text": {}}},
    }


def interpret(answer: Any, options: list[dict[str, Any]], lang: str | None) -> dict[str, Any]:
    """The model's answer as Hortulus shows it: known problem + organic advice, or its own words."""
    data = answer if isinstance(answer, Mapping) else {}
    known = {o["id"]: o for o in options}
    pid = str(data.get("problem_id") or "").strip().lower().replace(" ", "_").replace("-", "_")
    try:
        confidence = max(0, min(100, round(float(data.get("confidence") or 0))))
    except (TypeError, ValueError):
        confidence = 0
    explanation = str(data.get("explanation") or "").strip()[:600]
    if pid == HEALTHY:
        return {"problem_id": HEALTHY, "kind": HEALTHY, "name": "", "confidence": confidence,
                "explanation": explanation, "remedy": "", "known": True}  # fmt: skip
    if pid in known:
        return {"problem_id": pid, "kind": known[pid]["kind"], "name": label(pid, lang), "confidence": confidence,
                "explanation": explanation, "remedy": remedy(pid, lang), "known": True}  # fmt: skip
    name = str(data.get("other_problem") or data.get("problem_id") or "").strip()[:120]
    return {"problem_id": OTHER, "kind": OTHER, "name": name, "confidence": confidence,
            "explanation": explanation, "remedy": "", "known": False}  # fmt: skip
