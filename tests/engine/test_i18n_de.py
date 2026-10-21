"""German backend catalogues: parity with English and a season book in German."""

from __future__ import annotations

import json
from pathlib import Path
import re
import string

from custom_components.garden_manager.engine import (
    cooking,
    cooking_dishes,
    cooking_extras,
    eco,
    i18n,
    kitchen,
    printout,
    qa,
    qa_kb,
    seasonbook,
    slogans,
)
from custom_components.garden_manager.engine.i18n import MESSAGES, PEST_LABELS, normalize_lang, pest_label, t
from custom_components.garden_manager.engine.plantdb import FAMILIES, FAMILY_RELATIONS
from custom_components.garden_manager.engine.printout import PrintOptions
from custom_components.garden_manager.engine.seasonbook import TEXT, fmt_num, join_names, render_book_svg, safe
from custom_components.garden_manager.engine.supplies import TOOLS, TOOLS_DE, tool_name

from .test_seasonbook import _ctx, _year

ROOT = Path(__file__).resolve().parents[2] / "custom_components" / "garden_manager"


def _fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name is not None}


def _keys(doc: object, prefix: str = "") -> set[str]:
    if isinstance(doc, dict):
        return {k for key, value in doc.items() for k in _keys(value, f"{prefix}.{key}")}
    return {prefix}


def test_normalize_lang_accepts_german():
    assert "de" in i18n.SUPPORTED
    assert normalize_lang("de-AT") == "de" and normalize_lang("de_CH") == "de" and normalize_lang("DE") == "de"
    assert normalize_lang("es") == "en"


def test_every_message_has_german_with_the_same_placeholders():
    en, de = MESSAGES["en"], MESSAGES["de"]
    assert set(de) == set(en)
    mismatched = [k for k in en if _fields(en[k]) != _fields(de[k])]
    assert not mismatched, mismatched
    assert t("task.sow_direct", "de-AT", plant="Möhre", bed="Beet 1") == "Möhre in Beet 1 aussäen"


def test_pest_labels_and_families_have_german():
    assert all("de" in labels for labels in PEST_LABELS.values())
    assert pest_label("slugs", "de") == "Schnecken"
    assert all("de" in fam for fam in FAMILIES.values())
    assert all("de" in reasons for *_, reasons in FAMILY_RELATIONS)


def test_other_tables_have_german():
    assert set(TOOLS_DE) == set(TOOLS) and tool_name("hoe", "de") == "Hacke"
    assert all("de" in by_lang for by_lang in kitchen.TIPS.values())
    assert set(printout.LABELS["de"]) == set(printout.LABELS["en"]) and len(printout.MONTHS["de"]) == 12
    assert set(qa.L["de"]) == set(qa.L["en"]) and set(qa.STAGE["de"]) == set(qa.STAGE["en"])
    assert set(qa.LEVEL["de"]) == set(qa.LEVEL["en"])
    for table in (qa_kb.PROBLEMS, qa_kb.PESTS, qa_kb.DISEASES):
        assert all("de" in entry for entry in table.values())
    for theme, langs in slogans.SLOGANS.items():
        assert len(langs["de"]) == len(langs["en"]), theme
    assert eco.layer_names(["canopy", "shrub"], "de") == "Baumschicht, Sträucher"


def test_cooking_has_german():
    for table in (cooking._TITLE, cooking._STEPS, cooking._TECH_NAME, cooking._PREP, cooking._TAG, cooking._PDF):
        assert set(table["de"]) == set(table["en"])
    assert all(len(item.names) == 4 and item.name("de") for item in cooking.PANTRY.values())
    assert all(len(texts) == 4 for texts in cooking_dishes.TITLE.values())
    assert all(len(texts) == 4 for texts in cooking_extras.HERB.values())
    assert all(len(texts) == 5 for texts in cooking_extras.PREP.values())
    assert cooking.label("ingredients", "de") == "Zutaten"


def test_season_book_texts_match_english():
    assert set(TEXT["de"]) == set(TEXT["en"])
    assert [k for k in TEXT["en"] if _fields(TEXT["en"][k]) != _fields(TEXT["de"][k])] == []
    for table in (seasonbook.MONTHS, seasonbook.WEEKDAYS, seasonbook.MONTH_INTRO, seasonbook.FILLER_LINES):
        assert len(table["de"]) == len(table["en"])
    assert seasonbook.GLOSSARY["de"]
    # Umlauts, sharp s and German quotes survive the cp1252 PDF fonts.
    assert safe("Größe „Möhre“ süß") == "Größe „Möhre“ süß"
    assert fmt_num(2400.0, "de", 0) == "2.400" and fmt_num(1.25, "de", 2) == "1,25"
    assert join_names(["a", "b", "c"], "de") == "a, b und c"


def test_season_book_renders_in_german(garden, db, make_planting):
    pages = render_book_svg(
        _ctx(_year(garden, make_planting), db),
        PrintOptions.from_dict({"document": "book", "season": 2026, "lang": "de"}),
        200,
    )
    text = " ".join(pages)
    assert "Inhalt" in text and "Einleitung" in text and "Glossar" in text
    assert "Dies ist die Geschichte" in text  # the German introduction
    assert re.search(r"August|Juli", text)  # month chapters
    assert "Sommaire" not in text and "Contents" not in text


def test_data_files_have_german():
    plants = json.loads((ROOT / "data" / "plants.json").read_text(encoding="utf-8"))["plants"]
    assert all(p["names"].get("de") and len(p["tips"]["de"]) == len(p["tips"]["en"]) for p in plants)
    glossary = json.loads((ROOT / "data" / "handbook" / "glossary.json").read_text(encoding="utf-8"))
    assert all(entry["de"]["term"] and entry["de"]["text"] for entry in glossary.values())
    en = json.loads((ROOT / "translations" / "en.json").read_text(encoding="utf-8"))
    de = json.loads((ROOT / "translations" / "de.json").read_text(encoding="utf-8"))
    assert _keys(de) == _keys(en)
    assert (ROOT / "data" / "sentences" / "de" / "hortulus.yaml").is_file()
