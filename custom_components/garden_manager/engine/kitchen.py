"""From the garden to the kitchen - and what the garden is worth.

* **Ready now**: crops inside their harvest window, with how to keep them.
* **Surplus**: more picked in the last week than the household eats - with
  ideas to store, preserve or share.
* **Economics**: the harvest at shop prices against what the garden cost
  (expenses the gardener logs, plus garden water from the meter).

Shop prices are rounded Belgian/Dutch retail prices per kg (organic where
that is the usual choice for home-grown produce) and can be overridden per
crop in the settings.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import pairwise
from typing import Any

from .i18n import normalize_lang
from .models import GardenData, Plant, PlantCategory, PlantingStatus
from .plantdb import PlantDatabase
from .records import harvest_summary
from .region import season_for_date
from .schedule import PlantingTimeline

SURPLUS_FACTOR = 1.5  # this much more than the household eats in a week counts as surplus

GROUP_BY_FAMILY = {
    "Solanaceae": "fruiting",
    "Cucurbitaceae": "fruiting",
    "Brassicaceae": "brassica",
    "Asteraceae": "leafy",
    "Amaranthaceae": "leafy",
    "Polygonaceae": "leafy",
    "Montiaceae": "leafy",
    "Aizoaceae": "leafy",
    "Apiaceae": "root",
    "Fabaceae": "legume",
    "Amaryllidaceae": "allium",
    "Poaceae": "fruiting",
}

# EUR per kg in the shop (per group, then a few common crops).
GROUP_PRICE = {
    "fruiting": 3.5, "leafy": 7.0, "brassica": 3.5, "root": 2.0, "legume": 7.0,
    "allium": 2.5, "herb": 30.0, "fruit": 9.0, "flower": 0.0, "other": 3.0,
}  # fmt: skip
CROP_PRICE = {
    "tomato": 4.5, "cherry_tomato": 9.0, "beefsteak_tomato": 5.0, "cucumber": 2.5, "courgette": 2.5,
    "pumpkin": 2.0, "butternut": 2.5, "hokkaido": 2.5, "sweet_pepper": 6.0, "chili_pepper": 15.0, "aubergine": 4.0,
    "sweet_corn": 4.0, "potato": 1.5, "early_potato": 2.5, "carrot": 1.8, "beetroot": 2.5, "parsnip": 3.5,
    "celeriac": 3.0, "onion": 1.8, "shallot": 5.0, "garlic": 12.0, "leek": 3.5, "lettuce": 6.0, "spinach": 8.0,
    "rocket": 25.0, "lambs_lettuce": 20.0, "kale": 7.0, "broccoli": 5.0, "cauliflower": 3.5,
    "brussels_sprouts": 5.0, "pole_bean": 7.0, "bush_bean": 7.0, "runner_bean": 6.0, "pea": 9.0,
    "sugar_snap": 12.0, "snow_pea": 12.0, "asparagus": 14.0, "strawberry": 10.0, "raspberry": 22.0,
    "blackberry": 18.0, "redcurrant": 14.0, "blackcurrant": 14.0, "gooseberry": 12.0, "blueberry": 20.0,
    "apple": 2.8, "pear": 3.0, "plum": 4.5, "cherry": 10.0, "rhubarb": 5.0,
}  # fmt: skip

# What one person eats in a week (kg) per group - for the surplus check.
WEEKLY_KG = {
    "fruiting": 1.2, "leafy": 0.4, "brassica": 0.7, "root": 0.9, "legume": 0.4,
    "allium": 0.3, "herb": 0.05, "fruit": 1.0, "flower": 0.05, "other": 0.5,
}  # fmt: skip

TIPS: dict[str, dict[str, tuple[str, str]]] = {
    # group -> lang -> (keep, surplus ideas)
    "fruiting": {
        "en": (
            "Keep tomatoes and courgettes out of the fridge; pick every couple of days.",
            "Make passata, ratatouille or chutney, roast and freeze, or share with the neighbours.",
        ),
        "nl": (
            "Bewaar tomaten en courgettes buiten de koelkast; oogst om de paar dagen.",
            "Maak passata, ratatouille of chutney, rooster en vries in, of deel met de buren.",
        ),
        "fr": (
            "Gardez tomates et courgettes hors du réfrigérateur ; récoltez tous les deux ou trois jours.",
            "Faites du coulis, de la ratatouille ou un chutney, rôtissez et congelez, ou partagez avec les voisins.",
        ),
        "de": (
            "Tomaten und Zucchini nicht im Kühlschrank lagern; alle paar Tage ernten.",
            "Passata, Ratatouille oder Chutney kochen, rösten und einfrieren oder mit den Nachbarn teilen.",
        ),
    },
    "leafy": {
        "en": (
            "Pick in the cool of the morning, rinse and keep in a damp cloth in the fridge (3-5 days).",
            "Make pesto or soup, blanch and freeze spinach and chard, or sow less next time.",
        ),
        "nl": (
            "Oogst 's ochtends als het koel is, spoel en bewaar in een vochtige doek in de koelkast (3-5 dagen).",
            "Maak pesto of soep, blancheer en vries spinazie en snijbiet in, of zaai volgende keer minder.",
        ),
        "fr": (
            "Récoltez à la fraîcheur du matin, rincez et gardez dans un linge humide au réfrigérateur (3-5 jours).",
            "Faites un pesto ou une soupe, blanchissez et congelez épinards et blettes, ou semez moins la prochaine fois.",
        ),
        "de": (
            "Morgens in der Kühle ernten, abspülen und in einem feuchten Tuch im Kühlschrank aufbewahren (3-5 Tage).",
            "Pesto oder Suppe machen, Spinat und Mangold blanchieren und einfrieren oder beim nächsten Mal weniger säen.",
        ),
    },
    "brassica": {
        "en": (
            "Keep cool and wrapped in the fridge; many brassicas can also stay on the plant for a while.",
            "Blanch and freeze florets, make sauerkraut or kimchi, or leave hardy kale in the bed.",
        ),
        "nl": (
            "Koel en ingepakt in de koelkast; veel kolen kunnen ook nog even aan de plant blijven.",
            "Blancheer en vries roosjes in, maak zuurkool of kimchi, of laat winterharde boerenkool staan.",
        ),
        "fr": (
            "Gardez au frais et emballé au réfrigérateur ; beaucoup de choux peuvent aussi rester un moment sur pied.",
            "Blanchissez et congelez les bouquets, faites de la choucroute ou du kimchi, ou laissez le chou frisé rustique en place.",
        ),
        "de": (
            "Kühl und verpackt im Kühlschrank lagern; viele Kohlarten können auch noch eine Weile an der Pflanze bleiben.",
            "Röschen blanchieren und einfrieren, Sauerkraut oder Kimchi machen oder winterharten Grünkohl im Beet lassen.",
        ),
    },
    "root": {
        "en": (
            "Twist off the leaves, keep unwashed in a cool, dark, slightly damp place.",
            "Store in sand in a crate, leave them in the ground under straw, or make soup and freeze.",
        ),
        "nl": (
            "Draai het loof eraf, bewaar ongewassen koel, donker en licht vochtig.",
            "Kuil ze in zand in een kist, laat ze onder stro in de grond, of maak soep en vries in.",
        ),
        "fr": (
            "Tordez les fanes, gardez sans laver dans un endroit frais, sombre et légèrement humide.",
            "Conservez-les dans du sable en caisse, laissez-les en terre sous la paille, ou faites une soupe et congelez.",
        ),
        "de": (
            "Das Laub abdrehen und ungewaschen kühl, dunkel und leicht feucht lagern.",
            "In einer Kiste in Sand einschlagen, unter Stroh im Boden lassen oder Suppe kochen und einfrieren.",
        ),
    },
    "legume": {
        "en": (
            "Pick young and often; eat within a few days or blanch straight away.",
            "Blanch and freeze, or let the last pods dry on the plant for dried beans.",
        ),
        "nl": (
            "Pluk jong en vaak; eet binnen een paar dagen of blancheer meteen.",
            "Blancheer en vries in, of laat de laatste peulen aan de plant drogen voor droge bonen.",
        ),
        "fr": (
            "Cueillez jeune et souvent ; consommez en quelques jours ou blanchissez tout de suite.",
            "Blanchissez et congelez, ou laissez sécher les dernières gousses sur pied pour des haricots secs.",
        ),
        "de": (
            "Jung und oft pflücken; innerhalb weniger Tage essen oder sofort blanchieren.",
            "Blanchieren und einfrieren oder die letzten Hülsen an der Pflanze trocknen lassen für Trockenbohnen.",
        ),
    },
    "allium": {
        "en": (
            "Dry onions and garlic in the sun or an airy shed for two weeks before storing.",
            "Braid and hang them, make onion confit, or freeze chopped leek.",
        ),
        "nl": (
            "Laat uien en knoflook twee weken drogen in de zon of een luchtig hok voor je ze opslaat.",
            "Vlecht en hang ze op, maak uienconfit, of vries gesneden prei in.",
        ),
        "fr": (
            "Faites sécher oignons et ail deux semaines au soleil ou dans un abri aéré avant de les stocker.",
            "Tressez-les et suspendez-les, faites une confiture d'oignons, ou congelez du poireau émincé.",
        ),
        "de": (
            "Zwiebeln und Knoblauch vor dem Einlagern zwei Wochen in der Sonne oder in einem luftigen Schuppen trocknen.",
            "Zu Zöpfen flechten und aufhängen, Zwiebelkonfitüre kochen oder geschnittenen Lauch einfrieren.",
        ),
    },
    "herb": {
        "en": (
            "Cut in the morning, keep stems in water or wrapped in a damp cloth.",
            "Dry in bunches, freeze in ice cubes with oil, or make herb salt and pesto.",
        ),
        "nl": (
            "Knip 's ochtends, zet de stelen in water of in een vochtige doek.",
            "Droog in bosjes, vries in in ijsblokjes met olie, of maak kruidenzout en pesto.",
        ),
        "fr": (
            "Coupez le matin, gardez les tiges dans l'eau ou dans un linge humide.",
            "Faites sécher en bouquets, congelez en glaçons avec de l'huile, ou préparez du sel aux herbes et du pesto.",
        ),
        "de": (
            "Morgens schneiden, die Stiele in Wasser stellen oder in ein feuchtes Tuch wickeln.",
            "In Sträußen trocknen, mit Öl in Eiswürfeln einfrieren oder Kräutersalz und Pesto herstellen.",
        ),
    },
    "fruit": {
        "en": (
            "Pick dry and ripe, keep cool and unwashed; soft fruit within two days.",
            "Make jam or compote, freeze on a tray, or dry apple rings.",
        ),
        "nl": (
            "Pluk droog en rijp, bewaar koel en ongewassen; zacht fruit binnen twee dagen.",
            "Maak jam of compote, vries in op een plaat, of droog appelringen.",
        ),
        "fr": (
            "Cueillez sec et mûr, gardez au frais sans laver ; les petits fruits dans les deux jours.",
            "Faites de la confiture ou de la compote, congelez à plat sur un plateau, ou séchez des rondelles de pomme.",
        ),
        "de": (
            "Trocken und reif pflücken, kühl und ungewaschen lagern; Beerenobst innerhalb von zwei Tagen.",
            "Marmelade oder Kompott kochen, auf einem Blech einfrieren oder Apfelringe trocknen.",
        ),
    },
}
TIPS["other"] = TIPS["fruiting"]
TIPS["flower"] = {
    "en": ("Cut in the morning and put straight into water.", "Make bouquets, dry them, or share."),
    "nl": ("Knip 's ochtends en zet meteen in water.", "Maak boeketten, droog ze of deel ze uit."),
    "fr": ("Coupez le matin et mettez tout de suite dans l'eau.", "Faites des bouquets, séchez-les ou offrez-les."),
    "de": ("Morgens schneiden und sofort ins Wasser stellen.", "Sträuße binden, trocknen oder verschenken."),
}


def kitchen_group(plant: Plant | None) -> str:
    if plant is None:
        return "other"
    if plant.category is PlantCategory.HERB:
        return "herb"
    if plant.category is PlantCategory.FRUIT:
        return "fruit"
    if plant.category is PlantCategory.FLOWER:
        return "flower"
    return GROUP_BY_FAMILY.get(plant.family or "", "other")


def price_per_kg(plant_id: str, plant: Plant | None, overrides: Mapping[str, float]) -> float:
    if plant_id in overrides:
        return float(overrides[plant_id])
    return CROP_PRICE.get(plant_id, GROUP_PRICE[kitchen_group(plant)])


def _tips(group: str, lang: str) -> tuple[str, str]:
    by_lang = TIPS.get(group, TIPS["other"])
    return by_lang.get(normalize_lang(lang), by_lang["en"])


def kitchen_report(
    data: GardenData,
    db: PlantDatabase,
    timelines: Mapping[str, PlantingTimeline],
    today: date,
    lang: str = "en",
) -> dict[str, Any]:
    """Crops ready to pick now and crops picked faster than the household eats them."""
    ready = []
    for p in data.plantings:
        tl = timelines.get(p.id)
        plant = db.get(p.plant_id)
        if tl is None or plant is None or p.status in (PlantingStatus.FINISHED, PlantingStatus.FAILED):
            continue
        if p.status is PlantingStatus.PLANNED and p.sown_on is None:
            continue  # a plan is no harvest: only crops that were really sown or planted count
        if p.status is PlantingStatus.SOWN_INDOORS and tl.in_ground > today:
            continue
        if p.status is PlantingStatus.HARVESTING or tl.harvest_start <= today <= tl.harvest_end:
            group = kitchen_group(plant)
            bed = data.bed(p.bed_id)
            ready.append(
                {
                    "planting_id": p.id,
                    "plant_id": p.plant_id,
                    "name": plant.name(lang),
                    "bed": bed.name if bed else "",
                    "until": max(tl.harvest_end, today).isoformat(),
                    "group": group,
                    "keep": _tips(group, lang)[0],
                }
            )
    ready.sort(key=lambda r: r["until"])

    people = max(1, data.settings.resources.household_size)
    week_ago = today - timedelta(days=7)
    picked: dict[str, float] = {}
    for h in data.harvest_log:
        if week_ago < h.day <= today and h.kg > 0:
            picked[h.plant_id] = picked.get(h.plant_id, 0.0) + h.kg
    surplus = []
    for plant_id, kg in sorted(picked.items(), key=lambda kv: -kv[1]):
        plant = db.get(plant_id)
        group = kitchen_group(plant)
        need = WEEKLY_KG[group] * people
        if need > 0 and kg >= SURPLUS_FACTOR * need:
            surplus.append(
                {
                    "plant_id": plant_id,
                    "name": plant.name(lang) if plant else plant_id,
                    "kg_week": round(kg, 1),
                    "need_week": round(need, 1),
                    "group": group,
                    "ideas": _tips(group, lang)[1],
                }
            )
    return {"ready": ready, "surplus": surplus, "picked_week_kg": round(sum(picked.values()), 1), "people": people}


@dataclass(slots=True)
class CropValue:
    plant_id: str
    name: str
    kg: float
    price: float
    value: float


def economics(data: GardenData, db: PlantDatabase, season: int, lang: str = "en") -> dict[str, Any]:
    """The season's harvest at shop prices against what the garden cost."""
    eco = data.settings.economy
    crops: list[CropValue] = []
    for plant_id, crop in harvest_summary(data, season).items():
        plant = db.get(plant_id)
        price = price_per_kg(plant_id, plant, eco.prices)
        crops.append(
            CropValue(plant_id, plant.name(lang) if plant else plant_id, crop.kg, price, round(crop.kg * price, 2))
        )
    crops.sort(key=lambda c: -c.value)
    by_category: dict[str, float] = {}
    for e in data.expenses:
        if e.season == season:
            by_category[e.category] = round(by_category.get(e.category, 0.0) + e.amount, 2)
    water_m3 = _season_water_m3(data, season)
    water_cost = round(water_m3 * eco.water_price_m3, 2) if water_m3 is not None else 0.0
    harvest_value = round(sum(c.value for c in crops), 2)
    total_cost = round(sum(by_category.values()) + water_cost, 2)
    return {
        "season": season,
        "currency": eco.currency,
        "harvest_value": harvest_value,
        "harvest_kg": round(sum(c.kg for c in crops), 1),
        "crops": [
            {"plant_id": c.plant_id, "name": c.name, "kg": round(c.kg, 1), "price": c.price, "value": c.value}
            for c in crops
        ],
        "expenses": by_category,
        "water_m3": water_m3,
        "water_cost": water_cost,
        "total_cost": total_cost,
        "balance": round(harvest_value - total_cost, 2),
    }


def _season_water_m3(data: GardenData, season: int) -> float | None:
    """Meter use over the growing season (July-June in the southern hemisphere, like the harvest)."""
    region = data.settings.region
    readings = sorted(
        (r for r in data.water_log if r.meter_m3 is not None and season_for_date(region, r.day) == season),
        key=lambda r: r.day,
    )
    if len(readings) < 2:
        return None
    # the sum of the rises: a replaced or reset meter (a drop) does not wipe out the season
    rises = (b.meter_m3 - a.meter_m3 for a, b in pairwise(readings))  # type: ignore[operator]
    return round(sum(d for d in rises if d > 0), 2)
