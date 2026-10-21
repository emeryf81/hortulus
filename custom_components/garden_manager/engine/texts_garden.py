"""Texts for the phase 3 maintenance rules and weather tasks (EN / NL / FR / DE).

Kept apart from ``i18n.py`` so the core catalogue stays readable.  Imported
for its side effect at the bottom of ``i18n.py``.
"""

from __future__ import annotations

from .i18n import MESSAGES

MESSAGES["en"].update(
    {
        "overdue.title": "Garden: {count} tasks left undone",
        "voice.not_ready": "Hortulus is still starting up, ask me again in a minute.",
        "voice.no_tasks": "Nothing to do in the garden today. Enjoy it!",
        "voice.tasks": "{count} garden tasks today, about {minutes} minutes: {tasks}.",
        "voice.no_overdue": "No overdue garden tasks. Well done!",
        "voice.overdue": "{count} tasks are overdue: {tasks}.",
        "voice.harvest": "Ready to harvest: {plants}.",
        "voice.no_harvest": "Nothing is ready to harvest right now.",
        "voice.gh_temp": "It is {temp} degrees in {zone}.",
        "voice.gh_no_sensor": "{zone} has no thermometer linked.",
        "voice.gh_action.ventilate": "Open the vents.",
        "voice.gh_action.shade": "Put up the shading.",
        "voice.gh_action.close_up": "Close it before the evening.",
        "voice.gh_action.heat": "It is getting too cold, switch on the heating.",
        "voice.no_greenhouse": "You have no greenhouse in Hortulus.",
        "voice.water": "Yes, water {beds}.",
        "voice.no_water": "No, the soil is moist enough.",
        "voice.frost": "Yes, frost is expected, down to {temp} degrees. Cover tender plants.",
        "voice.no_frost": "No frost expected.",
        "desc.rain_water": "Rain water in the butts: about {liters} L - use it first.",
        "soil.adj.lime_dose": "Soil test: spread {grams} g garden lime (pH too low), not together with manure.",
        "soil.adj.om_low": "Soil test: little organic matter - compost increased by half.",
        "soil.adj.om_high": "Soil test: lots of organic matter - less compost needed.",
        "soil.adj.pk_high": "Soil test: phosphate and potassium are high - half the fertiliser, compost is enough.",
        "soil.adj.pk_low": "Soil test: phosphate or potassium is low - a little extra organic fertiliser (or wood ash for K).",
        "soil.adj.ph_high": "Soil test: pH above 7.5 - no lime; leaf mould and compost lower it slowly.",
        "weather.moved": "Moved to {date} because of the weather ({reason}).",
        "weather.no_good_day": "Weather warning: {reason} forecast - pick the best moment yourself or protect with fleece.",
        "weather.problem.rain": "rain",
        "weather.problem.frost": "frost",
        "weather.problem.heat": "heat",
        "weather.problem.wind": "strong wind",
        "overdue.window_closed": "too late now - skip it or choose an alternative",
        "overdue.still_ok": "still possible until {date}",
        "overdue.do_now": "{days} days late",
        "overdue.footer": "Open Hortulus to complete, postpone or skip.",
        "weekly.title": "Garden: your week ahead",
        "weekly.day": "{day}: {count} tasks (~{minutes} min)",
        "weekly.empty": "A quiet week - nothing planned.",
        # yearly garden work
        "maint.clean_pots": "Wash pots, trays and labels",
        "maint.clean_pots.desc": "Scrub pots and seed trays in hot water with a squirt of soft soap or a splash of vinegar; "
        "rinse and dry in the sun. Clean pots prevent damping off.",
        "maint.water_butts": "Clean and connect the water butts",
        "maint.water_butts.desc": "Scoop out sludge, check the diverter on the downpipe and put a lid or fine mesh on top "
        "(no mosquito larvae). Rain water is softer and warmer than tap water - plants love it.",
        "maint.irrigation_service": "Service the drip irrigation",
        "maint.irrigation_service.desc": "Flush the lines, clean filters and drippers (a night in vinegar dissolves lime), "
        "check for leaks and test every valve once.",
        "maint.green_manure_dig": "Cut down and dig in the green manure",
        "maint.green_manure_dig.desc": "Mow or chop the green manure, let it wilt for a few days and work it shallowly into "
        "the top 10 cm (no-dig: leave it as mulch under a cover). Sow 3-4 weeks later.",
        "maint.slug_patrol": "Start the slug patrol",
        "maint.slug_patrol.desc": "Go round with a torch after dusk or rain. Eco: beer trap (sunk jar, rim 2 cm above soil), "
        "a board to collect them under, a ring of wood ash, grit or crushed eggshell around seedlings; welcome hedgehogs, "
        "thrushes and ground beetles.",
        "maint.nettle_feed": "Make nettle feed (nitrogen)",
        "maint.nettle_feed.desc": "1 kg young nettles (before flowering) in 10 l rain water, stir daily, ferment 10-14 days. "
        "Dilute 1:10 for leafy crops and cabbages, 1:20 for seedlings. A lid keeps the smell in.",
        "maint.comfrey_feed": "Make comfrey feed (potassium)",
        "maint.comfrey_feed.desc": "Pack comfrey leaves in a bucket with a few holes in the bottom, weigh them down and collect "
        "the black liquid (or soak 1 kg in 10 l water for 3 weeks). Dilute 1:10 - perfect tomato and fruit feed.",
        "maint.sow_winter_crops": "Sow for autumn and winter harvests",
        "maint.sow_winter_crops.desc": "Last chance outdoors for winter crops: lamb's lettuce, spinach, winter purslane, "
        "rocket, pak choi, endive, turnip greens; plant out leeks, kale and winter cabbage. Sow green manure on empty beds.",
        "maint.hedge_trim": "Trim the hedge (after nesting season)",
        "maint.hedge_trim.desc": "Check for nests first - birds breed until mid-August. Use the clippings as mulch "
        "or in the compost (shredded).",
        "maint.seed_saving": "Save seed",
        "maint.seed_saving.desc": "Pick the best fruit of open-pollinated varieties (tomato, bean, pea, lettuce). "
        "Tomato: ferment the pulp 3 days in a glass of water, rinse and dry. Store in paper envelopes, cool and dry.",
        "maint.fleece_ready": "Get fleece, tunnels and frost cloth ready",
        "maint.fleece_ready.desc": "Check fleece and hoops, buy what is missing; old bed sheets and cardboard boxes "
        "work too for a night of frost.",
        "maint.leaf_mould": "Collect leaves for leaf mould",
        "maint.leaf_mould.desc": "Fill bin bags with damp autumn leaves, punch a few holes and leave them 1-2 years: "
        "the best free seed compost and mulch. Skip diseased leaves (scab, rust).",
        "maint.gutters": "Clear gutters and the rain diverter",
        "maint.gutters.desc": "Remove leaves from gutters, the water-butt filter and greenhouse gutters so winter rain "
        "is caught.",
        "maint.nest_boxes": "Clean nest boxes and feed the birds",
        "maint.nest_boxes.desc": "Empty old nests (fleas), rinse with boiling water - no chemicals. Tits eat thousands "
        "of caterpillars and aphids: hang the box 2-3 m high, entrance facing east.",
        "maint.storage_check": "Check the winter store",
        "maint.storage_check.desc": "Go through potatoes, onions, squash, apples and roots: remove anything soft or "
        "rotting, keep the store dark, frost-free and airy.",
        # greenhouse
        "maint.gh_windows": "Wash the windows of {zone}",
        "maint.gh_windows.desc": "Clean glass or polycarbonate inside and out: a dirty roof costs 10-20 % of the light. "
        "Warm water with green soap or a dash of vinegar, a soft brush on a pole, rinse with the hose; "
        "scrape algae out of the overlaps with a plant label.",
        "maint.gh_windows_autumn": "Clean the glass of {zone} for winter light",
        "maint.gh_windows_autumn.desc": "Wash off the shading paint and summer dirt so winter crops get every ray of light.",
        "maint.gh_vents_check": "Check vents and openers in {zone}",
        "maint.gh_vents_check.desc": "Test the automatic window openers (wax cylinders weaken after a few years), "
        "fans and the min/max thermometer before the first warm day.",
        "maint.gh_biocontrol": "Bring in the good bugs in {zone}",
        "maint.gh_biocontrol.desc": "From 15 °C: release Encarsia against whitefly, Phytoseiulus against spider mite and "
        "lacewing larvae against aphids. Hang yellow sticky cards to monitor. A dish of water and some flowers "
        "(marigold, alyssum) keep them there.",
        "maint.gh_winter_crops": "Plan winter crops in {zone}",
        "maint.gh_winter_crops.desc": "Sow or plant now for harvests all winter under glass: lamb's lettuce, winter "
        "purslane, spinach, pak choi, mizuna, rocket, chard, spring onion; lettuce for early spring.",
        # orchard
        "maint.orchard_winter_wash": "Winter check of the fruit trees in {zone}",
        "maint.orchard_winter_wash.desc": "Look for canker, mummified fruit and aphid eggs on a dry day; scrub loose bark "
        "with a stiff brush. Remove mummies (brown rot) and dead wood.",
        "maint.orchard_mow": "Mow the orchard paths, leave flower strips",
        "maint.orchard_mow.desc": "Keep a 1 m tree circle free of grass (mulch), mow the paths and leave strips to flower "
        "for pollinators and predatory insects.",
        "maint.orchard_grease_bands": "Put grease bands on the trees in {zone}",
        "maint.orchard_grease_bands.desc": "Grease bands at 1 m height stop wingless winter moth females climbing up "
        "to lay eggs. Remove them in March.",
        "maint.orchard_pollinators": "Help the pollinators in {zone}",
        "maint.orchard_pollinators.desc": "Blossom is coming: hang a mason-bee house (south-east, 1-2 m), leave dandelions "
        "flowering in the grass, never spray during bloom.",
        # weather episodes
        "weather.heat": "Heat ahead ({temp} °C on {day}): protect the garden",
        "weather.heat.desc": "Up to {temp} °C over {days} day(s). Water early in the morning (5-8 h), at the roots and "
        "deeply (10-20 l/m²) rather than a little every evening; mulch bare soil 5-8 cm (grass clippings, straw); "
        "harvest in the morning; don't sow, plant out or prune now; move pots into the shade and set out a dish of "
        "water for birds and insects.",
        "weather.heat.shade": "Shade the most sensitive crops at midday: {plants}. No shade cloth? An old net curtain, "
        "a double layer of fleece, a parasol or a bed sheet on canes works fine.",
        "weather.heat.very": "Very hot: tomatoes and peppers drop flowers above 32-35 °C - shade them too. "
        "Check pots and young plants twice a day.",
        "weather.heat_gh": "Heat ahead: cool {zone} ({temp} °C)",
        "weather.heat_gh.desc": "Open all vents and the door early in the morning, close the door only if nights drop "
        "below 12 °C; shading paint or netting on; damp down the floor and paths at midday (evaporation cools 3-5 °C); "
        "water in the morning; a bucket of water in the greenhouse buffers the night.",
        "weather.dry": "Dry, warm spell ({days} days): water smart",
        "weather.dry.desc": "Give one deep soak per week (20 l/m²) instead of daily sprinkling - roots grow deeper. "
        "Hoe once ('a hoeing is worth two waterings'), top up mulch, use the water butts first and water in the "
        "morning. Sunk bottles or ollas (unglazed pots) next to thirsty crops save half the water.",
        "weather.storm": "Storm coming ({day}): make the garden storm-proof",
        "weather.storm.desc": "Wind gusts up to {wind} km/h. Close greenhouse doors and vents, weigh down fleece and nets "
        "(stones, sandbags, tent pegs), move pots and seed trays to a sheltered spot and clear loose items.",
        "weather.storm.tall": "Check stakes and ties of tall crops: {plants}.",
        "weather.rain": "Heavy rain ({mm} mm on {day}): after-care",
        "weather.after_storm": "After the storm ({day}): look the garden over",
        "weather.after_storm.desc": "Gusts reached {wind} km/h. Re-tie and straighten tall crops, check stakes, netting, fleece and the greenhouse (doors, panes), and pick up broken stems before they rot.",
        "weather.dry_logged": "Dry spell: {mm} mm of rain in {days} days",
        "weather.dry_logged.desc": "Hardly any rain has fallen lately while the plants kept drinking. Give thirsty beds one deep soak (10-20 l/m²) early in the day rather than daily sips, mulch bare soil and check the water butts.",
        "weather.rain.desc": "After the rain: slug patrol at dusk (beer traps, collect them), stay off wet beds (use a "
        "plank), empty saucers and pots, check that water drains away. Wait a few days before sowing; "
        "remove rotting fruit (botrytis).",
    }
)

MESSAGES["nl"].update(
    {
        "overdue.title": "Moestuin: {count} taken blijven liggen",
        "voice.not_ready": "Hortulus is nog aan het opstarten, vraag het me zo meteen opnieuw.",
        "voice.no_tasks": "Vandaag niets te doen in de tuin. Geniet ervan!",
        "voice.tasks": "{count} tuintaken vandaag, ongeveer {minutes} minuten: {tasks}.",
        "voice.no_overdue": "Geen achterstallige tuintaken. Goed bezig!",
        "voice.overdue": "{count} taken zijn achterstallig: {tasks}.",
        "voice.harvest": "Klaar om te oogsten: {plants}.",
        "voice.no_harvest": "Er is nu niets oogstklaar.",
        "voice.gh_temp": "Het is {temp} graden in {zone}.",
        "voice.gh_no_sensor": "{zone} heeft geen thermometer gekoppeld.",
        "voice.gh_action.ventilate": "Zet de ramen open.",
        "voice.gh_action.shade": "Breng schaduw aan.",
        "voice.gh_action.close_up": "Sluit ze voor de avond.",
        "voice.gh_action.heat": "Het wordt te koud, zet de verwarming aan.",
        "voice.no_greenhouse": "Je hebt geen serre in Hortulus.",
        "voice.water": "Ja, geef water aan {beds}.",
        "voice.no_water": "Nee, de grond is vochtig genoeg.",
        "voice.frost": "Ja, er wordt vorst verwacht, tot {temp} graden. Dek gevoelige planten af.",
        "voice.no_frost": "Geen vorst verwacht.",
        "desc.rain_water": "Regenwater in de tonnen: ongeveer {liters} L - gebruik dat eerst.",
        "soil.adj.lime_dose": "Bodemanalyse: strooi {grams} g tuinkalk (pH te laag), niet samen met mest.",
        "soil.adj.om_low": "Bodemanalyse: weinig organische stof - de helft meer compost.",
        "soil.adj.om_high": "Bodemanalyse: veel organische stof - minder compost nodig.",
        "soil.adj.pk_high": "Bodemanalyse: fosfaat en kalium zijn hoog - halve bemesting, compost volstaat.",
        "soil.adj.pk_low": "Bodemanalyse: fosfaat of kalium is laag - wat extra organische mest (of houtas voor K).",
        "soil.adj.ph_high": "Bodemanalyse: pH boven 7,5 - geen kalk; bladaarde en compost verlagen hem traag.",
        "weather.moved": "Verplaatst naar {date} wegens het weer ({reason}).",
        "weather.no_good_day": "Weerwaarschuwing: {reason} voorspeld - kies zelf het beste moment of bescherm met vliesdoek.",
        "weather.problem.rain": "regen",
        "weather.problem.frost": "vorst",
        "weather.problem.heat": "hitte",
        "weather.problem.wind": "harde wind",
        "overdue.window_closed": "te laat nu - overslaan of een alternatief kiezen",
        "overdue.still_ok": "kan nog tot {date}",
        "overdue.do_now": "{days} dagen te laat",
        "overdue.footer": "Open Hortulus om af te vinken, uit te stellen of over te slaan.",
        "weekly.title": "Moestuin: je week",
        "weekly.day": "{day}: {count} taken (~{minutes} min)",
        "weekly.empty": "Een rustige week - niets gepland.",
        "maint.clean_pots": "Potten, zaaibakken en etiketten wassen",
        "maint.clean_pots.desc": "Schrob potten en zaaibakken in heet water met een scheut groene zeep of azijn, "
        "spoel na en laat drogen in de zon. Propere potten voorkomen kiemplantenziekte.",
        "maint.water_butts": "Regentonnen schoonmaken en aansluiten",
        "maint.water_butts.desc": "Schep het slib eruit, controleer de vulautomaat op de regenpijp en leg er een deksel "
        "of fijn gaas op (geen muggenlarven). Regenwater is zachter en warmer dan kraantjeswater - planten zijn er dol op.",
        "maint.irrigation_service": "Druppelirrigatie nakijken",
        "maint.irrigation_service.desc": "Spoel de leidingen door, reinig filters en druppelaars (een nacht in azijn lost "
        "kalk op), zoek lekken en test elke klep één keer.",
        "maint.green_manure_dig": "Groenbemester maaien en inwerken",
        "maint.green_manure_dig.desc": "Maai of hak de groenbemester, laat enkele dagen verwelken en werk hem ondiep "
        "in de bovenste 10 cm (niet-spitten: laat hem liggen als mulch onder een afdekking). Zaai 3-4 weken later.",
        "maint.slug_patrol": "Slakkenronde starten",
        "maint.slug_patrol.desc": "Ga na schemering of regen rond met een zaklamp. Ecologisch: bierval (ingegraven "
        "potje, rand 2 cm boven de grond), een plank waaronder ze schuilen, een ring van houtas, grit of gemalen "
        "eierschalen rond zaailingen; verwelkom egels, lijsters en loopkevers.",
        "maint.nettle_feed": "Brandnetelgier maken (stikstof)",
        "maint.nettle_feed.desc": "1 kg jonge brandnetels (voor de bloei) in 10 l regenwater, dagelijks roeren, "
        "10-14 dagen laten gisten. Verdun 1:10 voor bladgewassen en kolen, 1:20 voor zaailingen. Een deksel houdt de geur binnen.",
        "maint.comfrey_feed": "Smeerwortelgier maken (kalium)",
        "maint.comfrey_feed.desc": "Prop smeerwortelblad in een emmer met gaatjes in de bodem, verzwaar en vang het zwarte "
        "vocht op (of week 1 kg in 10 l water gedurende 3 weken). Verdun 1:10 - ideale voeding voor tomaten en fruit.",
        "maint.sow_winter_crops": "Zaaien voor herfst- en winteroogst",
        "maint.sow_winter_crops.desc": "Laatste kans buiten voor wintergroenten: veldsla, spinazie, winterpostelein, "
        "rucola, paksoi, andijvie, raapstelen; plant prei, boerenkool en winterkool uit. Zaai groenbemester op lege bedden.",
        "maint.hedge_trim": "Haag snoeien (na het broedseizoen)",
        "maint.hedge_trim.desc": "Kijk eerst naar nesten - vogels broeden tot half augustus. Gebruik het snoeisel "
        "(versnipperd) als mulch of in de compost.",
        "maint.seed_saving": "Zaad winnen",
        "maint.seed_saving.desc": "Neem de mooiste vruchten van samenbestuivende rassen (tomaat, boon, erwt, sla). "
        "Tomaat: laat het zaadmoes 3 dagen gisten in een glas water, spoel en droog. Bewaar in papieren zakjes, koel en droog.",
        "maint.fleece_ready": "Vliesdoek, tunnels en vorstdoek klaarleggen",
        "maint.fleece_ready.desc": "Controleer vliesdoek en tunnelbogen, koop wat ontbreekt; oude lakens en kartonnen "
        "dozen werken ook voor een vriesnacht.",
        "maint.leaf_mould": "Bladeren verzamelen voor bladaarde",
        "maint.leaf_mould.desc": "Vul vuilniszakken met vochtig herfstblad, prik er gaatjes in en laat 1-2 jaar staan: "
        "de beste gratis zaaigrond en mulch. Geen ziek blad (schurft, roest).",
        "maint.gutters": "Dakgoten en regenwateraftakking vrijmaken",
        "maint.gutters.desc": "Haal bladeren uit de goten, de filter van de regenton en de goten van de serre zodat "
        "de winterregen opgevangen wordt.",
        "maint.nest_boxes": "Nestkastjes schoonmaken en vogels voederen",
        "maint.nest_boxes.desc": "Haal oude nesten eruit (vlooien), spoel met kokend water - geen chemie. Mezen eten "
        "duizenden rupsen en bladluizen: hang het kastje op 2-3 m, opening naar het oosten.",
        "maint.storage_check": "Wintervoorraad controleren",
        "maint.storage_check.desc": "Loop aardappelen, uien, pompoenen, appels en wortelgroenten na: haal alles weg dat "
        "zacht wordt of rot, hou de berging donker, vorstvrij en luchtig.",
        "maint.gh_windows": "Ruiten van {zone} wassen",
        "maint.gh_windows.desc": "Maak glas of polycarbonaat binnen en buiten schoon: een vuil dak kost 10-20 % licht. "
        "Lauw water met groene zeep of een scheut azijn, een zachte borstel op een steel, naspoelen met de tuinslang; "
        "schraap algen uit de overlappingen met een plantenetiket.",
        "maint.gh_windows_autumn": "Glas van {zone} reinigen voor het winterlicht",
        "maint.gh_windows_autumn.desc": "Was de schaduwkalk en het zomerstof eraf zodat de wintergewassen elk straaltje licht krijgen.",
        "maint.gh_vents_check": "Ramen en raamopeners van {zone} nakijken",
        "maint.gh_vents_check.desc": "Test de automatische raamopeners (de wascilinders verzwakken na enkele jaren), "
        "ventilatoren en de min/max-thermometer vóór de eerste warme dag.",
        "maint.gh_biocontrol": "Nuttige insecten inzetten in {zone}",
        "maint.gh_biocontrol.desc": "Vanaf 15 °C: sluipwesp Encarsia tegen witte vlieg, roofmijt Phytoseiulus tegen spint "
        "en gaasvlieglarven tegen bladluis. Hang gele vangplaten om op te volgen. Een schaaltje water en wat bloemen "
        "(goudsbloem, zilverschildzaad) houden ze ter plaatse.",
        "maint.gh_winter_crops": "Wintergroenten plannen in {zone}",
        "maint.gh_winter_crops.desc": "Zaai of plant nu voor oogst de hele winter onder glas: veldsla, winterpostelein, "
        "spinazie, paksoi, mizuna, rucola, snijbiet, lente-ui; sla voor het vroege voorjaar.",
        "maint.orchard_winter_wash": "Wintercontrole van de fruitbomen in {zone}",
        "maint.orchard_winter_wash.desc": "Zoek op een droge dag naar kanker, mummievruchten en luizeneitjes; borstel losse "
        "schors met een stugge borstel. Verwijder mummies (moniliarot) en dood hout.",
        "maint.orchard_mow": "Paden in de boomgaard maaien, bloemstroken laten staan",
        "maint.orchard_mow.desc": "Hou een boomspiegel van 1 m grasvrij (mulch), maai de paden en laat stroken bloeien "
        "voor bestuivers en roofinsecten.",
        "maint.orchard_grease_bands": "Lijmbanden aanbrengen in {zone}",
        "maint.orchard_grease_bands.desc": "Lijmbanden op 1 m hoogte houden de vleugelloze wijfjes van de wintervlinder "
        "tegen die omhoog kruipen om eitjes te leggen. Verwijder ze in maart.",
        "maint.orchard_pollinators": "Help de bestuivers in {zone}",
        "maint.orchard_pollinators.desc": "De bloesem komt eraan: hang een metselbijenhotel (zuidoost, 1-2 m hoog), laat "
        "paardenbloemen bloeien in het gras, spuit nooit tijdens de bloei.",
        "weather.heat": "Hitte op komst ({temp} °C op {day}): bescherm de tuin",
        "weather.heat.desc": "Tot {temp} °C gedurende {days} dag(en). Geef 's ochtends vroeg water (5-8 u), aan de voet "
        "en grondig (10-20 l/m²) in plaats van elke avond een beetje; mulch kale grond 5-8 cm (grasmaaisel, stro); "
        "oogst 's ochtends; nu niet zaaien, uitplanten of snoeien; zet potten in de schaduw en zet een schaaltje "
        "water klaar voor vogels en insecten.",
        "weather.heat.shade": "Geef de gevoeligste gewassen 's middags schaduw: {plants}. Geen schaduwdoek? Een oud "
        "vitragegordijn, dubbel vliesdoek, een parasol of een laken op stokken werkt prima.",
        "weather.heat.very": "Zeer warm: tomaten en paprika laten bloemen vallen boven 32-35 °C - geef ook hen schaduw. "
        "Controleer potten en jonge planten twee keer per dag.",
        "weather.heat_gh": "Hitte op komst: koel {zone} ({temp} °C)",
        "weather.heat_gh.desc": "Zet 's ochtends vroeg alle ramen en de deur open, sluit de deur enkel als de nacht onder "
        "12 °C zakt; schaduwkalk of -doek erop; maak 's middags de vloer en paden nat (verdamping koelt 3-5 °C); "
        "water geven 's ochtends; een emmer water in de serre buffert de nacht.",
        "weather.dry": "Droge, warme periode ({days} dagen): slim water geven",
        "weather.dry.desc": "Geef één keer per week grondig water (20 l/m²) in plaats van dagelijks sproeien - de wortels "
        "groeien dieper. Schoffel één keer ('één keer schoffelen is twee keer gieten'), vul de mulch aan, gebruik eerst "
        "de regenton en geef 's ochtends water. Ingegraven flessen of olla's (ongeglazuurde potten) naast dorstige "
        "gewassen sparen de helft van het water.",
        "weather.storm": "Storm op komst ({day}): maak de tuin stormvast",
        "weather.storm.desc": "Windstoten tot {wind} km/u. Sluit deuren en ramen van de serre, verzwaar vliesdoek en netten "
        "(stenen, zandzakjes, tentharingen), zet potten en zaaibakken beschut en ruim losse spullen op.",
        "weather.storm.tall": "Controleer stokken en banden van hoge gewassen: {plants}.",
        "weather.rain": "Zware regen ({mm} mm op {day}): nazorg",
        "weather.after_storm": "Na de storm ({day}): loop de tuin na",
        "weather.after_storm.desc": "Er waren windstoten tot {wind} km/u. Bind hoge gewassen opnieuw op en zet ze recht, controleer steunen, netten, vliesdoek en de serre (deuren, ruiten) en ruim gebroken stengels op voor ze gaan rotten.",
        "weather.dry_logged": "Droge periode: {mm} mm regen in {days} dagen",
        "weather.dry_logged.desc": "Er viel de laatste tijd nauwelijks regen terwijl de planten bleven drinken. Geef dorstige bedden één keer flink water (10-20 l/m²) vroeg op de dag in plaats van dagelijks een beetje, mulch kale grond en kijk de regentonnen na.",
        "weather.rain.desc": "Na de regen: slakkenronde bij schemering (biervallen, rapen), blijf van natte bedden (gebruik "
        "een plank), maak schotels en potten leeg, controleer of het water wegloopt. Wacht enkele dagen met zaaien; "
        "verwijder rottend fruit (grauwe schimmel).",
    }
)

_PEST_NL = {
    "aphids": "bladluis",
    "whitefly": "witte vlieg",
    "red_spider_mite": "spint",
    "thrips": "trips",
    "slugs": "slakken",
    "cabbage_white": "koolwitje",
    "cabbage_root_fly": "koolvlieg",
    "flea_beetle": "aardvlo",
    "carrot_fly": "wortelvlieg",
    "onion_fly": "uienvlieg",
    "leek_moth": "preimot",
    "pea_moth": "erwtenbladroller",
    "birds": "vogels",
    "pigeons": "duiven",
    "black_bean_aphid": "zwarte bonenluis",
    "bean_weevil": "bonenkever",
    "leaf_miner": "bladmineerder",
    "asparagus_beetle": "aspergekever",
    "celery_fly": "selderijvlieg",
    "colorado_beetle": "coloradokever",
    "wireworm": "ritnaald",
    "codling_moth": "fruitmot",
    "woolly_aphid": "bloedluis",
    "winter_moth": "wintervlinder",
    "pear_midge": "perengalmug",
    "pear_psylla": "perenbladvlo",
    "plum_moth": "pruimenmot",
    "wasps": "wespen",
    "cherry_fruit_fly": "kersenvlieg",
    "spotted_wing_drosophila": "suzuki-fruitvlieg",
    "black_cherry_aphid": "zwarte kersenluis",
    "nut_weevil": "hazelnootboorder",
    "squirrels": "eekhoorns",
    "currant_blister_aphid": "bessenbladluis",
    "gooseberry_sawfly": "bessenbladwesp",
    "big_bud_mite": "rondknopmijt",
    "raspberry_beetle": "frambozenkever",
    "nematodes": "aaltjes",
    "moths": "motten",
    "ants": "mieren",
}
_PEST_FR = {
    "aphids": "pucerons",
    "whitefly": "aleurodes",
    "red_spider_mite": "araignée rouge",
    "thrips": "thrips",
    "slugs": "limaces",
    "cabbage_white": "piéride du chou",
    "cabbage_root_fly": "mouche du chou",
    "flea_beetle": "altise",
    "carrot_fly": "mouche de la carotte",
    "onion_fly": "mouche de l'oignon",
    "leek_moth": "teigne du poireau",
    "pea_moth": "tordeuse du pois",
    "birds": "oiseaux",
    "pigeons": "pigeons",
    "black_bean_aphid": "puceron noir de la fève",
    "bean_weevil": "bruche du haricot",
    "leaf_miner": "mineuse",
    "asparagus_beetle": "criocère de l'asperge",
    "celery_fly": "mouche du céleri",
    "colorado_beetle": "doryphore",
    "wireworm": "taupin",
    "codling_moth": "carpocapse",
    "woolly_aphid": "puceron lanigère",
    "winter_moth": "phalène hiémale",
    "pear_midge": "cécidomyie des poirettes",
    "pear_psylla": "psylle du poirier",
    "plum_moth": "carpocapse des prunes",
    "wasps": "guêpes",
    "cherry_fruit_fly": "mouche de la cerise",
    "spotted_wing_drosophila": "drosophile suzukii",
    "black_cherry_aphid": "puceron noir du cerisier",
    "nut_weevil": "balanin des noisettes",
    "squirrels": "écureuils",
    "currant_blister_aphid": "puceron du groseillier",
    "gooseberry_sawfly": "tenthrède du groseillier",
    "big_bud_mite": "phytopte du cassissier",
    "raspberry_beetle": "ver des framboises",
    "nematodes": "nématodes",
    "moths": "mites",
    "ants": "fourmis",
}
_PEST_DE = {
    "aphids": "Blattläuse",
    "whitefly": "Weiße Fliege",
    "red_spider_mite": "Rote Spinne",
    "thrips": "Thripse",
    "slugs": "Schnecken",
    "cabbage_white": "Kohlweißling",
    "cabbage_root_fly": "Kohlfliege",
    "flea_beetle": "Erdflöhe",
    "carrot_fly": "Möhrenfliege",
    "onion_fly": "Zwiebelfliege",
    "leek_moth": "Lauchmotte",
    "pea_moth": "Erbsenwickler",
    "birds": "Vögel",
    "pigeons": "Tauben",
    "black_bean_aphid": "Schwarze Bohnenlaus",
    "bean_weevil": "Bohnenkäfer",
    "leaf_miner": "Minierfliege",
    "asparagus_beetle": "Spargelhähnchen",
    "celery_fly": "Selleriefliege",
    "colorado_beetle": "Kartoffelkäfer",
    "wireworm": "Drahtwurm",
    "codling_moth": "Apfelwickler",
    "woolly_aphid": "Blutlaus",
    "winter_moth": "Frostspanner",
    "pear_midge": "Birnengallmücke",
    "pear_psylla": "Birnenblattsauger",
    "plum_moth": "Pflaumenwickler",
    "wasps": "Wespen",
    "cherry_fruit_fly": "Kirschfruchtfliege",
    "spotted_wing_drosophila": "Kirschessigfliege",
    "black_cherry_aphid": "Schwarze Kirschenlaus",
    "nut_weevil": "Haselnussbohrer",
    "squirrels": "Eichhörnchen",
    "currant_blister_aphid": "Johannisbeerblasenlaus",
    "gooseberry_sawfly": "Stachelbeerblattwespe",
    "big_bud_mite": "Johannisbeergallmilbe",
    "raspberry_beetle": "Himbeerkäfer",
    "nematodes": "Nematoden",
    "moths": "Motten",
    "ants": "Ameisen",
}
_MONTHS = {
    "en": [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
    "nl": [
        "januari",
        "februari",
        "maart",
        "april",
        "mei",
        "juni",
        "juli",
        "augustus",
        "september",
        "oktober",
        "november",
        "december",
    ],
    "fr": [
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ],
    "de": [
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    ],
}
for _lang in ("en", "nl", "fr", "de"):
    for _i, _m in enumerate(_MONTHS[_lang], start=1):
        MESSAGES[_lang][f"month.{_i}"] = _m
for _pid, _name in _PEST_NL.items():
    MESSAGES["nl"][f"pest.{_pid}"] = _name
    MESSAGES["en"][f"pest.{_pid}"] = _pid.replace("_", " ")
for _pid, _name in _PEST_FR.items():
    MESSAGES["fr"][f"pest.{_pid}"] = _name
for _pid, _name in _PEST_DE.items():
    MESSAGES["de"][f"pest.{_pid}"] = _name

MESSAGES["en"].update(
    {
        "method.indoor_sow": "Sow indoors",
        "method.direct_sow": "Sow outdoors",
        "method.transplant": "Plant out",
        "moisture.dry": "dry",
        "moisture.slightly_dry": "slightly dry",
        "moisture.optimal": "just right",
        "moisture.wet": "wet",
        "moisture.unknown": "unknown",
        "pollination.insects": "Pollinated by insects - flowers nearby help.",
        "pollination.wind": "Wind-pollinated - plant in blocks.",
        "pollination.partner": "Needs a second variety nearby to set fruit.",
        "advice.whole_garden": "Whole garden",
        "advice.tools": "Tools & supplies",
        "advice.partner": "{plant} needs a pollination partner",
        "advice.partner.text": "No second variety of {plant} nearby. Plant another variety that flowers at the same time "
        "(within about 50 m - a neighbour's tree counts), or graft a pollinator branch.",
        "advice.pollinators": "Add flowers for the pollinators in {zone}",
        "advice.pollinators.text": "{plants} need insects to set fruit. A strip of {flowers} draws bees and hoverflies "
        "(which also eat aphids).",
        "advice.enemy": "{a} and {b} are bad neighbours in {bed}",
        "advice.enemy.text": "{reason} Move one of them to another bed.",
        "advice.better": "Better neighbours: {plants}.",
        "advice.shade": "{tall} shades {short} in {bed}",
        "advice.shade.text": "Tall crops belong on the north side of a bed (top of the map) so they don't steal the sun "
        "from {short}.",
        "advice.gaps": "Fill the harvest gaps",
        "advice.gaps.text": "Nothing to harvest in {months}. Add for example {plants} - or store more of the summer harvest.",
        "advice.empty_bed": "{bed} is empty - sow a quick crop",
        "advice.empty_bed.text": "There is still time for a catch crop before the frost: {plants}.",
        "advice.empty_bed_late": "Cover {bed} for winter",
        "advice.empty_bed_late.text": "Too late for vegetables: sow a green manure ({plants}) or mulch the soil.",
        "advice.empty_greenhouse": "Use {bed} for winter crops",
        "advice.empty_greenhouse.text": "Under glass you can harvest all winter: {plants}.",
        "advice.rotation": "{n} crops break the rotation",
        "advice.rotation.text": "The same family grew there recently - higher risk of soil diseases. The planner shows "
        "better beds for each of them.",
        "advice.heat_stress": "Heat stress on {plants}",
        "advice.heat_stress.text": "Shade at midday, water in the morning and ventilate the greenhouse fully.",
        "advice.feed": "{bed} is running short of nutrients",
        "advice.feed.text": "Feed with diluted nettle feed (leaf crops) or comfrey feed (fruit crops) and top-dress compost.",
        "advice.flowers": "Plant flowers between the vegetables",
        "advice.flowers.text": "About one tenth flowers ({flowers}) brings pollinators and natural pest control.",
        "advice.year_transition": "Close {from} and move into {to}",
        "advice.year_transition.text": "The new year has started, but nothing carries over by itself: choose in the "
        "year-end transition which part of the garden plan, which perennials and which overwintering crops go "
        "into {to}. Until then they get no tasks for {to}.",
        "advice.compost": "Draw a compost heap",
        "advice.compost.text": "Your own compost is the best and cheapest soil improver - place it in a half-shaded corner.",
        "advice.water_butt": "Catch rain water",
        "advice.water_butt.text": "A water butt on the shed or greenhouse gutter gives soft, warm water and saves tap water.",
        "advice.habitat": "Make room for helpers",
        "advice.habitat.text": "A hedge, a small pond, a log pile or a wild corner brings hedgehogs, toads, birds and "
        "ground beetles - your best slug and caterpillar control.",
        "advice.gh_sensor": "Add a thermometer to the greenhouse",
        "advice.gh_sensor.text": "With a temperature sensor Hortulus can warn you before the greenhouse overheats or freezes. "
        "See the chapter on sensors.",
    }
)
MESSAGES["nl"].update(
    {
        "method.indoor_sow": "Binnen zaaien",
        "method.direct_sow": "Buiten zaaien",
        "method.transplant": "Uitplanten",
        "moisture.dry": "droog",
        "moisture.slightly_dry": "wat droog",
        "moisture.optimal": "goed",
        "moisture.wet": "nat",
        "moisture.unknown": "onbekend",
        "pollination.insects": "Bestuiving door insecten - bloemen in de buurt helpen.",
        "pollination.wind": "Windbestuiving - plant in blokken.",
        "pollination.partner": "Heeft een tweede ras in de buurt nodig om vruchten te zetten.",
        "advice.whole_garden": "Hele tuin",
        "advice.tools": "Gereedschap & benodigdheden",
        "advice.partner": "{plant} heeft een bestuivingspartner nodig",
        "advice.partner.text": "Er staat geen tweede ras van {plant} in de buurt. Plant een ander ras dat gelijktijdig bloeit "
        "(binnen ±50 m - de boom van de buren telt ook), of ent een bestuiverstak.",
        "advice.pollinators": "Zet bloemen voor de bestuivers in {zone}",
        "advice.pollinators.text": "{plants} hebben insecten nodig om vruchten te zetten. Een strook {flowers} lokt bijen "
        "en zweefvliegen (die ook bladluis eten).",
        "advice.enemy": "{a} en {b} zijn slechte buren in {bed}",
        "advice.enemy.text": "{reason} Verplaats één van beide naar een ander bed.",
        "advice.better": "Betere buren: {plants}.",
        "advice.shade": "{tall} geeft schaduw op {short} in {bed}",
        "advice.shade.text": "Hoge gewassen horen aan de noordkant van een bed (bovenaan de kaart), zodat ze de zon niet "
        "wegnemen van {short}.",
        "advice.gaps": "Vul de oogstgaten",
        "advice.gaps.text": "Niets te oogsten in {months}. Voeg bijvoorbeeld {plants} toe - of bewaar meer van de zomeroogst.",
        "advice.empty_bed": "{bed} is leeg - zaai een snelle teelt",
        "advice.empty_bed.text": "Er is nog tijd voor een tussenteelt voor de vorst: {plants}.",
        "advice.empty_bed_late": "Dek {bed} af voor de winter",
        "advice.empty_bed_late.text": "Te laat voor groenten: zaai een groenbemester ({plants}) of mulch de grond.",
        "advice.empty_greenhouse": "Gebruik {bed} voor wintergroenten",
        "advice.empty_greenhouse.text": "Onder glas oogst je de hele winter: {plants}.",
        "advice.rotation": "{n} teelten breken de wisselteelt",
        "advice.rotation.text": "Dezelfde familie stond er recent - meer kans op bodemziekten. De planner toont voor elk "
        "een beter bed.",
        "advice.heat_stress": "Hittestress bij {plants}",
        "advice.heat_stress.text": "Geef 's middags schaduw, water 's ochtends en verlucht de serre volledig.",
        "advice.feed": "{bed} raakt uitgeput",
        "advice.feed.text": "Geef verdunde brandnetelgier (bladgewassen) of smeerwortelgier (vruchtgewassen) en strooi compost.",
        "advice.flowers": "Plant bloemen tussen de groenten",
        "advice.flowers.text": "Ongeveer een tiende bloemen ({flowers}) brengt bestuivers en natuurlijke plaagbestrijding.",
        "advice.year_transition": "Sluit {from} af en zet je tuin over naar {to}",
        "advice.year_transition.text": "Het nieuwe jaar is begonnen, maar niets gaat vanzelf mee: kies in de "
        "jaarovergang welk deel van het tuinplan, welke vaste planten en welke overwinterende gewassen naar {to} gaan. "
        "Tot dan krijgen ze geen taken voor {to}.",
        "advice.compost": "Teken een composthoop",
        "advice.compost.text": "Eigen compost is de beste en goedkoopste bodemverbeteraar - zet hem in een halfschaduwrijke hoek.",
        "advice.water_butt": "Vang regenwater op",
        "advice.water_butt.text": "Een regenton aan de goot van het tuinhuis of de serre geeft zacht, warm water en spaart leidingwater.",
        "advice.habitat": "Maak plaats voor helpers",
        "advice.habitat.text": "Een haag, een kleine vijver, een takkenhoop of een wilde hoek lokt egels, padden, vogels en "
        "loopkevers - je beste bestrijding van slakken en rupsen.",
        "advice.gh_sensor": "Zet een thermometer in de serre",
        "advice.gh_sensor.text": "Met een temperatuursensor kan Hortulus je waarschuwen voordat de serre oververhit raakt of bevriest. "
        "Zie het hoofdstuk over sensoren.",
    }
)

MESSAGES["fr"].update(
    {
        "overdue.title": "Potager : {count} tâches en attente",
        "voice.not_ready": "Hortulus est encore en train de démarrer, redemandez-moi dans une minute.",
        "voice.no_tasks": "Rien à faire au potager aujourd'hui. Profitez-en !",
        "voice.tasks": "{count} tâches au potager aujourd'hui, environ {minutes} minutes : {tasks}.",
        "voice.no_overdue": "Aucune tâche en retard au potager. Bravo !",
        "voice.overdue": "{count} tâches sont en retard : {tasks}.",
        "voice.harvest": "Prêt à récolter : {plants}.",
        "voice.no_harvest": "Rien n'est prêt à récolter pour le moment.",
        "voice.gh_temp": "Il fait {temp} degrés dans {zone}.",
        "voice.gh_no_sensor": "{zone} n'a pas de thermomètre associé.",
        "voice.gh_action.ventilate": "Ouvrez les aérations.",
        "voice.gh_action.shade": "Installez l'ombrage.",
        "voice.gh_action.close_up": "Fermez-la avant le soir.",
        "voice.gh_action.heat": "Il fait trop froid, allumez le chauffage.",
        "voice.no_greenhouse": "Vous n'avez pas de serre dans Hortulus.",
        "voice.water": "Oui, arrosez {beds}.",
        "voice.no_water": "Non, le sol est assez humide.",
        "voice.frost": "Oui, du gel est prévu, jusqu'à {temp} degrés. Couvrez les plantes sensibles.",
        "voice.no_frost": "Pas de gel prévu.",
        "desc.rain_water": "Eau de pluie dans les récupérateurs : environ {liters} L - utilisez-la d'abord.",
        "soil.adj.lime_dose": "Analyse de sol : épandez {grams} g de chaux agricole (pH trop bas), pas en même temps que le fumier.",
        "soil.adj.om_low": "Analyse de sol : peu de matière organique - moitié plus de compost.",
        "soil.adj.om_high": "Analyse de sol : beaucoup de matière organique - moins de compost nécessaire.",
        "soil.adj.pk_high": "Analyse de sol : phosphore et potassium élevés - moitié moins d'engrais, le compost suffit.",
        "soil.adj.pk_low": "Analyse de sol : phosphore ou potassium bas - un peu plus d'engrais organique (ou de cendre de bois pour K).",
        "soil.adj.ph_high": "Analyse de sol : pH au-dessus de 7,5 - pas de chaux ; le terreau de feuilles et le compost le font baisser lentement.",
        "weather.moved": "Déplacé au {date} à cause de la météo ({reason}).",
        "weather.no_good_day": "Alerte météo : {reason} prévu(e) - choisissez vous-même le meilleur moment ou protégez avec un voile.",
        "weather.problem.rain": "pluie",
        "weather.problem.frost": "gel",
        "weather.problem.heat": "chaleur",
        "weather.problem.wind": "vent fort",
        "overdue.window_closed": "trop tard maintenant - passez ou choisissez une alternative",
        "overdue.still_ok": "encore possible jusqu'au {date}",
        "overdue.do_now": "{days} jours de retard",
        "overdue.footer": "Ouvrez Hortulus pour valider, reporter ou passer.",
        "weekly.title": "Potager : votre semaine",
        "weekly.day": "{day} : {count} tâches (~{minutes} min)",
        "weekly.empty": "Une semaine calme - rien de prévu.",
        "maint.clean_pots": "Laver pots, caissettes et étiquettes",
        "maint.clean_pots.desc": "Frottez pots et caissettes de semis dans de l'eau chaude avec un peu de savon noir ou "
        "de vinaigre ; rincez et séchez au soleil. Des pots propres évitent la fonte des semis.",
        "maint.water_butts": "Nettoyer et raccorder les récupérateurs d'eau",
        "maint.water_butts.desc": "Retirez la vase, vérifiez le collecteur sur la descente de gouttière et posez un "
        "couvercle ou une fine moustiquaire (pas de larves de moustiques). L'eau de pluie est plus douce et plus "
        "tiède que l'eau du robinet - les plantes l'adorent.",
        "maint.irrigation_service": "Entretenir le goutte-à-goutte",
        "maint.irrigation_service.desc": "Rincez les conduites, nettoyez filtres et goutteurs (une nuit dans le vinaigre "
        "dissout le calcaire), cherchez les fuites et testez chaque vanne une fois.",
        "maint.green_manure_dig": "Faucher et incorporer l'engrais vert",
        "maint.green_manure_dig.desc": "Fauchez ou hachez l'engrais vert, laissez-le flétrir quelques jours et "
        "incorporez-le superficiellement dans les 10 premiers cm (sans travail du sol : laissez-le en paillage sous "
        "une bâche). Semez 3-4 semaines plus tard.",
        "maint.slug_patrol": "Commencer la ronde des limaces",
        "maint.slug_patrol.desc": "Faites le tour avec une lampe de poche au crépuscule ou après la pluie. Écologique : "
        "piège à bière (pot enterré, bord 2 cm au-dessus du sol), une planche sous laquelle elles se cachent, un "
        "anneau de cendre de bois, de gravillons ou de coquilles d'œuf broyées autour des semis ; accueillez "
        "hérissons, grives et carabes.",
        "maint.nettle_feed": "Préparer du purin d'ortie (azote)",
        "maint.nettle_feed.desc": "1 kg de jeunes orties (avant floraison) dans 10 l d'eau de pluie, remuez chaque "
        "jour, laissez fermenter 10-14 jours. Diluez à 1:10 pour les légumes-feuilles et les choux, 1:20 pour les "
        "semis. Un couvercle retient l'odeur.",
        "maint.comfrey_feed": "Préparer du purin de consoude (potassium)",
        "maint.comfrey_feed.desc": "Tassez des feuilles de consoude dans un seau percé de quelques trous au fond, "
        "lestez-les et récupérez le liquide noir (ou faites macérer 1 kg dans 10 l d'eau pendant 3 semaines). "
        "Diluez à 1:10 - l'engrais idéal pour tomates et fruits.",
        "maint.sow_winter_crops": "Semer pour les récoltes d'automne et d'hiver",
        "maint.sow_winter_crops.desc": "Dernière chance en pleine terre pour les légumes d'hiver : mâche, épinard, "
        "claytone de Cuba, roquette, pak-choï, chicorée frisée, navet à feuilles ; repiquez poireaux, chou frisé et "
        "chou d'hiver. Semez un engrais vert sur les planches vides.",
        "maint.hedge_trim": "Tailler la haie (après la nidification)",
        "maint.hedge_trim.desc": "Vérifiez d'abord qu'il n'y a pas de nids - les oiseaux nichent jusqu'à mi-août. "
        "Utilisez les tailles (broyées) en paillage ou au compost.",
        "maint.seed_saving": "Récolter ses graines",
        "maint.seed_saving.desc": "Choisissez les plus beaux fruits de variétés non hybrides (tomate, haricot, pois, "
        "laitue). Tomate : faites fermenter la pulpe 3 jours dans un verre d'eau, rincez et séchez. Conservez dans "
        "des enveloppes en papier, au frais et au sec.",
        "maint.fleece_ready": "Préparer voiles, tunnels et toiles antigel",
        "maint.fleece_ready.desc": "Vérifiez le voile d'hivernage et les arceaux, achetez ce qui manque ; de vieux "
        "draps et des cartons font aussi l'affaire pour une nuit de gel.",
        "maint.leaf_mould": "Ramasser les feuilles pour le terreau de feuilles",
        "maint.leaf_mould.desc": "Remplissez des sacs poubelle de feuilles mortes humides, percez quelques trous et "
        "laissez-les 1-2 ans : le meilleur terreau de semis et paillage gratuit. Évitez les feuilles malades "
        "(tavelure, rouille).",
        "maint.gutters": "Dégager les gouttières et le collecteur d'eau de pluie",
        "maint.gutters.desc": "Retirez les feuilles des gouttières, du filtre du récupérateur et des gouttières de la "
        "serre pour recueillir la pluie d'hiver.",
        "maint.nest_boxes": "Nettoyer les nichoirs et nourrir les oiseaux",
        "maint.nest_boxes.desc": "Videz les vieux nids (puces), rincez à l'eau bouillante - pas de produits chimiques. "
        "Les mésanges mangent des milliers de chenilles et de pucerons : accrochez le nichoir à 2-3 m, l'entrée "
        "tournée vers l'est.",
        "maint.storage_check": "Contrôler les réserves d'hiver",
        "maint.storage_check.desc": "Passez en revue pommes de terre, oignons, courges, pommes et légumes-racines : "
        "retirez tout ce qui ramollit ou pourrit, gardez le local sombre, hors gel et aéré.",
        "maint.gh_windows": "Laver les vitres de {zone}",
        "maint.gh_windows.desc": "Nettoyez le verre ou le polycarbonate dedans et dehors : un toit sale coûte 10-20 % "
        "de la lumière. Eau tiède avec du savon noir ou un trait de vinaigre, une brosse douce sur un manche, rincez "
        "au tuyau ; grattez les algues des recouvrements avec une étiquette de plante.",
        "maint.gh_windows_autumn": "Nettoyer les vitres de {zone} pour la lumière d'hiver",
        "maint.gh_windows_autumn.desc": "Lavez le blanc d'ombrage et la poussière de l'été pour que les cultures "
        "d'hiver profitent du moindre rayon.",
        "maint.gh_vents_check": "Vérifier aérations et ouvre-fenêtres de {zone}",
        "maint.gh_vents_check.desc": "Testez les ouvre-fenêtres automatiques (les vérins à cire faiblissent après "
        "quelques années), les ventilateurs et le thermomètre mini/maxi avant la première journée chaude.",
        "maint.gh_biocontrol": "Introduire les auxiliaires dans {zone}",
        "maint.gh_biocontrol.desc": "Dès 15 °C : lâchez Encarsia contre l'aleurode, Phytoseiulus contre l'araignée "
        "rouge et des larves de chrysope contre les pucerons. Accrochez des pièges jaunes englués pour surveiller. "
        "Une coupelle d'eau et quelques fleurs (souci, alysse) les retiennent sur place.",
        "maint.gh_winter_crops": "Planifier les cultures d'hiver dans {zone}",
        "maint.gh_winter_crops.desc": "Semez ou plantez maintenant pour récolter tout l'hiver sous abri : mâche, "
        "claytone de Cuba, épinard, pak-choï, mizuna, roquette, blette, oignon blanc ; laitue pour le début du "
        "printemps.",
        "maint.orchard_winter_wash": "Contrôle hivernal des arbres fruitiers dans {zone}",
        "maint.orchard_winter_wash.desc": "Par temps sec, cherchez chancres, fruits momifiés et œufs de pucerons ; "
        "brossez l'écorce qui se détache avec une brosse dure. Retirez les momies (moniliose) et le bois mort.",
        "maint.orchard_mow": "Tondre les allées du verger, laisser des bandes fleuries",
        "maint.orchard_mow.desc": "Gardez un cercle de 1 m sans herbe au pied des arbres (paillage), tondez les "
        "allées et laissez fleurir des bandes pour les pollinisateurs et les insectes prédateurs.",
        "maint.orchard_grease_bands": "Poser des bandes de glu sur les arbres de {zone}",
        "maint.orchard_grease_bands.desc": "Des bandes de glu à 1 m de hauteur empêchent les femelles aptères de la "
        "phalène hiémale de grimper pour pondre. Retirez-les en mars.",
        "maint.orchard_pollinators": "Aider les pollinisateurs dans {zone}",
        "maint.orchard_pollinators.desc": "La floraison approche : installez un hôtel à osmies (sud-est, 1-2 m), "
        "laissez fleurir les pissenlits dans l'herbe, ne traitez jamais pendant la floraison.",
        "weather.heat": "Chaleur en vue ({temp} °C le {day}) : protégez le potager",
        "weather.heat.desc": "Jusqu'à {temp} °C pendant {days} jour(s). Arrosez tôt le matin (5-8 h), au pied et en "
        "profondeur (10-20 l/m²) plutôt qu'un peu chaque soir ; paillez le sol nu sur 5-8 cm (tonte, paille) ; "
        "récoltez le matin ; ne semez, ne repiquez et ne taillez pas maintenant ; mettez les pots à l'ombre et "
        "prévoyez une coupelle d'eau pour les oiseaux et les insectes.",
        "weather.heat.shade": "Ombrez les cultures les plus sensibles à midi : {plants}. Pas de toile d'ombrage ? Un "
        "vieux voilage, un voile d'hivernage en double, un parasol ou un drap sur des piquets conviennent très bien.",
        "weather.heat.very": "Très chaud : tomates et poivrons perdent leurs fleurs au-delà de 32-35 °C - ombrez-les "
        "aussi. Contrôlez les pots et les jeunes plants deux fois par jour.",
        "weather.heat_gh": "Chaleur en vue : rafraîchissez {zone} ({temp} °C)",
        "weather.heat_gh.desc": "Ouvrez toutes les aérations et la porte tôt le matin, ne fermez la porte que si la "
        "nuit descend sous 12 °C ; blanc d'ombrage ou filet en place ; mouillez le sol et les allées à midi "
        "(l'évaporation rafraîchit de 3-5 °C) ; arrosez le matin ; un seau d'eau dans la serre tamponne la nuit.",
        "weather.dry": "Période sèche et chaude ({days} jours) : arrosez malin",
        "weather.dry.desc": "Un arrosage copieux par semaine (20 l/m²) plutôt qu'un peu chaque jour - les racines "
        "descendent plus profond. Binez une fois (« un binage vaut deux arrosages »), complétez le paillage, utilisez "
        "d'abord les récupérateurs et arrosez le matin. Des bouteilles enterrées ou des oyas (pots non émaillés) "
        "près des cultures gourmandes économisent la moitié de l'eau.",
        "weather.storm": "Tempête en vue ({day}) : mettez le potager à l'abri",
        "weather.storm.desc": "Rafales jusqu'à {wind} km/h. Fermez portes et aérations de la serre, lestez voiles et "
        "filets (pierres, sacs de sable, sardines), mettez pots et caissettes à l'abri et rangez tout ce qui traîne.",
        "weather.storm.tall": "Vérifiez tuteurs et liens des cultures hautes : {plants}.",
        "weather.rain": "Fortes pluies ({mm} mm le {day}) : après la pluie",
        "weather.after_storm": "Après la tempête ({day}) : faites le tour du jardin",
        "weather.after_storm.desc": "Les rafales ont atteint {wind} km/h. Rattachez et redressez les grandes cultures, vérifiez tuteurs, filets, voiles et la serre (portes, vitres) et ramassez les tiges cassées avant qu'elles ne pourrissent.",
        "weather.dry_logged": "Période sèche : {mm} mm de pluie en {days} jours",
        "weather.dry_logged.desc": "Il n'a presque pas plu ces derniers temps alors que les plantes continuaient à boire. Donnez aux planches assoiffées un bon arrosage (10-20 l/m²) tôt le matin plutôt que de petites doses chaque jour, paillez le sol nu et vérifiez les récupérateurs.",
        "weather.rain.desc": "Après la pluie : ronde des limaces au crépuscule (pièges à bière, ramassage), ne marchez "
        "pas sur les planches mouillées (utilisez une planche), videz soucoupes et pots, vérifiez que l'eau "
        "s'écoule. Attendez quelques jours avant de semer ; retirez les fruits pourris (botrytis).",
    }
)

MESSAGES["de"].update(
    {
        "overdue.title": "Garten: {count} Aufgaben noch offen",
        "voice.not_ready": "Hortulus startet noch, fragen Sie mich in einer Minute noch einmal.",
        "voice.no_tasks": "Heute gibt es im Garten nichts zu tun. Genießen Sie es!",
        "voice.tasks": "{count} Gartenaufgaben heute, etwa {minutes} Minuten: {tasks}.",
        "voice.no_overdue": "Keine überfälligen Gartenaufgaben. Gut gemacht!",
        "voice.overdue": "{count} Aufgaben sind überfällig: {tasks}.",
        "voice.harvest": "Erntereif: {plants}.",
        "voice.no_harvest": "Im Moment ist nichts erntereif.",
        "voice.gh_temp": "In {zone} sind es {temp} Grad.",
        "voice.gh_no_sensor": "Mit {zone} ist kein Thermometer verknüpft.",
        "voice.gh_action.ventilate": "Öffnen Sie die Lüftungsklappen.",
        "voice.gh_action.shade": "Bringen Sie die Schattierung an.",
        "voice.gh_action.close_up": "Schließen Sie es vor dem Abend.",
        "voice.gh_action.heat": "Es wird zu kalt, schalten Sie die Heizung ein.",
        "voice.no_greenhouse": "Sie haben in Hortulus kein Gewächshaus.",
        "voice.water": "Ja, gießen Sie {beds}.",
        "voice.no_water": "Nein, der Boden ist feucht genug.",
        "voice.frost": "Ja, es wird Frost bis {temp} Grad erwartet. Decken Sie empfindliche Pflanzen ab.",
        "voice.no_frost": "Kein Frost erwartet.",
        "desc.rain_water": "Regenwasser in den Tonnen: etwa {liters} L - zuerst dieses verwenden.",
        "soil.adj.lime_dose": "Bodenprobe: {grams} g Gartenkalk ausbringen (pH-Wert zu niedrig), nicht zusammen mit Mist.",
        "soil.adj.om_low": "Bodenprobe: wenig organische Substanz - Kompost um die Hälfte erhöht.",
        "soil.adj.om_high": "Bodenprobe: viel organische Substanz - weniger Kompost nötig.",
        "soil.adj.pk_high": "Bodenprobe: Phosphat und Kalium sind hoch - halbe Düngermenge, Kompost genügt.",
        "soil.adj.pk_low": "Bodenprobe: Phosphat oder Kalium ist niedrig - etwas zusätzlicher organischer Dünger (oder Holzasche für K).",
        "soil.adj.ph_high": "Bodenprobe: pH-Wert über 7,5 - kein Kalk; Laubkompost und Kompost senken ihn langsam.",
        "weather.moved": "Wegen des Wetters auf {date} verschoben ({reason}).",
        "weather.no_good_day": "Wetterwarnung: {reason} vorhergesagt - den besten Zeitpunkt selbst wählen oder mit Vlies schützen.",
        "weather.problem.rain": "Regen",
        "weather.problem.frost": "Frost",
        "weather.problem.heat": "Hitze",
        "weather.problem.wind": "starker Wind",
        "overdue.window_closed": "jetzt zu spät - überspringen oder eine Alternative wählen",
        "overdue.still_ok": "noch bis {date} möglich",
        "overdue.do_now": "{days} Tage zu spät",
        "overdue.footer": "Hortulus öffnen, um zu erledigen, zu verschieben oder zu überspringen.",
        "weekly.title": "Garten: Ihre kommende Woche",
        "weekly.day": "{day}: {count} Aufgaben (~{minutes} Min.)",
        "weekly.empty": "Eine ruhige Woche - nichts geplant.",
        # yearly garden work
        "maint.clean_pots": "Töpfe, Schalen und Etiketten waschen",
        "maint.clean_pots.desc": "Töpfe und Anzuchtschalen in heißem Wasser mit einem Spritzer Schmierseife oder etwas Essig "
        "schrubben, abspülen und in der Sonne trocknen. Saubere Töpfe beugen der Umfallkrankheit vor.",
        "maint.water_butts": "Regentonnen reinigen und anschließen",
        "maint.water_butts.desc": "Schlamm herausschöpfen, den Regensammler am Fallrohr prüfen und einen Deckel oder ein feines "
        "Netz auflegen (keine Mückenlarven). Regenwasser ist weicher und wärmer als Leitungswasser - die Pflanzen lieben es.",
        "maint.irrigation_service": "Die Tropfbewässerung warten",
        "maint.irrigation_service.desc": "Die Leitungen durchspülen, Filter und Tropfer reinigen (eine Nacht in Essig löst Kalk), "
        "auf Lecks prüfen und jedes Ventil einmal testen.",
        "maint.green_manure_dig": "Gründüngung abschneiden und einarbeiten",
        "maint.green_manure_dig.desc": "Die Gründüngung mähen oder hacken, einige Tage welken lassen und flach in die "
        "obersten 10 cm einarbeiten (ohne Umgraben: als Mulch unter einer Abdeckung liegen lassen). 3-4 Wochen später säen.",
        "maint.slug_patrol": "Mit der Schneckenkontrolle beginnen",
        "maint.slug_patrol.desc": "Nach der Dämmerung oder nach Regen mit der Taschenlampe die Runde machen. Ökologisch: Bierfalle "
        "(eingegrabenes Glas, Rand 2 cm über dem Boden), ein Brett, unter dem sie sich sammeln, ein Ring aus Holzasche, Splitt oder "
        "zerstoßenen Eierschalen um Sämlinge; Igel, Drosseln und Laufkäfer willkommen heißen.",
        "maint.nettle_feed": "Brennnesseljauche ansetzen (Stickstoff)",
        "maint.nettle_feed.desc": "1 kg junge Brennnesseln (vor der Blüte) in 10 l Regenwasser, täglich umrühren, 10-14 Tage "
        "gären lassen. 1:10 verdünnt für Blattgemüse und Kohl, 1:20 für Sämlinge. Ein Deckel hält den Geruch zurück.",
        "maint.comfrey_feed": "Beinwelljauche ansetzen (Kalium)",
        "maint.comfrey_feed.desc": "Beinwellblätter in einen Eimer mit einigen Löchern im Boden packen, beschweren und die "
        "schwarze Flüssigkeit auffangen (oder 1 kg 3 Wochen lang in 10 l Wasser einweichen). 1:10 verdünnen - perfekter Dünger "
        "für Tomaten und Obst.",
        "maint.sow_winter_crops": "Für die Herbst- und Winterernte säen",
        "maint.sow_winter_crops.desc": "Letzte Gelegenheit im Freien für Winterkulturen: Feldsalat, Spinat, Winterportulak, "
        "Rucola, Pak Choi, Endivie, Stielmus; Lauch, Grünkohl und Winterkohl auspflanzen. Leere Beete mit Gründüngung einsäen.",
        "maint.hedge_trim": "Die Hecke schneiden (nach der Brutzeit)",
        "maint.hedge_trim.desc": "Zuerst nach Nestern sehen - Vögel brüten bis Mitte August. Den Schnitt als Mulch "
        "oder (gehäckselt) im Kompost verwenden.",
        "maint.seed_saving": "Saatgut gewinnen",
        "maint.seed_saving.desc": "Die besten Früchte samenfester Sorten auswählen (Tomate, Bohne, Erbse, Salat). "
        "Tomate: das Fruchtfleisch 3 Tage in einem Glas Wasser gären lassen, abspülen und trocknen. In Papiertüten kühl und trocken lagern.",
        "maint.fleece_ready": "Vlies, Folientunnel und Frostschutzgewebe bereitlegen",
        "maint.fleece_ready.desc": "Vlies und Bögen prüfen, Fehlendes kaufen; alte Bettlaken und Pappkartons "
        "helfen auch für eine Frostnacht.",
        "maint.leaf_mould": "Laub für Laubkompost sammeln",
        "maint.leaf_mould.desc": "Müllsäcke mit feuchtem Herbstlaub füllen, einige Löcher hineinstechen und 1-2 Jahre liegen lassen: "
        "die beste kostenlose Anzuchterde und Mulch. Kranke Blätter (Schorf, Rost) aussortieren.",
        "maint.gutters": "Dachrinnen und Regensammler reinigen",
        "maint.gutters.desc": "Laub aus den Dachrinnen, dem Filter der Regentonne und den Gewächshausrinnen entfernen, damit der "
        "Winterregen aufgefangen wird.",
        "maint.nest_boxes": "Nistkästen reinigen und die Vögel füttern",
        "maint.nest_boxes.desc": "Alte Nester entfernen (Flöhe), mit kochendem Wasser ausspülen - keine Chemie. Meisen fressen "
        "Tausende Raupen und Blattläuse: den Kasten in 2-3 m Höhe aufhängen, Einflugloch nach Osten.",
        "maint.storage_check": "Das Winterlager kontrollieren",
        "maint.storage_check.desc": "Kartoffeln, Zwiebeln, Kürbisse, Äpfel und Wurzelgemüse durchsehen: alles Weiche oder "
        "Faulende entfernen, das Lager dunkel, frostfrei und luftig halten.",
        # greenhouse
        "maint.gh_windows": "Die Scheiben von {zone} putzen",
        "maint.gh_windows.desc": "Glas oder Polycarbonat innen und außen reinigen: ein schmutziges Dach kostet 10-20 % des Lichts. "
        "Warmes Wasser mit Schmierseife oder einem Schuss Essig, eine weiche Bürste an einem Stiel, mit dem Schlauch abspülen; "
        "Algen mit einem Pflanzenetikett aus den Überlappungen kratzen.",
        "maint.gh_windows_autumn": "Das Glas von {zone} für das Winterlicht reinigen",
        "maint.gh_windows_autumn.desc": "Schattierfarbe und Sommerschmutz abwaschen, damit Winterkulturen jeden Lichtstrahl bekommen.",
        "maint.gh_vents_check": "Lüftungsklappen und Fensteröffner in {zone} prüfen",
        "maint.gh_vents_check.desc": "Die automatischen Fensteröffner testen (Wachszylinder lassen nach einigen Jahren nach), "
        "ebenso Ventilatoren und das Min/Max-Thermometer, vor dem ersten warmen Tag.",
        "maint.gh_biocontrol": "Nützlinge in {zone} einsetzen",
        "maint.gh_biocontrol.desc": "Ab 15 °C: Encarsia gegen die Weiße Fliege, Phytoseiulus gegen Spinnmilben und "
        "Florfliegenlarven gegen Blattläuse freilassen. Gelbtafeln zur Kontrolle aufhängen. Eine Schale Wasser und einige Blumen "
        "(Ringelblume, Steinkraut) halten sie dort.",
        "maint.gh_winter_crops": "Winterkulturen in {zone} planen",
        "maint.gh_winter_crops.desc": "Jetzt säen oder pflanzen für Ernten den ganzen Winter unter Glas: Feldsalat, Winterportulak, "
        "Spinat, Pak Choi, Mizuna, Rucola, Mangold, Frühlingszwiebeln; Salat für das zeitige Frühjahr.",
        # orchard
        "maint.orchard_winter_wash": "Winterkontrolle der Obstbäume in {zone}",
        "maint.orchard_winter_wash.desc": "An einem trockenen Tag nach Krebs, Fruchtmumien und Blattlauseiern suchen; lose Rinde "
        "mit einer harten Bürste abbürsten. Mumien (Monilia) und Totholz entfernen.",
        "maint.orchard_mow": "Wege im Obstgarten mähen, Blühstreifen stehen lassen",
        "maint.orchard_mow.desc": "Eine Baumscheibe von 1 m grasfrei halten (Mulch), die Wege mähen und Streifen für Bestäuber "
        "und Raubinsekten blühen lassen.",
        "maint.orchard_grease_bands": "Leimringe an den Bäumen in {zone} anbringen",
        "maint.orchard_grease_bands.desc": "Leimringe in 1 m Höhe hindern die flügellosen Weibchen des Frostspanners daran, "
        "zur Eiablage hinaufzuklettern. Im März wieder entfernen.",
        "maint.orchard_pollinators": "Den Bestäubern in {zone} helfen",
        "maint.orchard_pollinators.desc": "Die Blüte kommt: ein Mauerbienenhaus aufhängen (Südost, 1-2 m), Löwenzahn im Rasen "
        "blühen lassen, niemals während der Blüte spritzen.",
        # weather episodes
        "weather.heat": "Hitze im Anmarsch ({temp} °C am {day}): den Garten schützen",
        "weather.heat.desc": "Bis zu {temp} °C über {days} Tag(e). Früh am Morgen gießen (5-8 Uhr), an die Wurzeln und "
        "durchdringend (10-20 l/m²) statt jeden Abend ein wenig; offenen Boden 5-8 cm hoch mulchen (Rasenschnitt, Stroh); "
        "morgens ernten; jetzt nicht säen, auspflanzen oder schneiden; Töpfe in den Schatten stellen und eine Schale "
        "Wasser für Vögel und Insekten aufstellen.",
        "weather.heat.shade": "Die empfindlichsten Kulturen mittags schattieren: {plants}. Kein Schattiernetz? Eine alte Gardine, "
        "eine doppelte Lage Vlies, ein Sonnenschirm oder ein Bettlaken auf Stäben tun es auch.",
        "weather.heat.very": "Sehr heiß: Tomaten und Paprika werfen über 32-35 °C Blüten ab - auch sie schattieren. "
        "Töpfe und Jungpflanzen zweimal täglich kontrollieren.",
        "weather.heat_gh": "Hitze im Anmarsch: {zone} kühlen ({temp} °C)",
        "weather.heat_gh.desc": "Früh am Morgen alle Lüftungsklappen und die Tür öffnen, die Tür nur schließen, wenn die Nächte "
        "unter 12 °C fallen; Schattierfarbe oder -netz anbringen; mittags Boden und Wege befeuchten (Verdunstung kühlt um 3-5 °C); "
        "morgens gießen; ein Eimer Wasser im Gewächshaus puffert die Nacht ab.",
        "weather.dry": "Trockene, warme Phase ({days} Tage): klug gießen",
        "weather.dry.desc": "Einmal pro Woche durchdringend gießen (20 l/m²) statt täglich zu sprenkeln - die Wurzeln wachsen tiefer. "
        "Einmal hacken („einmal hacken spart zweimal gießen“), Mulch nachlegen, zuerst die Regentonnen nutzen und morgens "
        "gießen. Eingegrabene Flaschen oder Ollas (unglasierte Tontöpfe) neben durstigen Kulturen sparen die Hälfte des Wassers.",
        "weather.storm": "Sturm im Anmarsch ({day}): den Garten sturmfest machen",
        "weather.storm.desc": "Windböen bis {wind} km/h. Türen und Lüftungsklappen des Gewächshauses schließen, Vlies und Netze "
        "beschweren (Steine, Sandsäcke, Zeltheringe), Töpfe und Anzuchtschalen an einen geschützten Ort bringen und lose Gegenstände wegräumen.",
        "weather.storm.tall": "Stäbe und Bindungen hoher Kulturen prüfen: {plants}.",
        "weather.rain": "Starkregen ({mm} mm am {day}): Nachsorge",
        "weather.after_storm": "Nach dem Sturm ({day}): den Garten kontrollieren",
        "weather.after_storm.desc": "Die Böen erreichten {wind} km/h. Hohe Kulturen neu anbinden und aufrichten, Stäbe, Netze, Vlies und das Gewächshaus (Türen, Scheiben) kontrollieren und abgeknickte Stängel einsammeln, bevor sie faulen.",
        "weather.dry_logged": "Trockenphase: {mm} mm Regen in {days} Tagen",
        "weather.dry_logged.desc": "In letzter Zeit ist kaum Regen gefallen, während die Pflanzen weiter getrunken haben. Durstige Beete einmal früh am Tag durchdringend gießen (10-20 l/m²) statt täglich ein wenig, offenen Boden mulchen und die Regentonnen kontrollieren.",
        "weather.rain.desc": "Nach dem Regen: Schneckenrunde in der Dämmerung (Bierfallen, absammeln), nasse Beete nicht betreten "
        "(ein Brett benutzen), Untersetzer und Töpfe leeren, prüfen, ob das Wasser abläuft. Mit dem Säen einige Tage warten; "
        "faulende Früchte entfernen (Grauschimmel).",
    }
)

MESSAGES["fr"].update(
    {
        "method.indoor_sow": "Semis à l'intérieur",
        "method.direct_sow": "Semis en pleine terre",
        "method.transplant": "Repiquage",
        "moisture.dry": "sec",
        "moisture.slightly_dry": "un peu sec",
        "moisture.optimal": "parfait",
        "moisture.wet": "humide",
        "moisture.unknown": "inconnu",
        "pollination.insects": "Pollinisé par les insectes - des fleurs à proximité aident.",
        "pollination.wind": "Pollinisé par le vent - plantez en blocs.",
        "pollination.partner": "A besoin d'une deuxième variété à proximité pour fructifier.",
        "advice.whole_garden": "Tout le jardin",
        "advice.tools": "Outils et fournitures",
        "advice.partner": "{plant} a besoin d'un pollinisateur",
        "advice.partner.text": "Pas de deuxième variété de {plant} à proximité. Plantez une autre variété qui fleurit en "
        "même temps (dans un rayon d'environ 50 m - l'arbre du voisin compte), ou greffez une branche pollinisatrice.",
        "advice.pollinators": "Ajoutez des fleurs pour les pollinisateurs dans {zone}",
        "advice.pollinators.text": "{plants} ont besoin d'insectes pour fructifier. Une bande de {flowers} attire abeilles "
        "et syrphes (qui mangent aussi les pucerons).",
        "advice.enemy": "{a} et {b} sont de mauvais voisins dans {bed}",
        "advice.enemy.text": "{reason} Déplacez l'un des deux vers une autre planche.",
        "advice.better": "Meilleurs voisins : {plants}.",
        "advice.shade": "{tall} fait de l'ombre à {short} dans {bed}",
        "advice.shade.text": "Les cultures hautes vont du côté nord de la planche (en haut du plan) pour ne pas voler le "
        "soleil à {short}.",
        "advice.gaps": "Comblez les creux de récolte",
        "advice.gaps.text": "Rien à récolter en {months}. Ajoutez par exemple {plants} - ou conservez davantage de la "
        "récolte d'été.",
        "advice.empty_bed": "{bed} est vide - semez une culture rapide",
        "advice.empty_bed.text": "Il reste du temps pour une culture dérobée avant le gel : {plants}.",
        "advice.empty_bed_late": "Couvrez {bed} pour l'hiver",
        "advice.empty_bed_late.text": "Trop tard pour des légumes : semez un engrais vert ({plants}) ou paillez le sol.",
        "advice.empty_greenhouse": "Utilisez {bed} pour les cultures d'hiver",
        "advice.empty_greenhouse.text": "Sous abri, on récolte tout l'hiver : {plants}.",
        "advice.rotation": "{n} cultures ne respectent pas la rotation",
        "advice.rotation.text": "La même famille y a poussé récemment - risque accru de maladies du sol. Le planning "
        "indique de meilleures planches pour chacune.",
        "advice.heat_stress": "Stress thermique sur {plants}",
        "advice.heat_stress.text": "Ombrez à midi, arrosez le matin et aérez complètement la serre.",
        "advice.feed": "{bed} manque de nutriments",
        "advice.feed.text": "Apportez du purin d'ortie dilué (légumes-feuilles) ou du purin de consoude (légumes-fruits) "
        "et une couche de compost.",
        "advice.flowers": "Plantez des fleurs entre les légumes",
        "advice.flowers.text": "Environ un dixième de fleurs ({flowers}) attire pollinisateurs et lutte naturelle contre "
        "les ravageurs.",
        "advice.year_transition": "Clôturez {from} et passez à {to}",
        "advice.year_transition.text": "La nouvelle année a commencé, mais rien n'est reporté automatiquement : "
        "choisissez lors du passage d'année quelle partie du plan, quelles vivaces et quelles cultures hivernantes "
        "passent à {to}. D'ici là, elles n'ont pas de tâches pour {to}.",
        "advice.compost": "Dessinez un tas de compost",
        "advice.compost.text": "Votre propre compost est le meilleur amendement et le moins cher - placez-le dans un coin "
        "mi-ombragé.",
        "advice.water_butt": "Récupérez l'eau de pluie",
        "advice.water_butt.text": "Un récupérateur sur la gouttière de l'abri ou de la serre donne une eau douce et tiède "
        "et économise l'eau du robinet.",
        "advice.habitat": "Faites de la place aux auxiliaires",
        "advice.habitat.text": "Une haie, une petite mare, un tas de bois ou un coin sauvage attire hérissons, crapauds, "
        "oiseaux et carabes - vos meilleurs alliés contre limaces et chenilles.",
        "advice.gh_sensor": "Ajoutez un thermomètre dans la serre",
        "advice.gh_sensor.text": "Avec une sonde de température, Hortulus peut vous prévenir avant que la serre ne "
        "surchauffe ou ne gèle. Voir le chapitre sur les capteurs.",
    }
)

MESSAGES["de"].update(
    {
        "method.indoor_sow": "Drinnen vorziehen",
        "method.direct_sow": "Direktsaat im Freien",
        "method.transplant": "Auspflanzen",
        "moisture.dry": "trocken",
        "moisture.slightly_dry": "etwas trocken",
        "moisture.optimal": "genau richtig",
        "moisture.wet": "nass",
        "moisture.unknown": "unbekannt",
        "pollination.insects": "Insektenbestäubt - Blumen in der Nähe helfen.",
        "pollination.wind": "Windbestäubt - in Blöcken pflanzen.",
        "pollination.partner": "Braucht eine zweite Sorte in der Nähe, um Früchte anzusetzen.",
        "advice.whole_garden": "Ganzer Garten",
        "advice.tools": "Werkzeug und Zubehör",
        "advice.partner": "{plant} braucht einen Befruchterpartner",
        "advice.partner.text": "Keine zweite Sorte von {plant} in der Nähe. Eine andere Sorte pflanzen, die zur gleichen Zeit "
        "blüht (im Umkreis von etwa 50 m - ein Baum beim Nachbarn zählt mit), oder einen Befruchterast aufveredeln.",
        "advice.pollinators": "Blumen für die Bestäuber in {zone} pflanzen",
        "advice.pollinators.text": "{plants} brauchen Insekten, um Früchte anzusetzen. Ein Streifen {flowers} lockt Bienen und "
        "Schwebfliegen an (die auch Blattläuse fressen).",
        "advice.enemy": "{a} und {b} sind schlechte Nachbarn in {bed}",
        "advice.enemy.text": "{reason} Eine der beiden Kulturen in ein anderes Beet umsetzen.",
        "advice.better": "Bessere Nachbarn: {plants}.",
        "advice.shade": "{tall} beschattet {short} in {bed}",
        "advice.shade.text": "Hohe Kulturen gehören an die Nordseite eines Beets (oben auf dem Plan), damit sie {short} "
        "nicht die Sonne nehmen.",
        "advice.gaps": "Die Erntelücken füllen",
        "advice.gaps.text": "Im {months} gibt es nichts zu ernten. Zum Beispiel {plants} ergänzen - oder mehr von der "
        "Sommerernte einlagern.",
        "advice.empty_bed": "{bed} ist leer - eine schnelle Kultur säen",
        "advice.empty_bed.text": "Vor dem Frost ist noch Zeit für eine Zwischenkultur: {plants}.",
        "advice.empty_bed_late": "{bed} für den Winter abdecken",
        "advice.empty_bed_late.text": "Zu spät für Gemüse: eine Gründüngung ({plants}) säen oder den Boden mulchen.",
        "advice.empty_greenhouse": "{bed} für Winterkulturen nutzen",
        "advice.empty_greenhouse.text": "Unter Glas lässt sich den ganzen Winter ernten: {plants}.",
        "advice.rotation": "{n} Kulturen verletzen die Fruchtfolge",
        "advice.rotation.text": "Dieselbe Familie stand dort vor Kurzem - höheres Risiko für Bodenkrankheiten. Der Planer zeigt "
        "für jede davon bessere Beete.",
        "advice.heat_stress": "Hitzestress bei {plants}",
        "advice.heat_stress.text": "Mittags schattieren, morgens gießen und das Gewächshaus vollständig lüften.",
        "advice.feed": "{bed} gehen die Nährstoffe aus",
        "advice.feed.text": "Mit verdünnter Brennnesseljauche (Blattgemüse) oder Beinwelljauche (Fruchtgemüse) düngen und Kompost aufbringen.",
        "advice.flowers": "Blumen zwischen das Gemüse pflanzen",
        "advice.flowers.text": "Etwa ein Zehntel Blumen ({flowers}) bringt Bestäuber und natürliche Schädlingsregulierung.",
        "advice.year_transition": "{from} abschließen und zu {to} wechseln",
        "advice.year_transition.text": "Das neue Jahr hat begonnen, aber nichts wird von selbst übernommen: Wählen Sie beim "
        "Jahreswechsel, welcher Teil des Gartenplans, welche Stauden und welche überwinternden Kulturen nach {to} "
        "übernommen werden. Bis dahin erhalten sie keine Aufgaben für {to}.",
        "advice.compost": "Einen Komposthaufen einzeichnen",
        "advice.compost.text": "Eigener Kompost ist der beste und günstigste Bodenverbesserer - am besten in einer halbschattigen Ecke.",
        "advice.water_butt": "Regenwasser auffangen",
        "advice.water_butt.text": "Eine Regentonne an der Dachrinne von Schuppen oder Gewächshaus liefert weiches, warmes Wasser und spart Leitungswasser.",
        "advice.habitat": "Platz für Nützlinge schaffen",
        "advice.habitat.text": "Eine Hecke, ein kleiner Teich, ein Holzstapel oder eine wilde Ecke lockt Igel, Kröten, Vögel und "
        "Laufkäfer an - die beste Abwehr gegen Schnecken und Raupen.",
        "advice.gh_sensor": "Ein Thermometer ins Gewächshaus hängen",
        "advice.gh_sensor.text": "Mit einem Temperatursensor kann Hortulus warnen, bevor das Gewächshaus überhitzt oder einfriert. "
        "Siehe das Kapitel über Sensoren.",
    }
)
