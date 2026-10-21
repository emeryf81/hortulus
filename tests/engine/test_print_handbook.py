"""Printouts (PDF / SVG) and the handbook."""

from __future__ import annotations

from datetime import date
import re
import zlib

import pytest

from custom_components.garden_manager.engine.handbook import chapter, chapters, glossary, search
from custom_components.garden_manager.engine.maintenance import ECO_RULES, GARDEN_RULES, GREENHOUSE_RULES
from custom_components.garden_manager.engine.models import Feature, FeatureType, TaskType, Zone, ZoneType
from custom_components.garden_manager.engine.pdf import MM, PdfDocument, text_width, wrap
from custom_components.garden_manager.engine.printout import (
    DOCUMENTS,
    PAGE_SIZES,
    PrintContext,
    PrintOptions,
    render_pdf,
    render_svg,
)
from custom_components.garden_manager.engine.region import season_anchors
from custom_components.garden_manager.engine.schedule import planting_timeline
from custom_components.garden_manager.engine.tasks import make_user_task


@pytest.fixture
def ctx(garden, db, make_planting):
    garden.plantings = [
        make_planting("tomato", "gh_bed", 2026, width_cm=200, length_cm=50),
        make_planting("carrot", "bed_1", 2026, x_cm=0, y_cm=0, width_cm=200, length_cm=30),
        make_planting("onion", "bed_1", 2026, x_cm=0, y_cm=40, width_cm=200, length_cm=30),
        make_planting("basil", "gh_bed", 2026, x_cm=210, width_cm=40, length_cm=40),
    ]
    garden.features = [Feature("f1", "Path", FeatureType.PATH, x_cm=0, y_cm=200, width_cm=800, length_cm=60)]
    now = __import__("datetime").datetime(2026, 5, 1, 9)
    garden.tasks = [make_user_task(title="Repair the fence", due=date(2026, 5, 3), now=now, task_type=TaskType.CUSTOM)]
    anchors = season_anchors(garden.settings.region, 2026)
    timelines = {
        p.id: planting_timeline(
            p, db.get(p.plant_id), anchors, garden.zone(garden.bed(p.bed_id).zone_id), date(2026, 5, 1)
        )
        for p in garden.plantings
    }
    return PrintContext(garden, db, timelines, date(2026, 5, 1), "Test garden")


def _pages(pdf: bytes) -> list[tuple[float, float]]:
    return [(float(w), float(h)) for w, h in re.findall(rb"/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]", pdf)]


def _streams(pdf: bytes) -> list[bytes]:
    return [zlib.decompress(m) for m in re.findall(rb"stream\n(.*?)\nendstream", pdf, re.S)]


@pytest.mark.parametrize("document", DOCUMENTS)
def test_every_document_renders_a_valid_pdf(ctx, document):
    pdf = render_pdf(ctx, PrintOptions(document=document, page="a4", lang="nl"))
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    # xref offsets point at the objects
    xref = int(re.search(rb"startxref\n(\d+)", pdf).group(1))
    assert pdf[xref : xref + 4] == b"xref"
    offsets = [int(o) for o in re.findall(rb"(\d{10}) 00000 n", pdf)]
    for i, off in enumerate(offsets, start=1):
        assert pdf[off:].startswith(f"{i} 0 obj".encode())
    assert _pages(pdf)
    for stream in _streams(pdf):
        assert b" rl " not in stream  # only real PDF operators
    svgs = render_svg(ctx, PrintOptions(document=document, page="a4", lang="nl"))
    # the season book previews its first 16 pages only
    assert len(svgs) == (min(16, len(_pages(pdf))) if document == "book" else len(_pages(pdf)))
    assert all(s.startswith("<svg") and s.endswith("</svg>") for s in svgs)


def test_remarkable_page_size_and_toolbar_margin(ctx):
    pdf = render_pdf(ctx, PrintOptions(document="garden", page="remarkable", color_mode="eink"))
    w, h = _pages(pdf)[0]
    assert w == pytest.approx(179.6 * MM, abs=0.05) and h == pytest.approx(239.5 * MM, abs=0.05)
    assert h / w == pytest.approx(4 / 3, abs=0.001)  # Paper Pro: 2160 x 1620 px
    land = _pages(render_pdf(ctx, PrintOptions(document="garden", page="remarkable", landscape=True)))[0]
    assert land[0] > land[1]


def test_garden_map_contains_legend_crops_and_notes(ctx):
    text = "".join(render_svg(ctx, PrintOptions(document="garden", page="a4", lang="nl")))
    for word in ("Legende", "Notities", "Tomaat", "Nachtschadefamilie", "Serre", "Pad"):
        assert word in text
    assert ">N</text>" in text  # north arrow


def test_every_element_and_zone_type_prints_with_its_label(ctx):
    garden = ctx.data
    garden.features = [
        Feature(f"f_{t.value}", "", t, x_cm=(i % 6) * 150, y_cm=300 + (i // 6) * 120, width_cm=120, length_cm=100)
        for i, t in enumerate(FeatureType)
    ]
    # every type has a style and a label in both languages
    for lang in ("en", "nl"):
        assert render_svg(ctx, PrintOptions(document="garden", page="a4", lang=lang))
    # the legend has room for a handful: check the new ones
    keep = {
        FeatureType.WOOD_PATH,
        FeatureType.STONE_PATH,
        FeatureType.STEPPING_STONES,
        FeatureType.POOL,
        FeatureType.WALL,
    }
    garden.features = [f for f in garden.features if f.type in keep]
    garden.zones += [
        Zone(id="z_garden", name="Voortuin", type=ZoneType.GARDEN, x_cm=0, y_cm=800, width_cm=400, length_cm=200),
        Zone(id="z_pots", name="Terras", type=ZoneType.CONTAINERS, x_cm=500, y_cm=800, width_cm=200, length_cm=200),
    ]
    text = "".join(render_svg(ctx, PrintOptions(document="garden", page="a4", lang="nl")))
    for word in ("Houten pad", "Stenen pad", "Stapstenen", "Zwembad", "Muur", "Siertuin", "Bloembakken"):
        assert word in text, word


def test_ornamental_garden_beds_use_the_outdoor_sensors(garden):
    garden.settings.outdoor_sensors.air_temperature = "sensor.outside"
    garden.zones[0].type = ZoneType.GARDEN
    assert garden.bed_sensors(garden.bed("bed_1")).air_temperature == "sensor.outside"
    assert garden.bed_sensors(garden.bed("gh_bed")).air_temperature == "sensor.greenhouse_temp"


def test_eink_mode_adds_patterns(ctx):
    color = render_svg(ctx, PrintOptions(document="garden", color_mode="color"))[0]
    eink = render_svg(ctx, PrintOptions(document="garden", color_mode="eink"))[0]
    assert eink.count("clipPath") > color.count("clipPath")
    gray = render_svg(ctx, PrintOptions(document="garden", color_mode="grayscale"))[0]
    for r, g, b in re.findall(r'fill="#([0-9A-F]{2})([0-9A-F]{2})([0-9A-F]{2})"', gray):
        assert r == g == b


def test_task_checklist_lists_open_tasks(ctx):
    svg = "".join(render_svg(ctx, PrintOptions(document="tasks", lang="en", days=14)))
    assert "Repair the fence" in svg and "Extra tasks" in svg


def test_print_options_validation():
    with pytest.raises(ValueError):
        PrintOptions.from_dict({"document": "poster"})
    with pytest.raises(ValueError):
        PrintOptions.from_dict({"page": "a0"})
    opts = PrintOptions.from_dict({"document": "beds", "page": "remarkable", "days": 999, "unknown": 1})
    assert opts.days == 120 and set(PAGE_SIZES) >= {"a4", "a3", "letter", "remarkable"}


def test_text_metrics_and_wrapping():
    assert text_width("MMMM", 10) > text_width("iiii", 10)
    assert text_width("Wortel", 10, bold=True) > text_width("Wortel", 10)
    lines = wrap("een twee drie vier vijf zes zeven acht", 20, 9)
    assert len(lines) > 1 and all(text_width(line, 9) <= 20 for line in lines)


def test_pdf_handles_non_latin_text():
    doc = PdfDocument(title="Test → ≈")
    page = doc.add_page(100, 100)
    page.text(10, 10, "Kool → spruitjes ≈ 2 m² · 5 °C")
    assert b"%%EOF" in doc.to_bytes()


# --------------------------------------------------------------------------- #
# Handbook
# --------------------------------------------------------------------------- #
def test_handbook_has_the_same_chapters_in_both_languages():
    en, nl = chapters("en"), chapters("nl")
    assert len(en) >= 15
    assert [c.id for c in en] == [c.id for c in nl]
    for a, b in zip(en, nl, strict=True):
        assert a.title and b.title and a.title != b.title
        assert len(a.sections) == len(b.sections)


def test_glossary_terms_link_to_existing_chapters():
    ids = {c.id for c in chapters("en")}
    for lang in ("en", "nl"):
        terms = glossary(lang)
        assert len(terms) >= 25
        assert all(t["chapter"] in ids for t in terms.values())
    assert glossary("nl")["rotation"]["term"] == "Vruchtwisseling"


def test_maintenance_tasks_reference_existing_chapters():
    ids = {c.id for c in chapters("en")}
    assert {r.handbook for r in (*GARDEN_RULES, *GREENHOUSE_RULES, *ECO_RULES)} <= ids
    assert {"soil", "perennials", "permaculture", "food_forest"} <= ids


def test_handbook_search_and_fallback():
    hits = search("serre", "nl")
    assert hits and hits[0]["id"] == "greenhouse"
    assert chapter("watering", "de").title == chapter("watering", "en").title


def test_every_handbook_file_is_a_chapter():
    from pathlib import Path

    from custom_components.garden_manager.engine.handbook import chapters as all_chapters

    root = Path(__file__).resolve().parents[2] / "custom_components/garden_manager/data/handbook"
    for lang in ("en", "nl"):
        files = list((root / lang).glob("*.md"))
        assert len(all_chapters(lang)) == len(files) >= 21
