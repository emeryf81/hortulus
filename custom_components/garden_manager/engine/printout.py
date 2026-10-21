"""Printable documents: garden maps, bed sheets, checklists, season charts.

Every document is laid out once on the abstract :class:`~.pdf.Surface` and
rendered as PDF (print, reMarkable) or SVG (preview in the panel).

Paper formats include the **reMarkable Paper Pro** (179.6 x 239.5 mm, 4:3)
with a wider left margin for the toolbar.  Colour modes:

``color``      family colours as soft tints, outlines in full colour.
``eink``       lighter tints plus a hatch pattern per family, so beds stay
               distinguishable on a colour e-paper screen and leave room
               for drawing on top; dot grids for notes.
``grayscale``  everything converted to grey, patterns carry the meaning.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import dataclasses
from dataclasses import dataclass, field
from datetime import date, timedelta
import math
from typing import Any

from .coverage import feature_layers
from .fertilizer import bed_fertilizer_plan
from .geometry import plant_count, plant_positions
from .i18n import normalize_lang
from .models import (
    BedKind,
    Feature,
    FeatureType,
    GardenBed,
    GardenData,
    Plant,
    Planting,
    PlantingStatus,
    Relation,
    Task,
    Zone,
    ZoneType,
    present_in,
)
from .pdf import Image, PdfDocument, Surface, SvgPage, ellipsize, hex_rgb, text_width
from .plantdb import FAMILIES, PlantDatabase
from .region import season_anchors, season_bounds
from .schedule import PlantingTimeline
from .seasons import layout_for

PAGE_SIZES: dict[str, tuple[float, float]] = {
    "a4": (210.0, 297.0),
    "a3": (297.0, 420.0),
    "a5": (148.0, 210.0),
    "letter": (215.9, 279.4),
    "remarkable": (179.6, 239.5),  # reMarkable Paper Pro, 2160 x 1620 px @ 229 ppi
}
DOCUMENTS = ("garden", "zone", "beds", "tasks", "season", "year", "blank", "plants", "book")
COLOR_MODES = ("color", "eink", "grayscale")
PATTERNS = ("diag", "back", "horiz", "vert", "cross", "dots", "grid")

INK = "#1F2A24"
MUTED = "#5E6B63"
FAINT = "#B9C2BC"
GRID = "#C9D1CB"
BRAND = "#2F6B4F"

LABELS: dict[str, dict[str, str]] = {
    "en": {
        "garden": "Garden plan", "zone": "Zone plan", "beds": "Bed sheet", "tasks": "Task checklist",
        "season": "Season overview", "blank": "Planning sheet", "plants": "Plant cards",
        "year": "Year plan", "sow_indoor": "Sow indoors", "grow": "Growing", "tasks_month": "Tasks",
        "season_n": "Season {season}", "printed": "Printed {date}", "page": "Page {n}/{total}",
        "legend": "Legend", "notes": "Notes", "north": "N", "families": "Plant families", "zones": "Zones",
        "features": "Garden elements", "crops": "Crops", "crop": "Crop", "bed": "Bed", "count": "Plants",
        "sow": "Sow", "plant_out": "Plant out", "harvest": "Harvest", "method": "Method", "spacing": "Spacing",
        "due": "Due", "task": "Task", "minutes": "Min", "done": "Done", "week": "Week of {date}",
        "outdoor": "Outdoor", "greenhouse": "Greenhouse", "cold_frame": "Cold frame", "bed_outline": "Bed",
        "container": "Container", "plant_pos": "Plant position", "area": "Area", "soil": "Soil",
        "compost": "Compost {kg} kg", "fertilizer": "organic fertiliser {g} g", "lime": "check pH (brassicas)",
        "rotation": "Previously", "none": "-", "frost_last": "last frost", "frost_first": "first frost",
        "today": "today", "indoor": "indoors", "direct": "direct", "transplant": "transplant",
        "good_neighbours": "Good neighbours", "bad_neighbours": "Avoid", "depth": "Depth", "water": "Water",
        "feeding": "Feeding", "low": "low", "medium": "medium", "high": "high", "sowing_windows": "Sowing",
        "add_tasks": "Extra tasks", "scale": "Scale", "empty": "Nothing planned yet.",
        "path": "Path", "compost_heap": "Compost", "water_butt": "Water butt", "shed": "Shed", "tree": "Tree",
        "hedge": "Hedge", "trellis": "Trellis", "other": "Other", "draw_here": "Sketch your plan here",
        "house": "House", "driveway": "Driveway", "street": "Street", "parking": "Parking",
        "play": "Play area", "beehive": "Beehive",
        "terrace": "Terrace", "lawn": "Lawn", "flowerbed": "Flower bed", "fence": "Fence", "pond": "Pond",
        "orchard": "Orchard", "food_forest": "Food forest", "fruit": "Soft fruit", "herbs": "Herb garden", "flowers": "Flower garden",
        "zone_garden": "Ornamental garden", "zone_containers": "Planters & pots",
        "stone_path": "Stone path", "wood_path": "Wooden path", "stepping_stones": "Stepping stones",
        "bark_path": "Bark path", "decking": "Decking", "wall": "Wall", "carport": "Carport / garage",
        "shrub": "Shrub", "pool": "Swimming pool", "seating": "Seating area",
        "before": "before", "after": "after",
        "days_to_harvest": "Days to harvest", "family": "Family",
    },
    "nl": {
        "garden": "Tuinplan", "zone": "Zoneplan", "beds": "Bedfiche", "tasks": "Takenlijst",
        "season": "Seizoensoverzicht", "blank": "Planningsblad", "plants": "Plantkaarten",
        "year": "Jaarplan", "sow_indoor": "Binnen zaaien", "grow": "Groeit", "tasks_month": "Taken",
        "season_n": "Seizoen {season}", "printed": "Afgedrukt {date}", "page": "Pagina {n}/{total}",
        "legend": "Legende", "notes": "Notities", "north": "N", "families": "Plantenfamilies", "zones": "Zones",
        "features": "Tuinelementen", "crops": "Gewassen", "crop": "Gewas", "bed": "Bed", "count": "Planten",
        "sow": "Zaaien", "plant_out": "Uitplanten", "harvest": "Oogst", "method": "Methode", "spacing": "Afstand",
        "due": "Datum", "task": "Taak", "minutes": "Min", "done": "Klaar", "week": "Week van {date}",
        "outdoor": "Buiten", "greenhouse": "Serre", "cold_frame": "Koude bak", "bed_outline": "Bed",
        "container": "Bak / pot", "plant_pos": "Plantplaats", "area": "Oppervlakte", "soil": "Bodem",
        "compost": "Compost {kg} kg", "fertilizer": "organische mest {g} g", "lime": "pH controleren (kolen)",
        "rotation": "Voorheen", "none": "-", "frost_last": "laatste vorst", "frost_first": "eerste vorst",
        "today": "vandaag", "indoor": "binnen", "direct": "ter plaatse", "transplant": "plantgoed",
        "good_neighbours": "Goede buren", "bad_neighbours": "Vermijden", "depth": "Diepte", "water": "Water",
        "feeding": "Bemesting", "low": "laag", "medium": "matig", "high": "hoog", "sowing_windows": "Zaaien",
        "add_tasks": "Extra taken", "scale": "Schaal", "empty": "Nog niets gepland.",
        "path": "Pad", "compost_heap": "Compost", "water_butt": "Regenton", "shed": "Tuinhuis", "tree": "Boom",
        "hedge": "Haag", "trellis": "Klimrek", "other": "Overig", "draw_here": "Schets hier je plan",
        "house": "Huis", "driveway": "Oprit", "street": "Straat", "parking": "Parking",
        "play": "Speelhoek", "beehive": "Bijenkast",
        "terrace": "Terras", "lawn": "Gazon", "flowerbed": "Bloemperk", "fence": "Omheining", "pond": "Vijver",
        "orchard": "Boomgaard", "food_forest": "Voedselbos", "fruit": "Kleinfruit", "herbs": "Kruidentuin", "flowers": "Bloementuin",
        "zone_garden": "Siertuin", "zone_containers": "Bloembakken & potten",
        "stone_path": "Stenen pad", "wood_path": "Houten pad", "stepping_stones": "Stapstenen",
        "bark_path": "Schorspad", "decking": "Vlonder", "wall": "Muur", "carport": "Carport / garage",
        "shrub": "Heester", "pool": "Zwembad", "seating": "Zithoek",
        "before": "voor", "after": "na",
        "days_to_harvest": "Dagen tot oogst", "family": "Familie",
    },
    "fr": {
        "garden": "Plan du jardin", "zone": "Plan de zone", "beds": "Fiche de planche", "tasks": "Liste des tâches",
        "season": "Aperçu de la saison", "blank": "Feuille de planification", "plants": "Fiches plantes",
        "year": "Plan annuel", "sow_indoor": "Semis à l'abri", "grow": "Croissance", "tasks_month": "Tâches",
        "season_n": "Saison {season}", "printed": "Imprimé le {date}", "page": "Page {n}/{total}",
        "legend": "Légende", "notes": "Notes", "north": "N", "families": "Familles de plantes", "zones": "Zones",
        "features": "Éléments du jardin", "crops": "Cultures", "crop": "Culture", "bed": "Planche", "count": "Plants",
        "sow": "Semis", "plant_out": "Repiquage", "harvest": "Récolte", "method": "Méthode", "spacing": "Espacement",
        "due": "Échéance", "task": "Tâche", "minutes": "Min", "done": "Fait", "week": "Semaine du {date}",
        "outdoor": "Extérieur", "greenhouse": "Serre", "cold_frame": "Châssis", "bed_outline": "Planche",
        "container": "Bac / pot", "plant_pos": "Emplacement", "area": "Surface", "soil": "Sol",
        "compost": "Compost {kg} kg", "fertilizer": "engrais organique {g} g", "lime": "vérifier le pH (choux)",
        "rotation": "Précédemment", "none": "-", "frost_last": "dernières gelées", "frost_first": "premières gelées",
        "today": "aujourd'hui", "indoor": "à l'abri", "direct": "en place", "transplant": "plants",
        "good_neighbours": "Bons voisins", "bad_neighbours": "À éviter", "depth": "Profondeur", "water": "Eau",
        "feeding": "Fertilisation", "low": "faible", "medium": "moyen", "high": "élevé", "sowing_windows": "Semis",
        "add_tasks": "Tâches supplémentaires", "scale": "Échelle", "empty": "Rien de prévu pour l'instant.",
        "path": "Allée", "compost_heap": "Compost", "water_butt": "Récupérateur d'eau", "shed": "Abri de jardin", "tree": "Arbre",
        "hedge": "Haie", "trellis": "Treillis", "other": "Autre", "draw_here": "Esquissez votre plan ici",
        "house": "Maison", "driveway": "Allée de garage", "street": "Rue", "parking": "Parking",
        "play": "Coin jeux", "beehive": "Ruche",
        "terrace": "Terrasse", "lawn": "Pelouse", "flowerbed": "Massif de fleurs", "fence": "Clôture", "pond": "Mare",
        "orchard": "Verger", "food_forest": "Forêt comestible", "fruit": "Petits fruits", "herbs": "Jardin d'aromatiques", "flowers": "Jardin de fleurs",
        "zone_garden": "Jardin d'agrément", "zone_containers": "Jardinières et pots",
        "stone_path": "Allée en pierre", "wood_path": "Allée en bois", "stepping_stones": "Pas japonais",
        "bark_path": "Allée en écorces", "decking": "Platelage", "wall": "Mur", "carport": "Carport / garage",
        "shrub": "Arbuste", "pool": "Piscine", "seating": "Coin salon",
        "before": "avant", "after": "après",
        "days_to_harvest": "Jours jusqu'à la récolte", "family": "Famille",
    },
    "de": {
        "garden": "Gartenplan", "zone": "Zonenplan", "beds": "Beetblatt", "tasks": "Aufgabenliste",
        "season": "Saisonübersicht", "blank": "Planungsblatt", "plants": "Pflanzenkarten",
        "year": "Jahresplan", "sow_indoor": "Drinnen vorziehen", "grow": "Wachstum", "tasks_month": "Aufgaben",
        "season_n": "Saison {season}", "printed": "Gedruckt am {date}", "page": "Seite {n}/{total}",
        "legend": "Legende", "notes": "Notizen", "north": "N", "families": "Pflanzenfamilien", "zones": "Zonen",
        "features": "Gartenelemente", "crops": "Kulturen", "crop": "Kultur", "bed": "Beet", "count": "Pflanzen",
        "sow": "Aussaat", "plant_out": "Auspflanzen", "harvest": "Ernte", "method": "Methode", "spacing": "Abstand",
        "due": "Fällig", "task": "Aufgabe", "minutes": "Min.", "done": "Erledigt", "week": "Woche vom {date}",
        "outdoor": "Freiland", "greenhouse": "Gewächshaus", "cold_frame": "Frühbeet", "bed_outline": "Beet",
        "container": "Kübel / Topf", "plant_pos": "Pflanzstelle", "area": "Fläche", "soil": "Boden",
        "compost": "Kompost {kg} kg", "fertilizer": "organischer Dünger {g} g", "lime": "pH-Wert prüfen (Kohl)",
        "rotation": "Vorher", "none": "-", "frost_last": "letzter Frost", "frost_first": "erster Frost",
        "today": "heute", "indoor": "drinnen", "direct": "direkt", "transplant": "Jungpflanzen",
        "good_neighbours": "Gute Nachbarn", "bad_neighbours": "Meiden", "depth": "Tiefe", "water": "Wasser",
        "feeding": "Düngung", "low": "gering", "medium": "mittel", "high": "hoch", "sowing_windows": "Aussaat",
        "add_tasks": "Zusätzliche Aufgaben", "scale": "Maßstab", "empty": "Noch nichts geplant.",
        "path": "Weg", "compost_heap": "Kompost", "water_butt": "Regentonne", "shed": "Gartenhaus", "tree": "Baum",
        "hedge": "Hecke", "trellis": "Rankgitter", "other": "Sonstiges", "draw_here": "Skizzieren Sie hier Ihren Plan",
        "house": "Haus", "driveway": "Einfahrt", "street": "Straße", "parking": "Parkplatz",
        "play": "Spielecke", "beehive": "Bienenstock",
        "terrace": "Terrasse", "lawn": "Rasen", "flowerbed": "Blumenbeet", "fence": "Zaun", "pond": "Teich",
        "orchard": "Obstgarten", "food_forest": "Waldgarten", "fruit": "Beerenobst", "herbs": "Kräutergarten", "flowers": "Blumengarten",
        "zone_garden": "Ziergarten", "zone_containers": "Pflanzkübel und Töpfe",
        "stone_path": "Steinweg", "wood_path": "Holzweg", "stepping_stones": "Trittsteine",
        "bark_path": "Rindenmulchweg", "decking": "Holzdeck", "wall": "Mauer", "carport": "Carport / Garage",
        "shrub": "Strauch", "pool": "Schwimmbecken", "seating": "Sitzplatz",
        "before": "vor", "after": "nach",
        "days_to_harvest": "Tage bis zur Ernte", "family": "Familie",
    },
}  # fmt: skip
MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "nl": ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
    "fr": ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."],
    "de": ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sep.", "Okt.", "Nov.", "Dez."],
}


@dataclass(slots=True)
class PrintOptions:
    document: str = "garden"
    page: str = "a4"
    landscape: bool = False
    color_mode: str = "color"
    season: int | None = None
    zone_id: str | None = None
    bed_ids: list[str] | None = None
    plant_ids: list[str] | None = None
    days: int = 28
    notes: bool = True
    grid: bool = True
    labels: bool = True
    title: str | None = None
    lang: str = "en"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PrintOptions:
        known = {k: v for k, v in raw.items() if k in cls.__dataclass_fields__ and v is not None}
        opts = cls(**known)
        if opts.document not in DOCUMENTS:
            raise ValueError(f"unknown document {opts.document}")
        if opts.page not in PAGE_SIZES:
            raise ValueError(f"unknown page size {opts.page}")
        if opts.color_mode not in COLOR_MODES:
            raise ValueError(f"unknown colour mode {opts.color_mode}")
        opts.days = max(1, min(int(opts.days), 120))
        return opts


@dataclass(slots=True)
class PrintContext:
    data: GardenData
    db: PlantDatabase
    timelines: dict[str, PlantingTimeline]
    today: date
    garden_name: str = "Hortulus"
    # photo id -> JPEG for the season book (``(id, grayscale)``; None = not available)
    photos: Callable[[str, bool], Image | None] | None = None


@dataclass(slots=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h


# --------------------------------------------------------------------------- #
# Theme
# --------------------------------------------------------------------------- #
def _mix(color: str, amount: float, base: str = "#FFFFFF") -> str:
    """``amount`` of ``color`` over ``base`` (0 = base, 1 = colour)."""
    r1, g1, b1 = hex_rgb(color)
    r2, g2, b2 = hex_rgb(base)
    r, g, b = (r2 + (r1 - r2) * amount, g2 + (g1 - g2) * amount, b2 + (b1 - b2) * amount)
    return f"#{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}"


def _gray(color: str) -> str:
    r, g, b = hex_rgb(color)
    v = round((0.299 * r + 0.587 * g + 0.114 * b) * 255)
    return f"#{v:02X}{v:02X}{v:02X}"


@dataclass(slots=True)
class Theme:
    mode: str
    families: list[str] = field(default_factory=list)

    def col(self, color: str) -> str:
        return _gray(color) if self.mode == "grayscale" else color

    def family_color(self, family: str) -> str:
        return self.col(FAMILIES.get(family, {}).get("color", "#7A8B80"))

    def family_fill(self, family: str) -> str:
        amount = {"color": 0.38, "eink": 0.24, "grayscale": 0.22}[self.mode]
        return _mix(self.family_color(family), amount)

    def family_pattern(self, family: str) -> str:
        if self.mode == "color":
            return "none"
        if family not in self.families:
            self.families.append(family)
        return PATTERNS[self.families.index(family) % len(PATTERNS)]

    def zone_fill(self, zone: Zone) -> str:
        base = ZONE_COLORS.get(zone.type.value, ZONE_COLORS["outdoor"])[0]
        return _mix(self.col(base), 0.10 if self.mode == "color" else 0.06)

    def zone_stroke(self, zone: Zone) -> str:
        base = ZONE_COLORS.get(zone.type.value, ZONE_COLORS["outdoor"])[1]
        return self.col(base)


# zone type: (fill, stroke)
ZONE_COLORS: dict[str, tuple[str, str]] = {
    "outdoor": ("#7FB069", "#4E7D3A"),
    "greenhouse": ("#5DA9C9", "#2D7898"),
    "cold_frame": ("#8FB8C9", "#4F8399"),
    "orchard": ("#9CC46A", "#5F8F45"),
    "food_forest": ("#7FA35A", "#3F6B2A"),
    "fruit": ("#D27A8E", "#A8506A"),
    "herbs": ("#8FA3D6", "#4F6FB0"),
    "garden": ("#6E965A", "#7A9A5A"),
    "containers": ("#B07A5C", "#8A5A3E"),
    "flowers": ("#E39AC0", "#B25A8A"),
}
FEATURE_STYLE: dict[FeatureType, tuple[str, str]] = {
    FeatureType.PATH: ("#D8CBB3", "dots"),
    FeatureType.COMPOST: ("#8A6A45", "cross"),
    FeatureType.WATER_BUTT: ("#4C8FBF", "none"),
    FeatureType.SHED: ("#9AA3A0", "back"),
    FeatureType.TREE: ("#4E7D3A", "none"),
    FeatureType.HEDGE: ("#5F8F45", "grid"),
    FeatureType.TRELLIS: ("#7A5C3E", "vert"),
    FeatureType.TERRACE: ("#CFC6B8", "grid"),
    FeatureType.LAWN: ("#9CC46A", "dots"),
    FeatureType.FLOWERBED: ("#E39AC0", "dots"),
    FeatureType.FENCE: ("#8A6A45", "vert"),
    FeatureType.POND: ("#7FB6D9", "none"),
    FeatureType.HOUSE: ("#B9A79A", "back"),
    FeatureType.DRIVEWAY: ("#C9C3BA", "grid"),
    FeatureType.STREET: ("#9A9A9A", "none"),
    FeatureType.PARKING: ("#C9C3BA", "grid"),
    FeatureType.PLAY: ("#E8D58A", "dots"),
    FeatureType.BEEHIVE: ("#E0A526", "none"),
    FeatureType.STONE_PATH: ("#C9C3BA", "grid"),
    FeatureType.WOOD_PATH: ("#B98A5A", "vert"),
    FeatureType.STEPPING_STONES: ("#BDB6AA", "dots"),
    FeatureType.BARK_PATH: ("#A07A52", "dots"),
    FeatureType.DECKING: ("#B98A5A", "vert"),
    FeatureType.WALL: ("#A9775A", "grid"),
    FeatureType.CARPORT: ("#A4ACA9", "back"),
    FeatureType.SHRUB: ("#5F8F45", "none"),
    FeatureType.POOL: ("#5FB0E0", "none"),
    FeatureType.SEATING: ("#C9B28A", "none"),
    FeatureType.OTHER: ("#B4B4B4", "diag"),
}


def zone_label(zone_type: ZoneType) -> str:
    """Label key of a zone type ("garden" is taken by the garden-plan title)."""
    return f"zone_{zone_type.value}" if zone_type in (ZoneType.GARDEN, ZoneType.CONTAINERS) else zone_type.value


FEATURE_LABEL = {
    FeatureType.PATH: "path", FeatureType.COMPOST: "compost_heap", FeatureType.WATER_BUTT: "water_butt",
    FeatureType.SHED: "shed", FeatureType.TREE: "tree", FeatureType.HEDGE: "hedge", FeatureType.TRELLIS: "trellis",
    FeatureType.TERRACE: "terrace", FeatureType.LAWN: "lawn", FeatureType.FLOWERBED: "flowerbed",
    FeatureType.FENCE: "fence", FeatureType.POND: "pond", FeatureType.HOUSE: "house",
    FeatureType.DRIVEWAY: "driveway", FeatureType.STREET: "street", FeatureType.PARKING: "parking",
    FeatureType.PLAY: "play", FeatureType.BEEHIVE: "beehive", FeatureType.OTHER: "other",
    FeatureType.STONE_PATH: "stone_path", FeatureType.WOOD_PATH: "wood_path",
    FeatureType.STEPPING_STONES: "stepping_stones", FeatureType.BARK_PATH: "bark_path",
    FeatureType.DECKING: "decking", FeatureType.WALL: "wall", FeatureType.CARPORT: "carport",
    FeatureType.SHRUB: "shrub", FeatureType.POOL: "pool", FeatureType.SEATING: "seating",
}  # fmt: skip


# --------------------------------------------------------------------------- #
# Page frame
# --------------------------------------------------------------------------- #
class Page:
    """A surface plus margins, header and footer."""

    def __init__(self, surface: Surface, opts: PrintOptions, ctx: PrintContext, theme: Theme, title: str) -> None:
        self.s = surface
        self.opts = opts
        self.ctx = ctx
        self.theme = theme
        self.title = title
        rm = opts.page == "remarkable"
        # The reMarkable toolbar sits on the left edge in portrait.
        self.left = 13.0 if rm and not opts.landscape else 8.0 if rm else 12.0
        self.right = 6.0 if rm else 12.0
        self.top = 7.0 if rm else 11.0
        self.bottom = 7.0 if rm else 11.0
        self.body = Box(self.left, self.top + 14, surface.width - self.left - self.right, 0)
        self.body.h = surface.height - self.body.y - self.bottom - 6

    def lbl(self, key: str, **params: Any) -> str:
        return label(self.opts.lang, key, **params)

    def header(self, subtitle: str = "") -> None:
        s, x, y = self.s, self.left, self.top
        _logo(s, x, y, 9.0, self.theme.col(BRAND))
        s.text(x + 11.5, y + 5.0, self.title, size=14, bold=True, color=INK)
        sub = " · ".join(p for p in (self.ctx.garden_name, subtitle) if p)
        s.text(x + 11.5, y + 9.5, sub, size=8, color=MUTED)
        s.text(
            s.width - self.right, y + 9.5, self.lbl("printed", date=self.ctx.today.isoformat()),
            size=7, color=MUTED, anchor="end",
        )  # fmt: skip
        s.line(x, y + 12, s.width - self.right, y + 12, stroke=self.theme.col(BRAND), width=0.5)

    def footer(self, n: int, total: int) -> None:
        s = self.s
        y = s.height - self.bottom + 1
        s.line(self.left, y - 4, s.width - self.right, y - 4, stroke=FAINT, width=0.2)
        s.text(self.left, y, "Hortulus", size=7, color=MUTED, bold=True)
        s.text(s.width - self.right, y, self.lbl("page", n=n, total=total), size=7, color=MUTED, anchor="end")


def label(lang: str, key: str, **params: Any) -> str:
    table = LABELS.get(normalize_lang(lang), LABELS["en"])
    return table.get(key, LABELS["en"].get(key, key)).format(**params)


def _logo(s: Surface, x: float, y: float, size: float, color: str) -> None:
    """The Hortulus mark: a leaf in a rounded square."""
    s.rect(x, y, size, size, fill=color, radius=size * 0.22)
    cx, cy = x + size / 2, y + size / 2
    leaf = [
        (cx - size * 0.28, cy + size * 0.28),
        (cx - size * 0.22, cy - size * 0.10),
        (cx + size * 0.05, cy - size * 0.30),
        (cx + size * 0.30, cy - size * 0.30),
        (cx + size * 0.28, cy - size * 0.02),
        (cx + size * 0.08, cy + size * 0.24),
    ]
    s.polygon(leaf, fill="#FFFFFF")
    s.line(cx - size * 0.28, cy + size * 0.28, cx + size * 0.18, cy - size * 0.18, stroke=color, width=size * 0.05)


def _dot_grid(s: Surface, box: Box, pitch: float = 5.0, color: str = GRID) -> None:
    pts = []
    y = box.y + pitch / 2
    while y < box.y2:
        x = box.x + pitch / 2
        while x < box.x2:
            pts.append((x, y))
            x += pitch
        y += pitch
    s.dots(pts, r=0.22, color=color)


def _notes(page: Page, box: Box) -> None:
    if box.h < 15 or box.w < 30:
        return
    s = page.s
    s.text(box.x, box.y + 3.5, page.lbl("notes"), size=8, bold=True, color=MUTED)
    _dot_grid(s, Box(box.x, box.y + 6, box.w, box.h - 6))


# --------------------------------------------------------------------------- #
# Map
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class MapResult:
    scale: float  # mm per cm
    numbered: list[tuple[int, Planting, Plant]] = field(default_factory=list)
    families: list[str] = field(default_factory=list)
    zone_types: set[ZoneType] = field(default_factory=set)
    features: set[FeatureType] = field(default_factory=set)
    has_container: bool = False


def _bounds(zones: Sequence[Zone], beds: Sequence[GardenBed], features: Sequence[Feature]) -> tuple[float, ...]:
    xs, ys, x2s, y2s = [], [], [], []
    for z in zones:
        xs.append(z.x_cm), ys.append(z.y_cm), x2s.append(z.x_cm + z.width_cm), y2s.append(z.y_cm + z.length_cm)
    for b in beds:
        xs.append(b.x_cm), ys.append(b.y_cm), x2s.append(b.x_cm + b.width_cm), y2s.append(b.y_cm + b.length_cm)
    for f in features:
        xs.append(f.x_cm), ys.append(f.y_cm), x2s.append(f.x_cm + f.width_cm), y2s.append(f.y_cm + f.length_cm)
    if not xs:
        return 0.0, 0.0, 100.0, 100.0
    return min(xs), min(ys), max(x2s), max(y2s)


def _season_plantings(ctx: PrintContext, season: int, bed_ids: set[str]) -> list[Planting]:
    return [
        p
        for p in ctx.data.plantings
        if p.bed_id in bed_ids and p.status is not PlantingStatus.FAILED and _present(ctx, p, season)
    ]


def _present(ctx: PrintContext, p: Planting, season: int) -> bool:
    plant = ctx.db.get(p.plant_id)
    return present_in(p, bool(plant and plant.perennial), season)


def draw_map(
    page: Page,
    box: Box,
    zones: Sequence[Zone],
    beds: Sequence[GardenBed],
    features: Sequence[Feature],
    season: int,
    *,
    plantings: bool = True,
    bed_grid_cm: float | None = None,
    number_from: int = 1,
) -> MapResult:
    s, theme, ctx, lang = page.s, page.theme, page.ctx, page.opts.lang
    x0, y0, x1, y1 = _bounds(zones, beds, features)
    pad = 6.0
    world_w, world_h = max(x1 - x0, 1.0), max(y1 - y0, 1.0)
    arrow = 12.0  # keep the north arrow clear of the drawing
    scale = min((box.w - 2 * pad - arrow) / world_w, (box.h - 2 * pad - 6) / world_h)
    ox = box.x + pad + ((box.w - 2 * pad - arrow) - world_w * scale) / 2
    oy = box.y + pad + ((box.h - 2 * pad - 6) - world_h * scale) / 2

    def X(cm: float) -> float:
        return ox + (cm - x0) * scale

    def Y(cm: float) -> float:
        return oy + (cm - y0) * scale

    result = MapResult(scale)
    ground, above = feature_layers(features)

    def draw_feature(f: Feature) -> None:
        result.features.add(f.type)
        color, pattern = FEATURE_STYLE[f.type]
        color = theme.col(color)
        fx, fy, fw, fh = X(f.x_cm), Y(f.y_cm), f.width_cm * scale, f.length_cm * scale
        if f.type in (FeatureType.TREE, FeatureType.WATER_BUTT, FeatureType.SHRUB):
            r = min(fw, fh) / 2
            s.circle(fx + fw / 2, fy + fh / 2, r, fill=_mix(color, 0.35), stroke=color, width=0.3)
        else:
            s.rect(fx, fy, fw, fh, fill=_mix(color, 0.3), stroke=color, width=0.25)
            s.hatch(fx, fy, fw, fh, pattern, color, spacing=2.0)
        if fw > 12 and fh > 4:
            s.text(fx + fw / 2, fy + fh / 2 + 1.0, ellipsize(f.name, fw - 2, 6), size=6, color=INK, anchor="middle")

    # Ground covers first: zones and other elements drawn on them take their piece (a house on the lawn).
    for f in ground:
        draw_feature(f)
    for z in zones:
        result.zone_types.add(z.type)
        zx, zy, zw, zh = X(z.x_cm), Y(z.y_cm), z.width_cm * scale, z.length_cm * scale
        s.rect(zx, zy, zw, zh, fill=theme.zone_fill(z))
        if z.type is ZoneType.GREENHOUSE:
            s.rect(zx, zy, zw, zh, stroke=theme.zone_stroke(z), width=0.6)
            s.rect(zx + 0.8, zy + 0.8, zw - 1.6, zh - 1.6, stroke=theme.zone_stroke(z), width=0.2)
        else:
            dash = (1.5, 1.0) if z.type is ZoneType.COLD_FRAME else (3.0, 1.5)
            s.rect(zx, zy, zw, zh, stroke=theme.zone_stroke(z), width=0.35, dash=dash)
        # Zone names sit on the bottom edge: bed names are drawn above each bed.
        s.text(
            zx + 1.5, zy + zh - 1.5, ellipsize(z.name, zw - 3, 7, True), size=7, bold=True, color=theme.zone_stroke(z)
        )

    for f in above:
        draw_feature(f)

    bed_ids = {b.id for b in beds}
    items = _season_plantings(ctx, season, bed_ids) if plantings else []
    number = number_from
    for bed in beds:
        bx, by, bw, bh = X(bed.x_cm), Y(bed.y_cm), bed.width_cm * scale, bed.length_cm * scale
        container = bed.kind is BedKind.CONTAINER
        result.has_container |= container
        s.rect(bx, by, bw, bh, fill="#FFFFFF", radius=1.5 if container else 0)
        if bed_grid_cm:
            step = bed_grid_cm * scale
            gx = bx + step
            while gx < bx + bw - 0.1:
                s.line(gx, by, gx, by + bh, stroke=GRID, width=0.12)
                gx += step
            gy = by + step
            while gy < by + bh - 0.1:
                s.line(bx, gy, bx + bw, gy, stroke=GRID, width=0.12)
                gy += step
        for p in (p for p in items if p.bed_id == bed.id):
            plant = ctx.db.get(p.plant_id)
            if plant is None:
                continue
            if plant.family not in result.families:
                result.families.append(plant.family)
            px, py, pw, ph = bx + p.x_cm * scale, by + p.y_cm * scale, p.width_cm * scale, p.length_cm * scale
            fam = theme.family_color(plant.family)
            s.rect(px, py, pw, ph, fill=theme.family_fill(plant.family), stroke=fam, width=0.3)
            s.hatch(px, py, pw, ph, theme.family_pattern(plant.family), _mix(fam, 0.55), spacing=2.2)
            positions = plant_positions(p, plant)
            r = plant.spacing_cm * scale * 0.18
            if r >= 0.35 and len(positions) <= 400:
                pts = [(bx + cx * scale, by + cy * scale) for cx, cy in positions]
                if r >= 0.9:
                    for cx, cy in pts:
                        s.circle(cx, cy, min(r, 2.2), stroke=fam, width=0.2, fill="#FFFFFF")
                else:
                    s.dots(pts, r=r, color=fam)
            name = plant.name(lang)
            size = 6.5 if scale > 0.25 else 5.5
            if page.opts.labels and pw > text_width(name, size, True) + 2 and ph > 4.5:
                tw = text_width(name, size, True) + 1.6
                s.rect(px + pw / 2 - tw / 2, py + ph / 2 - 2.3, tw, 3.3, fill="#FFFFFF", radius=0.8)
                s.text(px + pw / 2, py + ph / 2 + 0.2, name, size=size, bold=True, color=INK, anchor="middle")
            else:
                result.numbered.append((number, p, plant))
                rr = 1.7
                cx, cy = px + min(pw / 2, max(rr, pw - rr)), py + min(ph / 2, max(rr, ph - rr))
                s.circle(cx, cy, rr, fill="#FFFFFF", stroke=fam, width=0.25)
                s.text(cx, cy + 0.85, str(number), size=5.5, bold=True, color=INK, anchor="middle")
                number += 1
        s.rect(bx, by, bw, bh, stroke=INK, width=0.45, radius=1.5 if container else 0)
        if bh > 3:
            lbl = ellipsize(bed.name, max(bw, 15), 6.5, True)
            s.text(bx, by - 1.0, lbl, size=6.5, bold=True, color=INK)

    _north_arrow(s, box.x2 - 9, box.y + 3, page.theme)
    _scale_bar(s, box.x + 2, box.y2 - 3, scale, page)
    return result


def _north_arrow(s: Surface, x: float, y: float, theme: Theme) -> None:
    """Canvas north is up (the planner draws north at the top)."""
    s.circle(x + 3.5, y + 5, 4.2, fill="#FFFFFF", stroke=FAINT, width=0.2)
    s.polygon([(x + 3.5, y + 1.2), (x + 5.5, y + 7.5), (x + 3.5, y + 6.2), (x + 1.5, y + 7.5)], fill=INK)
    s.text(x + 3.5, y + 11.8, "N", size=7, bold=True, color=INK, anchor="middle")


def _nice_length(cm_per_mm: float, target_mm: float = 28.0) -> float:
    raw = cm_per_mm * target_mm
    for nice in (10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000):
        if nice >= raw * 0.7:
            return float(nice)
    return 10000.0


def _scale_bar(s: Surface, x: float, y: float, scale: float, page: Page) -> None:
    length_cm = _nice_length(1 / scale)
    w = length_cm * scale
    half = w / 2
    s.rect(x, y - 2.0, half, 1.6, fill=INK)
    s.rect(x + half, y - 2.0, half, 1.6, fill="#FFFFFF", stroke=INK, width=0.2)
    s.rect(x, y - 2.0, w, 1.6, stroke=INK, width=0.2)
    text = f"{length_cm / 100:g} m" if length_cm >= 100 else f"{length_cm:g} cm"
    s.text(x + w + 1.5, y - 0.4, text, size=6.5, color=INK)
    ratio = round(10 / scale)  # 1 mm on paper = 1/scale cm = 10/scale mm
    s.text(x + w + 1.5 + text_width(text, 6.5) + 3, y - 0.4, f"1:{_round_ratio(ratio)}", size=6.5, color=MUTED)


def _round_ratio(value: int) -> int:
    if value < 10:
        return value
    digits = 10 ** (len(str(value)) - 2)
    return round(value / digits) * digits


def draw_legend(page: Page, box: Box, result: MapResult, *, crops: bool = True) -> float:
    """Legend: families, zones, elements, symbols and the numbered crops."""
    s, theme, lang = page.s, page.theme, page.opts.lang
    y = box.y + 3.5
    s.text(box.x, y, page.lbl("legend"), size=8, bold=True, color=MUTED)
    y += 2.0
    cols = 2 if box.w > 70 else 1
    col_w = (box.w - 4) / 2 if cols == 2 else box.w
    entries: list[tuple[Callable[[float, float], None], str]] = []
    for fam in result.families:
        info = FAMILIES.get(fam, {})
        name = info.get(normalize_lang(lang), fam)

        def swatch(xx: float, yy: float, fam: str = fam) -> None:
            col = theme.family_color(fam)
            s.rect(xx, yy, 6, 3.6, fill=theme.family_fill(fam), stroke=col, width=0.3)
            s.hatch(xx, yy, 6, 3.6, theme.family_pattern(fam), _mix(col, 0.55), spacing=1.6)

        entries.append((swatch, name))
    for zt in sorted(result.zone_types, key=lambda z: z.value):
        zone = Zone("legend", "", type=zt)

        def zswatch(xx: float, yy: float, zone: Zone = zone) -> None:
            dash = None if zone.type is ZoneType.GREENHOUSE else (1.5, 1.0)
            s.rect(xx, yy, 6, 3.6, fill=theme.zone_fill(zone), stroke=theme.zone_stroke(zone), width=0.35, dash=dash)

        entries.append((zswatch, page.lbl(zone_label(zt))))
    for ft in sorted(result.features, key=lambda f: f.value):
        color, pattern = FEATURE_STYLE[ft]

        def fswatch(xx: float, yy: float, color: str = theme.col(color), pattern: str = pattern) -> None:
            s.rect(xx, yy, 6, 3.6, fill=_mix(color, 0.3), stroke=color, width=0.25)
            s.hatch(xx, yy, 6, 3.6, pattern, color, spacing=1.4)

        entries.append((fswatch, page.lbl(FEATURE_LABEL[ft])))

    def bed_sw(xx: float, yy: float) -> None:
        s.rect(xx, yy, 6, 3.6, fill="#FFFFFF", stroke=INK, width=0.45)

    entries.append((bed_sw, page.lbl("bed_outline")))
    if result.has_container:
        entries.append(
            (lambda xx, yy: s.rect(xx, yy, 6, 3.6, stroke=INK, width=0.45, radius=1.2), page.lbl("container"))
        )
    entries.append(
        (lambda xx, yy: s.circle(xx + 3, yy + 1.8, 1.2, stroke=MUTED, width=0.2, fill="#FFFFFF"), page.lbl("plant_pos"))
    )
    row_h = 5.0
    for i, (draw, text) in enumerate(entries):
        cx = box.x + (i % cols) * (col_w + 4)
        cy = y + (i // cols) * row_h
        if cy + row_h > box.y2:
            break
        draw(cx, cy)
        s.text(cx + 8, cy + 3.0, ellipsize(text, col_w - 9, 7), size=7, color=INK)
    y += math.ceil(len(entries) / cols) * row_h + 2
    if crops and result.numbered:
        for i, (num, p, plant) in enumerate(result.numbered):
            cx = box.x + (i % cols) * (col_w + 4)
            cy = y + (i // cols) * 4.2
            if cy + 4.2 > box.y2:
                break
            s.circle(cx + 1.7, cy + 1.6, 1.6, fill="#FFFFFF", stroke=theme.family_color(plant.family), width=0.25)
            s.text(cx + 1.7, cy + 2.4, str(num), size=5.5, bold=True, color=INK, anchor="middle")
            bed = page.ctx.data.bed(p.bed_id)
            s.text(
                cx + 5,
                cy + 2.6,
                ellipsize(f"{plant.name(lang)} ({bed.name if bed else ''})", col_w - 6, 6.5),
                size=6.5,
                color=INK,
            )
        y += math.ceil(len(result.numbered) / cols) * 4.2 + 2
    return y


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class Column:
    title: str
    width: float  # fraction of the table width
    align: str = "start"


def draw_table(
    s: Surface,
    box: Box,
    columns: Sequence[Column],
    rows: Sequence[Sequence[str]],
    *,
    size: float = 7.5,
    row_h: float = 5.2,
    swatches: Sequence[str | None] | None = None,
    checkbox: bool = False,
) -> int:
    """Draw as many rows as fit; returns how many were drawn."""
    y = box.y
    widths = [c.width * box.w for c in columns]
    s.rect(box.x, y, box.w, row_h, fill="#EEF2EF")
    x = box.x
    for col, w in zip(columns, widths, strict=True):
        tx = x + 1.2 if col.align == "start" else x + w - 1.2
        s.text(tx, y + row_h * 0.68, ellipsize(col.title, w - 2, size, True), size=size, bold=True, color=INK,
               anchor="start" if col.align == "start" else "end")  # fmt: skip
        x += w
    y += row_h
    drawn = 0
    for idx, row in enumerate(rows):
        if y + row_h > box.y2:
            break
        if idx % 2:
            s.rect(box.x, y, box.w, row_h, fill="#F7F9F7")
        x = box.x
        for c_idx, (col, w, cell) in enumerate(zip(columns, widths, row, strict=False)):
            pad = 1.2
            if c_idx == 0 and checkbox:
                s.rect(x + 1.2, y + row_h / 2 - 1.6, 3.2, 3.2, stroke=INK, width=0.3, radius=0.4)
                pad = 5.6
            if c_idx == 0 and swatches and swatches[idx]:
                s.rect(x + pad, y + row_h / 2 - 1.3, 2.6, 2.6, fill=swatches[idx])
                pad += 3.6
            tx = x + pad if col.align == "start" else x + w - 1.2
            s.text(tx, y + row_h * 0.68, ellipsize(cell, w - pad - 1, size), size=size, color=INK,
                   anchor="start" if col.align == "start" else "end")  # fmt: skip
            x += w
        s.line(box.x, y + row_h, box.x2, y + row_h, stroke="#E1E6E2", width=0.15)
        y += row_h
        drawn += 1
    return drawn


def _fmt(d: date | None, lang: str) -> str:
    if d is None:
        return "-"
    code = normalize_lang(lang)
    day = f"{d.day}." if code == "de" else str(d.day)  # German: "5. Mai"
    return f"{day} {MONTHS[code][d.month - 1]}"


def _crop_rows(ctx: PrintContext, plantings: Sequence[Planting], lang: str) -> tuple[list[list[str]], list[str | None]]:
    rows, swatches = [], []
    for p in sorted(plantings, key=lambda p: (ctx.data.bed(p.bed_id).name if ctx.data.bed(p.bed_id) else "", p.x_cm)):
        plant = ctx.db.get(p.plant_id)
        bed = ctx.data.bed(p.bed_id)
        if plant is None or bed is None:
            continue
        tl = ctx.timelines.get(p.id)
        rows.append(
            [
                plant.name(lang),
                bed.name,
                str(plant_count(p, plant)),
                _fmt(tl.sow_date if tl else None, lang),
                _fmt(tl.transplant_date if tl else None, lang),
                f"{_fmt(tl.harvest_start, lang)} - {_fmt(tl.harvest_end, lang)}" if tl else "-",
            ]
        )
        swatches.append(FAMILIES.get(plant.family, {}).get("color"))
    return rows, swatches


def _crop_columns(page: Page) -> list[Column]:
    return [
        Column(page.lbl("crop"), 0.27),
        Column(page.lbl("bed"), 0.2),
        Column(page.lbl("count"), 0.09, "end"),
        Column(page.lbl("sow"), 0.12),
        Column(page.lbl("plant_out"), 0.12),
        Column(page.lbl("harvest"), 0.2),
    ]


# --------------------------------------------------------------------------- #
# Documents
# --------------------------------------------------------------------------- #
class Renderer:
    """Produces pages on any surface factory (PDF or SVG)."""

    def __init__(self, ctx: PrintContext, opts: PrintOptions, new_surface: Callable[[float, float], Surface]) -> None:
        self.ctx = ctx
        self.opts = opts
        self.new_surface = new_surface
        self.theme = Theme(opts.color_mode)
        self.pages: list[Page] = []
        w, h = PAGE_SIZES[opts.page]
        self.size = (h, w) if opts.landscape else (w, h)
        self.season = opts.season or _current_season(ctx)
        # Print the garden plan of the chosen season (a copy of the data with that plan).
        layout = layout_for(ctx.data, self.season)
        if layout is not None and layout.zones is not ctx.data.zones:
            data = dataclasses.replace(ctx.data, zones=layout.zones, beds=layout.beds, features=layout.features)
            self.ctx = dataclasses.replace(ctx, data=data)

    def page(self, title: str, subtitle: str = "") -> Page:
        surface = self.new_surface(*self.size)
        if self.opts.color_mode == "grayscale":
            surface.grayscale = True  # type: ignore[attr-defined]
        page = Page(surface, self.opts, self.ctx, self.theme, title)
        page.header(subtitle)
        self.pages.append(page)
        return page

    def lbl(self, key: str, **params: Any) -> str:
        return label(self.opts.lang, key, **params)

    def render(self) -> list[Page]:
        getattr(self, f"_doc_{self.opts.document}")()
        for i, page in enumerate(self.pages, start=1):
            page.footer(i, len(self.pages))
        return self.pages

    # -- helpers ------------------------------------------------------------ #
    def _split(self, page: Page, map_share: float = 0.64) -> tuple[Box, Box]:
        b = page.body
        if page.s.width > page.s.height:  # landscape: map left, side panel right
            mw = b.w * 0.68
            return Box(b.x, b.y, mw, b.h), Box(b.x + mw + 5, b.y, b.w - mw - 5, b.h)
        mh = b.h * map_share
        return Box(b.x, b.y, b.w, mh), Box(b.x, b.y + mh + 4, b.w, b.h - mh - 4)

    def _map_page(
        self, title: str, zones: list[Zone], beds: list[GardenBed], subtitle: str, features: Sequence[Feature] = ()
    ) -> None:
        page = self.page(title, subtitle)
        # A wide garden needs less height: give the rest to legend and notes.
        x0, y0, x1, y1 = _bounds(zones, beds, features)
        wanted = (page.body.w - 24) * (y1 - y0) / max(x1 - x0, 1.0) + 26
        map_box, side = self._split(page, max(0.4, min(0.66, wanted / page.body.h)))
        result = draw_map(page, map_box, zones, beds, features, self.season)
        if page.s.width > page.s.height:
            y = draw_legend(page, side, result)
            if self.opts.notes:
                _notes(page, Box(side.x, y + 2, side.w, side.y2 - y - 2))
        else:
            legend_w = side.w * (0.55 if self.opts.notes else 1.0)
            draw_legend(page, Box(side.x, side.y, legend_w, side.h), result)
            if self.opts.notes:
                _notes(page, Box(side.x + legend_w + 4, side.y, side.w - legend_w - 4, side.h))
        plantings = _season_plantings(self.ctx, self.season, {b.id for b in beds})
        self._crop_table_pages(plantings, title)

    def _crop_table_pages(self, plantings: list[Planting], title: str) -> None:
        rows, swatches = _crop_rows(self.ctx, plantings, self.opts.lang)
        while rows:
            page = self.page(title, self.lbl("crops"))
            drawn = draw_table(page.s, page.body, _crop_columns(page), rows, swatches=swatches)
            rows, swatches = rows[drawn:], swatches[drawn:]
            if not drawn:
                break

    # -- documents ---------------------------------------------------------- #
    def _doc_garden(self) -> None:
        data = self.ctx.data
        self._map_page(
            self.opts.title or self.lbl("garden"),
            list(data.zones),
            list(data.beds),
            self.lbl("season_n", season=self.season),
            data.features,
        )

    def _doc_zone(self) -> None:
        data = self.ctx.data
        zones = [z for z in data.zones if self.opts.zone_id in (None, z.id)]
        if self.opts.zone_id is None:
            zones = [z for z in zones if z.is_enclosed] or zones
        for zone in zones:
            beds = [b for b in data.beds if b.zone_id == zone.id]
            sub = f"{zone.name} · {self.lbl(zone_label(zone.type))} · {self.lbl('season_n', season=self.season)}"
            self._map_page(self.opts.title or self.lbl("zone"), [zone], beds, sub)

    def _doc_blank(self) -> None:
        data = self.ctx.data
        zones = [z for z in data.zones if self.opts.zone_id in (None, z.id)]
        beds = [b for b in data.beds if any(b.zone_id == z.id for z in zones)]
        page = self.page(self.opts.title or self.lbl("blank"), self.lbl("season_n", season=self.season))
        map_box, side = self._split(page, 0.7)
        _dot_grid(page.s, map_box, pitch=5.0, color="#DDE3DF")
        result = draw_map(page, map_box, zones, beds, data.features, self.season, plantings=False)
        # Every family as a colour key to fill in by hand.
        result.families = [f for f in FAMILIES if f in {p.family for p in self.ctx.db.all()}][:14]
        draw_legend(page, side, result, crops=False)

    def _doc_beds(self) -> None:
        data, lang = self.ctx.data, self.opts.lang
        beds = [b for b in data.beds if self.opts.bed_ids is None or b.id in self.opts.bed_ids]
        for bed in beds:
            zone = data.zone(bed.zone_id)
            sub = f"{bed.name} · {zone.name if zone else ''} · {bed.width_cm / 100:g} x {bed.length_cm / 100:g} m"
            page = self.page(self.opts.title or self.lbl("beds"), sub)
            b = page.body
            plan_h = min(b.h * 0.5, b.w * bed.length_cm / max(bed.width_cm, 1) + 18)
            result = draw_map(
                page,
                Box(b.x, b.y, b.w, plan_h),
                [],
                [bed],
                [],
                self.season,
                bed_grid_cm=10.0 if self.opts.grid else None,
            )
            y = b.y + plan_h + 2
            plantings = _season_plantings(self.ctx, self.season, {bed.id})
            plants = [pl for pl in (self.ctx.db.get(p.plant_id) for p in plantings) if pl]
            info = [
                f"{self.lbl('area')}: {bed.area_m2:.1f} m²",
                f"{self.lbl('soil')}: {bed.soil.value}",
            ]
            if plants:
                fert = bed_fertilizer_plan(bed.area_m2, plants, lang, bed.latest_soil_test)
                info.append(self.lbl("compost", kg=fert.compost_kg))
                if fert.base_fertilizer_g:
                    info.append(self.lbl("fertilizer", g=fert.base_fertilizer_g))
                if fert.lime_check:
                    info.append(self.lbl("lime"))
            history = sorted(
                {(r.season, r.family) for r in data.rotation_history if r.bed_id == bed.id and r.season < self.season},
                reverse=True,
            )[:3]
            if history:
                fams = ", ".join(f"{s_}: {FAMILIES.get(f, {}).get(normalize_lang(lang), f)}" for s_, f in history)
                info.append(f"{self.lbl('rotation')}: {fams}")
            y = page.s.text_block(b.x, y, b.w, " · ".join(info), size=7.5, color=MUTED)
            rows, swatches = _crop_rows(self.ctx, plantings, lang)
            cols = _crop_columns(page)
            cols[1] = Column(self.lbl("spacing"), 0.2)
            for row, p in zip(rows, sorted(plantings, key=lambda p: p.x_cm), strict=False):
                plant = self.ctx.db.get(p.plant_id)
                row[1] = f"{plant.spacing_cm:g} x {plant.row_spacing_cm:g} cm" if plant else "-"
            table_h = min(5.2 * (len(rows) + 1) + 1, (b.y2 - y) * 0.6)
            if rows:
                draw_table(page.s, Box(b.x, y + 2, b.w, table_h), cols, rows, swatches=swatches)
            else:
                page.s.text(b.x, y + 6, self.lbl("empty"), size=8, color=MUTED)
                table_h = 8
            if result.numbered:
                draw_legend(
                    page, Box(b.x, y + table_h + 4, b.w, 20), MapResult(result.scale, result.numbered), crops=True
                )
            if self.opts.notes:
                top = y + table_h + 6 + (24 if result.numbered else 0)
                _notes(page, Box(b.x, top, b.w, b.y2 - top))

    def _doc_tasks(self) -> None:
        data, lang, today = self.ctx.data, self.opts.lang, self.ctx.today
        until = today + timedelta(days=self.opts.days)
        tasks: list[Task] = sorted(
            (t for t in data.tasks if t.is_open and t.due <= until),
            key=lambda t: (max(t.due, today), -t.priority.rank, t.title),
        )
        rows: list[list[str]] = []
        week_rows: list[bool] = []
        current_week = None
        for t in tasks:
            due = max(t.due, today)
            monday = due - timedelta(days=due.weekday())
            if monday != current_week:
                current_week = monday
                rows.append([self.lbl("week", date=_fmt(monday, lang)), "", "", ""])
                week_rows.append(True)
            bed = data.bed(t.bed_id) if t.bed_id else None
            zone = data.zone(t.zone_id) if t.zone_id else None
            where = bed.name if bed else zone.name if zone else ""
            overdue = " !" if t.due < today else ""
            rows.append([t.title, _fmt(t.due, lang) + overdue, where, str(t.estimated_minutes or "")])
            week_rows.append(False)
        cols = [
            Column(self.lbl("task"), 0.56),
            Column(self.lbl("due"), 0.14),
            Column(self.lbl("bed"), 0.2),
            Column(self.lbl("minutes"), 0.1, "end"),
        ]
        first = True
        while rows or first:
            page = self.page(self.opts.title or self.lbl("tasks"), f"{_fmt(today, lang)} - {_fmt(until, lang)}")
            body = page.body
            drawn = self._task_table(
                page.s, Box(body.x, body.y, body.w, body.h - (34 if first else 0)), cols, rows, week_rows
            )
            rows, week_rows = rows[drawn:], week_rows[drawn:]
            if first:
                # Empty lines for extra tasks, written by hand.
                y = body.y2 - 30
                page.s.text(body.x, y, self.lbl("add_tasks"), size=8, bold=True, color=MUTED)
                for i in range(5):
                    ly = y + 5 + i * 5.5
                    page.s.rect(body.x + 1.2, ly - 2.6, 3.2, 3.2, stroke=INK, width=0.3, radius=0.4)
                    page.s.line(body.x + 6.5, ly + 0.8, body.x2, ly + 0.8, stroke=FAINT, width=0.2)
            first = False
            if not drawn:
                break

    def _task_table(
        self, s: Surface, box: Box, cols: list[Column], rows: list[list[str]], week_rows: list[bool]
    ) -> int:
        """Checklist rows with a checkbox; week rows act as sub-headings."""
        widths = [c.width * box.w for c in cols]
        size = 7.5
        y = box.y
        s.rect(box.x, y, box.w, 5.2, fill="#EEF2EF")
        x = box.x + 5.6
        for col, w in zip(cols, widths, strict=True):
            tx = x if col.align == "start" else x + w - 6.8
            s.text(
                tx,
                y + 3.6,
                col.title,
                size=size,
                bold=True,
                color=INK,
                anchor="start" if col.align == "start" else "end",
            )
            x += w
        y += 5.2
        drawn = 0
        for idx, row in enumerate(rows):
            row_h = 7.0 if week_rows[idx] else 5.6
            if y + row_h > box.y2:
                break
            if week_rows[idx]:
                s.text(box.x, y + 5.2, row[0], size=8, bold=True, color=self.theme.col(BRAND))
                s.line(box.x, y + 6.4, box.x2, y + 6.4, stroke=self.theme.col(BRAND), width=0.3)
            else:
                s.rect(box.x + 1.2, y + row_h / 2 - 1.6, 3.2, 3.2, stroke=INK, width=0.3, radius=0.4)
                x = box.x + 5.6
                for col, w, cell in zip(cols, widths, row, strict=True):
                    avail = w - (6.8 if x == box.x + 5.6 else 1.2)
                    tx = x if col.align == "start" else x + w - 6.8
                    s.text(
                        tx,
                        y + 3.9,
                        ellipsize(cell, avail, size),
                        size=size,
                        color=INK,
                        anchor="start" if col.align == "start" else "end",
                    )
                    x += w
                s.line(box.x, y + row_h, box.x2, y + row_h, stroke="#E1E6E2", width=0.15)
            y += row_h
            drawn += 1
        return drawn

    def _doc_season(self) -> None:
        data, region = self.ctx.data, self.ctx.data.settings.region
        start, end = season_bounds(region, self.season)
        anchors = season_anchors(region, self.season)
        plantings = sorted(
            (p for p in data.plantings if _present(self.ctx, p, self.season) and p.id in self.ctx.timelines),
            key=lambda p: ((data.bed(p.bed_id).name if data.bed(p.bed_id) else ""), self.ctx.timelines[p.id].in_ground),
        )
        first = True
        while plantings or first:
            page = self.page(self.opts.title or self.lbl("season"), self.lbl("season_n", season=self.season))
            drawn = self._gantt(page, page.body, plantings, start, end, anchors)
            plantings = plantings[drawn:]
            first = False
            if not drawn:
                break

    def _gantt(self, page: Page, box: Box, plantings: list[Planting], start: date, end: date, anchors: Any) -> int:
        s, lang, theme = page.s, self.opts.lang, self.theme
        label_w = min(48.0, box.w * 0.3)
        gx, gw = box.x + label_w, box.w - label_w
        total = (end - start).days + 1

        def X(d: date) -> float:
            return gx + max(0, min(total, (d - start).days)) / total * gw

        # month header
        d = start
        while d <= end:
            nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
            x1, x2 = X(d), X(min(nxt, end + timedelta(days=1)))
            if d.month % 2:
                s.rect(x1, box.y, x2 - x1, box.h, fill="#F6F8F6")
            s.text(
                (x1 + x2) / 2,
                box.y + 4,
                MONTHS[normalize_lang(lang)][d.month - 1],
                size=7,
                bold=True,
                color=MUTED,
                anchor="middle",
            )
            d = nxt
        top = box.y + 10
        if not anchors.frost_free:
            for day, key in ((anchors.last_frost, "frost_last"), (anchors.first_frost, "frost_first")):
                if start <= day <= end:
                    s.line(X(day), top, X(day), box.y2, stroke="#5DA9C9", width=0.35, dash=(1.2, 1.0))
                    s.text(X(day) + 0.8, box.y + 8.3, self.lbl(key), size=5.5, color="#2D7898")
        if start <= self.ctx.today <= end:
            s.line(X(self.ctx.today), top, X(self.ctx.today), box.y2, stroke="#C8432F", width=0.35)
        row_h = 5.0
        y = top
        drawn = 0
        for p in plantings:
            if y + row_h > box.y2 - 4:
                break
            plant = self.ctx.db.get(p.plant_id)
            bed = self.ctx.data.bed(p.bed_id)
            tl = self.ctx.timelines[p.id]
            if plant is None:
                continue
            fam = theme.family_color(plant.family)
            name = f"{plant.name(lang)} · {bed.name if bed else ''}"
            s.text(box.x, y + 3.6, ellipsize(name, label_w - 2, 6.5), size=6.5, color=INK)
            if tl.sow_date and tl.sow_date < tl.in_ground:
                s.rect(
                    X(tl.sow_date),
                    y + 1.6,
                    X(tl.in_ground) - X(tl.sow_date),
                    1.8,
                    fill=_mix(fam, 0.25),
                    stroke=fam,
                    width=0.15,
                    dash=(0.6, 0.5),
                )
            s.rect(
                X(tl.in_ground),
                y + 0.8,
                max(X(tl.harvest_start) - X(tl.in_ground), 0.3),
                3.4,
                fill=theme.family_fill(plant.family),
                stroke=fam,
                width=0.2,
            )
            s.hatch(
                X(tl.in_ground),
                y + 0.8,
                max(X(tl.harvest_start) - X(tl.in_ground), 0.3),
                3.4,
                theme.family_pattern(plant.family),
                _mix(fam, 0.55),
                spacing=1.6,
            )
            s.rect(X(tl.harvest_start), y + 0.8, max(X(tl.harvest_end) - X(tl.harvest_start), 0.6), 3.4, fill=fam)
            s.line(box.x, y + row_h, box.x2, y + row_h, stroke="#EEF1EE", width=0.12)
            y += row_h
            drawn += 1
        # key
        ky = box.y2 - 1
        kx = gx + gw * 0.35
        s.rect(kx, ky - 2.6, 5, 1.8, fill="#E5EBE6", stroke=MUTED, width=0.15, dash=(0.6, 0.5))
        s.text(kx + 6, ky - 1, self.lbl("sow"), size=5.5, color=MUTED)
        kx += 6 + text_width(self.lbl("sow"), 5.5) + 4
        s.rect(kx, ky - 2.9, 5, 2.4, fill="#D6E6CC", stroke=MUTED, width=0.15)
        s.text(kx + 6, ky - 1, self.lbl("plant_out"), size=5.5, color=MUTED)
        kx += 6 + text_width(self.lbl("plant_out"), 5.5) + 4
        s.rect(kx, ky - 2.9, 5, 2.4, fill=MUTED)
        s.text(kx + 6, ky - 1, self.lbl("harvest"), size=5.5, color=MUTED)
        return drawn

    def _doc_year(self) -> None:
        """Month matrix: per crop when to sow, plant out, let grow and harvest."""
        from .records import year_matrix

        matrix = year_matrix(self.ctx.data, self.ctx.db, self.ctx.timelines, self.season)
        rows = matrix["rows"]
        lang = normalize_lang(self.opts.lang)
        colors = {
            "sow_indoor": "#CFE3C0",
            "sow": "#9CC46A",
            "plant": "#4E7D3A",
            "grow": "#EEF3EA",
            "harvest": "#E0A526",
        }
        order = ("harvest", "plant", "sow", "sow_indoor", "grow")
        first = True
        while rows or first:
            first = False
            page = self.page(self.opts.title or self.lbl("year"), self.lbl("season_n", season=self.season))
            s, box = page.s, page.body
            label_w = min(46.0, box.w * 0.3)
            col_w = (box.w - label_w) / 12
            for m in range(12):
                x = box.x + label_w + m * col_w
                if m % 2 == 0:
                    s.rect(x, box.y, col_w, box.h - 8, fill="#F6F8F6")
                s.text(x + col_w / 2, box.y + 4, MONTHS[lang][m], size=7, bold=True, color=MUTED, anchor="middle")
            row_h = 6.0
            y = box.y + 7
            drawn = 0
            for row in rows:
                if y + row_h > box.y2 - 16:
                    break
                plant = self.ctx.db.get(row["plant_id"])
                name = plant.name(lang) if plant else row["plant_id"]
                s.text(box.x, y + 4, ellipsize(name, label_w - 2, 7), size=7, color=INK)
                for m in range(12):
                    acts = row["months"][str(m + 1)]
                    act = next((a for a in order if a in acts), None)
                    if act is None:
                        continue
                    x = box.x + label_w + m * col_w
                    s.rect(x + 0.4, y + 1, col_w - 0.8, row_h - 2, fill=colors[act], stroke=MUTED, width=0.1)
                    if len(acts) > 1 and act != "grow":
                        s.text(x + col_w - 1.2, y + 4, "+", size=5.5, color=INK, anchor="end")
                s.line(box.x, y + row_h, box.x2, y + row_h, stroke="#EEF1EE", width=0.12)
                y += row_h
                drawn += 1
            rows = rows[drawn:]
            # tasks per month + key
            ty = box.y2 - 12
            s.text(box.x, ty + 4, self.lbl("tasks_month"), size=7, bold=True, color=INK)
            for m in range(12):
                x = box.x + label_w + m * col_w
                s.text(x + col_w / 2, ty + 4, str(matrix["tasks"][m]), size=7, color=MUTED, anchor="middle")
            kx, ky = box.x, box.y2 - 2
            for act in ("sow_indoor", "sow", "plant", "grow", "harvest"):
                key = {"sow": "sow", "plant": "plant_out", "harvest": "harvest"}.get(act, act)
                s.rect(kx, ky - 2.6, 5, 2.4, fill=colors[act], stroke=MUTED, width=0.12)
                s.text(kx + 6, ky - 0.8, self.lbl(key), size=5.5, color=MUTED)
                kx += 6 + text_width(self.lbl(key), 5.5) + 5
            if not drawn:
                break

    def _doc_plants(self) -> None:
        db = self.ctx.db
        if self.opts.plant_ids:
            plants = [p for p in (db.get(i) for i in self.opts.plant_ids) if p]
        else:
            ids = []
            for p in self.ctx.data.plantings:
                if _present(self.ctx, p, self.season) and p.plant_id not in ids:
                    ids.append(p.plant_id)
            plants = [p for p in (db.get(i) for i in ids) if p]
        per_page = 6 if self.size[1] > 250 else 4
        cols = 2
        for start in range(0, max(len(plants), 1), per_page):
            page = self.page(self.opts.title or self.lbl("plants"), self.lbl("season_n", season=self.season))
            b = page.body
            rows = per_page // cols
            cw, ch = (b.w - 4) / cols, (b.h - 4 * (rows - 1)) / rows
            if not plants:
                page.s.text(b.x, b.y + 6, self.lbl("empty"), size=9, color=MUTED)
            for i, plant in enumerate(plants[start : start + per_page]):
                self._plant_card(page, Box(b.x + (i % cols) * (cw + 4), b.y + (i // cols) * (ch + 4), cw, ch), plant)

    def _window_text(self, wdw: Any) -> str:
        """``-8..-6`` -> "8-6 wk before last frost"; ``-2..4`` -> "2 wk before - 4 wk after"."""
        anchor = self.lbl("frost_last" if wdw.anchor == "last_frost" else "frost_first")

        def rel(week: int) -> str:
            return self.lbl("before") if week < 0 else self.lbl("after")

        a, b = wdw.start_week, wdw.end_week
        if a == 0 and b == 0:
            return anchor
        if (a < 0) == (b < 0) or a == 0 or b == 0:
            ref = a if a != 0 else b
            return f"{abs(a)}-{abs(b)} wk {rel(ref)} {anchor}"
        return f"{abs(a)} wk {rel(a)} - {abs(b)} wk {rel(b)} {anchor}"

    def _plant_card(self, page: Page, box: Box, plant: Plant) -> None:
        s, lang, theme = page.s, self.opts.lang, self.theme
        fam = theme.family_color(plant.family)
        s.rect(box.x, box.y, box.w, box.h, stroke=FAINT, width=0.3, radius=2)
        s.rect(box.x, box.y, 2.2, box.h, fill=fam)
        x, w = box.x + 5, box.w - 8
        s.text(x, box.y + 6, ellipsize(plant.name(lang), w, 11, True), size=11, bold=True, color=INK)
        fam_name = FAMILIES.get(plant.family, {}).get(normalize_lang(lang), plant.family)
        s.text(x, box.y + 10, ellipsize(f"{plant.scientific_name} · {fam_name}", w, 7), size=7, color=MUTED)
        lv = {"low": self.lbl("low"), "medium": self.lbl("medium"), "high": self.lbl("high")}
        facts = [
            (self.lbl("spacing"), f"{plant.spacing_cm:g} x {plant.row_spacing_cm:g} cm"),
            (self.lbl("depth"), f"{plant.sowing_depth_cm:g} cm"),
            (self.lbl("days_to_harvest"), f"{plant.days_to_maturity[0]}-{plant.days_to_maturity[-1]}"),
            (self.lbl("water"), lv.get(plant.water_needs.value, plant.water_needs.value)),
            (self.lbl("feeding"), lv.get(plant.nutrient_needs.value, plant.nutrient_needs.value)),
        ]
        y = box.y + 15
        for k, v in facts:
            s.text(x, y, k, size=7, color=MUTED)
            s.text(x + w, y, v, size=7, bold=True, color=INK, anchor="end")
            y += 4.0
        sow = []
        for kind, windows in (
            ("indoor", plant.sowing.indoor_sow),
            ("direct", plant.sowing.direct_sow),
            ("transplant", plant.sowing.transplant),
        ):
            for wdw in windows[:1]:
                sow.append(f"{self.lbl(kind)}: {self._window_text(wdw)}")
        y = s.text_block(
            x, y - 1, w, f"{self.lbl('sowing_windows')}: " + "; ".join(sow) if sow else "", size=6.8, color=INK
        )
        friends = [self.ctx.db.get(c.plant) for c in plant.companions if c.relation is Relation.FRIEND]
        enemies = [self.ctx.db.get(c.plant) for c in plant.companions if c.relation is Relation.ENEMY]
        if friends:
            y = s.text_block(
                x,
                y + 0.5,
                w,
                f"{self.lbl('good_neighbours')}: " + ", ".join(p.name(lang) for p in friends if p),
                size=6.8,
                color="#3F6B2A",
                max_lines=2,
            )
        if enemies:
            y = s.text_block(
                x,
                y + 0.5,
                w,
                f"{self.lbl('bad_neighbours')}: " + ", ".join(p.name(lang) for p in enemies if p),
                size=6.8,
                color="#A13A2A",
                max_lines=2,
            )
        tip = plant.pruning_notes.get(normalize_lang(lang)) or plant.greenhouse.notes.get(normalize_lang(lang)) or ""
        if tip and y + 6 < box.y2:
            s.text_block(x, y + 0.5, w, tip, size=6.5, color=MUTED, max_lines=max(1, int((box.y2 - y - 3) / 3.2)))


def _current_season(ctx: PrintContext) -> int:
    from .region import season_for_date

    return season_for_date(ctx.data.settings.region, ctx.today)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def render_pdf(ctx: PrintContext, opts: PrintOptions) -> bytes:
    if opts.document == "book":
        from .seasonbook import render_book

        return render_book(ctx, opts)
    doc = PdfDocument(title=f"Hortulus - {label(opts.lang, opts.document)}")

    def factory(w: float, h: float) -> Surface:
        return doc.add_page(w, h)

    Renderer(ctx, opts, factory).render()
    return doc.to_bytes()


def render_svg(ctx: PrintContext, opts: PrintOptions) -> list[str]:
    if opts.document == "book":
        from .seasonbook import render_book_svg

        return render_book_svg(ctx, opts)

    def factory(w: float, h: float) -> Surface:
        return SvgPage(w, h)

    pages = Renderer(ctx, opts, factory).render()
    return [page.s.to_svg(f"p{i}") for i, page in enumerate(pages)]  # type: ignore[attr-defined]


def filename(opts: PrintOptions, season: int | None = None) -> str:
    parts = ["hortulus", opts.document, str(season or opts.season or ""), opts.page]
    return "-".join(p for p in parts if p) + ".pdf"
