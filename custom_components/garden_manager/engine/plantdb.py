"""Plant database: built-in starter pack + user custom plants + overrides."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import copy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
import unicodedata

from .models import CompanionLink, Plant, Relation
from .serde import from_dict, to_dict

BUILTIN_PATH = Path(__file__).resolve().parent.parent / "data" / "plants.json"

# Plant family metadata.  ``color`` matches the frontend design tokens.
FAMILIES: dict[str, dict[str, str]] = {
    "Solanaceae": {"en": "Nightshades", "nl": "Nachtschadefamilie", "fr": "Solanacées", "color": "#C8432F"},
    "Cucurbitaceae": {"en": "Cucurbits", "nl": "Komkommerfamilie", "fr": "Cucurbitacées", "color": "#E0A526"},
    "Fabaceae": {"en": "Legumes", "nl": "Vlinderbloemigen", "fr": "Légumineuses", "color": "#6A9F3A"},
    "Brassicaceae": {"en": "Brassicas", "nl": "Kruisbloemigen", "fr": "Crucifères", "color": "#3E7C8C"},
    "Apiaceae": {"en": "Umbellifers", "nl": "Schermbloemigen", "fr": "Ombellifères", "color": "#E07A2E"},
    "Amaryllidaceae": {"en": "Alliums", "nl": "Uiachtigen", "fr": "Alliacées", "color": "#8E5BA8"},
    "Amaranthaceae": {
        "en": "Beets & spinach",
        "nl": "Amarantenfamilie",
        "fr": "Bettes et épinards",
        "color": "#A23E6B",
    },
    "Asteraceae": {"en": "Daisy family", "nl": "Composietenfamilie", "fr": "Astéracées", "color": "#4FA38A"},
    "Lamiaceae": {"en": "Mints & herbs", "nl": "Lipbloemigen", "fr": "Lamiacées", "color": "#4F6FB0"},
    "Poaceae": {"en": "Grasses", "nl": "Grassenfamilie", "fr": "Graminées", "color": "#B79F2E"},
    "Polygonaceae": {"en": "Knotweed family", "nl": "Duizendknoopfamilie", "fr": "Polygonacées", "color": "#B5485A"},
    "Rosaceae": {"en": "Rose family", "nl": "Rozenfamilie", "fr": "Rosacées", "color": "#D9577A"},
    "Asparagaceae": {"en": "Asparagus family", "nl": "Aspergefamilie", "fr": "Asparagacées", "color": "#5E8C61"},
    "Boraginaceae": {"en": "Borage family", "nl": "Ruwbladigen", "fr": "Boraginacées", "color": "#5C7FC4"},
    "Tropaeolaceae": {"en": "Nasturtiums", "nl": "Oost-Indische-kersfamilie", "fr": "Capucines", "color": "#E2702F"},
    "Caprifoliaceae": {
        "en": "Honeysuckle family",
        "nl": "Kamperfoeliefamilie",
        "fr": "Caprifoliacées",
        "color": "#7AA36A",
    },
    "Portulacaceae": {"en": "Purslanes", "nl": "Posteleinfamilie", "fr": "Pourpiers", "color": "#8DB255"},
    "Montiaceae": {"en": "Miner's lettuces", "nl": "Winterposteleinfamilie", "fr": "Claytones", "color": "#6FA69A"},
    "Aizoaceae": {"en": "Ice plants", "nl": "IJskruidfamilie", "fr": "Aizoacées", "color": "#7F9F4F"},
    "Malvaceae": {"en": "Mallows", "nl": "Kaasjeskruidfamilie", "fr": "Malvacées", "color": "#C77DB0"},
    "Lauraceae": {"en": "Laurels", "nl": "Laurierfamilie", "fr": "Lauracées", "color": "#4D7A4A"},
    "Verbenaceae": {"en": "Verbenas", "nl": "IJzerhardfamilie", "fr": "Verbénacées", "color": "#9A72C2"},
    "Iridaceae": {"en": "Irises", "nl": "Lissenfamilie", "fr": "Iridacées", "color": "#8A5CC4"},
    "Urticaceae": {"en": "Nettles", "nl": "Brandnetelfamilie", "fr": "Urticacées", "color": "#62815A"},
    "Rutaceae": {"en": "Rues", "nl": "Wijnruitfamilie", "fr": "Rutacées", "color": "#A8A23A"},
}


def load_builtin_json(path: Path = BUILTIN_PATH) -> list[dict[str, Any]]:
    """Blocking read of the starter pack - call from an executor in HA."""
    with path.open(encoding="utf-8") as fh:
        doc = json.load(fh)
    return list(doc["plants"])


def deep_merge(base: Mapping[str, Any], patch: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge ``patch`` into a copy of ``base`` (lists are replaced)."""
    out = copy.deepcopy(dict(base))
    for key, value in patch.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _fold(text: str) -> str:
    """Accent- and case-insensitive search key ("Tomaat" ~ "tomaat")."""
    norm = unicodedata.normalize("NFKD", text)
    return "".join(c for c in norm if not unicodedata.combining(c)).casefold()


# Family-level relations: used when no plant-level relation exists, so that
# custom plants and new varieties get sensible companion advice too.
FAMILY_RELATIONS: list[tuple[str, str, Relation, int, dict[str, str]]] = [
    ("Amaryllidaceae", "Fabaceae", Relation.ENEMY, 2,
     {"en": "Alliums inhibit the nitrogen-fixing bacteria of legumes.",
      "nl": "Uiachtigen remmen de stikstofbindende bacteriën van peulvruchten.",
      "fr": "Les alliacées freinent les bactéries fixatrices d'azote des légumineuses."}),
    ("Amaryllidaceae", "Apiaceae", Relation.FRIEND, 2,
     {"en": "Their scents mask each other from onion fly and carrot fly.",
      "nl": "Hun geuren maskeren elkaar voor uienvlieg en wortelvlieg.",
      "fr": "Leurs odeurs se masquent mutuellement contre la mouche de l'oignon et la mouche de la carotte."}),
    ("Brassicaceae", "Solanaceae", Relation.ENEMY, 1,
     {"en": "Two groups of heavy feeders competing for nutrients.",
      "nl": "Twee groepen zware eters die om voeding concurreren.",
      "fr": "Deux groupes de gros consommateurs qui se disputent les nutriments."}),
    ("Lamiaceae", "Brassicaceae", Relation.FRIEND, 1,
     {"en": "Aromatic herbs mask brassicas from cabbage white and flea beetle.",
      "nl": "Aromatische kruiden verbergen kool voor koolwitje en aardvlo.",
      "fr": "Les aromatiques cachent les choux à la piéride et à l'altise."}),
    ("Fabaceae", "Cucurbitaceae", Relation.FRIEND, 1,
     {"en": "Legumes add nitrogen for the hungry cucurbits.",
      "nl": "Peulvruchten leveren stikstof voor de hongerige komkommerachtigen.",
      "fr": "Les légumineuses apportent de l'azote aux cucurbitacées gourmandes."}),
    ("Fabaceae", "Poaceae", Relation.FRIEND, 2,
     {"en": "Nitrogen for the grass, support for the climber (Three Sisters).",
      "nl": "Stikstof voor het gras, steun voor de klimmer (drie zussen).",
      "fr": "De l'azote pour la graminée, un support pour la grimpante (les trois sœurs)."}),
    ("Poaceae", "Cucurbitaceae", Relation.FRIEND, 1,
     {"en": "Squash leaves act as living mulch under corn.",
      "nl": "Pompoenblad werkt als levende mulch onder maïs.",
      "fr": "Les feuilles de courge font un paillage vivant sous le maïs."}),
    ("Fabaceae", "Brassicaceae", Relation.FRIEND, 1,
     {"en": "Legumes leave nitrogen for heavy-feeding brassicas.",
      "nl": "Peulvruchten laten stikstof achter voor zwaar etende kolen.",
      "fr": "Les légumineuses laissent de l'azote pour les choux gourmands."}),
]  # fmt: skip


@dataclass(frozen=True, slots=True)
class RelationInfo:
    relation: Relation
    strength: int
    reasons: dict[str, str]
    # True when only one side declared it (we treat relations as symmetric).
    one_sided: bool
    source: str = "plant"  # plant | family


class PlantDatabase:
    """Immutable view on all plants available to the planner."""

    def __init__(
        self,
        builtin: Iterable[Mapping[str, Any]],
        custom: Iterable[Plant] = (),
        overrides: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        overrides = overrides or {}
        plants: dict[str, Plant] = {}
        for raw in builtin:
            pid = raw["id"]
            if pid in overrides:
                plant = from_dict(Plant, deep_merge(raw, overrides[pid]))
                plant.source = "override"
            else:
                plant = from_dict(Plant, raw)
                plant.source = "builtin"
            plants[pid] = plant
        for plant in custom:
            plant.source = "custom"
            plants[plant.id] = plant
        self._plants = plants
        self._relations = self._index_relations()

    # ------------------------------------------------------------------ #
    def __contains__(self, plant_id: object) -> bool:
        return plant_id in self._plants

    def __len__(self) -> int:
        return len(self._plants)

    def get(self, plant_id: str) -> Plant | None:
        return self._plants.get(plant_id)

    def all(self) -> list[Plant]:
        return sorted(self._plants.values(), key=lambda p: p.id)

    def as_dicts(self) -> list[dict[str, Any]]:
        return [to_dict(p) for p in self.all()]

    def search(
        self,
        query: str = "",
        *,
        family: str | None = None,
        tags: Iterable[str] = (),
        greenhouse_only: bool = False,
    ) -> list[Plant]:
        q = _fold(query.strip())
        wanted_tags = set(tags)
        result = []
        for plant in self.all():
            if family and plant.family != family:
                continue
            if wanted_tags and not wanted_tags.issubset(plant.tags):
                continue
            if greenhouse_only and plant.greenhouse.suitability.value == "no":
                continue
            if q:
                haystack = " ".join(
                    [plant.id, plant.scientific_name, plant.variety or "", plant.family] + list(plant.names.values())
                )
                if q not in _fold(haystack):
                    continue
            result.append(plant)
        return result

    # ------------------------------------------------------------------ #
    def _index_relations(self) -> dict[tuple[str, str], list[CompanionLink]]:
        index: dict[tuple[str, str], list[CompanionLink]] = {}
        for plant in self._plants.values():
            for link in plant.companions:
                index.setdefault((plant.id, link.plant), []).append(link)
        return index

    def relation(self, a: str, b: str) -> RelationInfo:
        """Symmetric relation between two plants.

        If the two sides disagree, *enemy* wins - a planner should rather warn
        once too often than recommend a harmful combination.
        """
        links = self._relations.get((a, b), []) + self._relations.get((b, a), [])
        if not links:
            return self.family_relation(a, b)
        enemies = [link for link in links if link.relation is Relation.ENEMY]
        chosen = enemies or [link for link in links if link.relation is Relation.FRIEND]
        if not chosen:
            return RelationInfo(Relation.NEUTRAL, 0, links[0].reason, one_sided=False)
        reasons: dict[str, str] = {}
        for link in chosen:
            for lang, text in link.reason.items():
                reasons[lang] = f"{reasons[lang]} {text}" if lang in reasons else text
        one_sided = not (self._relations.get((a, b)) and self._relations.get((b, a)))
        return RelationInfo(
            chosen[0].relation,
            max(link.strength for link in chosen),
            reasons,
            one_sided,
        )

    def family_relation(self, a: str, b: str) -> RelationInfo:
        pa, pb = self._plants.get(a), self._plants.get(b)
        if pa is None or pb is None or pa.family == pb.family:
            return RelationInfo(Relation.NEUTRAL, 0, {}, one_sided=False)
        for fa, fb, rel, strength, reason in FAMILY_RELATIONS:
            if {fa, fb} == {pa.family, pb.family}:
                return RelationInfo(rel, strength, reason, one_sided=False, source="family")
        return RelationInfo(Relation.NEUTRAL, 0, {}, one_sided=False)

    def friends_of(self, plant_id: str) -> list[str]:
        return sorted(
            other
            for other in self._plants
            if other != plant_id and self.relation(plant_id, other).relation is Relation.FRIEND
        )

    def enemies_of(self, plant_id: str) -> list[str]:
        return sorted(
            other
            for other in self._plants
            if other != plant_id and self.relation(plant_id, other).relation is Relation.ENEMY
        )


def validate_plant_dict(raw: Mapping[str, Any]) -> Plant:
    """Validate a user-supplied plant definition; raises ``ValueError``."""
    if not raw.get("id") or not str(raw["id"]).replace("_", "").isalnum():
        raise ValueError("Plant id must be a non-empty slug (letters, digits, _)")
    if not raw.get("names"):
        raise ValueError("Plant needs at least one localized name")
    if not raw.get("family"):
        raise ValueError("Plant family is required")
    try:
        plant = from_dict(Plant, dict(raw))
    except (TypeError, ValueError, KeyError) as err:
        raise ValueError(f"Invalid plant definition: {err}") from err
    if plant.spacing_cm <= 0 or plant.row_spacing_cm <= 0:
        raise ValueError("Spacing must be positive")
    if len(plant.days_to_maturity) != 2 or plant.days_to_maturity[0] > plant.days_to_maturity[1]:
        raise ValueError("days_to_maturity must be [min, max]")
    if len(plant.germination_days) != 2:
        raise ValueError("germination_days must be [min, max]")
    return plant
