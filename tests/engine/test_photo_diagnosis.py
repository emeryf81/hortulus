"""Photo diagnosis: the question for the AI model and how its answer is read."""

from __future__ import annotations

from custom_components.garden_manager.engine import photo_diagnosis as pd


def test_the_crops_own_problems_come_first(db):
    options = pd.candidates(db, ["tomato"], "nl")
    likely = [o["id"] for o in options if o["likely"]]
    assert "late_blight" in likely
    assert options[0]["likely"] and not options[-1]["likely"]
    assert len({o["id"] for o in options}) == len(options)
    text = pd.instructions(["Tomato"], options, "nl")
    assert "Dutch" in text and "late_blight" in text and pd.HEALTHY in text and pd.OTHER in text
    assert set(pd.structure()) >= {"problem_id", "confidence", "explanation"}


def test_answers_are_read_safely(db):
    options = pd.candidates(db, ["tomato"], "nl")
    known = pd.interpret(
        {"problem_id": "Late Blight", "confidence": 87.4, "explanation": "bruine vlekken"}, options, "nl"
    )
    assert known["problem_id"] == "late_blight" and known["known"] and known["confidence"] == 87
    assert known["name"] == "Phytophthora" and known["remedy"]  # the Dutch name and the organic advice
    other = pd.interpret({"problem_id": "magnesium shortage", "confidence": "x"}, options, "en")
    assert other["problem_id"] == pd.OTHER and other["name"] == "magnesium shortage" and other["confidence"] == 0
    healthy = pd.interpret({"problem_id": "healthy", "confidence": 140}, options, "fr")
    assert healthy["kind"] == pd.HEALTHY and healthy["confidence"] == 100
    assert pd.interpret(None, options, "en")["problem_id"] == pd.OTHER
