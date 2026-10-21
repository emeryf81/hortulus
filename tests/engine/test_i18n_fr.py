"""French backend catalogues: parity with English and a season book in French."""

from __future__ import annotations

import re
import string

from custom_components.garden_manager.engine import i18n, kitchen, printout, qa, qa_kb, seasonbook
from custom_components.garden_manager.engine.i18n import MESSAGES, PEST_LABELS, normalize_lang, pest_label, t
from custom_components.garden_manager.engine.plantdb import FAMILIES, FAMILY_RELATIONS
from custom_components.garden_manager.engine.printout import PrintOptions
from custom_components.garden_manager.engine.seasonbook import TEXT, fmt_num, join_names, render_book_svg, safe
from custom_components.garden_manager.engine.supplies import TOOLS, TOOLS_FR, tool_name

from .test_seasonbook import _ctx, _year


def _fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name is not None}


def test_normalize_lang_accepts_french():
    assert "fr" in i18n.SUPPORTED
    assert normalize_lang("fr-BE") == "fr" and normalize_lang("fr_FR") == "fr" and normalize_lang("FR") == "fr"
    assert normalize_lang("de") == "en"


def test_every_message_has_french_with_the_same_placeholders():
    en, fr = MESSAGES["en"], MESSAGES["fr"]
    assert set(fr) == set(en)
    mismatched = [k for k in en if _fields(en[k]) != _fields(fr[k])]
    assert not mismatched, mismatched
    assert t("task.sow_direct", "fr-BE", plant="Carotte", bed="Planche 1") == "Semer Carotte dans Planche 1"


def test_pest_labels_and_families_have_french():
    assert all("fr" in labels for labels in PEST_LABELS.values())
    assert pest_label("slugs", "fr") == "limaces"
    assert all("fr" in fam for fam in FAMILIES.values())
    assert all("fr" in reasons for *_, reasons in FAMILY_RELATIONS)


def test_other_tables_have_french():
    assert set(TOOLS_FR) == set(TOOLS) and tool_name("hoe", "fr") == "Binette"
    assert all("fr" in by_lang for by_lang in kitchen.TIPS.values())
    assert set(printout.LABELS["fr"]) == set(printout.LABELS["en"]) and len(printout.MONTHS["fr"]) == 12
    assert set(qa.L["fr"]) == set(qa.L["en"]) and set(qa.STAGE["fr"]) == set(qa.STAGE["en"])
    for table in (qa_kb.PROBLEMS, qa_kb.PESTS, qa_kb.DISEASES):
        assert all("fr" in entry for entry in table.values())


def test_season_book_texts_match_english():
    assert set(TEXT["fr"]) == set(TEXT["en"])
    assert [k for k in TEXT["en"] if _fields(TEXT["en"][k]) != _fields(TEXT["fr"][k])] == []
    for table in (seasonbook.MONTHS, seasonbook.WEEKDAYS, seasonbook.MONTH_INTRO, seasonbook.FILLER_LINES):
        assert len(table["fr"]) == len(table["en"])
    assert seasonbook.GLOSSARY["fr"]
    # French accents and guillemets survive the cp1252 PDF fonts.
    assert safe("Récolte « œuf » à l'été, ça") == "Récolte « œuf » à l'été, ça"
    assert fmt_num(2400.0, "fr", 0) == "2\xa0400" and fmt_num(1.25, "fr", 2) == "1,25"
    assert join_names(["a", "b", "c"], "fr") == "a, b et c"


def test_season_book_renders_in_french(garden, db, make_planting):
    pages = render_book_svg(
        _ctx(_year(garden, make_planting), db),
        PrintOptions.from_dict({"document": "book", "season": 2026, "lang": "fr"}),
        200,
    )
    text = " ".join(pages)
    assert "Sommaire" in text and "Introduction" in text and "Glossaire" in text
    assert "Voici l" in text  # the French introduction
    assert re.search(r"Ao[uû]t|Juillet", text)  # month chapters
    assert "Inhoud" not in text and "Contents" not in text
