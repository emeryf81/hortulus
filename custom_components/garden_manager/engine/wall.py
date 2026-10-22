"""The wall screen's blocks and the bits of reading it can show.

The wall screen (kiosk) is a grid of blocks the gardener arranges: which blocks, in which order,
how wide. The layout lives in the garden's settings so a tablet in the kitchen and the panel show
the same screen. The reading blocks (a weather saying, an organic gardening fact, a recipe tip)
are Dutch only for now; in other languages the wall keeps its fixed default layout.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any

# Every block the wall knows, with its default width (1–4 columns of a 4-column grid).
BLOCKS: dict[str, int] = {
    "clock": 2,
    "weather_now": 2,
    "forecast": 2,
    "radar": 1,
    "tasks": 2,
    "agenda": 2,
    "moisture": 2,
    "watering": 1,
    "harvest_ready": 1,
    "sow_week": 1,
    "pests": 2,
    "garden": 1,
    "sun": 1,
    "saying": 1,
    "fact": 2,
    "eco_month": 2,
    "recipe": 2,
    "slogan": 2,
}
# The wall as it always was: clock and weather on top, today's tasks next to the forecast and moisture.
DEFAULT_LAYOUT: tuple[tuple[str, int], ...] = (
    ("clock", 2), ("weather_now", 2), ("tasks", 2), ("forecast", 2), ("moisture", 2),
)  # fmt: skip
MAX_BLOCKS = 24


def default_layout() -> list[dict[str, Any]]:
    return [{"id": block, "w": width} for block, width in DEFAULT_LAYOUT]


def clean_layout(raw: Any) -> list[dict[str, Any]] | None:
    """A layout from the panel, made safe: known blocks only, each once, widths 1–4. None = default."""
    if raw is None:
        return None
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("layout must be a list")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        block = item.get("id")
        if not isinstance(block, str) or block not in BLOCKS or block in seen:
            continue
        try:
            width = int(item.get("w", BLOCKS[block]))
        except (TypeError, ValueError, OverflowError):
            width = BLOCKS[block]
        out.append({"id": block, "w": max(1, min(4, width))})
        seen.add(block)
        if len(out) >= MAX_BLOCKS:
            break
    return out


def _of_the_day(items: Sequence[str], day: date, salt: int = 0) -> str:
    return items[(day.toordinal() + salt) % len(items)] if items else ""


def saying(day: date, south: bool = False) -> str:
    """A Dutch folk weather saying for the month (the northern month, shifted in the south)."""
    month = ((day.month + 5) % 12) + 1 if south else day.month
    return _of_the_day(SAYINGS[month], day)


def fact(day: date) -> str:
    """An organic gardening fact, a different one every day."""
    return _of_the_day(FACTS, day, salt=7)


def recipe_tip(recipes: Iterable[Mapping[str, Any]], day: date) -> dict[str, Any] | None:
    """One of the suggested recipes for what the garden gives now, a different one every day."""
    pool = [r for r in recipes if r.get("title")]
    if not pool:
        return None
    r = pool[day.toordinal() % len(pool)]
    produce = [
        str(i["name"])
        for i in r.get("ingredients", [])
        if isinstance(i, Mapping) and i.get("group") == "garden" and i.get("name")
    ]
    return {"title": r["title"], "minutes": r.get("minutes"), "produce": produce, "course": r.get("course_name")}


# --------------------------------------------------------------------------- #
# Dutch texts
# --------------------------------------------------------------------------- #
SAYINGS: dict[int, list[str]] = {
    1: [
        "Januari koud en wit, maakt de boeren blij.",
        "Als de dagen beginnen te lengen, begint de winter te strengen.",
        "Is januari nat, dan blijft het vat leeg.",
        "Een warme januari, een koude lente.",
    ],
    2: [
        "Februari met regen maakt de boer verlegen.",
        "Lichtmis helder en klaar geeft een goed en vruchtbaar jaar.",
        "Sneeuw in februari is goede mest.",
        "Schijnt op Lichtmis de zon, dan is de winter nog niet om.",
    ],
    3: [
        "Maart roert zijn staart.",
        "Een droge maart en een natte april, dat is de boer naar zijn wil.",
        "Zoveel nevels in maart, zoveel regens in de zomer.",
        "Komt maart binnen als een lam, dan gaat hij weg als een leeuw.",
    ],
    4: [
        "April doet wat hij wil.",
        "Een natte april belooft veel vruchten.",
        "Aprilletje zoet geeft nog wel eens een witte hoed.",
        "Is april droog en schraal, dan groeit er weinig in de stal.",
    ],
    5: [
        "Na de IJsheiligen gaan de tere planten naar buiten.",
        "Mei koel en nat vult de schuur en het vat.",
        "Een zwerm bijen in mei is een voer hooi waard.",
        "Een koude mei is goed voor koren en hooi.",
    ],
    6: [
        "Regent het op Sint-Medardus, dan regent het nog veertig dagen.",
        "Zonneschijn in juni maakt het fruit zoet.",
        "Een droge juni brengt een goede oogst.",
        "Juni warm en klaar, het beste van het jaar.",
    ],
    7: [
        "Wat juli en augustus niet koken, laat september ongebraden.",
        "Juli warm en droog, de oogst gaat hoog.",
        "Hondsdagen helder en klaar beloven een goed jaar.",
        "Een julizon brandt de tuin het snelst droog.",
    ],
    8: [
        "Augustus rijp, september pluk.",
        "Wat augustus niet kookt, kan september niet braden.",
        "Dauw in augustus: het mooie weer houdt aan.",
        "Is augustus warm, dan wordt de winter lang en wit.",
    ],
    9: [
        "Een warme september maakt de appels zoet.",
        "Septemberregen is voor het zaad een zegen.",
        "September schoon, de herfst lacht.",
        "Donder in september voorspelt veel sneeuw in de winter.",
    ],
    10: [
        "Oktober ruw, januari zacht.",
        "Blijven de bladeren lang aan de bomen, dan volgt een strenge winter.",
        "Oktober vol regen vult kelder en schuur.",
        "Valt het blad vroeg, de winter komt vroeg genoeg.",
    ],
    11: [
        "Sint-Maarten helder en klaar, dan wordt de winter hard en zwaar.",
        "Dansen in november de muggen, dan is de winter niet ver.",
        "November nat, de lente zat.",
        "Donder in november voorspelt een vruchtbaar jaar.",
    ],
    12: [
        "December koud met sneeuw geeft koren voor een eeuw.",
        "Groene kerst, witte Pasen.",
        "Veel sneeuw in december belooft een vruchtbaar jaar.",
        "Is december zacht, dan wordt de winter streng verwacht.",
    ],
}

FACTS: list[str] = [
    "Een handvol gezonde tuingrond bevat meer levende wezens dan er mensen op aarde zijn.",
    "Regenwormen trekken dode bladeren de grond in en maken er in een jaar tot enkele kilo's wormmest per m² van.",
    "Goudsbloemen tussen de tomaten lokken zweefvliegen, en hun larven eten bladluizen.",
    "Eén lieveheersbeestjeslarve eet in haar leven honderden bladluizen.",
    "Een laagje mulch van gras of stro houdt de grond vochtig en voedt het bodemleven.",
    "Brandnetelgier is een gratis stikstofmest: verdund 1 op 10 geef je hem aan bladgroenten.",
    "Smeerwortelbladeren zijn rijk aan kalium: een goede gier voor tomaten en bessen.",
    "Vlinderbloemigen zoals bonen en erwten halen met hun wortelknolletjes stikstof uit de lucht.",
    "Laat de wortels van bonen na de oogst in de grond zitten: de stikstof blijft dan voor de volgende teelt.",
    "Een groenbemester zoals phacelia in de herfst beschermt de grond en lokt bijen in bloei.",
    "Wisselteelt in vier vakken voorkomt dat ziektes en plagen zich in de grond ophopen.",
    "Uien of prei tussen de wortelen verwarren de wortelvlieg met hun geur.",
    "Een egelhuis in een rustige hoek levert gratis slakkenbestrijders op.",
    "Kikkers en padden in een vijver eten slakken en insecten: een kleine poel helpt al.",
    "Gieten 's ochtends is beter dan 's avonds: het blad droogt snel en slakken hebben minder kans.",
    "Eén keer flink gieten is beter dan elke dag een beetje: de wortels groeien dan dieper.",
    "Compost is klaar als hij donker, kruimelig en naar bosgrond ruikt.",
    "Een goede composthoop heeft ongeveer twee delen bruin (blad, karton) op één deel groen (gras, keukenafval).",
    "Koffiedik in de compost voedt de wormen; strooi het niet in dikke lagen op de grond.",
    "Insectenhotels met holle stengels geven solitaire bijen een plek om eitjes te leggen.",
    "Laat een paar groenten doorschieten: hun bloemen voeden bestuivers en je wint eigen zaad.",
    "Eigen zaad van bonen, tomaten en sla is makkelijk te winnen: ze bestuiven zichzelf meestal.",
    "Dille en venkel lokken sluipwespen die rupsen en bladluizen parasiteren.",
    "Oost-Indische kers is een vangplant: bladluizen en koolwitjes gaan er liever op zitten dan op de kool.",
    "Een insectengaas houdt koolvlieg, wortelvlieg en preimot tegen zonder één druppel bestrijdingsmiddel.",
    "Bladluizen op jonge scheuten spuit je weg met een harde waterstraal; de vijanden doen de rest.",
    "Slakken houden van vochtige schuilplekken: leg een plank neer en raap ze 's ochtends op.",
    "Bodem met veel organische stof houdt tot het tienvoudige van zijn gewicht aan water vast.",
    "Spitten verstoort het bodemleven; losmaken met een grelinette of riek houdt de lagen intact.",
    "Een bloemenrand met inheemse planten trekt tot vijf keer meer nuttige insecten aan.",
    "Tomaten en basilicum zijn goede buren: basilicum houdt witte vlieg op afstand.",
    "Bieslook onder fruitbomen zou schurft helpen voorkomen en trekt bijen aan als hij bloeit.",
    "Een paar rotte appels in de herfst laten liggen geeft vogels en egels wintervoer.",
    "Grasmaaisel droog laten worden voor je het als mulch gebruikt: dan gaat het niet rotten of broeien.",
    "Regenwater uit de ton is zacht en op temperatuur: planten verkiezen het boven leidingwater.",
    "Een dikke laag blad in de herfst over lege bedden beschermt de grond tegen slempen.",
    "Mulch van houtsnippers hoort bij vaste planten en paden, niet bij jonge groenten.",
    "Wilde bijen bestuiven veel fruit beter dan honingbijen: geef ze bloemen van maart tot oktober.",
    "Vogels eten in het broedseizoen vooral rupsen: een nestkast in de moestuin loont.",
    "Groenten die je 's ochtends oogst blijven langer knapperig dan wat je in de middagzon plukt.",
]
