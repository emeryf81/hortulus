"""Seasonal cooking: a cookbook built from what the garden gives right now.

What is ready to pick (the kitchen report) is matched to cooking techniques that
suit it - a soup, a tray of roasted vegetables, a stir-fry, a pasta, a risotto,
a salad, a gratin, a stew, a frittata, stoemp, stuffed vegetables, a plate with
meat and fries, a pesto, a fruit dessert.  The cook adds what is in the fridge,
a kind of meat or fish (or none), and a side (pasta, rice, bulgur, gnocchi,
potatoes, fries, couscous, pearl couscous ...).  Every recipe is described by a
small *spec* (technique, garden produce, side, protein, extras, servings) and
rendered from it in the user's language, so a saved recipe stays small and
reads well in any language.

The garden produce always comes first: a recipe is only proposed when the garden
supplies its main ingredients; the rest becomes the shopping list.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
import hashlib
import json
import math
from typing import Any

from . import cooking_dishes as _d, cooking_extras as _x
from .models import Plant, PlantCategory
from .pdf import PT_TO_MM, Image, PdfDocument, PdfPage, wrap
from .plantdb import PlantDatabase

# --------------------------------------------------------------------------- #
# Garden produce
# --------------------------------------------------------------------------- #
KINDS = (
    "leafy",
    "brassica",
    "root",
    "allium",
    "fruiting",
    "squash",
    "legume",
    "potato",
    "corn",
    "asparagus",
    "herb",
    "fruit",
)

_ID_KIND = {
    **dict.fromkeys(("potato", "early_potato", "sweet_potato", "oca"), "potato"),
    **dict.fromkeys(("pumpkin", "butternut", "hokkaido", "spaghetti_squash", "patisson"), "squash"),
    **dict.fromkeys(("sweet_corn",), "corn"),
    **dict.fromkeys(("asparagus",), "asparagus"),
    **dict.fromkeys(("onion", "shallot", "spring_onion", "welsh_onion", "leek", "garlic", "elephant_garlic"), "allium"),
    **dict.fromkeys(("florence_fennel", "celery", "celeriac", "jerusalem_artichoke", "yacon", "salsify", "scorzonera",
                     "chinese_artichoke", "radish", "winter_radish", "daikon", "turnip", "swede", "beetroot", "kohlrabi"), "root"),
    **dict.fromkeys(("stinging_nettle", "watercress", "garden_cress", "sorrel", "nz_spinach", "purslane", "winter_purslane",
                     "claytonia_red", "ice_plant", "orache", "samphire"), "leafy"),
    **dict.fromkeys(("rhubarb",), "fruit"),
}  # fmt: skip
_FAMILY_KIND = {
    "Solanaceae": "fruiting", "Cucurbitaceae": "fruiting", "Brassicaceae": "brassica", "Asteraceae": "leafy",
    "Amaranthaceae": "leafy", "Polygonaceae": "leafy", "Montiaceae": "leafy", "Aizoaceae": "leafy", "Caprifoliaceae": "leafy",
    "Apiaceae": "root", "Fabaceae": "legume", "Amaryllidaceae": "allium", "Malvaceae": "fruiting", "Poaceae": "corn",
}  # fmt: skip
# Herbs worth cooking with (the rest of the herb garden is for tea, bees or medicine).
CULINARY_HERBS = frozenset((
    "basil", "greek_basil", "lemon_basil", "purple_basil", "thai_basil", "holy_basil", "parsley", "chives", "garlic_chives",
    "wild_garlic", "dill", "coriander", "thyme", "lemon_thyme", "rosemary", "sage", "oregano", "marjoram", "peppermint",
    "spearmint", "apple_mint", "tarragon", "chervil", "chervil_winter", "lovage", "bay_laurel", "summer_savory",
    "winter_savory", "leaf_celery", "shiso_green", "perilla", "lemongrass", "lemon_balm", "nasturtium", "salad_burnet",
    "vietnamese_coriander", "horseradish",
))  # fmt: skip
_NOT_FOOD = frozenset(("chili_pepper",))  # spice: used, but never as a main vegetable
# Eaten raw: only in salads (and on the side), never cooked in a soup or a wok.
RAW_ONLY = frozenset((
    "lettuce", "cos_lettuce", "iceberg_lettuce", "loose_leaf_lettuce", "lambs_lettuce", "rocket", "purslane", "ice_plant",
    "claytonia_red", "winter_purslane", "garden_cress", "watercress", "watercress_land", "cucumber", "gherkin", "cucamelon",
    "radish", "endive", "radicchio", "salad_burnet",
))  # fmt: skip

MAX_INGREDIENTS = 40  # what a recipe of the cook's own may hold
MAX_STEPS = 30
# Never eaten raw or half-cooked: out of every dish that does not cook its produce (elderberries are
# poisonous raw; beans and chickpeas carry lectins).
COOK_FIRST = frozenset((
    "elderberry", "bush_bean", "pole_bean", "runner_bean", "borlotti_bean", "broad_bean", "field_beans", "edamame",
    "chickpea", "marrowfat_pea",
))  # fmt: skip

GRAMS_PER_PERSON = {
    "leafy": 90, "brassica": 150, "root": 150, "allium": 40, "fruiting": 150, "squash": 200, "legume": 110,
    "potato": 250, "corn": 120, "asparagus": 150, "herb": 5, "fruit": 130,
}  # fmt: skip
# Colours for the dish picture and the PDF (by kind; the panel uses the crop's own glyph colour).
KIND_COLOR = {
    "leafy": "#5a9a3c", "brassica": "#4f7f3a", "root": "#ef8a1e", "allium": "#d9c7a0", "fruiting": "#d9412b",
    "squash": "#e9922b", "legume": "#7fae4a", "potato": "#c9a46a", "corn": "#f2c230", "asparagus": "#93b35a",
    "herb": "#3f8a3a", "fruit": "#c8325a",
}  # fmt: skip


def produce_kind(plant: Plant | None) -> str | None:
    """What a crop is in the kitchen (None: not something to cook with)."""
    if plant is None or plant.id in _NOT_FOOD:
        return None
    if plant.id in _ID_KIND:
        return _ID_KIND[plant.id]
    if plant.category is PlantCategory.FLOWER:
        return None
    if plant.category is PlantCategory.HERB:
        return "herb" if plant.id in CULINARY_HERBS else None
    if plant.category is PlantCategory.FRUIT:
        return "fruit"
    return _FAMILY_KIND.get(plant.family or "", "leafy")


# --------------------------------------------------------------------------- #
# The rest of the kitchen: sides, meat & fish, what is in the fridge
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class Item:
    names: tuple[str, str, str]  # en, nl, fr
    qty: float  # per person (or per dish for "dish" units)
    unit: str  # g | ml | pc | clove | slice | tbsp | cube | can
    group: str  # side | meat | fish | veg_protein | dairy | pantry | basic
    per_dish: bool = False
    fridge: bool = True  # offered as 'use this up from the fridge'

    def name(self, lang: str) -> str:
        return self.names[{"en": 0, "nl": 1, "fr": 2}.get(lang, 0)]


SIDES: dict[str, Item] = {
    "pasta": Item(("pasta", "pasta", "pâtes"), 90, "g", "side"),
    "rice": Item(("rice", "rijst", "riz"), 75, "g", "side"),
    "bulgur": Item(("bulgur", "bulgur", "boulgour"), 70, "g", "side"),
    "couscous": Item(("couscous", "couscous", "couscous"), 70, "g", "side"),
    "pearl_couscous": Item(("pearl couscous", "parelcouscous", "couscous perlé"), 75, "g", "side"),
    "gnocchi": Item(("gnocchi", "gnocchi", "gnocchis"), 200, "g", "side"),
    "potatoes": Item(("potatoes", "aardappelen", "pommes de terre"), 250, "g", "side"),
    "fries": Item(("fries", "frietjes", "frites"), 200, "g", "side"),
    "bread": Item(("crusty bread", "stokbrood", "pain croustillant"), 2, "slice", "side"),
    "noodles": Item(("noodles", "noedels", "nouilles"), 80, "g", "side"),
}
PROTEINS: dict[str, Item] = {
    "chicken": Item(("chicken breast", "kipfilet", "blanc de poulet"), 150, "g", "meat"),
    "chicken_mince": Item(("chicken mince", "kippengehakt", "haché de poulet"), 125, "g", "meat"),
    "beef": Item(("beef (steak strips)", "rundvlees (reepjes)", "bœuf (lanières)"), 150, "g", "meat"),
    "steak": Item(("steak", "steak", "steak"), 180, "g", "meat"),
    "stew_beef": Item(("stewing beef", "stoofvlees", "bœuf à braiser"), 175, "g", "meat"),
    "pork": Item(("pork (strips)", "varkensvlees (reepjes)", "porc (lanières)"), 150, "g", "meat"),
    "pork_tenderloin": Item(("pork tenderloin", "varkenshaasje", "filet mignon de porc"), 150, "g", "meat"),
    "mince": Item(("minced meat", "gehakt", "haché"), 125, "g", "meat"),
    "burger": Item(("burger", "hamburger", "hamburger"), 1, "pc", "meat"),
    "sweetbread": Item(("sweetbreads", "zwezerik", "ris de veau"), 120, "g", "meat"),
    "sausage": Item(("sausage", "worst", "saucisse"), 1, "pc", "meat"),
    "bacon": Item(("bacon cubes", "spekblokjes", "lardons"), 50, "g", "meat"),
    "ham": Item(("ham", "ham", "jambon"), 50, "g", "meat"),
    "salmon": Item(("salmon fillet", "zalmfilet", "filet de saumon"), 125, "g", "fish"),
    "white_fish": Item(("white fish fillet", "witvisfilet", "filet de poisson blanc"), 150, "g", "fish"),
    "shrimp": Item(("prawns", "scampi", "scampis"), 100, "g", "fish"),
    "tofu": Item(("tofu", "tofu", "tofu"), 125, "g", "veg_protein"),
    "chickpeas": Item(("chickpeas (tin)", "kikkererwten (blik)", "pois chiches (boîte)"), 120, "g", "veg_protein"),
    "lentils": Item(("lentils", "linzen", "lentilles"), 60, "g", "veg_protein"),
    "egg": Item(("eggs", "eieren", "œufs"), 2, "pc", "veg_protein"),
    "halloumi": Item(("halloumi", "halloumi", "halloumi"), 70, "g", "veg_protein"),
    "goat_cheese": Item(("goat's cheese", "geitenkaas", "fromage de chèvre"), 50, "g", "veg_protein"),
}
PANTRY: dict[str, Item] = {
    "butter": Item(("butter", "boter", "beurre"), 10, "g", "dairy"),
    "cream": Item(("cream", "room", "crème"), 40, "ml", "dairy"),
    "milk": Item(("milk", "melk", "lait"), 100, "ml", "dairy"),
    "eggs": Item(("eggs", "eieren", "œufs"), 2, "pc", "dairy"),
    "parmesan": Item(("parmesan", "parmezaan", "parmesan"), 15, "g", "dairy"),
    "feta": Item(("feta", "feta", "feta"), 40, "g", "dairy"),
    "mozzarella": Item(("mozzarella", "mozzarella", "mozzarella"), 60, "g", "dairy"),
    "grated_cheese": Item(("grated cheese", "geraspte kaas", "fromage râpé"), 30, "g", "dairy"),
    "yoghurt": Item(("yoghurt", "yoghurt", "yaourt"), 50, "ml", "dairy"),
    "lemon": Item(("lemon", "citroen", "citron"), 0.5, "pc", "pantry", per_dish=True),
    "garlic": Item(("garlic", "look", "ail"), 2, "clove", "pantry", per_dish=True),
    "onion": Item(("onion", "ui", "oignon"), 1, "pc", "pantry", per_dish=True),
    "stock": Item(("stock cube", "bouillonblokje", "cube de bouillon"), 1, "cube", "pantry", per_dish=True),
    "white_wine": Item(("white wine", "witte wijn", "vin blanc"), 100, "ml", "pantry", per_dish=True),
    "tomato_paste": Item(("tomato paste", "tomatenpuree", "concentré de tomates"), 1, "tbsp", "pantry", per_dish=True),
    "coconut_milk": Item(("coconut milk", "kokosmelk", "lait de coco"), 1, "can", "pantry", per_dish=True),
    "curry_paste": Item(("curry paste", "currypasta", "pâte de curry"), 2, "tbsp", "pantry", per_dish=True),
    "soy_sauce": Item(("soy sauce", "sojasaus", "sauce soja"), 2, "tbsp", "pantry", per_dish=True),
    "ginger": Item(("fresh ginger", "verse gember", "gingembre frais"), 1, "pc", "pantry", per_dish=True),
    "honey": Item(("honey", "honing", "miel"), 1, "tbsp", "pantry", per_dish=True),
    "mustard": Item(("mustard", "mosterd", "moutarde"), 1, "tbsp", "pantry", per_dish=True),
    "nuts": Item(
        ("nuts (walnuts, pine nuts)", "noten (walnoten, pijnboompitten)", "noix (noix, pignons)"), 15, "g", "pantry"
    ),
    "flour": Item(("flour", "bloem", "farine"), 2, "tbsp", "pantry", per_dish=True),
    "breadcrumbs": Item(("breadcrumbs", "paneermeel", "chapelure"), 3, "tbsp", "pantry", per_dish=True),
    "puff_pastry": Item(("puff pastry", "bladerdeeg", "pâte feuilletée"), 1, "pc", "pantry", per_dish=True),
    "sugar": Item(("sugar", "suiker", "sucre"), 25, "g", "pantry"),
    "oats": Item(("rolled oats", "havervlokken", "flocons d'avoine"), 25, "g", "pantry"),
    "vinegar": Item(("vinegar", "azijn", "vinaigre"), 1, "tbsp", "pantry", per_dish=True),
    # for the dishes of ``cooking_dishes`` (store-cupboard items, not something to use up from the fridge)
    "ricotta": Item(("ricotta", "ricotta", "ricotta"), 60, "g", "dairy", fridge=False),
    "tahini": Item(("tahini", "tahin", "tahini"), 2, "tbsp", "pantry", per_dish=True, fridge=False),
    "olives": Item(("olives", "olijven", "olives"), 40, "g", "pantry", per_dish=True, fridge=False),
    "capers": Item(("capers", "kappertjes", "câpres"), 1, "tbsp", "pantry", per_dish=True, fridge=False),
    "raisins": Item(("raisins", "rozijnen", "raisins secs"), 40, "g", "pantry", per_dish=True, fridge=False),
    "baking_powder": Item(
        ("baking powder", "bakpoeder", "levure chimique"), 1, "tbsp", "pantry", per_dish=True, fridge=False
    ),
    "cinnamon": Item(("cinnamon", "kaneel", "cannelle"), 1, "tbsp", "pantry", per_dish=True, fridge=False),
    "cumin": Item(("ground cumin", "komijnpoeder", "cumin moulu"), 1, "tbsp", "pantry", per_dish=True, fridge=False),
    "canned_tomatoes": Item(
        ("tinned tomatoes", "tomaten uit blik", "tomates en boîte"), 1, "can", "pantry", per_dish=True, fridge=False
    ),
    "gelatine": Item(
        ("gelatine sheets", "gelatineblaadjes", "feuilles de gélatine"), 3, "pc", "pantry", per_dish=True, fridge=False
    ),
    "jam_sugar": Item(("jam sugar", "geleisuiker", "sucre gélifiant"), 400, "g", "pantry", per_dish=True, fridge=False),
    "soup_pasta": Item(("small soup pasta", "soeppasta", "petites pâtes à potage"), 20, "g", "pantry", fridge=False),
}
# Always in the house: never on a shopping list.
BASICS = {
    "salt": Item(("salt", "zout", "sel"), 0, "", "basic"),
    "pepper": Item(("pepper", "peper", "poivre"), 0, "", "basic"),
    "oil": Item(("olive oil", "olijfolie", "huile d'olive"), 0, "", "basic"),
}


# --------------------------------------------------------------------------- #
# Techniques
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class Technique:
    id: str
    kinds: tuple[str, ...]  # garden produce it suits, best first
    sides: tuple[str, ...]  # sides that belong in the dish (others are served next to it)
    proteins: tuple[str, ...]  # proteins that fit
    staples: tuple[str, ...] = ()  # pantry items the dish needs
    minutes: int = 30
    min_garden: int = 1
    max_garden: int = 3
    sweet: bool = False
    tags: tuple[str, ...] = ()
    # --- for the dishes of ``cooking_dishes`` ---
    plants: tuple[str, ...] = ()  # only these plants (empty: any plant of the kinds)
    course: str = ""  # soup | starter | main | dessert | preserve ("": worked out by ``course_of``)
    strict: bool = False  # only the proteins that fit, never another one
    no_side: bool = False  # no side dish at all
    must_side: bool = False  # the dish needs one of its sides (the first when the cook picked another)
    raw: bool = False  # the produce may be eaten raw (lettuce, cucumber ...)
    hearty: bool = False  # a starter that becomes a main course with meat or fish
    herbs_in_pool: bool = False  # garden herbs are ingredients of the dish
    needs_herb: bool = False  # ... and it takes at least one
    herb_grams: int = 0  # grams of herbs per person (0: the usual pinch)
    batch: float = 1.0  # preserving: how many times the usual amount
    side_in_method: bool = False  # the method itself cooks the side (risotto rice, stoemp potatoes)
    needs_main: bool = False  # at least one vegetable or fruit besides the herbs
    scale: tuple[tuple[str, float], ...] = ()  # pantry item -> how many times its usual amount in this dish


TECHNIQUES: tuple[Technique, ...] = (
    Technique("soup", ("root", "squash", "leafy", "brassica", "legume", "potato", "fruiting", "allium", "asparagus", "corn"),
              ("bread",), ("bacon", "chicken", "mince", "sausage", "chickpeas", "shrimp", "lentils"), ("onion", "stock", "cream"), 35,
              tags=("warm",)),
    Technique("roast", ("root", "squash", "fruiting", "brassica", "potato", "allium", "corn", "asparagus"),
              ("couscous", "pearl_couscous", "bulgur", "potatoes", "bread"),
              ("chicken", "pork_tenderloin", "sausage", "chicken_mince", "salmon", "halloumi", "chickpeas", "goat_cheese"),
              ("garlic",), 45, 2, 4, tags=("oven",)),
    Technique("stir_fry", ("brassica", "legume", "leafy", "allium", "fruiting", "corn", "asparagus", "root"),
              ("rice", "noodles"), ("chicken", "beef", "pork", "shrimp", "tofu", "chicken_mince"),
              ("garlic", "ginger", "soy_sauce"), 20, 2, 4, tags=("quick",)),
    Technique("pasta", ("fruiting", "leafy", "brassica", "legume", "allium", "squash", "asparagus", "herb"),
              ("pasta", "gnocchi"), ("mince", "bacon", "chicken", "shrimp", "salmon", "sausage", "ham"),
              ("garlic", "parmesan"), 25, 1, 3, tags=("quick",), must_side=True),
    Technique("risotto", ("squash", "leafy", "asparagus", "legume", "root", "brassica", "fruiting"),
              ("rice",), ("chicken", "bacon", "shrimp", "sweetbread", "salmon", "sausage"),
              ("onion", "stock", "white_wine", "parmesan", "butter"), 35, 1, 2, must_side=True, side_in_method=True),
    Technique("salad", ("leafy", "fruiting", "root", "legume", "fruit", "corn", "asparagus", "brassica", "herb"),
              ("bulgur", "couscous", "pearl_couscous", "potatoes", "bread", "pasta"),
              ("chicken", "steak", "salmon", "egg", "goat_cheese", "halloumi", "shrimp", "chickpeas", "ham"),
              ("lemon", "mustard"), 20, 2, 4, tags=("fresh", "quick"), raw=True),
    Technique("gratin", ("potato", "brassica", "root", "squash", "leafy", "fruiting"),
              ("potatoes", "pasta"), ("mince", "ham", "chicken", "bacon", "sausage"),
              ("cream", "grated_cheese", "garlic"), 50, 1, 3, tags=("oven",)),
    Technique("stew", ("root", "squash", "legume", "fruiting", "leafy", "brassica", "potato"),
              ("rice", "couscous", "bread", "potatoes"), ("chicken", "stew_beef", "pork", "chickpeas", "lentils"),
              ("onion", "garlic", "curry_paste", "coconut_milk"), 45, 2, 4, tags=("warm",)),
    Technique("frittata", ("leafy", "allium", "fruiting", "asparagus", "potato", "legume", "herb", "brassica"),
              ("bread", "potatoes"), ("bacon", "ham", "salmon", "goat_cheese"), ("eggs", "grated_cheese"), 25, 1, 3),
    Technique("stoemp", ("leafy", "root", "brassica", "allium"), ("potatoes",),
              ("sausage", "mince", "pork_tenderloin", "burger", "bacon"), ("butter", "milk"), 35, 1, 2, tags=("warm",),
              must_side=True, side_in_method=True),
    Technique("stuffed", ("fruiting", "squash"), ("rice", "bulgur", "couscous"), ("mince", "chicken_mince", "lentils", "feta"),
              ("onion", "garlic", "grated_cheese"), 50, 1, 2, tags=("oven",), must_side=True),
    Technique("plate", ("legume", "brassica", "leafy", "root", "asparagus", "fruiting", "squash", "corn"),
              ("fries", "potatoes"), ("steak", "burger", "sweetbread", "pork_tenderloin", "chicken", "salmon", "sausage"),
              ("butter",), 30, 1, 2),
    Technique("pesto", ("herb", "leafy"), ("pasta", "gnocchi", "bread"), ("chicken", "shrimp"), ("garlic", "parmesan", "nuts"),
              15, 1, 2, tags=("quick",), strict=True, herbs_in_pool=True, needs_herb=True, herb_grams=25, must_side=True),
    Technique("dessert", ("fruit",), (), (), ("sugar", "butter", "flour", "oats"), 40, 1, 2, sweet=True, tags=("sweet",)),
    Technique("cold_soup", ("fruiting", "herb"), ("bread",), ("shrimp", "ham", "egg"),
              ("garlic", "vinegar"), 45, 2, 4, tags=("fresh",), raw=True),  # 15 minutes work + 30 chilling
    Technique("crostini", ("fruiting", "legume", "leafy", "squash", "asparagus", "allium", "herb"), ("bread",),
              ("ham", "goat_cheese", "salmon", "shrimp"), ("garlic",), 15, 1, 2, tags=("quick",), raw=True, must_side=True),
    Technique("compote", ("fruit",), (), (), ("sugar", "lemon"), 20, 1, 2, sweet=True, tags=("sweet", "quick")),
    *(Technique(**spec) for spec in _d.SPECS),
)  # fmt: skip
_RAW_OK = frozenset(t.id for t in TECHNIQUES if t.raw)
_UNCOOKED = _RAW_OK | {"sorbet", "cups", "panna_cotta"}  # dishes that do not cook their produce

# The chapters of the cookbook: every recipe belongs to one course.
COURSES = ("soup", "starter", "main", "dessert", "preserve")
MEAL_COURSES = COURSES[:4]  # what a meal is made of (preserving is for the surplus)
_COURSE_NAME = {
    "en": {"soup": "Soups", "starter": "Starters", "main": "Main courses", "dessert": "Desserts",
           "preserve": "Preserving & pickles"},
    "nl": {"soup": "Soepen", "starter": "Voorgerechten", "main": "Hoofdgerechten", "dessert": "Desserten",
           "preserve": "Bewaren & inmaken"},
    "fr": {"soup": "Soupes", "starter": "Entrées", "main": "Plats", "dessert": "Desserts", "preserve": "Conserves"},
}  # fmt: skip


def course_of(technique: str, protein: str = "", side: str = "") -> str:
    """The chapter a dish goes in: a salad without meat or fish, crostini or pesto on bread start
    the meal; with meat, fish or a filling side they are the meal itself."""
    tech = TECHNIQUE.get(technique)
    if tech is not None and tech.course:
        return "main" if tech.course == "starter" and tech.hearty and protein else tech.course
    if technique in ("soup", "cold_soup"):
        return "soup"
    if technique in ("dessert", "compote"):
        return "dessert"
    if (
        technique == "crostini"
        or (technique == "salad" and not protein)
        or (technique == "pesto" and side in ("", "bread"))
    ):
        return "starter"
    return "main"


def course_name(course: str, lang: str | None = "en") -> str:
    return _COURSE_NAME[_lang(lang)].get(course, course)


TECHNIQUE = {t.id: t for t in TECHNIQUES}

# --------------------------------------------------------------------------- #
# Texts
# --------------------------------------------------------------------------- #
_PREP: dict[str, dict[str, str]] = {
    "en": {"leafy": "{n} roughly chopped", "brassica": "{n} in florets or strips", "root": "{n} peeled and diced",
           "allium": "{n} finely chopped", "fruiting": "{n} in chunks", "squash": "{n} in cubes", "legume": "{n} podded or cut",
           "potato": "{n} in cubes", "corn": "{n} cut from the cob", "asparagus": "{n} peeled, woody ends off",
           "herb": "{n} chopped", "fruit": "{n} washed and cut"},
    "nl": {"leafy": "{n} grof gesneden", "brassica": "{n} in roosjes of repen", "root": "{n} geschild in blokjes",
           "allium": "{n} fijngesneden", "fruiting": "{n} in stukken", "squash": "{n} in blokjes", "legume": "{n} gedopt of in stukjes",
           "potato": "{n} in blokjes", "corn": "{n} van de kolf gesneden", "asparagus": "{n} geschild, houtige voetjes eraf",
           "herb": "{n} fijngehakt", "fruit": "{n} gewassen en in stukken"},
    "fr": {"leafy": "{n} grossièrement haché", "brassica": "{n} en fleurettes ou lanières", "root": "{n} pelé en dés",
           "allium": "{n} finement émincé", "fruiting": "{n} en morceaux", "squash": "{n} en cubes", "legume": "{n} écossé ou coupé",
           "potato": "{n} en cubes", "corn": "{n} égrené", "asparagus": "{n} pelé, bouts durs ôtés",
           "herb": "{n} ciselé", "fruit": "{n} lavé et coupé"},
}  # fmt: skip

_TITLE: dict[str, dict[str, str]] = {
    "en": {"soup": "{a} soup", "roast": "Roasted {a}",
           "stir_fry": "Stir-fried {a}", "pasta": "Pasta with {a}",
           "risotto": "{a} risotto", "salad": "Salad of {a}",
           "gratin": "{a} gratin", "stew": "{a} stew",
           "frittata": "Frittata with {a}", "stoemp": "Stoemp with {a}",
           "stuffed": "Stuffed {a}", "plate": "Plate with {a}",
           "pesto": "{a} pesto", "dessert": "{a} crumble",
           "cold_soup": "Chilled {a} soup", "crostini": "Crostini with {a}", "compote": "Warm {a} compote"},
    "nl": {"soup": "Soep van {a}", "roast": "Geroosterde {a}",
           "stir_fry": "Wok met {a}", "pasta": "Pasta met {a}",
           "risotto": "Risotto met {a}", "salad": "Salade met {a}",
           "gratin": "Gratin van {a}", "stew": "Stoofpotje van {a}",
           "frittata": "Frittata met {a}", "stoemp": "Stoemp met {a}",
           "stuffed": "Gevulde {a}", "plate": "Bord met {a}",
           "pesto": "Pesto van {a}", "dessert": "Crumble van {a}",
           "cold_soup": "Koude soep van {a}", "crostini": "Crostini met {a}", "compote": "Lauwe compote van {a}"},
    "fr": {"soup": "Soupe de {a}", "roast": "{a} rôtis au four",
           "stir_fry": "Wok de {a}", "pasta": "Pâtes aux {a}",
           "risotto": "Risotto aux {a}", "salad": "Salade de {a}",
           "gratin": "Gratin de {a}", "stew": "Mijoté de {a}",
           "frittata": "Frittata aux {a}", "stoemp": "Stoemp aux {a}",
           "stuffed": "{a} farcis", "plate": "Assiette aux {a}",
           "pesto": "Pesto de {a}", "dessert": "Crumble de {a}",
           "cold_soup": "Soupe froide de {a}", "crostini": "Crostini aux {a}", "compote": "Compote tiède de {a}"},
}  # fmt: skip

_WITH = {"en": "with {p}", "nl": "met {p}", "fr": "avec {p}"}
_AND = {"en": "and", "nl": "en", "fr": "et"}

# The steps of each technique.  {veg}: the garden produce, {prep}: how to cut it,
# {herbs}: garden herbs (or a fallback), {side}: the side in the dish.
_STEPS: dict[str, dict[str, list[str]]] = {
    "en": {
        "soup": ["Prepare the vegetables: {prep}.", "Soften the onion in a little oil in a large pan, add the vegetables and stir for 3 minutes.",
                 "Cover with water and the stock cube, bring to the boil and simmer for 20 minutes until tender.",
                 "Blend smooth (or leave chunky), stir in the cream and season with salt and pepper."],
        "roast": ["Heat the oven to 210 °C. Prepare the vegetables: {prep}.",
                  "Toss them on a baking tray with olive oil, the crushed garlic, salt and pepper.",
                  "Roast for 30-35 minutes, turning halfway, until golden at the edges."],
        "stir_fry": ["Prepare the vegetables: {prep}. Chop garlic and ginger finely.",
                     "Heat a wok or large pan very hot with a little oil; stir-fry garlic and ginger for 30 seconds.",
                     "Add the firmest vegetables first, the tender ones after 2 minutes; keep everything crisp.",
                     "Season with soy sauce and a splash of water, toss and serve straight away."],
        "pasta": ["Prepare the vegetables: {prep}.", "Gently fry the garlic in olive oil, add the vegetables and cook 6-8 minutes until just tender.",
                  "Toss with the drained {side} and a ladle of cooking water until glossy.", "Serve with grated parmesan and black pepper."],
        "risotto": ["Prepare the vegetables: {prep}. Keep the stock hot in a pan.",
                    "Soften the onion in butter, add the rice and stir for 2 minutes; deglaze with the wine.",
                    "Add hot stock ladle by ladle, stirring, for 18 minutes; add the vegetables halfway.",
                    "Off the heat stir in a knob of butter and the parmesan; rest 2 minutes, covered."],
        "salad": ["Prepare the vegetables: {prep}.", "Whisk a dressing of 3 tbsp olive oil, the lemon juice, a teaspoon of mustard, salt and pepper.",
                  "Toss everything just before serving."],
        "gratin": ["Heat the oven to 190 °C. Prepare the vegetables: {prep}.",
                   "Blanch the firm vegetables for 5 minutes in salted water and drain well.",
                   "Layer them in a buttered dish, pour over the cream with the crushed garlic, salt and pepper.",
                   "Cover with grated cheese and bake for 30 minutes until golden and bubbling."],
        "stew": ["Prepare the vegetables: {prep}.", "Soften onion and garlic in oil, stir in the curry paste for a minute.",
                 "Add the vegetables, the coconut milk and a glass of water; simmer gently for 25 minutes.",
                 "Season with salt and a squeeze of lemon if you have one."],
        "frittata": ["Prepare the vegetables: {prep}.", "Soften them in a little oil in an ovenproof pan for 5 minutes.",
                     "Beat the eggs with the cheese, salt and pepper and pour over the vegetables.",
                     "Cook on a low heat for 8 minutes, then 5 minutes under the grill until set and golden."],
        "stoemp": ["Prepare the vegetables: {prep}.", "Boil the potatoes in salted water for 20 minutes; add the vegetables for the last 6-8 minutes.",
                   "Drain and mash coarsely with butter and a splash of warm milk; season with salt, pepper and a little nutmeg."],
        "stuffed": ["Heat the oven to 190 °C. Hollow out the vegetables: {prep}; keep the flesh.",
                    "Fry the onion, garlic and chopped flesh, mix with the cooked {side} and season well.",
                    "Fill the vegetables, top with grated cheese and bake for 30 minutes."],
        "plate": ["Prepare the vegetables: {prep}.", "Steam or boil them briefly until just tender, then toss in butter with salt and pepper.",
                  "Plate everything together while hot."],
        "pesto": ["Blend the herbs and greens ({prep}) with garlic, nuts, parmesan and olive oil to a coarse paste.",
                  "Season with salt, pepper and lemon; loosen with a little cooking water.",
                  "Toss with the hot {side} or spread on toasted bread."],
        "dessert": ["Heat the oven to 180 °C. Prepare the fruit: {prep}; put it in a buttered dish with a spoon of sugar.",
                    "Rub flour, oats, sugar and cold butter to coarse crumbs and scatter over the fruit.",
                    "Bake for 30-35 minutes until golden and bubbling."],
        "cold_soup": ["Prepare the vegetables: {prep}.", "Blend them with a crushed garlic clove, a splash of vinegar, 4 tbsp olive oil and a little cold water until smooth; season well.", "Chill for at least 30 minutes and serve very cold with a drizzle of olive oil."],
        "crostini": ["Prepare the vegetables: {prep}; fry the firm ones briefly in olive oil, keep tender ones raw.", "Toast slices of bread, rub them with a cut garlic clove and drizzle with olive oil.", "Pile the vegetables on the warm toasts, season with salt and pepper and serve at once."],
        "compote": ["Prepare the fruit: {prep}.", "Simmer it gently with 2 tbsp sugar, a squeeze of lemon and a splash of water for 10-15 minutes until soft.", "Serve lukewarm."],
    },
    "nl": {
        "soup": ["Maak de groenten klaar: {prep}.", "Stoof de ui in wat olie in een grote pot, voeg de groenten toe en roer 3 minuten.",
                 "Giet er water op met het bouillonblokje, breng aan de kook en laat 20 minuten zacht koken tot alles gaar is.",
                 "Mix glad (of laat wat stukjes), roer de room erdoor en breng op smaak met peper en zout."],
        "roast": ["Verwarm de oven voor op 210 °C. Maak de groenten klaar: {prep}.",
                  "Meng ze op een bakplaat met olijfolie, de geplette look, peper en zout.",
                  "Rooster 30-35 minuten, halverwege omscheppen, tot de randjes goudbruin zijn."],
        "stir_fry": ["Maak de groenten klaar: {prep}. Hak look en gember fijn.",
                     "Verhit een wok of grote pan heel heet met wat olie; roerbak look en gember 30 seconden.",
                     "Eerst de stevigste groenten, na 2 minuten de zachte; alles moet knapperig blijven.",
                     "Blus met sojasaus en een scheutje water, schep om en dien meteen op."],
        "pasta": ["Maak de groenten klaar: {prep}.", "Fruit de look zachtjes in olijfolie, voeg de groenten toe en bak 6-8 minuten tot ze net gaar zijn.",
                  "Meng met de uitgelekte {side} en een soeplepel kookvocht tot alles glanst.", "Dien op met geraspte parmezaan en versgemalen peper."],
        "risotto": ["Maak de groenten klaar: {prep}. Houd de bouillon warm in een pannetje.",
                    "Stoof de ui in boter, voeg de rijst toe en roer 2 minuten; blus met de wijn.",
                    "Voeg al roerend lepel per lepel warme bouillon toe, 18 minuten lang; de groenten halverwege erbij.",
                    "Van het vuur een klontje boter en de parmezaan erdoor; laat 2 minuten afgedekt rusten."],
        "salad": ["Maak de groenten klaar: {prep}.", "Klop een dressing van 3 el olijfolie, het citroensap, een koffielepel mosterd, peper en zout.",
                  "Meng alles vlak voor het opdienen."],
        "gratin": ["Verwarm de oven voor op 190 °C. Maak de groenten klaar: {prep}.",
                   "Blancheer de stevige groenten 5 minuten in gezouten water en laat goed uitlekken.",
                   "Leg ze in laagjes in een beboterde ovenschaal, giet de room met geplette look, peper en zout erover.",
                   "Bestrooi met geraspte kaas en bak 30 minuten tot het goudbruin borrelt."],
        "stew": ["Maak de groenten klaar: {prep}.", "Stoof ui en look in olie, roer de currypasta er een minuut door.",
                 "Voeg de groenten, de kokosmelk en een glas water toe; laat 25 minuten zacht pruttelen.",
                 "Breng op smaak met zout en een scheutje citroensap."],
        "frittata": ["Maak de groenten klaar: {prep}.", "Stoof ze 5 minuten in wat olie in een ovenvaste pan.",
                     "Klop de eieren los met de kaas, peper en zout en giet over de groenten.",
                     "Laat 8 minuten op laag vuur stollen en zet dan 5 minuten onder de grill tot de bovenkant goudbruin is."],
        "stoemp": ["Maak de groenten klaar: {prep}.", "Kook de aardappelen 20 minuten in gezouten water; de groenten de laatste 6-8 minuten erbij.",
                   "Giet af en stamp grof met boter en een scheut warme melk; peper, zout en een snuifje nootmuskaat."],
        "stuffed": ["Verwarm de oven voor op 190 °C. Hol de groenten uit: {prep}; bewaar het vruchtvlees.",
                    "Bak ui, look en het gehakte vruchtvlees, meng met de gekookte {side} en kruid goed.",
                    "Vul de groenten, bestrooi met geraspte kaas en bak 30 minuten in de oven."],
        "plate": ["Maak de groenten klaar: {prep}.", "Stoom of kook ze kort tot ze net gaar zijn en schep ze om in boter met peper en zout.",
                  "Schik alles warm op het bord."],
        "pesto": ["Mix de kruiden en het blad ({prep}) met look, noten, parmezaan en olijfolie tot een grove pasta.",
                  "Breng op smaak met peper, zout en citroen; maak wat losser met een scheutje kookvocht.",
                  "Meng met de warme {side} of smeer op geroosterd brood."],
        "dessert": ["Verwarm de oven voor op 180 °C. Maak het fruit klaar: {prep}; leg het in een beboterde schaal met een lepel suiker.",
                    "Wrijf bloem, havervlokken, suiker en koude boter tot grove kruimels en strooi over het fruit.",
                    "Bak 30-35 minuten tot het goudbruin borrelt."],
        "cold_soup": ["Maak de groenten klaar: {prep}.", "Mix ze glad met een geperst teentje look, een scheutje azijn, 4 el olijfolie en wat koud water; kruid goed.", "Laat minstens 30 minuten koelen en dien ijskoud op met een draadje olijfolie."],
        "crostini": ["Maak de groenten klaar: {prep}; bak de stevige kort in olijfolie, laat zachte rauw.", "Rooster sneetjes brood, wrijf ze in met een doorgesneden teentje look en besprenkel met olijfolie.", "Schep de groenten op de warme toastjes, kruid met peper en zout en dien meteen op."],
        "compote": ["Maak het fruit klaar: {prep}.", "Laat het met 2 el suiker, een scheutje citroensap en een bodem water 10-15 minuten zacht garen.", "Dien lauw op."],
    },
    "fr": {
        "soup": ["Préparez les légumes : {prep}.", "Faites revenir l'oignon dans un peu d'huile, ajoutez les légumes et remuez 3 minutes.",
                 "Couvrez d'eau avec le cube de bouillon, portez à ébullition et laissez mijoter 20 minutes.",
                 "Mixez (ou gardez des morceaux), ajoutez la crème, salez et poivrez."],
        "roast": ["Préchauffez le four à 210 °C. Préparez les légumes : {prep}.",
                  "Mélangez-les sur une plaque avec l'huile d'olive, l'ail écrasé, sel et poivre.",
                  "Rôtissez 30-35 minutes en remuant à mi-cuisson, jusqu'à ce que les bords dorent."],
        "stir_fry": ["Préparez les légumes : {prep}. Hachez finement l'ail et le gingembre.",
                     "Chauffez un wok très fort avec un peu d'huile ; faites sauter l'ail et le gingembre 30 secondes.",
                     "D'abord les légumes fermes, les tendres après 2 minutes ; tout doit rester croquant.",
                     "Déglacez à la sauce soja et un trait d'eau, mélangez et servez aussitôt."],
        "pasta": ["Préparez les légumes : {prep}.", "Faites revenir l'ail doucement dans l'huile d'olive, ajoutez les légumes et cuisez 6-8 minutes.",
                  "Mélangez avec les {side} égouttées et une louche d'eau de cuisson.", "Servez avec du parmesan râpé et du poivre."],
        "risotto": ["Préparez les légumes : {prep}. Gardez le bouillon chaud.",
                    "Faites suer l'oignon au beurre, ajoutez le riz et remuez 2 minutes ; déglacez au vin.",
                    "Ajoutez le bouillon louche par louche en remuant pendant 18 minutes ; les légumes à mi-cuisson.",
                    "Hors du feu, une noix de beurre et le parmesan ; laissez reposer 2 minutes couvert."],
        "salad": ["Préparez les légumes : {prep}.", "Fouettez une vinaigrette : 3 c. à s. d'huile d'olive, le jus de citron, une c. à c. de moutarde, sel, poivre.",
                  "Mélangez juste avant de servir."],
        "gratin": ["Préchauffez le four à 190 °C. Préparez les légumes : {prep}.",
                   "Blanchissez les légumes fermes 5 minutes à l'eau salée et égouttez bien.",
                   "Disposez-les dans un plat beurré, versez la crème avec l'ail écrasé, sel et poivre.",
                   "Parsemez de fromage râpé et enfournez 30 minutes jusqu'à ce que ce soit doré."],
        "stew": ["Préparez les légumes : {prep}.", "Faites revenir oignon et ail, ajoutez la pâte de curry une minute.",
                 "Ajoutez les légumes, le lait de coco et un verre d'eau ; mijotez 25 minutes.",
                 "Salez et ajoutez un trait de citron."],
        "frittata": ["Préparez les légumes : {prep}.", "Faites-les revenir 5 minutes dans une poêle allant au four.",
                     "Battez les œufs avec le fromage, sel et poivre et versez sur les légumes.",
                     "Laissez prendre 8 minutes à feu doux, puis 5 minutes sous le gril."],
        "stoemp": ["Préparez les légumes : {prep}.", "Cuisez les pommes de terre 20 minutes à l'eau salée ; les légumes les 6-8 dernières minutes.",
                   "Égouttez et écrasez grossièrement avec du beurre et un peu de lait chaud ; sel, poivre, muscade."],
        "stuffed": ["Préchauffez le four à 190 °C. Évidez les légumes : {prep} ; gardez la chair.",
                    "Faites revenir oignon, ail et la chair hachée, mélangez avec le {side} cuit et assaisonnez.",
                    "Farcissez, parsemez de fromage râpé et enfournez 30 minutes."],
        "plate": ["Préparez les légumes : {prep}.", "Cuisez-les brièvement à la vapeur ou à l'eau, puis enrobez-les de beurre, sel et poivre.",
                  "Dressez le tout bien chaud."],
        "pesto": ["Mixez les herbes et les feuilles ({prep}) avec ail, noix, parmesan et huile d'olive.",
                  "Salez, poivrez, ajoutez du citron ; détendez avec un peu d'eau de cuisson.",
                  "Mélangez aux {side} chaudes ou tartinez sur du pain grillé."],
        "dessert": ["Préchauffez le four à 180 °C. Préparez les fruits : {prep} ; mettez-les dans un plat beurré avec une cuillerée de sucre.",
                    "Sablez farine, flocons d'avoine, sucre et beurre froid et parsemez sur les fruits.",
                    "Enfournez 30-35 minutes."],
        "cold_soup": ["Préparez les légumes : {prep}.", "Mixez-les avec une gousse d'ail écrasée, un trait de vinaigre, 4 c. à s. d'huile d'olive et un peu d'eau froide ; assaisonnez bien.", "Réfrigérez au moins 30 minutes et servez bien froid avec un filet d'huile d'olive."],
        "crostini": ["Préparez les légumes : {prep} ; faites revenir les fermes à l'huile d'olive, gardez les tendres crus.", "Faites griller des tranches de pain, frottez-les d'ail et arrosez d'huile d'olive.", "Garnissez les toasts chauds de légumes, salez, poivrez et servez aussitôt."],
        "compote": ["Préparez les fruits : {prep}.", "Faites-les mijoter doucement 10-15 minutes avec 2 c. à s. de sucre, un filet de citron et un peu d'eau.", "Servez tiède."],
    },
}  # fmt: skip

# How each protein is cooked, by where it goes in the dish.
_PROTEIN_STEP = {
    "en": {"meat": "Cook the {p} in a hot pan with a little oil until browned and cooked through; season with salt and pepper.",
           "stew_beef": "Brown the {p} on all sides first and let it simmer along for at least 1 hour (add the vegetables later).",
           "fish": "Cook the {p} gently in a little oil or butter for 3-4 minutes per side; season with salt and lemon.",
           "veg_protein": "Add the {p}: pan-fry tofu or halloumi until golden, warm chickpeas or lentils through the dish, boil eggs for 7 minutes.",
           "bacon": "Fry the {p} crisp first and use the fat for the vegetables.",
           "lentils": "Rinse the {p} and simmer them in plenty of unsalted water for 20-25 minutes until tender; drain and stir them into the dish."},
    "nl": {"meat": "Bak het {p} in een hete pan met wat olie bruin en gaar; kruid met peper en zout.",
           "stew_beef": "Schroei het {p} eerst rondom dicht en laat het minstens 1 uur mee sudderen (de groenten later toevoegen).",
           "fish": "Bak de {p} zachtjes 3-4 minuten per kant in wat olie of boter; kruid met zout en citroen.",
           "veg_protein": "Voeg de {p} toe: tofu of halloumi goudbruin bakken, kikkererwten of linzen meewarmen, eieren 7 minuten koken.",
           "bacon": "Bak eerst de {p} krokant en gebruik het vet voor de groenten.",
           "lentils": "Spoel de {p} en laat ze 20-25 minuten zachtjes koken in ruim ongezouten water tot ze gaar zijn; giet af en roer door het gerecht."},
    "fr": {"meat": "Faites dorer le {p} dans une poêle chaude avec un peu d'huile jusqu'à cuisson ; salez et poivrez.",
           "stew_beef": "Saisissez d'abord le {p} de tous côtés et laissez-le mijoter au moins 1 heure (ajoutez les légumes ensuite).",
           "fish": "Cuisez le {p} doucement 3-4 minutes par face dans un peu d'huile ou de beurre ; sel et citron.",
           "veg_protein": "Ajoutez le {p} : tofu ou halloumi dorés à la poêle, pois chiches ou lentilles réchauffés dans le plat, œufs cuits 7 minutes.",
           "bacon": "Faites d'abord croustiller les {p} et utilisez la graisse pour les légumes.",
           "lentils": "Rincez les {p} et cuisez-les 20 à 25 minutes à feu doux dans beaucoup d'eau non salée ; égouttez et incorporez-les au plat."},
}  # fmt: skip

_SIDE_STEP = {
    "en": {"pasta": "Cook the pasta al dente in plenty of salted water.", "rice": "Cook the rice as on the pack.",
           "bulgur": "Pour boiling water over the bulgur (1.5 times its volume), cover and leave 15 minutes.",
           "couscous": "Pour boiling stock over the couscous (same volume), cover for 5 minutes and fluff with a fork.",
           "pearl_couscous": "Cook the pearl couscous for 8 minutes in salted water and drain.",
           "gnocchi": "Cook the gnocchi until they float (2-3 minutes), or fry them golden in butter.",
           "potatoes": "Boil the potatoes in salted water for 20 minutes (or roast them in wedges).",
           "fries": "Bake or fry the fries until golden and crisp.", "bread": "Toast the bread or warm it in the oven.",
           "noodles": "Cook the noodles as on the pack and rinse briefly."},
    "nl": {"pasta": "Kook de pasta beetgaar in ruim gezouten water.", "rice": "Kook de rijst volgens de verpakking.",
           "bulgur": "Giet kokend water over de bulgur (1,5 keer het volume), dek af en laat 15 minuten wellen.",
           "couscous": "Giet kokende bouillon over de couscous (zelfde volume), laat 5 minuten afgedekt staan en maak los met een vork.",
           "pearl_couscous": "Kook de parelcouscous 8 minuten in gezouten water en giet af.",
           "gnocchi": "Kook de gnocchi tot ze bovendrijven (2-3 minuten), of bak ze goudbruin in boter.",
           "potatoes": "Kook de aardappelen 20 minuten in gezouten water (of rooster ze in partjes).",
           "fries": "Bak de frietjes goudbruin en krokant (oven of friteuse).", "bread": "Rooster het brood of warm het op in de oven.",
           "noodles": "Kook de noedels volgens de verpakking en spoel ze kort."},
    "fr": {"pasta": "Cuisez les pâtes al dente dans beaucoup d'eau salée.", "rice": "Cuisez le riz selon l'emballage.",
           "bulgur": "Versez de l'eau bouillante sur le boulgour (1,5 fois son volume), couvrez 15 minutes.",
           "couscous": "Versez du bouillon bouillant sur la semoule (même volume), couvrez 5 minutes et égrenez.",
           "pearl_couscous": "Cuisez le couscous perlé 8 minutes à l'eau salée et égouttez.",
           "gnocchi": "Cuisez les gnocchis jusqu'à ce qu'ils remontent (2-3 minutes), ou dorez-les au beurre.",
           "potatoes": "Cuisez les pommes de terre 20 minutes à l'eau salée (ou rôtissez-les en quartiers).",
           "fries": "Faites cuire les frites jusqu'à ce qu'elles soient dorées et croustillantes.",
           "bread": "Faites griller le pain ou réchauffez-le au four.", "noodles": "Cuisez les nouilles selon l'emballage et rincez."},
}  # fmt: skip
_SERVE_SIDE = {"en": "Serve with the {s}.", "nl": "Serveer met de {s}.", "fr": "Servez avec les {s}."}

# What the cook has in the fridge ("use this up") only goes into a dish it suits, in a way of its
# own (``cooking_extras``): items a dish does not list stay in the fridge for another one.
_CHEESES = frozenset(("parmesan", "feta", "mozzarella", "grated_cheese"))
_CREAMY = frozenset(("cream", "coconut_milk", "milk"))
# Garden herbs that belong in a cold sauce or butter (rosemary or sage do not)
_SAUCE_HERBS = ("dill", *_d.MINTS, "parsley", "chives", "coriander")
_LANG_IX = {"nl": 0, "en": 1, "fr": 2}
_LANG_IX_EN = {"en": 0, "nl": 1, "fr": 2}  # the order of the texts of ``cooking_dishes``
# A fridge item the dish's own garden produce already brings
_GARDEN_GIVES = {"onion": {"onion", "shallot", "leek"}, "garlic": {"garlic", "elephant_garlic"}}


def _seed(produce_ids: Sequence[str]) -> int:
    return int(hashlib.sha1(",".join(produce_ids).encode()).hexdigest()[:8], 16)


def _plan_extras(technique: str, items: Iterable[str], has_protein: bool, produce: Sequence[str]) -> dict[str, str]:
    """item -> preparation for the fridge items a dish takes.  The produce picks among an item's
    preparations (dishes vary); an item whose pick clashes tries its others.  At most one extra
    cheese (none on top of a cheese the recipe has, mixed in it may), one extra cream, one of each
    group (dressing, pasta sauce, crunchy topping ...), nothing the dish already uses, a pan sauce
    only with meat or fish, and ``MAX_PER_DISH`` in all."""
    tech = TECHNIQUE.get(technique)
    if tech is None:
        return {}
    wanted = set(items)
    seed = _seed(produce)
    out: dict[str, str] = {}
    groups: set[str] = set()
    for item, keys in _x.USES.get(technique, {}).items():
        if len(out) >= _x.MAX_PER_DISH:
            break
        if item not in wanted or item in tech.staples or _GARDEN_GIVES.get(item, {item}) & set(produce):
            continue  # the garden's own onion or garlic is in the dish already
        if item in _CHEESES and any(x in _CHEESES for x in out):
            continue
        # one cream per dish; a splash of milk in the recipe is no cream (stoemp still takes cream)
        if item in _CREAMY and any(x in _CREAMY for x in [*out, *(t for t in tech.staples if t != "milk")]):
            continue
        start = seed % len(keys)
        for key in [*keys[start:], *keys[:start]]:
            if key in _x.NEEDS_PROTEIN and not has_protein:
                continue
            if item in _CHEESES and key not in _x.INSIDE and any(t in _CHEESES for t in tech.staples):
                continue
            if _x.GROUP.get(key) in groups:
                continue
            out[item] = key
            if key in _x.GROUP:
                groups.add(_x.GROUP[key])
            break
    return out


def pan_meat(protein_id: str) -> bool:
    """Meat or fish leaves a pan to make a sauce in (tofu, eggs or chickpeas do not)."""
    item = PROTEINS.get(protein_id)
    return item is not None and item.group in ("meat", "fish")


def fitting_extras(
    technique: str, items: Iterable[str], has_protein: bool = True, produce: Sequence[str] = ()
) -> list[str]:
    """The fridge items that suit a dish, in the dish's own order (see ``_plan_extras``)."""
    return list(_plan_extras(technique, items, has_protein, produce))


def _extra_steps(technique: str, extras: Sequence[str], lang: str, herbs: Sequence[str] = (),
                 produce: Sequence[str] = (), has_protein: bool = True) -> tuple[list[str], list[str], list[str], list[str]]:  # fmt: skip
    """The steps for the fridge items: (after the second technique step, before the last – the
    timed oven or grill additions –, after the last).
    ``herbs``: fresh garden herbs for a sauce or butter (else the one the preparation suggests)."""
    plan = _plan_extras(technique, extras, has_protein, produce)
    ix = _LANG_IX[lang]
    mid: list[str] = []
    early: list[str] = []
    during: list[str] = []
    late: list[str] = []
    for item, key in plan.items():
        where, *texts = _x.PREP[key]
        default = _x.HERB.get(key, ("verse kruiden", "fresh herbs", "fines herbes"))[ix]
        h = _join(list(herbs)[:2], lang) if herbs and key not in _x.FIXED_HERB else default
        name = PANTRY[item].name(lang).split(" (")[0]  # "nuts (walnuts, pine nuts)" -> "nuts"
        {"early": early, "mid": mid, "during": during}.get(where, late).append(texts[ix].format(x=name, h=h))
    return early, mid, during, late


_HERBS = {"en": "Scatter over the {h} just before serving.", "nl": "Strooi vlak voor het opdienen de {h} erover.",
          "fr": "Parsemez de {h} juste avant de servir."}  # fmt: skip
_UNITS = {
    "en": {
        "g": "g",
        "ml": "ml",
        "pc": "",
        "clove": "cloves",
        "slice": "slices",
        "tbsp": "tbsp",
        "cube": "",
        "can": "tin",
    },
    "nl": {
        "g": "g",
        "ml": "ml",
        "pc": "",
        "clove": "teentjes",
        "slice": "sneden",
        "tbsp": "el",
        "cube": "",
        "can": "blik",
    },
    "fr": {
        "g": "g",
        "ml": "ml",
        "pc": "",
        "clove": "gousses",
        "slice": "tranches",
        "tbsp": "c. à s.",
        "cube": "",
        "can": "boîte",
    },
}
_TAG = {
    "en": {"warm": "warming", "oven": "oven", "quick": "quick", "fresh": "fresh", "sweet": "sweet", "vegetarian": "vegetarian",
           "garden": "from the garden"},
    "nl": {"warm": "verwarmend", "oven": "oven", "quick": "snel", "fresh": "fris", "sweet": "zoet", "vegetarian": "vegetarisch",
           "garden": "uit de tuin"},
    "fr": {"warm": "réconfortant", "oven": "four", "quick": "rapide", "fresh": "frais", "sweet": "sucré", "vegetarian": "végétarien",
           "garden": "du jardin"},
}  # fmt: skip
_TECH_NAME = {
    "en": {"soup": "Soup", "roast": "Oven tray", "stir_fry": "Stir-fry", "pasta": "Pasta", "risotto": "Risotto", "salad": "Salad",
           "gratin": "Gratin", "stew": "Stew & curry", "frittata": "Frittata", "stoemp": "Stoemp", "stuffed": "Stuffed vegetables",
           "plate": "Meat & two veg", "pesto": "Pesto", "dessert": "Dessert", "cold_soup": "Chilled soup", "crostini": "Crostini",
           "compote": "Compote"},
    "nl": {"soup": "Soep", "roast": "Ovenschotel", "stir_fry": "Wok", "pasta": "Pasta", "risotto": "Risotto", "salad": "Salade",
           "gratin": "Gratin", "stew": "Stoofpot & curry", "frittata": "Frittata", "stoemp": "Stoemp", "stuffed": "Gevulde groenten",
           "plate": "Bord met vlees en groenten", "pesto": "Pesto", "dessert": "Dessert", "cold_soup": "Koude soep",
           "crostini": "Crostini", "compote": "Compote"},
    "fr": {"soup": "Soupe", "roast": "Plaque au four", "stir_fry": "Wok", "pasta": "Pâtes", "risotto": "Risotto", "salad": "Salade",
           "gratin": "Gratin", "stew": "Mijoté & curry", "frittata": "Frittata", "stoemp": "Stoemp", "stuffed": "Légumes farcis",
           "plate": "Assiette viande et légumes", "pesto": "Pesto", "dessert": "Dessert", "cold_soup": "Soupe froide",
           "crostini": "Crostini", "compote": "Compote"},
}  # fmt: skip
for _ix, _lang_code in enumerate(("en", "nl", "fr")):  # the texts of the dishes of cooking_dishes
    for _id, _texts in _d.TITLE.items():
        _TITLE[_lang_code][_id] = _texts[_ix]
    for _id, _texts in _d.NAME.items():
        _TECH_NAME[_lang_code][_id] = _texts[_ix]
    for _id, _texts in _d.STEPS.items():
        _STEPS[_lang_code][_id] = _texts[_ix]

_PDF = {
    "en": {"book": "Seasonal cookbook", "from_garden": "from the garden", "ingredients": "Ingredients", "method": "Method",
           "servings": "{n} servings", "minutes": "{n} min", "shopping": "Shopping list", "to_buy": "To buy",
           "garden_items": "From the garden (no need to buy)", "contents": "In this book", "made": "Made with Hortulus on {d}"},
    "nl": {"book": "Seizoenskookboek", "from_garden": "uit de tuin", "ingredients": "Ingrediënten", "method": "Bereiding",
           "servings": "{n} personen", "minutes": "{n} min", "shopping": "Boodschappenlijst", "to_buy": "Te kopen",
           "garden_items": "Uit de tuin (niet kopen)", "contents": "In dit kookboek", "made": "Gemaakt met Hortulus op {d}"},
    "fr": {"book": "Livre de cuisine de saison", "from_garden": "du jardin", "ingredients": "Ingrédients", "method": "Préparation",
           "servings": "{n} personnes", "minutes": "{n} min", "shopping": "Liste de courses", "to_buy": "À acheter",
           "garden_items": "Du jardin (inutile d'acheter)", "contents": "Dans ce livre", "made": "Réalisé avec Hortulus le {d}"},
}  # fmt: skip


def short_name(plant: Plant, lang: str) -> str:
    """'Pumpkin / Winter squash' -> 'pumpkin', 'French bean (bush)' -> 'french bean'."""
    return plant.name(lang).split(" / ")[0].split(" (")[0].strip().lower()


def label(key: str, lang: str | None = "en") -> str:
    """A fixed text of the cookbook (``shopping``, ``book`` ...) in ``lang``."""
    return _PDF[_lang(lang)][key]


def _lang(lang: str | None) -> str:
    return lang if lang in ("en", "nl", "fr") else "en"


def _join(names: Sequence[str], lang: str) -> str:
    names = [n for n in names if n]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + f" {_AND[lang]} " + names[-1]


# --------------------------------------------------------------------------- #
# Building a recipe from its spec
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class Prefs:
    """What the cook adds: fridge items to use, proteins they like, a side, how many eat."""

    pantry: list[str] = field(default_factory=list)  # in the house (not to buy)
    use: list[str] = field(default_factory=list)  # extras to work into the dish
    proteins: list[str] = field(default_factory=list)  # empty: vegetarian
    side: str = ""  # "" = the dish's own choice
    servings: int = 2

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any] | None) -> Prefs:
        raw = raw if isinstance(raw, Mapping) else {}

        def ids(key: str, *allowed: Mapping[str, Any]) -> list[str]:
            value = raw.get(key)
            items = value if isinstance(value, list) else []
            return [x for x in items if isinstance(x, str) and any(x in a for a in allowed)]

        side = raw.get("side")
        return cls(
            pantry=ids("pantry", PANTRY, SIDES, PROTEINS),
            use=ids("use", PANTRY),
            proteins=ids("proteins", PROTEINS),
            side=side if isinstance(side, str) and (side in SIDES or side == "none") else "",
            servings=servings_of(raw.get("servings")),
        )


def servings_of(value: Any, default: int = 2) -> int:
    """A number of servings between 1 and 12 (anything unreadable: the default)."""
    try:
        n = int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        n = default
    return max(1, min(12, n))


def str_ids(value: Any) -> list[str]:
    """The string ids in a list (anything else, or a non-list: nothing)."""
    return [x for x in value if isinstance(x, str)] if isinstance(value, (list, tuple)) else []


def spec_id(spec: Mapping[str, Any]) -> str:
    key = json.dumps(
        {k: spec.get(k) for k in ("technique", "produce", "side", "protein", "extras", "servings")}, sort_keys=True
    )
    return "r" + hashlib.sha1(key.encode()).hexdigest()[:11]


def _qty(value: float, unit: str) -> float:
    if unit in ("g", "ml"):
        return float(max(5, round(value / 10) * 10)) if value >= 20 else float(max(5, round(value / 5) * 5))
    return round(value * 2) / 2 if value < 5 else float(round(value))


def _fmt(qty: float, unit: str, lang: str) -> str:
    if not unit and not qty:
        return ""
    num = f"{qty:g}".replace(".", "," if lang != "en" else ".")
    label = _UNITS[lang].get(unit, unit)
    return f"{num} {label}".strip()


def render(spec: Mapping[str, Any], db: PlantDatabase, lang: str | None = "en", garden_herbs: Sequence[str] = (),
           pantry: Iterable[str] = ()) -> dict[str, Any] | None:  # fmt: skip
    """The full recipe for a spec, in ``lang``.  None when the spec no longer makes sense."""
    lang = _lang(lang)
    if not isinstance(spec, Mapping):
        return None
    tech = TECHNIQUE.get(str(spec.get("technique")))
    if tech is None:
        return None
    servings = servings_of(spec.get("servings"))
    produce: list[tuple[Plant, str]] = []
    for pid in str_ids(spec.get("produce")):
        plant = db.get(pid)
        kind = produce_kind(plant)
        if plant is not None and kind is not None:
            produce.append((plant, kind))
    if not produce:
        return None
    if tech.plants and any(p.id not in tech.plants and (k != "herb" or tech.herbs_in_pool) for p, k in produce):
        return None  # a dish made for certain plants only (no tomato cake)
    if tech.id in _UNCOOKED and any(p.id in COOK_FIRST for p, _ in produce):
        return None  # raw elderberries or beans are not food
    if tech.needs_main and all(k == "herb" for _, k in produce):
        return None  # a caprese of basil alone
    side_id = str(spec.get("side") or "")
    if tech.no_side or tech.sweet:
        side_id = ""
    elif tech.must_side and side_id not in tech.sides:
        side_id = tech.sides[0]  # crostini always need their bread (also on the shopping list)
    side = SIDES.get(side_id)
    protein_id = "" if tech.sweet else str(spec.get("protein") or "")  # no meat in a dessert
    protein = PROTEINS.get(protein_id)
    produce_ids = [p.id for p, _ in produce]
    meat = pan_meat(protein_id if protein else "")
    plan = _plan_extras(tech.id, [x for x in str_ids(spec.get("extras")) if x in PANTRY], meat, produce_ids)
    extras = list(plan)
    needed = [d for key in plan.values() for d in _x.DEPENDS.get(key, ())]  # what the preparations need too
    in_house = set(pantry) | set(extras)  # what the cook took from the fridge is in the house

    names = [short_name(p, lang) for p, _ in produce]
    main_names = [n for (p, k), n in zip(produce, names, strict=True) if k != "herb"] or names
    a = main_names[0]
    title = _TITLE[lang][tech.id].format(a=_join(main_names[:3], lang))
    title = title[0].upper() + title[1:]
    subtitle = _WITH[lang].format(p=protein.name(lang)) if protein else ""

    # ingredients
    ingredients: list[dict[str, Any]] = []
    non_herbs = [(p, k) for p, k in produce if k != "herb"]
    share = 1.0 if len(non_herbs) <= 1 else (1.6 / len(non_herbs))  # several vegetables share the plate
    for plant, kind in produce:
        grams = GRAMS_PER_PERSON[kind] * servings * (1.0 if kind == "herb" else share)
        if tech.herb_grams and kind in ("herb", "leafy"):
            grams = tech.herb_grams * servings
        grams *= tech.batch
        ingredients.append({"id": plant.id, "plant_id": plant.id, "name": plant.name(lang), "qty": _qty(grams, "g"), "unit": "g",
                            "group": "garden", "kind": kind, "source": "garden", "color": plant.color or KIND_COLOR[kind]})  # fmt: skip
    if side is not None:
        qty = side.qty * servings
        ingredients.append({"id": side_id, "name": side.name(lang), "qty": _qty(qty, side.unit), "unit": side.unit, "group": "side",
                            "source": "pantry" if side_id in in_house else "shop"})  # fmt: skip
    if protein is not None:
        qty = protein.qty * servings
        ingredients.append({"id": protein_id, "name": protein.name(lang), "qty": _qty(qty, protein.unit), "unit": protein.unit,
                            "group": protein.group, "source": "pantry" if protein_id in in_house else "shop"})  # fmt: skip
    garden_ids = {p.id for p, _ in produce}
    wanted = dict.fromkeys([*tech.staples, *extras, *needed])
    for item_id in wanted:
        if item_id in ("onion", "garlic") and garden_ids & (
            {"onion", "shallot", "leek"} if item_id == "onion" else {"garlic", "elephant_garlic"}
        ):
            continue  # the garden gives it
        item = PANTRY[item_id]
        qty = item.qty * (1 if item.per_dish else servings) * dict(tech.scale).get(item_id, 1.0)
        ingredients.append({"id": item_id, "name": item.name(lang), "qty": _qty(qty, item.unit), "unit": item.unit, "group": item.group,
                "source": "pantry" if item_id in in_house else "shop", "extra": item_id in extras})  # fmt: skip
    for basic_id, item in BASICS.items():
        ingredients.append(
            {"id": basic_id, "name": item.name(lang), "qty": 0, "unit": "", "group": "basic", "source": "basic"}
        )
    herbs = [short_name(p, lang) for p, k in produce if k == "herb"] or [h for h in garden_herbs if h]
    for ing in ingredients:
        ing["label"] = _fmt(float(ing["qty"]), str(ing["unit"]), lang)

    # steps
    prep = _join(
        [
            _PREP[lang][k].format(n=n)
            for (p, k), n in zip(produce, names, strict=True)
            if k != "herb" or tech.herbs_in_pool
        ],
        lang,
    )
    side_name = (
        side.name(lang)
        if side
        else (SIDES["pasta"].name(lang) if tech.id in ("pasta", "pesto") else SIDES["rice"].name(lang))
    )
    steps: list[str] = []
    after_first: list[str] = []  # the protein, when the dish takes it after its second step
    tail: list[str] = []  # ... or at the very end
    in_dish_side = side is not None and side_id in tech.sides
    if side is not None and side_id != "bread" and not tech.side_in_method:  # bread is toasted at the end
        steps.append(_SIDE_STEP[lang][side_id])
    if protein is not None:
        key = (
            "stew_beef"
            if protein_id == "stew_beef"
            else "bacon"
            if protein_id == "bacon"
            else "lentils"
            if protein_id == "lentils"
            else protein.group
            if protein.group in ("fish", "veg_protein")
            else "meat"
        )
        own = _d.PROTEIN_STEP.get(tech.id, {})  # e.g. poached in the waterzooi, ham next to the asparagus
        text, where = _PROTEIN_STEP[lang][key], "start"
        for hit in (protein_id, protein.group):
            if hit in own:
                where, *texts = own[hit]
                text = texts[_LANG_IX_EN[lang]]
                break
        text = text.format(p=protein.name(lang).split(" (")[0].lower())
        {"early": after_first, "end": tail}.get(where, steps).append(text)
    fresh = {short_name(p, lang) for i in _SAUCE_HERBS if (p := db.get(i)) is not None}
    early, mid, during, late = _extra_steps(tech.id, extras, lang, [h for h in herbs if h in fresh], produce_ids, meat)
    method = _STEPS[lang][tech.id]
    for n, step in enumerate(method):
        if n == 1:  # before the cooking starts (honey instead of sugar ...)
            steps += early
            early = []
        if n == len(method) - 1:  # "for the last 10 minutes ...": said before the oven or grill step it times
            steps += mid + during
            mid = during = []
        steps.append(step.format(prep=prep or a, side=side_name.lower(), veg=_join(names, lang)))
        if n == 1:
            steps += mid + after_first
            mid = []
    steps += early + mid + during + tail + late
    if herbs and not (tech.herbs_in_pool or tech.sweet):
        steps.append(_HERBS[lang].format(h=_join(herbs[:3], lang)))
    if side_id == "bread" and tech.id != "crostini":  # crostini toast their own bread
        steps.append(_SIDE_STEP[lang]["bread"])
    if side is not None and not in_dish_side:
        steps.append(_SERVE_SIDE[lang].format(s=side.name(lang)))

    tags = [*tech.tags, "garden"]
    if protein is None or protein.group == "veg_protein":
        tags.append("vegetarian")
    minutes = tech.minutes + (60 if protein_id == "stew_beef" else 0)
    shopping = [{"id": i["id"], "name": i["name"], "qty": i["qty"], "unit": i["unit"], "label": i["label"], "group": i["group"]}
                for i in ingredients if i["source"] == "shop"]  # fmt: skip
    clean_spec = {"technique": tech.id, "produce": [p.id for p, _ in produce], "side": side_id if side else "",
                  "protein": protein_id if protein else "", "extras": extras, "servings": servings}  # fmt: skip
    return {
        "id": spec_id(clean_spec),
        "spec": clean_spec,
        "title": title,
        "subtitle": subtitle,
        "technique": tech.id,
        "technique_name": _TECH_NAME[lang][tech.id],
        "course": (course := course_of(tech.id, protein_id if protein else "", side_id if side else "")),
        "course_name": course_name(course, lang),
        "minutes": minutes,
        "servings": servings,
        "ingredients": ingredients,
        "steps": steps,
        "shopping": shopping,
        "tags": tags,
        "tag_names": [_TAG[lang].get(t, t) for t in tags],
        "garden_share": round(
            sum(1 for i in ingredients if i["source"] == "garden")
            / max(1, sum(1 for i in ingredients if i["source"] != "basic")),
            2,
        ),
        "picture": {
            "produce": [
                {"plant_id": p.id, "kind": k, "color": p.color or KIND_COLOR[k], "icon": p.icon, "emoji": p.emoji}
                for p, k in produce
            ],
            "side": side_id if side else "",
            "protein": protein_id if protein else "",
            "extras": extras,
            "technique": tech.id,
        },
    }


UNITS = ("g", "ml", "pc", "clove", "slice", "tbsp", "cube", "can")
SOURCES = ("garden", "pantry", "shop")
_GROUP_ORDER = ("meat", "fish", "veg_protein", "dairy", "side", "pantry", "other")


def _ingredient_id(raw_id: Any, name: str) -> str:
    """A generated ingredient keeps its id; a new one is named after what it is, so two recipes' new
    ingredients never merge on a shopping list just because they sit at the same row."""
    given = str(raw_id or "")[:60]
    if given and not given.startswith("custom-"):
        return given
    return "custom-" + hashlib.sha1(name.casefold().encode()).hexdigest()[:10]


def custom_ingredient(raw: Any, n: int) -> dict[str, Any] | None:
    """One ingredient as the cook typed it (None when it has no name)."""
    if not isinstance(raw, Mapping):
        return None
    name = str(raw.get("name") or "").strip()[:80]
    if not name:
        return None
    try:
        qty = float(raw.get("qty") or 0)
    except (TypeError, ValueError):
        qty = 0.0
    qty = round(qty, 2) if math.isfinite(qty) and 0 <= qty <= 100000 else 0.0
    unit = str(raw.get("unit") or "")
    source = str(raw.get("source") or "shop")
    group = str(raw.get("group") or "other")
    out: dict[str, Any] = {
        "id": _ingredient_id(raw.get("id"), name),
        "name": name,
        "qty": qty,  # exactly what the cook typed (1 g of saffron stays 1 g)
        "unit": unit if unit in UNITS else "",
        "source": source if source in SOURCES else "shop",
        "group": group if group in _GROUP_ORDER or group == "garden" else "other",
    }
    for key in ("plant_id", "kind", "color"):
        if isinstance(raw.get(key), str) and raw.get(key):
            out[key] = str(raw[key])[:40]
    return out


def apply_custom(recipe: dict[str, Any], ingredients: Sequence[Mapping[str, Any]], steps: Sequence[str],
                 lang: str | None = "en") -> dict[str, Any]:  # fmt: skip
    """A recipe with the cook's own ingredient list and/or method (an empty one keeps the generated)."""
    lang = _lang(lang)
    if ingredients:
        rows = []
        for raw in ingredients:
            row = dict(raw)
            row["label"] = _fmt(float(row.get("qty") or 0), str(row.get("unit") or ""), lang) if row.get("qty") else ""
            rows.append(row)
        basics = [i for i in recipe["ingredients"] if i.get("source") == "basic"]
        recipe["ingredients"] = [*rows, *basics]
        recipe["shopping"] = [{"id": i["id"], "name": i["name"], "qty": i["qty"], "unit": i["unit"], "label": i["label"],
                               "group": i["group"]} for i in rows if i["source"] == "shop"]  # fmt: skip
        recipe["garden_share"] = round(sum(1 for i in rows if i["source"] == "garden") / max(1, len(rows)), 2)
    if steps:
        recipe["steps"] = list(steps)
    recipe["custom"] = bool(ingredients or steps)
    return recipe


# --------------------------------------------------------------------------- #
# Suggestions
# --------------------------------------------------------------------------- #
def ready_produce(ready: Sequence[Mapping[str, Any]], db: PlantDatabase) -> list[dict[str, Any]]:
    """The kitchen report's 'ready' list as cooking produce: one entry per crop, most urgent first."""
    seen: dict[str, dict[str, Any]] = {}
    for r in sorted(ready, key=lambda x: str(x.get("until", ""))):
        pid = str(r.get("plant_id"))
        plant = db.get(pid)
        kind = produce_kind(plant)
        if plant is None or kind is None or pid in seen:
            continue
        seen[pid] = {
            "plant_id": pid,
            "kind": kind,
            "until": r.get("until"),
            "beds": [r.get("bed")] if r.get("bed") else [],
        }
    return list(seen.values())


def _interleave(recipes: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """The dishes made for certain plants (ratatouille, fritters ...) and the general ones (a
    pasta, a tray ...) in turn, so neither crowds out the other."""
    specific = [r for r in recipes if TECHNIQUE[r["technique"]].plants]
    general = [r for r in recipes if not TECHNIQUE[r["technique"]].plants]
    out: list[dict[str, Any]] = []
    while specific or general:
        if specific:
            out.append(specific.pop(0))
        if general:
            out.append(general.pop(0))
    return out


def suggest(produce: Sequence[Mapping[str, Any]], db: PlantDatabase, prefs: Prefs, lang: str | None = "en",
            limit: int = 9) -> list[dict[str, Any]]:  # fmt: skip
    """Recipes for the produce at hand (``ready_produce``), the garden first, spread over the
    chapters (soups, starters, main courses, desserts) and in that order, plus up to two ideas
    for preserving the surplus."""
    lang = _lang(lang)
    every = _suggest_all(produce, db, prefs, lang, max(limit * 8, 80))
    by_course = {c: _interleave([r for r in every if r["course"] == c]) for c in COURSES}
    picked: list[dict[str, Any]] = []
    while len(picked) < limit and any(by_course[c] for c in MEAL_COURSES):
        for c in MEAL_COURSES:  # one of each chapter in turn, so none is crowded out
            if by_course[c] and len(picked) < limit:
                picked.append(by_course[c].pop(0))
    picked.sort(key=lambda r: COURSES.index(r["course"]))
    return [*picked, *by_course["preserve"][:2]]


def _overlap(recipe: Mapping[str, Any], chosen: Sequence[Mapping[str, Any]]) -> int:
    """How many garden plants a recipe shares with the courses already in a menu."""
    plants = {p for r in chosen for p in r["spec"]["produce"]}
    return sum(1 for p in recipe["spec"]["produce"] if p in plants)


def menus(produce: Sequence[Mapping[str, Any]], db: PlantDatabase, prefs: Prefs, lang: str | None = "en",
          count: int = 4, today: date | None = None) -> list[dict[str, Any]]:  # fmt: skip
    """Complete menus (a soup or starter, a main course and a dessert) from the produce at hand:
    the themed ones of the season first (a Provençal dinner, a Flemish spring menu ...), then menus
    built around a main course.  A dish is used in one menu only."""
    lang = _lang(lang)
    month = (today or date.today()).month
    every = _suggest_all(produce, db, prefs, lang, 160)
    used: set[str] = set()
    out: list[dict[str, Any]] = []

    def pick(candidates: Sequence[dict[str, Any]], chosen: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
        fresh = [r for r in candidates if r["id"] not in used]
        return min(fresh, key=lambda r: _overlap(r, chosen)) if fresh else None  # first of the least overlap

    def build(theme: str, title: str, slots: Sequence[Sequence[dict[str, Any]]]) -> bool:
        chosen: list[dict[str, Any]] = []
        for cands in slots:
            recipe = pick(cands, chosen)
            if recipe is None:
                return False
            chosen.append(recipe)
        used.update(r["id"] for r in chosen)
        out.append(
            {
                "id": "m" + hashlib.sha1(",".join(r["id"] for r in chosen).encode()).hexdigest()[:11],
                "theme": theme,
                "title": title,
                "courses": [{"course": r["course"], "recipe": r} for r in chosen],
                "minutes": sum(int(r["minutes"]) for r in chosen),
                "servings": prefs.servings,
            }
        )
        return True

    themes = sorted(_d.MENU_THEMES, key=lambda t: 0 if month in t["months"] else 1)  # the season first
    for theme in themes:
        if len(out) >= count:
            break
        if month not in theme["months"] and len(out) >= count - 1:
            continue  # leave a place for a menu around the main course
        plants = {p for r in every for p in r["spec"]["produce"]}
        needs = theme.get("needs", ())
        if needs and not plants & set(needs):
            continue
        slots = [
            [r for tid in theme[slot] for r in every if r["technique"] == tid and r["course"] in courses]
            for slot, courses in (("starter", ("soup", "starter")), ("main", ("main",)), ("dessert", ("dessert",)))
        ]
        if all(slots):
            build(theme["id"], theme["names"][_LANG_IX_EN[lang]], slots)

    meals = {c: _interleave([r for r in every if r["course"] == c]) for c in MEAL_COURSES}
    starters = [*meals["soup"], *meals["starter"]]
    for main in meals["main"]:
        if len(out) >= count:
            break
        if main["id"] in used:
            continue
        a = _join([short_name(p, lang) for i in main["spec"]["produce"][:2] if (p := db.get(i)) is not None], lang)
        title = _d.MENU_TITLE["generic"][_LANG_IX_EN[lang]].format(a=a)
        build("", title[0].upper() + title[1:], [starters, [main], meals["dessert"]])
    return out[:count]


def _suggest_all(produce: Sequence[Mapping[str, Any]], db: PlantDatabase, prefs: Prefs, lang: str,
                 limit: int) -> list[dict[str, Any]]:  # fmt: skip
    items = [p for p in produce if p.get("kind") in KINDS]
    herbs = [p for p in items if p["kind"] == "herb"]
    veg = [p for p in items if p["kind"] != "herb"]
    herb_names = [short_name(p, lang) for h in herbs[:3] if (p := db.get(h["plant_id"])) is not None]
    out: list[dict[str, Any]] = []
    used_mains: dict[str, int] = {}
    protein_cycle = list(prefs.proteins)
    for round_no in range(2):  # a second round varies the main vegetable
        for tech in TECHNIQUES:
            pool = [
                p
                for p in (herbs + veg if tech.herbs_in_pool else veg)
                if p["kind"] in tech.kinds
                and (not tech.plants or p["plant_id"] in tech.plants)
                and not (tech.id in _UNCOOKED and p["plant_id"] in COOK_FIRST)
                and (tech.id in _RAW_OK or p["plant_id"] not in RAW_ONLY)
            ]
            if tech.needs_herb and not any(p["kind"] == "herb" for p in pool):
                continue
            if len(pool) < tech.min_garden:
                continue
            pool.sort(
                key=lambda p: (tech.kinds.index(p["kind"]), used_mains.get(p["plant_id"], 0), str(p.get("until", "")))
            )
            if round_no == 1:
                if len(pool) < 2:
                    continue
                pool = pool[1:] + pool[:1]
            # variety first (one of each kind), then the same kinds fill the places that are left
            picked: list[Mapping[str, Any]] = []
            for p in pool:
                if len(picked) < tech.max_garden and all(p["kind"] != q["kind"] for q in picked):
                    picked.append(p)
            for p in pool:
                if len(picked) < tech.max_garden and all(p is not q for q in picked):
                    picked.append(p)
            chosen = [p for p in pool if any(p is q for q in picked)]
            if (
                len(chosen) < tech.min_garden
                or (tech.needs_herb and not any(c["kind"] == "herb" for c in chosen))
                or (tech.needs_main and all(c["kind"] == "herb" for c in chosen))
            ):
                continue
            side = prefs.side if prefs.side and prefs.side != "none" else (tech.sides[0] if tech.sides else "")
            if prefs.side == "none" or tech.sweet or tech.no_side:
                side = ""
            if tech.must_side and side not in tech.sides:
                side = tech.sides[0]  # the toasts, the grain: the dish, whatever side the cook prefers
            protein = ""
            if protein_cycle and not tech.sweet:
                fits = [p for p in protein_cycle if p in tech.proteins] or ([] if tech.strict else protein_cycle[:1])
                if fits:
                    protein = fits[(len(out)) % len(fits)]
            extras = list(prefs.use)  # render keeps only what suits this dish
            spec = {"technique": tech.id, "produce": [c["plant_id"] for c in chosen], "side": side, "protein": protein,
                    "extras": extras, "servings": prefs.servings}  # fmt: skip
            recipe = render(spec, db, lang, herb_names, [*prefs.pantry, *prefs.use])
            if recipe is None or any(r["id"] == recipe["id"] for r in out):
                continue
            used_mains[chosen[0]["plant_id"]] = used_mains.get(chosen[0]["plant_id"], 0) + 1
            out.append(recipe)
            if len(out) >= limit:
                return out
    return out


def shopping_list(recipes: Sequence[Mapping[str, Any]], lang: str | None = "en") -> dict[str, Any]:
    """One list for several recipes: the same item adds up; garden produce listed apart."""
    lang = _lang(lang)
    buy: dict[tuple[str, str], dict[str, Any]] = {}
    garden: dict[str, dict[str, Any]] = {}
    for r in recipes:
        for i in r.get("ingredients", []):
            if i.get("source") == "shop":
                key = (str(i["id"]), str(i["unit"]))
                row = buy.setdefault(
                    key, {"id": i["id"], "name": i["name"], "qty": 0.0, "unit": i["unit"], "group": i["group"]}
                )
                row["qty"] += float(i["qty"])
            elif i.get("source") == "garden":
                row = garden.setdefault(str(i["id"]), {"id": i["id"], "name": i["name"], "qty": 0.0, "unit": "g"})
                row["qty"] += float(i["qty"])
    order = {g: n for n, g in enumerate(_GROUP_ORDER)}
    rows = sorted(buy.values(), key=lambda x: (order.get(str(x["group"]), 9), str(x["name"])))
    for row in [*rows, *garden.values()]:
        row["qty"] = _qty(float(row["qty"]), str(row["unit"]))
        row["label"] = _fmt(float(row["qty"]), str(row["unit"]), lang)
    return {"buy": rows, "garden": sorted(garden.values(), key=lambda x: str(x["name"]))}


def shopping_text(recipes: Sequence[Mapping[str, Any]], lang: str | None = "en") -> str:
    """The shopping list as plain text (mail, notification, to-do)."""
    lang = _lang(lang)
    lst = shopping_list(recipes, lang)
    lines = [f"{_PDF[lang]['shopping']}: " + _join([str(r["title"]) for r in recipes], lang), ""]
    lines += [f"- {r['name']}" + (f" ({r['label']})" if r["label"] else "") for r in lst["buy"]]
    if lst["garden"]:
        lines += ["", _PDF[lang]["garden_items"] + ":"] + [f"- {r['name']} ({r['label']})" for r in lst["garden"]]
    return "\n".join(lines)


def recipe_text(recipe: Mapping[str, Any], lang: str | None = "en") -> str:
    """A recipe as plain text (mail, notification)."""
    lang = _lang(lang)
    t = _PDF[lang]
    head = f"{recipe['title']}" + (f" {recipe['subtitle']}" if recipe.get("subtitle") else "")
    meta = f"{t['servings'].format(n=recipe['servings'])} · {t['minutes'].format(n=recipe['minutes'])}"
    ingr = [f"- {i['name']}" + (f" ({i['label']})" if i.get("label") else "") + (f" – {t['from_garden']}" if i.get("source") == "garden" else "")
            for i in recipe["ingredients"] if i.get("source") != "basic"]  # fmt: skip
    steps = [f"{n}. {s}" for n, s in enumerate(recipe["steps"], 1)]
    return "\n".join([head, meta, "", t["ingredients"] + ":", *ingr, "", t["method"] + ":", *steps])


# --------------------------------------------------------------------------- #
# PDF: one recipe, a cookbook, a shopping list
# --------------------------------------------------------------------------- #
_GREEN = "#2f6b4f"
_INK = "#1d2a24"
_MUTED = "#66756d"


def _picture(page: PdfPage, x: float, y: float, size: float, recipe: Mapping[str, Any], image: Image | None) -> None:
    """The dish picture: the panel's image when it sent one, else a drawn plate."""
    if image is not None:
        h = size * image.aspect
        page.rect(x, y, size, h, fill="#f6f4ee", radius=3)
        page.image(x, y, size, h, image)
        return
    cx, cy, r = x + size / 2, y + size / 2, size / 2
    page.circle(cx, cy, r, fill="#efe9dc")
    page.circle(cx, cy, r * 0.82, fill="#ffffff", stroke="#e2dccd", width=0.4)
    produce = recipe.get("picture", {}).get("produce", [])
    n = max(1, len(produce))
    for i, p in enumerate(produce):
        ang = 2 * math.pi * i / n - math.pi / 2
        page.circle(
            cx + math.cos(ang) * r * 0.42, cy + math.sin(ang) * r * 0.42, r * 0.22, fill=p.get("color", "#5a9a3c")
        )
    if recipe.get("picture", {}).get("protein"):
        page.circle(cx, cy, r * 0.2, fill="#b5674a")


_PAGE_END = 268.0  # below this a new page starts
_PAGE_LIMIT = 284.0  # ... and a block that would end below this goes to the next page whole


def _continued_page(doc: PdfDocument, recipe: Mapping[str, Any]) -> PdfPage:
    """The next page of a recipe too long for one: the title again, then the rest in full width."""
    page = doc.add_page(210, 297)
    page.rect(0, 0, 210, 6, fill=_GREEN)
    page.text(18, 20, str(recipe["title"]), size=13, bold=True, color=_INK)
    page.text(105, 289, "Hortulus", size=7.5, color=_MUTED, anchor="middle")
    return page


def _recipe_page(doc: PdfDocument, recipe: Mapping[str, Any], lang: str, image: Image | None) -> None:
    t = _PDF[lang]
    page = doc.add_page(210, 297)
    page.rect(0, 0, 210, 6, fill=_GREEN)
    x, w = 18, 174
    pic = 62
    _picture(page, 210 - 18 - pic, 16, pic, recipe, image)
    y = 20.0
    tw = w - pic - 8
    for line in wrap(str(recipe["title"]), tw, 20, True)[:3]:
        y += 8.5
        page.text(x, y, line, size=20, bold=True, color=_INK)
    if recipe.get("subtitle"):
        y += 7
        page.text(x, y, str(recipe["subtitle"]), size=12, color=_GREEN)
    y += 7
    page.text(x, y, f"{recipe.get('technique_name', '')} · {t['servings'].format(n=recipe['servings'])} · {t['minutes'].format(n=recipe['minutes'])}",
              size=9.5, color=_MUTED)  # fmt: skip
    y += 5.5
    page.text(x, y, " · ".join(recipe.get("tag_names", [])), size=8.5, color=_MUTED)
    y = max(y + 10, 16 + pic + 8)
    # ingredients (left), method (right)
    col = 62
    page.text(x, y, t["ingredients"], size=12, bold=True, color=_GREEN)
    yi = y + 3
    ipage = page
    for ing in recipe["ingredients"]:
        if ing.get("source") == "basic":
            continue
        label = (f"{ing['label']}  " if ing.get("label") else "") + str(ing["name"])
        lines = len(wrap(label, col - 4, 9.5))
        if (
            yi > _PAGE_END or yi + lines * 9.5 * PT_TO_MM * 1.3 + 1 > _PAGE_LIMIT
        ):  # a long list goes on to a page of its own
            ipage = _continued_page(doc, recipe)
            yi = 26.0
        if ing.get("source") == "garden":
            ipage.circle(x + 1.2, yi + 3.3, 1.2, fill=ing.get("color", "#5a9a3c"))
        yi = ipage.text_block(x + (4 if ing.get("source") == "garden" else 0), yi, col - 4, label, size=9.5, color=_INK)
    basics = [i["name"] for i in recipe["ingredients"] if i.get("source") == "basic"]
    ipage.text_block(x, yi + 1.5, col, ", ".join(basics), size=8.5, color=_MUTED)
    mx = x + col + 8
    mw = w - col - 8
    page.text(mx, y, t["method"], size=12, bold=True, color=_GREEN)
    ym = y + 3
    spage = page
    for n, step in enumerate(recipe["steps"], 1):
        height = len(wrap(step, mw - 7, 10)) * 10 * PT_TO_MM * 1.35 + 3
        if ym > _PAGE_END or ym + height > _PAGE_LIMIT:  # the method goes on, full width, on the next page
            spage = _continued_page(doc, recipe)
            mx, mw, ym = x, w, 26.0
        spage.circle(mx + 2.3, ym + 4.2, 2.3, fill=_GREEN)
        spage.text(mx + 2.3, ym + 5.2, str(n), size=7.5, bold=True, color="#ffffff", anchor="middle")
        ym = spage.text_block(mx + 7, ym + 0.6, mw - 7, step, size=10, color=_INK, leading=1.35) + 2.5
    page.text(105, 289, "Hortulus", size=7.5, color=_MUTED, anchor="middle")


def _shopping_page(doc: PdfDocument, recipes: Sequence[Mapping[str, Any]], lang: str) -> None:
    t = _PDF[lang]
    lst = shopping_list(recipes, lang)
    page = doc.add_page(210, 297)
    page.rect(0, 0, 210, 6, fill=_GREEN)
    x = 18
    page.text(x, 26, t["shopping"], size=20, bold=True, color=_INK)
    y = page.text_block(x, 29, 174, _join([str(r["title"]) for r in recipes], lang), size=9.5, color=_MUTED) + 6
    page.text(x, y, t["to_buy"], size=12, bold=True, color=_GREEN)
    y += 4
    for row in lst["buy"]:
        page.rect(x, y + 1.6, 3.6, 3.6, stroke=_MUTED, width=0.35, radius=0.6)
        y = (
            page.text_block(
                x + 6, y, 168, f"{row['name']}" + (f"  ({row['label']})" if row["label"] else ""), size=10.5, color=_INK
            )
            + 1.2
        )
        if y > 270:
            page = doc.add_page(210, 297)
            y = 20
    if lst["garden"]:
        y += 6
        page.text(x, y, t["garden_items"], size=12, bold=True, color=_GREEN)
        y += 4
        for row in lst["garden"]:
            y = page.text_block(x + 6, y, 168, f"{row['name']}  ({row['label']})", size=10, color=_MUTED) + 1


def _chapters(recipes: Sequence[Mapping[str, Any]]) -> list[tuple[str, list[Mapping[str, Any]]]]:
    """The recipes by course, in the cookbook's order; empty chapters left out."""

    def course(r: Mapping[str, Any]) -> str:
        c = str(r.get("course") or course_of(str(r.get("technique") or "")))
        return c if c in COURSES else "main"

    return [(c, rows) for c in COURSES if (rows := [r for r in recipes if course(r) == c])]


def recipes_pdf(recipes: Sequence[Mapping[str, Any]], lang: str | None = "en", kind: str = "book",
                images: Mapping[str, bytes] | None = None, today: date | None = None, title: str | None = None) -> bytes:  # fmt: skip
    """``kind``: recipe (one recipe + its shopping list), book (cover, recipes, shopping list) or shopping."""
    lang = _lang(lang)
    t = _PDF[lang]
    doc = PdfDocument(title=title or t["book"])
    pics = {k: img for k, v in (images or {}).items() if (img := Image.from_jpeg(v)) is not None}
    if kind == "shopping":
        _shopping_page(doc, recipes, lang)
        return doc.to_bytes()
    if kind == "book":
        page = doc.add_page(210, 297)
        page.rect(0, 0, 210, 297, fill="#f6f4ee")
        page.rect(0, 0, 210, 92, fill=_GREEN)
        page.text(18, 50, title or t["book"], size=30, bold=True, color="#ffffff")
        page.text(18, 64, (today or date.today()).strftime("%d/%m/%Y"), size=12, color="#d7ebdf")
        y = 112.0
        page.text(18, y, t["contents"], size=13, bold=True, color=_GREEN)
        y += 4
        n = 0
        for course, chapter in _chapters(recipes):
            y = page.text_block(18, y + 3, 174, course_name(course, lang), size=11.5, bold=True, color=_GREEN) + 1
            for r in chapter:
                n += 1
                line = f"{n}. {r['title']}" + (f" {r['subtitle']}" if r.get("subtitle") else "")
                y = page.text_block(22, y, 170, line, size=10.5, color=_INK) + 1.2
        page.text(
            105,
            285,
            t["made"].format(d=(today or date.today()).strftime("%d/%m/%Y")),
            size=8,
            color=_MUTED,
            anchor="middle",
        )
        doc.outline.append((title or t["book"], 0))
    chapters = _chapters(recipes) if kind == "book" else [("", list(recipes))]
    for course, chapter in chapters:
        if course and len(chapters) > 1:  # a chapter page: Soups, Starters, Main courses, Desserts
            doc.outline.append((course_name(course, lang), len(doc.pages)))
            page = doc.add_page(210, 297)
            page.rect(0, 0, 210, 297, fill="#f6f4ee")
            page.rect(0, 118, 210, 46, fill=_GREEN)
            page.text(105, 147, course_name(course, lang), size=30, bold=True, color="#ffffff", anchor="middle")
        for r in chapter:
            doc.outline.append((str(r["title"]), len(doc.pages)))
            _recipe_page(doc, r, lang, pics.get(str(r["id"])))
    doc.outline.append((t["shopping"], len(doc.pages)))
    _shopping_page(doc, recipes, lang)
    return doc.to_bytes()


# --------------------------------------------------------------------------- #
# What the panel offers to choose from
# --------------------------------------------------------------------------- #
def catalog(lang: str | None = "en") -> dict[str, Any]:
    lang = _lang(lang)
    return {
        "sides": [{"id": k, "name": v.name(lang)} for k, v in SIDES.items()],
        "proteins": [{"id": k, "name": v.name(lang), "group": v.group} for k, v in PROTEINS.items()],
        "pantry": [{"id": k, "name": v.name(lang), "group": v.group, "fridge": v.fridge} for k, v in PANTRY.items()],
        "techniques": [{"id": t.id, "name": _TECH_NAME[lang][t.id], "course": t.course} for t in TECHNIQUES],
    }
