"""Knowledge base for the Q&A assistant (EN / NL / FR).

``PROBLEMS``: per problem the likely causes, what to do now, ecological
home remedies and prevention.  ``PESTS`` / ``DISEASES``: recognition and
eco control per pest or disease id used in the plant database.  The Q&A
engine combines these with live data (sensors, forecast, plan, tasks).
"""

from __future__ import annotations

KB = dict[str, dict[str, list[str]]]


def _e(causes=(), actions=(), remedies=(), prevention=()) -> dict[str, list[str]]:
    return {
        "causes": list(causes),
        "actions": list(actions),
        "remedies": list(remedies),
        "prevention": list(prevention),
    }


PROBLEMS: dict[str, dict[str, dict[str, list[str]]]] = {
    "growth": {
        "en": _e(
            [
                "Soil too cold for the crop (check soil temperature).",
                "Too little light: shade, short days or a dirty greenhouse roof.",
                "Hungry soil - especially nitrogen for leafy crops.",
                "Drought stress or waterlogged, airless soil.",
                "Root damage (wireworm, cabbage root fly) or a crowded spot.",
            ],
            [
                "Compare soil temperature with the crop's minimum; cover with fleece to warm up.",
                "Feed hungry crops with diluted nettle feed (1:10) every 2 weeks.",
                "Water deeply once or twice a week instead of a little every day.",
                "Thin crowded seedlings to the right spacing.",
            ],
            [
                "Nettle feed for nitrogen, comfrey feed for fruiting crops.",
                "Compost tea as a gentle tonic.",
                "A dark mulch or black fleece warms the soil in spring.",
            ],
            [
                "Sow at the right soil temperature, not by the calendar.",
                "Add 3-5 l compost per m² every year.",
                "Keep the greenhouse glass clean (10-20 % more light).",
            ],
        ),
        "nl": _e(
            [
                "Grond te koud voor het gewas (kijk naar de bodemtemperatuur).",
                "Te weinig licht: schaduw, korte dagen of een vuil serredak.",
                "Hongerige grond - vooral stikstof voor bladgewassen.",
                "Droogtestress of te natte, luchtarme grond.",
                "Wortelschade (ritnaald, koolvlieg) of te dicht op elkaar.",
            ],
            [
                "Vergelijk de bodemtemperatuur met het minimum van het gewas; leg vliesdoek om op te warmen.",
                "Geef hongerige gewassen om de 2 weken verdunde brandnetelgier (1:10).",
                "Geef één à twee keer per week grondig water in plaats van dagelijks een beetje.",
                "Dun te dichte zaailingen uit tot de juiste afstand.",
            ],
            [
                "Brandnetelgier voor stikstof, smeerwortelgier voor vruchtgewassen.",
                "Compostthee als zachte opkikker.",
                "Een donkere mulch of zwart vlies verwarmt de grond in het voorjaar.",
            ],
            [
                "Zaai bij de juiste bodemtemperatuur, niet volgens de kalender.",
                "Geef elk jaar 3-5 l compost per m².",
                "Hou het serreglas proper (10-20 % meer licht).",
            ],
        ),
    },
    "yellow_leaves": {
        "en": _e(
            [
                "Old lower leaves yellowing is normal ageing.",
                "Nitrogen shortage: whole plant pale, oldest leaves first.",
                "Too wet: roots suffocate (yellow + limp).",
                "Magnesium shortage (tomato): yellow between green veins.",
                "Cold nights or a sudden change (just planted out).",
            ],
            [
                "Remove yellow leaves at the bottom (better airflow).",
                "Feed nettle feed 1:10; for tomatoes comfrey feed.",
                "Check soil moisture with a finger 5 cm deep before watering.",
                "Magnesium: Epsom salt 20 g per 10 l water on the soil.",
            ],
            [
                "Nettle feed (nitrogen).",
                "Epsom salt (magnesium sulphate) for tomato and pepper.",
                "Coffee grounds and compost as slow feed.",
            ],
            ["Good drainage: raised beds on heavy soil.", "Regular compost; rotate crops."],
        ),
        "nl": _e(
            [
                "Vergelende oude onderste bladeren is normale veroudering.",
                "Stikstoftekort: hele plant bleek, oudste bladeren eerst.",
                "Te nat: de wortels stikken (geel + slap).",
                "Magnesiumtekort (tomaat): geel tussen groene nerven.",
                "Koude nachten of een plotse verandering (net uitgeplant).",
            ],
            [
                "Haal gele bladeren onderaan weg (betere luchtcirculatie).",
                "Geef brandnetelgier 1:10; voor tomaten smeerwortelgier.",
                "Voel 5 cm diep met een vinger voor je water geeft.",
                "Magnesium: Epsomzout 20 g per 10 l water op de grond.",
            ],
            [
                "Brandnetelgier (stikstof).",
                "Epsomzout (magnesiumsulfaat) voor tomaat en paprika.",
                "Koffiedik en compost als trage voeding.",
            ],
            ["Goede drainage: verhoogde bedden op zware grond.", "Regelmatig compost; wisselteelt."],
        ),
    },
    "wilting": {
        "en": _e(
            [
                "Drought - the most common cause, especially in pots and greenhouses.",
                "Midday heat: leaves droop but recover in the evening (normal).",
                "Root rot or waterlogging.",
                "Wilt diseases (verticillium, fusarium) or root pests (wireworm, vine weevil).",
                "Slugs or cutworms gnawing the stem at soil level.",
            ],
            [
                "Water early in the morning, deeply at the base.",
                "Shade the plants at midday during heat.",
                "If the plant stays limp in moist soil in the evening: check roots and stem base.",
                "Remove plants with brown vascular tissue (wilt disease); don't compost.",
            ],
            [
                "Shade with an old net curtain or a double layer of fleece.",
                "Mulch 5-8 cm to keep the soil cool and moist.",
                "Sunk bottle or olla next to thirsty plants.",
            ],
            ["Mulch and deep watering.", "Grafted tomatoes/cucumbers on resistant rootstocks.", "Crop rotation."],
        ),
        "nl": _e(
            [
                "Droogte - de meest voorkomende oorzaak, zeker in potten en serres.",
                "Middaghitte: bladeren hangen maar herstellen 's avonds (normaal).",
                "Wortelrot of te natte grond.",
                "Verwelkingsziekten (verticillium, fusarium) of wortelplagen (ritnaald, taxuskever).",
                "Slakken of aardrupsen die de stengel op grondhoogte aanvreten.",
            ],
            [
                "Geef 's ochtends vroeg water, grondig aan de voet.",
                "Geef de planten 's middags schaduw bij hitte.",
                "Blijft de plant 's avonds slap in vochtige grond: controleer wortels en stengelvoet.",
                "Verwijder planten met bruine vaatbundels (verwelkingsziekte); niet composteren.",
            ],
            [
                "Schaduw met een oud vitragegordijn of dubbel vliesdoek.",
                "Mulch 5-8 cm om de grond koel en vochtig te houden.",
                "Ingegraven fles of olla naast dorstige planten.",
            ],
            ["Mulch en grondig water geven.", "Geënte tomaten/komkommers op resistente onderstam.", "Wisselteelt."],
        ),
    },
    "no_fruit": {
        "en": _e(
            [
                "No pollinators: cold, rain, or no flowers nearby.",
                "Pollination partner missing (apple, pear, sweet cherry, blueberry, kiwi berry).",
                "Too hot (>32 °C) or too cold at flowering: flowers drop.",
                "Too much nitrogen: lots of leaves, few flowers.",
                "Young tree not bearing yet, or frost on the blossom.",
            ],
            [
                "Hand-pollinate: brush male onto female flowers (cucurbits), shake tomato trusses mid-morning.",
                "Plant a second variety as pollinator.",
                "Shade and ventilate the greenhouse on hot days.",
                "Switch to a potassium feed (comfrey).",
            ],
            [
                "Comfrey feed (potassium) for flowers and fruit.",
                "Borage, phacelia and calendula nearby draw bees.",
                "Fleece over early blossom on frosty nights.",
            ],
            [
                "Flowers in every bed; a bee hotel.",
                "Never spray during bloom.",
                "Varieties suited to the climate (parthenocarpic cucumbers under glass).",
            ],
        ),
        "nl": _e(
            [
                "Geen bestuivers: koud, regen of geen bloemen in de buurt.",
                "Bestuivingspartner ontbreekt (appel, peer, zoete kers, blauwe bes, kiwibes).",
                "Te heet (>32 °C) of te koud tijdens de bloei: bloemen vallen af.",
                "Te veel stikstof: veel blad, weinig bloemen.",
                "Jonge boom draagt nog niet, of vorst op de bloesem.",
            ],
            [
                "Bestuif met de hand: mannelijke op vrouwelijke bloemen wrijven (pompoenachtigen), tomatentrossen 's ochtends schudden.",
                "Plant een tweede ras als bestuiver.",
                "Geef schaduw en verlucht de serre op hete dagen.",
                "Schakel over op kaliumrijke voeding (smeerwortel).",
            ],
            [
                "Smeerwortelgier (kalium) voor bloemen en vruchten.",
                "Bernagie, phacelia en goudsbloem in de buurt lokken bijen.",
                "Vliesdoek over vroege bloesem bij vriesnachten.",
            ],
            [
                "Bloemen in elk bed; een bijenhotel.",
                "Nooit spuiten tijdens de bloei.",
                "Rassen die bij het klimaat passen (parthenocarpe komkommers onder glas).",
            ],
        ),
    },
    "bolting": {
        "en": _e(
            [
                "Long days and heat (lettuce, spinach, coriander, rocket, pak choi).",
                "Cold spell after sowing (beetroot, celery, onions from sets).",
                "Drought stress.",
                "Sown too early or a variety not suited to the season.",
            ],
            [
                "Harvest now - bolting plants turn bitter.",
                "Sow again in shade or late summer.",
                "Pull and compost, or leave a few to flower for insects.",
            ],
            ["Shade cloth or an old curtain over salads in summer.", "Water regularly."],
            [
                "Sow summer salads every 2-3 weeks in small amounts.",
                "Choose bolt-resistant varieties; spinach & coriander in spring and autumn.",
            ],
        ),
        "nl": _e(
            [
                "Lange dagen en hitte (sla, spinazie, koriander, rucola, paksoi).",
                "Koude periode na het zaaien (rode biet, selder, plantuitjes).",
                "Droogtestress.",
                "Te vroeg gezaaid of een ras dat niet past bij het seizoen.",
            ],
            [
                "Oogst nu - doorgeschoten planten worden bitter.",
                "Zaai opnieuw in de schaduw of nazomer.",
                "Uittrekken en composteren, of een paar laten bloeien voor insecten.",
            ],
            ["Schaduwdoek of een oud gordijn over slaatjes in de zomer.", "Regelmatig water geven."],
            [
                "Zaai zomerslaatjes om de 2-3 weken in kleine hoeveelheden.",
                "Kies doorschietresistente rassen; spinazie & koriander in voor- en najaar.",
            ],
        ),
    },
    "pests": {
        "en": _e(
            [
                "Pests strike weakened plants first (drought, too much nitrogen).",
                "No natural enemies yet (early season, sprayed garden).",
                "No physical barrier on vulnerable crops.",
            ],
            [
                "Identify the pest first (look under the leaves, at night with a torch).",
                "Remove by hand or with a strong water jet.",
                "Cover vulnerable crops with insect mesh.",
            ],
            [
                "Soft soap 20 g/l against aphids and whitefly.",
                "Beer traps and evening collecting against slugs.",
                "Yellow sticky cards in the greenhouse.",
            ],
            [
                "Flowers for beneficials (hoverflies, lacewings).",
                "Mixed planting and rotation.",
                "Mesh straight after sowing or planting.",
            ],
        ),
        "nl": _e(
            [
                "Plagen vallen eerst verzwakte planten aan (droogte, te veel stikstof).",
                "Nog geen natuurlijke vijanden (vroeg in het seizoen, bespoten tuin).",
                "Geen fysieke barrière op gevoelige gewassen.",
            ],
            [
                "Bepaal eerst welke plaag (onder de bladeren kijken, 's avonds met een zaklamp).",
                "Verwijder met de hand of met een krachtige waterstraal.",
                "Dek gevoelige gewassen af met insectengaas.",
            ],
            [
                "Zachte zeep 20 g/l tegen bladluis en witte vlieg.",
                "Biervallen en 's avonds rapen tegen slakken.",
                "Gele vangplaten in de serre.",
            ],
            [
                "Bloemen voor nuttige insecten (zweefvliegen, gaasvliegen).",
                "Gemengde teelt en wisselteelt.",
                "Gaas meteen na zaaien of planten.",
            ],
        ),
    },
    "disease": {
        "en": _e(
            [
                "Wet leaves for many hours (rain, evening watering, condensation in the greenhouse).",
                "Crowded plants, still air.",
                "Infected soil or plant debris from last year.",
                "Susceptible variety.",
            ],
            [
                "Remove infected leaves straight away (bin, not compost).",
                "Water in the morning at the base only.",
                "Ventilate the greenhouse, especially in the morning.",
                "Give plants more space.",
            ],
            [
                "Milk spray 1:9 against powdery mildew.",
                "Horsetail tea as a preventive tonic.",
                "Garlic tea against fungi (1:5).",
            ],
            ["Resistant varieties.", "Rotation (3-4 years).", "Clean up and disinfect the greenhouse in autumn."],
        ),
        "nl": _e(
            [
                "Bladeren lang nat (regen, 's avonds water geven, condens in de serre).",
                "Te dicht op elkaar, stilstaande lucht.",
                "Besmette grond of plantenresten van vorig jaar.",
                "Vatbaar ras.",
            ],
            [
                "Verwijder aangetaste bladeren meteen (restafval, niet de compost).",
                "Geef 's ochtends water, alleen aan de voet.",
                "Verlucht de serre, vooral 's ochtends.",
                "Geef de planten meer ruimte.",
            ],
            [
                "Melkspray 1:9 tegen echte meeldauw.",
                "Heermoesthee als preventieve versterker.",
                "Knoflookthee tegen schimmels (1:5).",
            ],
            ["Resistente rassen.", "Wisselteelt (3-4 jaar).", "De serre in het najaar opruimen en ontsmetten."],
        ),
    },
    "slugs": {
        "en": _e(
            ["Mild, wet weather; mulch and boards give hiding places.", "Young seedlings planted out too small."],
            [
                "Collect at dusk and after rain.",
                "Beer traps (rim 2 cm above soil).",
                "Raise sturdy plants in pots before planting out.",
            ],
            [
                "Ring of wood ash, grit or crushed eggshell (only works while dry).",
                "A board or cabbage leaf as a trap.",
                "Coffee grounds around seedlings.",
            ],
            [
                "Welcome hedgehogs, toads, thrushes and ground beetles.",
                "Water in the morning, not in the evening.",
                "Keep bed edges short-mown.",
            ],
        ),
        "nl": _e(
            ["Zacht, nat weer; mulch en planken bieden schuilplaatsen.", "Te kleine zaailingen uitgeplant."],
            [
                "Raap bij schemering en na regen.",
                "Biervallen (rand 2 cm boven de grond).",
                "Kweek stevige planten in potjes voor je uitplant.",
            ],
            [
                "Ring van houtas, grit of gemalen eierschalen (werkt enkel als het droog blijft).",
                "Een plank of koolblad als val.",
                "Koffiedik rond zaailingen.",
            ],
            [
                "Verwelkom egels, padden, lijsters en loopkevers.",
                "Geef 's ochtends water, niet 's avonds.",
                "Hou randen rond de bedden kort gemaaid.",
            ],
        ),
    },
    "too_hot": {
        "en": _e(
            ["Sun on the glass with closed vents.", "No shading in summer.", "Dry air: spider mite and flower drop."],
            [
                "Open all vents and the door early in the morning.",
                "Put up shading (net, paint, old curtain).",
                "Damp down the floor and paths at midday.",
                "Water in the morning.",
            ],
            [
                "A bucket of water as thermal mass.",
                "Old bed sheet or net curtain as shade cloth.",
                "Whitewash (chalk + water) as shade paint.",
            ],
            ["Automatic vent openers.", "Shading from mid-spring.", "A fan for air movement."],
        ),
        "nl": _e(
            ["Zon op het glas met gesloten ramen.", "Geen schaduw in de zomer.", "Droge lucht: spint en bloemval."],
            [
                "Zet 's ochtends vroeg alle ramen en de deur open.",
                "Breng schaduw aan (doek, kalk, oud gordijn).",
                "Maak 's middags de vloer en paden nat.",
                "Geef 's ochtends water.",
            ],
            [
                "Een emmer water als warmtebuffer.",
                "Oud laken of vitrage als schaduwdoek.",
                "Witkalk (krijt + water) als schaduwkalk.",
            ],
            ["Automatische raamopeners.", "Schaduw vanaf half voorjaar.", "Een ventilator voor luchtbeweging."],
        ),
    },
    "frost": {
        "en": _e(
            [
                "Clear, still night after a cold day.",
                "Tender crops planted out before the last frost date.",
                "Low spots collect cold air.",
            ],
            [
                "Cover tender crops with fleece (double layer) before dusk.",
                "Close the greenhouse in time; water butts inside buffer heat.",
                "Bring pots indoors.",
                "Water the soil in the afternoon: moist soil releases more heat at night.",
            ],
            [
                "Old bed sheets, cardboard boxes or upturned buckets over plants.",
                "Bubble wrap on the greenhouse glass.",
                "Bottles of warm water between plants under fleece.",
            ],
            [
                "Plant out tender crops after the last frost date (Hortulus waits for you).",
                "Keep fleece ready in autumn and spring.",
            ],
        ),
        "nl": _e(
            [
                "Heldere, windstille nacht na een koude dag.",
                "Gevoelige gewassen uitgeplant voor de laatste vorstdatum.",
                "Lage plekken verzamelen koude lucht.",
            ],
            [
                "Dek gevoelige gewassen voor de schemering af met vliesdoek (dubbel).",
                "Sluit de serre op tijd; regentonnen binnen bufferen warmte.",
                "Zet potten binnen.",
                "Geef 's namiddags water: vochtige grond geeft 's nachts meer warmte af.",
            ],
            [
                "Oude lakens, kartonnen dozen of omgekeerde emmers over de planten.",
                "Noppenfolie tegen het serreglas.",
                "Flessen warm water tussen de planten onder vliesdoek.",
            ],
            [
                "Plant gevoelige gewassen pas uit na de laatste vorstdatum (Hortulus wacht voor je).",
                "Hou vliesdoek klaar in najaar en voorjaar.",
            ],
        ),
    },
    "soil": {
        "en": _e(
            [
                "Heavy clay: wet and cold in spring, cracks in summer.",
                "Sandy soil: dries out and washes out nutrients.",
                "Compacted by walking on wet beds.",
            ],
            [
                "Add 3-5 l compost per m² every year.",
                "Never walk on beds; work from paths or a plank.",
                "Loosen with a fork without turning (broadfork).",
            ],
            [
                "Leaf mould and grass clippings as mulch.",
                "Green manure in every empty bed.",
                "Wood ash for potassium (not for potatoes).",
            ],
            ["Permanent beds and paths.", "Keep the soil covered all year.", "A soil test every 3 years (pH 6.5-7)."],
        ),
        "nl": _e(
            [
                "Zware klei: nat en koud in het voorjaar, scheuren in de zomer.",
                "Zandgrond: droogt uit en spoelt voedingsstoffen weg.",
                "Verdicht door op natte bedden te lopen.",
            ],
            [
                "Geef elk jaar 3-5 l compost per m².",
                "Loop nooit op de bedden; werk vanaf de paden of een plank.",
                "Maak los met een riek zonder te keren (grelinette).",
            ],
            [
                "Bladaarde en grasmaaisel als mulch.",
                "Groenbemester in elk leeg bed.",
                "Houtas voor kalium (niet bij aardappel).",
            ],
            ["Vaste bedden en paden.", "Hou de grond het hele jaar bedekt.", "Om de 3 jaar een bodemstaal (pH 6,5-7)."],
        ),
    },
}
# Problems that reuse another entry.
PROBLEMS["too_cold"] = PROBLEMS["frost"]

PESTS: dict[str, dict[str, str]] = {
    "aphids": {
        "en": "Aphids: water jet, soft soap 20 g/l, ladybirds and hoverflies; less nitrogen.",
        "nl": "Bladluis: waterstraal, zachte zeep 20 g/l, lieveheersbeestjes en zweefvliegen; minder stikstof.",
    },
    "slugs": {
        "en": "Slugs: collect at dusk, beer traps, grit or wood-ash rings, hedgehogs.",
        "nl": "Slakken: 's avonds rapen, biervallen, ringen van grit of houtas, egels.",
    },
    "whitefly": {
        "en": "Whitefly: yellow cards, Encarsia wasps, French marigolds, soft soap.",
        "nl": "Witte vlieg: gele vangplaten, sluipwesp Encarsia, Afrikaantjes, zachte zeep.",
    },
    "red_spider_mite": {
        "en": "Spider mite: raise humidity (damp the floor), predatory mite Phytoseiulus.",
        "nl": "Spint: luchtvochtigheid verhogen (vloer natmaken), roofmijt Phytoseiulus.",
    },
    "cabbage_white": {
        "en": "Cabbage white: insect mesh, pick off eggs and caterpillars, nasturtium as trap crop.",
        "nl": "Koolwitje: insectengaas, eitjes en rupsen weghalen, Oost-Indische kers als vangplant.",
    },
    "cabbage_root_fly": {
        "en": "Cabbage root fly: mesh or a cardboard collar around the stem.",
        "nl": "Koolvlieg: gaas of een kartonnen kraag rond de stengel.",
    },
    "carrot_fly": {
        "en": "Carrot fly: mesh or a 60 cm fleece fence, onions alongside, thin in the evening.",
        "nl": "Wortelvlieg: gaas of een vliesscherm van 60 cm, uien ernaast, 's avonds dunnen.",
    },
    "onion_fly": {
        "en": "Onion fly: mesh, carrots alongside, sets rather than seed.",
        "nl": "Uienvlieg: gaas, wortelen ernaast, plantuitjes i.p.v. zaad.",
    },
    "leek_moth": {
        "en": "Leek moth: insect mesh from May; remove affected leaves.",
        "nl": "Preimot: insectengaas vanaf mei; aangetaste bladeren weg.",
    },
    "flea_beetle": {
        "en": "Flea beetle: keep the soil moist, fleece, sow when growing fast.",
        "nl": "Aardvlo: grond vochtig houden, vliesdoek, zaaien als het snel groeit.",
    },
    "colorado_beetle": {
        "en": "Colorado beetle: collect beetles and orange egg clusters under the leaves.",
        "nl": "Coloradokever: kevers en oranje eitjes onder de bladeren rapen.",
    },
    "black_bean_aphid": {
        "en": "Black bean aphid: pinch out the tops of broad beans once pods set.",
        "nl": "Zwarte bonenluis: top de tuinbonen zodra de eerste peulen zetten.",
    },
    "codling_moth": {
        "en": "Codling moth: cardboard band round the trunk from June, nest boxes for tits.",
        "nl": "Fruitmot: golfkartonband rond de stam vanaf juni, nestkastjes voor mezen.",
    },
    "winter_moth": {
        "en": "Winter moth: grease bands at 1 m height from October to March.",
        "nl": "Wintervlinder: lijmbanden op 1 m van oktober tot maart.",
    },
    "birds": {
        "en": "Birds: fine net, pegged down, a few weeks before ripening.",
        "nl": "Vogels: fijn net, vastgepind, enkele weken voor de rijping.",
    },
    "gooseberry_sawfly": {
        "en": "Sawfly: check the centre of the bush from April and pick off larvae.",
        "nl": "Bladwesp: vanaf april het hart van de struik nakijken en larven weghalen.",
    },
    "spotted_wing_drosophila": {
        "en": "Drosophila suzukii: pick daily, remove overripe fruit, fine mesh.",
        "nl": "Drosophila suzukii: dagelijks plukken, overrijp fruit weg, fijn gaas.",
    },
    "wireworm": {
        "en": "Wireworm: potato pieces on a stick as a trap; not straight after grass.",
        "nl": "Ritnaald: stukjes aardappel op een stokje als val; niet meteen na grasland.",
    },
    "thrips": {
        "en": "Thrips: blue sticky cards, raise humidity.",
        "nl": "Trips: blauwe vangplaten, luchtvochtigheid verhogen.",
    },
}
DISEASES: dict[str, dict[str, str]] = {
    "late_blight": {
        "en": "Late blight: roof over tomatoes, water the soil, remove lower leaves, resistant varieties; bin infected plants.",
        "nl": "Phytophthora: overkapping boven tomaten, water op de grond, onderste bladeren weg, resistente rassen; zieke planten in de restafval.",
    },
    "powdery_mildew": {
        "en": "Powdery mildew: milk spray 1:9, even watering, airy spacing.",
        "nl": "Echte meeldauw: melkspray 1:9, regelmatig water, luchtige teelt.",
    },
    "downy_mildew": {
        "en": "Downy mildew: water in the morning, ventilate, remove spotted leaves.",
        "nl": "Valse meeldauw: 's ochtends water geven, verluchten, gevlekte bladeren weg.",
    },
    "botrytis": {
        "en": "Grey mould: ventilate, remove dead tissue and rotting fruit, avoid wounds.",
        "nl": "Grauwe schimmel: verluchten, dood weefsel en rottende vruchten weg, wonden vermijden.",
    },
    "blossom_end_rot": {
        "en": "Blossom-end rot: a calcium uptake problem from uneven watering - water regularly, mulch.",
        "nl": "Neusrot: kalkopnameprobleem door onregelmatig water geven - regelmatig gieten, mulchen.",
    },
    "clubroot": {
        "en": "Clubroot: lime to pH 7+, long rotation (7 years), raise plants in clean compost.",
        "nl": "Knolvoet: bekalken tot pH 7+, lange rotatie (7 jaar), planten opkweken in propere potgrond.",
    },
    "scab": {
        "en": "Scab: resistant varieties, rake up fallen leaves, horsetail tea.",
        "nl": "Schurft: resistente rassen, afgevallen blad opruimen, heermoesthee.",
    },
    "brown_rot": {
        "en": "Brown rot: remove mummified fruit and wilted shoots immediately.",
        "nl": "Moniliarot: mummievruchten en verwelkte scheuten meteen verwijderen.",
    },
    "rust": {
        "en": "Rust: remove affected leaves, don't overfeed nitrogen, wider spacing.",
        "nl": "Roest: aangetaste bladeren weg, niet te veel stikstof, ruimer planten.",
    },
    "peach_leaf_curl": {
        "en": "Leaf curl: rain shelter from leaf fall to April.",
        "nl": "Krulziekte: regendak van bladval tot april.",
    },
    "white_rot": {
        "en": "White rot: long rotation for alliums, don't move infected soil.",
        "nl": "Witrot: lange rotatie voor uien, besmette grond niet verplaatsen.",
    },
    "damping_off": {
        "en": "Damping off: clean pots, fresh seed compost, water from below, airflow.",
        "nl": "Kiemplantenziekte: propere potjes, verse zaaigrond, water van onderen, luchtcirculatie.",
    },
}

# French, kept as one block and merged into the tables above.
_PROBLEMS_FR: dict[str, dict[str, list[str]]] = {
    "growth": _e(
        [
            "Sol trop froid pour la culture (vérifiez la température du sol).",
            "Trop peu de lumière : ombre, jours courts ou toit de serre sale.",
            "Sol affamé - surtout en azote pour les légumes-feuilles.",
            "Stress hydrique ou sol détrempé et asphyxié.",
            "Racines abîmées (taupin, mouche du chou) ou plants trop serrés.",
        ],
        [
            "Comparez la température du sol au minimum de la culture ; posez un voile pour réchauffer.",
            "Nourrissez les cultures gourmandes au purin d'ortie dilué (1:10) toutes les 2 semaines.",
            "Arrosez copieusement une ou deux fois par semaine plutôt qu'un peu chaque jour.",
            "Éclaircissez les semis trop serrés au bon espacement.",
        ],
        [
            "Purin d'ortie pour l'azote, purin de consoude pour les légumes-fruits.",
            "Thé de compost comme stimulant doux.",
            "Un paillage sombre ou un voile noir réchauffe le sol au printemps.",
        ],
        [
            "Semez à la bonne température de sol, pas selon le calendrier.",
            "Apportez chaque année 3-5 l de compost par m².",
            "Gardez les vitres de la serre propres (10-20 % de lumière en plus).",
        ],
    ),
    "yellow_leaves": _e(
        [
            "Le jaunissement des vieilles feuilles du bas est un vieillissement normal.",
            "Manque d'azote : plante entière pâle, les plus vieilles feuilles d'abord.",
            "Trop humide : les racines s'asphyxient (jaune + mou).",
            "Manque de magnésium (tomate) : jaune entre des nervures vertes.",
            "Nuits froides ou changement brusque (tout juste repiqué).",
        ],
        [
            "Retirez les feuilles jaunes du bas (meilleure circulation de l'air).",
            "Apportez du purin d'ortie à 1:10 ; pour les tomates, du purin de consoude.",
            "Vérifiez l'humidité du sol avec un doigt à 5 cm avant d'arroser.",
            "Magnésium : sel d'Epsom, 20 g pour 10 l d'eau au pied.",
        ],
        [
            "Purin d'ortie (azote).",
            "Sel d'Epsom (sulfate de magnésium) pour tomate et poivron.",
            "Marc de café et compost comme engrais lent.",
        ],
        ["Bon drainage : planches surélevées en sol lourd.", "Compost régulier ; rotation des cultures."],
    ),
    "wilting": _e(
        [
            "Sécheresse - la cause la plus fréquente, surtout en pot et en serre.",
            "Chaleur de midi : les feuilles pendent mais se redressent le soir (normal).",
            "Pourriture des racines ou sol détrempé.",
            "Maladies du flétrissement (verticilliose, fusariose) ou ravageurs des racines (taupin, otiorhynque).",
            "Limaces ou vers gris qui rongent la tige au ras du sol.",
        ],
        [
            "Arrosez tôt le matin, copieusement au pied.",
            "Ombrez les plantes à midi par forte chaleur.",
            "Si la plante reste molle le soir en sol humide : contrôlez racines et collet.",
            "Arrachez les plantes aux vaisseaux brunis (flétrissement) ; ne les compostez pas.",
        ],
        [
            "Ombrez avec un vieux voilage ou un voile d'hivernage en double.",
            "Paillez sur 5-8 cm pour garder le sol frais et humide.",
            "Bouteille enterrée ou oya près des plantes gourmandes en eau.",
        ],
        [
            "Paillage et arrosages copieux.",
            "Tomates/concombres greffés sur porte-greffe résistant.",
            "Rotation des cultures.",
        ],
    ),
    "no_fruit": _e(
        [
            "Pas de pollinisateurs : froid, pluie ou pas de fleurs à proximité.",
            "Pollinisateur manquant (pommier, poirier, cerisier doux, myrtillier, kiwaï).",
            "Trop chaud (>32 °C) ou trop froid à la floraison : les fleurs coulent.",
            "Trop d'azote : beaucoup de feuilles, peu de fleurs.",
            "Jeune arbre qui ne porte pas encore, ou gel sur la floraison.",
        ],
        [
            "Pollinisez à la main : frottez les fleurs mâles sur les fleurs femelles (cucurbitacées), secouez les grappes de tomates en milieu de matinée.",
            "Plantez une deuxième variété comme pollinisateur.",
            "Ombrez et aérez la serre les jours chauds.",
            "Passez à un engrais riche en potassium (consoude).",
        ],
        [
            "Purin de consoude (potassium) pour les fleurs et les fruits.",
            "Bourrache, phacélie et souci à proximité attirent les abeilles.",
            "Un voile sur la floraison précoce les nuits de gel.",
        ],
        [
            "Des fleurs dans chaque planche ; un hôtel à insectes.",
            "Ne traitez jamais pendant la floraison.",
            "Des variétés adaptées au climat (concombres parthénocarpiques sous abri).",
        ],
    ),
    "bolting": _e(
        [
            "Jours longs et chaleur (laitue, épinard, coriandre, roquette, pak-choï).",
            "Coup de froid après le semis (betterave, céleri, bulbilles d'oignon).",
            "Stress hydrique.",
            "Semé trop tôt ou variété inadaptée à la saison.",
        ],
        [
            "Récoltez maintenant - les plantes montées deviennent amères.",
            "Ressemez à l'ombre ou en fin d'été.",
            "Arrachez et compostez, ou laissez-en fleurir quelques-unes pour les insectes.",
        ],
        ["Toile d'ombrage ou vieux rideau sur les salades en été.", "Arrosez régulièrement."],
        [
            "Semez les salades d'été toutes les 2-3 semaines en petites quantités.",
            "Choisissez des variétés lentes à monter ; épinard et coriandre au printemps et à l'automne.",
        ],
    ),
    "pests": _e(
        [
            "Les ravageurs attaquent d'abord les plantes affaiblies (sécheresse, excès d'azote).",
            "Pas encore d'ennemis naturels (début de saison, jardin traité).",
            "Pas de barrière physique sur les cultures sensibles.",
        ],
        [
            "Identifiez d'abord le ravageur (regardez sous les feuilles, le soir à la lampe de poche).",
            "Retirez à la main ou avec un jet d'eau puissant.",
            "Couvrez les cultures sensibles d'un filet anti-insectes.",
        ],
        [
            "Savon noir 20 g/l contre pucerons et aleurodes.",
            "Pièges à bière et ramassage le soir contre les limaces.",
            "Pièges jaunes englués dans la serre.",
        ],
        [
            "Des fleurs pour les auxiliaires (syrphes, chrysopes).",
            "Cultures associées et rotation.",
            "Filet dès le semis ou la plantation.",
        ],
    ),
    "disease": _e(
        [
            "Feuillage mouillé pendant de longues heures (pluie, arrosage le soir, condensation en serre).",
            "Plantes trop serrées, air stagnant.",
            "Sol contaminé ou débris végétaux de l'an dernier.",
            "Variété sensible.",
        ],
        [
            "Retirez immédiatement les feuilles atteintes (poubelle, pas le compost).",
            "Arrosez le matin, uniquement au pied.",
            "Aérez la serre, surtout le matin.",
            "Donnez plus d'espace aux plantes.",
        ],
        [
            "Pulvérisation de lait à 1:9 contre l'oïdium.",
            "Décoction de prêle comme fortifiant préventif.",
            "Décoction d'ail contre les champignons (1:5).",
        ],
        ["Variétés résistantes.", "Rotation (3-4 ans).", "Nettoyer et désinfecter la serre à l'automne."],
    ),
    "slugs": _e(
        ["Temps doux et humide ; paillage et planches leur offrent des cachettes.", "Plants repiqués trop petits."],
        [
            "Ramassez-les au crépuscule et après la pluie.",
            "Pièges à bière (bord 2 cm au-dessus du sol).",
            "Élevez des plants robustes en godets avant de les repiquer.",
        ],
        [
            "Anneau de cendre de bois, de gravillons ou de coquilles d'œuf broyées (efficace seulement au sec).",
            "Une planche ou une feuille de chou comme piège.",
            "Marc de café autour des semis.",
        ],
        [
            "Accueillez hérissons, crapauds, grives et carabes.",
            "Arrosez le matin, pas le soir.",
            "Gardez les bords des planches tondus court.",
        ],
    ),
    "too_hot": _e(
        [
            "Soleil sur les vitres avec les aérations fermées.",
            "Pas d'ombrage en été.",
            "Air sec : araignée rouge et coulure des fleurs.",
        ],
        [
            "Ouvrez toutes les aérations et la porte tôt le matin.",
            "Installez un ombrage (filet, blanc d'ombrage, vieux rideau).",
            "Mouillez le sol et les allées à midi.",
            "Arrosez le matin.",
        ],
        [
            "Un seau d'eau comme masse thermique.",
            "Un vieux drap ou un voilage comme toile d'ombrage.",
            "Lait de chaux (craie + eau) comme blanc d'ombrage.",
        ],
        ["Ouvre-fenêtres automatiques.", "Ombrage dès la mi-printemps.", "Un ventilateur pour brasser l'air."],
    ),
    "frost": _e(
        [
            "Nuit claire et sans vent après une journée froide.",
            "Cultures frileuses repiquées avant la date des dernières gelées.",
            "Les points bas accumulent l'air froid.",
        ],
        [
            "Couvrez les cultures frileuses d'un voile (en double) avant la tombée de la nuit.",
            "Fermez la serre à temps ; des récupérateurs d'eau à l'intérieur stockent la chaleur.",
            "Rentrez les pots.",
            "Arrosez le sol l'après-midi : un sol humide restitue plus de chaleur la nuit.",
        ],
        [
            "Vieux draps, cartons ou seaux retournés sur les plantes.",
            "Film à bulles contre les vitres de la serre.",
            "Bouteilles d'eau chaude entre les plantes sous le voile.",
        ],
        [
            "Repiquez les cultures frileuses après la date des dernières gelées (Hortulus attend pour vous).",
            "Gardez un voile à portée de main à l'automne et au printemps.",
        ],
    ),
    "soil": _e(
        [
            "Argile lourde : humide et froide au printemps, crevassée en été.",
            "Sol sableux : sèche vite et lessive les nutriments.",
            "Tassé à force de marcher sur les planches mouillées.",
        ],
        [
            "Apportez chaque année 3-5 l de compost par m².",
            "Ne marchez jamais sur les planches ; travaillez depuis les allées ou une planche.",
            "Ameublissez à la fourche sans retourner (grelinette).",
        ],
        [
            "Terreau de feuilles et tonte de gazon en paillage.",
            "Un engrais vert dans chaque planche vide.",
            "Cendre de bois pour le potassium (pas pour les pommes de terre).",
        ],
        [
            "Planches et allées permanentes.",
            "Gardez le sol couvert toute l'année.",
            "Une analyse de sol tous les 3 ans (pH 6,5-7).",
        ],
    ),
}
for _key, _entry in _PROBLEMS_FR.items():
    PROBLEMS[_key]["fr"] = _entry  # "too_cold" shares the "frost" entry

_PESTS_FR = {
    "aphids": "Pucerons : jet d'eau, savon noir 20 g/l, coccinelles et syrphes ; moins d'azote.",
    "slugs": "Limaces : ramassage au crépuscule, pièges à bière, anneaux de gravillons ou de cendre, hérissons.",
    "whitefly": "Aleurodes : pièges jaunes, Encarsia, œillets d'Inde, savon noir.",
    "red_spider_mite": "Araignée rouge : augmenter l'humidité (mouiller le sol), acarien prédateur Phytoseiulus.",
    "cabbage_white": "Piéride du chou : filet anti-insectes, retirer œufs et chenilles, capucine comme plante piège.",
    "cabbage_root_fly": "Mouche du chou : filet ou collerette en carton autour de la tige.",
    "carrot_fly": "Mouche de la carotte : filet ou barrière de voile de 60 cm, oignons à côté, éclaircir le soir.",
    "onion_fly": "Mouche de l'oignon : filet, carottes à côté, bulbilles plutôt que semis.",
    "leek_moth": "Teigne du poireau : filet anti-insectes dès mai ; retirer les feuilles atteintes.",
    "flea_beetle": "Altise : garder le sol humide, voile, semer quand la pousse est rapide.",
    "colorado_beetle": "Doryphore : ramasser les adultes et les pontes orange sous les feuilles.",
    "black_bean_aphid": "Puceron noir de la fève : pincer l'extrémité des fèves dès que les premières gousses se forment.",
    "codling_moth": "Carpocapse : bande de carton ondulé autour du tronc dès juin, nichoirs à mésanges.",
    "winter_moth": "Phalène hiémale : bandes de glu à 1 m de hauteur d'octobre à mars.",
    "birds": "Oiseaux : filet fin, bien fixé au sol, quelques semaines avant la maturité.",
    "gooseberry_sawfly": "Tenthrède : contrôler le cœur du buisson dès avril et retirer les larves.",
    "spotted_wing_drosophila": "Drosophila suzukii : cueillir chaque jour, retirer les fruits trop mûrs, filet fin.",
    "wireworm": "Taupin : morceaux de pomme de terre sur un bâton comme piège ; pas juste après une prairie.",
    "thrips": "Thrips : pièges bleus englués, augmenter l'humidité.",
}
for _key, _text in _PESTS_FR.items():
    PESTS[_key]["fr"] = _text

_DISEASES_FR = {
    "late_blight": "Mildiou : abri au-dessus des tomates, arroser le sol, retirer les feuilles du bas, variétés résistantes ; plantes malades à la poubelle.",
    "powdery_mildew": "Oïdium : pulvérisation de lait à 1:9, arrosage régulier, plantation aérée.",
    "downy_mildew": "Mildiou (feuilles) : arroser le matin, aérer, retirer les feuilles tachées.",
    "botrytis": "Pourriture grise : aérer, retirer les tissus morts et les fruits pourris, éviter les blessures.",
    "blossom_end_rot": "Nécrose apicale : problème d'absorption du calcium dû à un arrosage irrégulier - arroser régulièrement, pailler.",
    "clubroot": "Hernie du chou : chauler jusqu'à pH 7+, longue rotation (7 ans), élever les plants dans un terreau propre.",
    "scab": "Tavelure : variétés résistantes, ramasser les feuilles tombées, décoction de prêle.",
    "brown_rot": "Moniliose : retirer immédiatement les fruits momifiés et les pousses flétries.",
    "rust": "Rouille : retirer les feuilles atteintes, pas trop d'azote, espacer davantage.",
    "peach_leaf_curl": "Cloque : abri contre la pluie de la chute des feuilles à avril.",
    "white_rot": "Pourriture blanche : longue rotation pour les alliacées, ne pas déplacer la terre contaminée.",
    "damping_off": "Fonte des semis : godets propres, terreau de semis frais, arrosage par le dessous, circulation de l'air.",
}
for _key, _text in _DISEASES_FR.items():
    DISEASES[_key]["fr"] = _text
