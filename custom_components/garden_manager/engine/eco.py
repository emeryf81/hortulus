"""Ecological gardening and permaculture: recommended, never required.

* Organic help with every pest warning and disease check: natural enemies,
  plant extracts (nettle, horsetail, garlic), trap crops and good habits.
* Extra seasonal work for a living garden in the calendar: flower strips for
  hoverflies and parasitic wasps, horsetail tea against fungi, no-dig
  mulching instead of digging, a wild corner, insect hotels, a drinking dish.
* Food forest (forest garden): a zone type built in layers - canopy,
  sub-canopy, shrubs, herbs, ground cover, roots, climbers - with advice on
  the layers still missing.
* A tip of the month on the advice page.

Everything follows ``GardenSettings.eco_tips`` (on by default) and can be
switched off in the settings.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .i18n import MESSAGES, t
from .models import GardenData, Plant, PlantCategory, PlantingStatus, ZoneType, present_in
from .plantdb import PlantDatabase

LAYERS = ("canopy", "sub_canopy", "shrub", "herb", "ground", "root", "climber")


def forest_layer(plant: Plant) -> str | None:
    """The food-forest layer a perennial plant belongs to (None for annuals)."""
    if not plant.perennial:
        return None
    habit = plant.habit.value
    if habit in ("climbing", "vine"):
        return "climber"
    if habit in ("root", "bulb"):
        return "root"
    h = plant.height_cm
    if plant.category is PlantCategory.FRUIT and h >= 450:
        return "canopy"
    if h >= 250:
        return "sub_canopy"
    if h >= 90:
        return "shrub"
    if h >= 30:
        return "herb"
    return "ground"


@dataclass(slots=True)
class ForestLayers:
    zone_id: str
    present: dict[str, list[str]]  # layer -> plant ids
    missing: list[str]
    suggestions: dict[str, list[str]]  # missing layer -> plant ids from the database

    def to_dict(self) -> dict[str, object]:
        return {
            "zone_id": self.zone_id,
            "present": self.present,
            "missing": self.missing,
            "suggestions": self.suggestions,
        }


def food_forest_layers(data: GardenData, db: PlantDatabase, season: int) -> list[ForestLayers]:
    """Per food-forest zone: which layers are planted and which are still empty."""
    out: list[ForestLayers] = []
    for zone in data.zones:
        if zone.type is not ZoneType.FOOD_FOREST:
            continue
        beds = {b.id for b in data.beds if b.zone_id == zone.id}
        present: dict[str, list[str]] = {}
        for p in data.plantings:
            plant = db.get(p.plant_id)
            if p.bed_id not in beds or plant is None or p.status is PlantingStatus.FAILED:
                continue
            if not present_in(p, plant.perennial, season):
                continue
            layer = forest_layer(plant)
            if layer and plant.id not in present.setdefault(layer, []):
                present[layer].append(plant.id)
        missing = [layer for layer in LAYERS if layer not in present]
        suggestions: dict[str, list[str]] = {}
        for layer in missing:
            ids = [pl.id for pl in db.all() if forest_layer(pl) == layer]
            suggestions[layer] = sorted(ids)[:4]
        out.append(ForestLayers(zone.id, present, missing, suggestions))
    return out


def pest_bio(pest: str, lang: str | None) -> str:
    key = f"bio.pest.{pest}"
    return t(key, lang) if key in MESSAGES["en"] else ""


def with_bio(text: str, pest: str, lang: str | None, eco: bool) -> str:
    """Append the organic tip for this pest (when ecological tips are on)."""
    bio = pest_bio(pest, lang) if eco else ""
    return f"{text} {t('bio.prefix', lang)} {bio}" if bio else text


def month_tip(month: int, lang: str | None) -> tuple[str, str]:
    return t(f"eco.month.{month}", lang), t(f"eco.month.{month}.text", lang)


# --------------------------------------------------------------------------- #
# Texts
# --------------------------------------------------------------------------- #
_EN = {
    "bio.prefix": "Organic:",
    "bio.pest.carrot_fly": "sow thinly so you need not thin, sow after the first flight (June) and mix rows of onions or leeks between the carrots - the smell confuses the fly.",
    "bio.pest.cabbage_root_fly": "plant brassicas firmly, earth them up a little and keep the soil alive with compost; ground beetles and rove beetles eat the eggs.",
    "bio.pest.cabbage_white": "sow nasturtium as a trap crop away from the cabbages and let parasitic wasps work - leave yellow cocoons on the leaves alone.",
    "bio.pest.onion_fly": "mix onions with carrots, sow late and avoid fresh manure; sets suffer less than seed-sown onions.",
    "bio.pest.leek_moth": "plant leeks among carrots or celery and keep birds around (nest boxes) - tits eat the caterpillars.",
    "bio.pest.pea_moth": "sow early or late peas outside the flight (June-July) and leave a wild corner for parasitic wasps.",
    "bio.pest.flea_beetle": "keep the soil moist (they hate it), mulch between the plants and cover young brassicas with fleece.",
    "bio.pest.aphids": "spray a cold nettle extract (1 kg nettles, 10 l water, 24 h, undiluted) and sow dill, calendula and phacelia for hoverflies, lacewings and ladybirds.",
    "bio.pest.black_bean_aphid": "pinch out the bean tips once the first pods set, sow broad beans early and leave the ladybirds to it.",
    "bio.pest.colorado_beetle": "pick daily, plant catmint, coriander or flax between the potatoes and leave room for ground beetles.",
    "bio.pest.asparagus_beetle": "pick the beetles in the morning and leave a few tomato plants nearby - their smell keeps them away.",
    "bio.pest.whitefly": "hang yellow sticky cards, plant French marigold (Tagetes) between the tomatoes and introduce Encarsia wasps in the greenhouse.",
    "bio.pest.red_spider_mite": "keep the greenhouse air humid (mist the paths) and release predatory mites (Phytoseiulus) at the first spots.",
    "bio.pest.slugs": "welcome hedgehogs, toads and ground beetles (a log pile, a pond), water in the morning instead of the evening, and lay wool or a ring of dry bran around young plants.",
    "bio.disease": "Organic: spray horsetail tea preventively (every 1-2 weeks), mulch so no soil splashes on the leaves, and choose resistant varieties next year.",
    "maint.eco_flower_strip": "Sow a flower strip for helpful insects",
    "maint.eco_flower_strip.desc": "Phacelia, calendula, cornflower, dill and buckwheat along the beds feed hoverflies, lacewings and parasitic wasps - they keep aphids and caterpillars down.",
    "maint.eco_horsetail": "Make horsetail tea (against fungi)",
    "maint.eco_horsetail.desc": "Boil 150 g dried (1 kg fresh) horsetail in 10 l rain water for 30 minutes, leave overnight, dilute 1:5 and spray on tomatoes, potatoes and courgettes every 1-2 weeks in damp weather.",
    "maint.eco_no_dig": "Feed the soil instead of digging (no-dig)",
    "maint.eco_no_dig.desc": "Spread 3-5 cm compost, leaves or straw on the empty beds. Worms work it in over winter; the soil life stays intact and weeds get less chance.",
    "maint.eco_wild_corner": "Leave a wild corner and seed heads",
    "maint.eco_wild_corner.desc": "A log pile, leaves under the hedge and hollow stems standing until spring: hedgehogs, ladybirds and solitary bees overwinter there.",
    "maint.eco_insect_hotel": "Check the insect hotel",
    "maint.eco_insect_hotel.desc": "Replace split or mouldy tubes and add new reeds or drilled hardwood (holes 3-8 mm) before the solitary bees fly.",
    "maint.eco_stems": "Cut back last year's stems now",
    "maint.eco_stems.desc": "Insects that overwintered in the hollow stems are flying again: cut the stems back and leave them in a heap for a few weeks.",
    "maint.eco_water_dish": "Put out a drinking dish for birds and bees",
    "maint.eco_water_dish.desc": "A shallow dish with stones to land on, refreshed every few days, helps birds and insects through dry spells.",
    "eco.month.1": "Plan for diversity",
    "eco.month.1.text": "Mix families in every bed, add flowers and herbs, and plan a corner of perennials - a varied garden has fewer pests.",
    "eco.month.2": "Clean nest boxes, feed the soil",
    "eco.month.2.text": "Birds are prospecting: hang clean nest boxes. Spread compost on the beds instead of digging.",
    "eco.month.3": "Make room for helpers",
    "eco.month.3.text": "Leave the dandelions in the lawn: they are the first food for bumblebees. Check the insect hotel.",
    "eco.month.4": "Nettles: free feed",
    "eco.month.4.text": "Young nettles make the best nettle feed (1:10 as feed, cold extract undiluted against aphids). Leave a patch for the butterflies.",
    "eco.month.5": "Mulch and flowers",
    "eco.month.5.text": "Mulch the warm soil with grass clippings and sow a flower strip - hoverflies arrive in time for the first aphids.",
    "eco.month.6": "Water wisely",
    "eco.month.6.text": "Water in the morning at the foot of the plants, catch rain from every roof and keep the soil covered.",
    "eco.month.7": "Let them be",
    "eco.month.7.text": "A few aphids feed ladybird larvae. Wait a week before you act - nature often solves it.",
    "eco.month.8": "Green manure after the harvest",
    "eco.month.8.text": "Sow phacelia, clover or winter rye on every empty spot: no bare soil, more soil life, nitrogen for next year.",
    "eco.month.9": "Save your own seed",
    "eco.month.9.text": "Let the best beans, tomatoes and lettuce run to seed - adapted to your garden and free.",
    "eco.month.10": "Leaves are gold",
    "eco.month.10.text": "Rake leaves onto the beds or into a wire bin for leaf mould. Never burn them.",
    "eco.month.11": "Plant trees and shrubs",
    "eco.month.11.text": "Bare-root fruit trees, berries and native hedges now: the start of a food forest or a living hedge.",
    "eco.month.12": "Rest and look back",
    "eco.month.12.text": "Leave seed heads for the birds, look at what worked and plan more perennials for an easier garden.",
    "forest.layer.canopy": "Canopy",
    "forest.layer.sub_canopy": "Low trees",
    "forest.layer.shrub": "Shrubs",
    "forest.layer.herb": "Herbs & perennials",
    "forest.layer.ground": "Ground cover",
    "forest.layer.root": "Roots & bulbs",
    "forest.layer.climber": "Climbers",
    "advice.food_forest": "Food forest {zone}: still to fill: {layers}",
    "advice.food_forest.text": "A food forest copies a young forest edge: every layer has its plants and together they feed, shelter and protect each other. Ideas: {plants}.",
    "advice.food_forest_try": "Turn {zone} into a food forest",
    "advice.food_forest_try.text": "Under and between the fruit trees there is room for berries, herbs, ground cover and climbers. Change the zone type to food forest: Hortulus then shows the layers still missing.",
    "advice.eco_month": "Ecological tip: {title}",
    "advice.eco_month.text": "{text}",
    "advice.polyculture": "{bed}: one family only",
    "advice.polyculture.text": "Everything in {bed} is {family}. Mix in another family, a herb or a flower - mixed beds have fewer pests and use the soil better.",
}
_NL = {
    "bio.prefix": "Biologisch:",
    "bio.pest.carrot_fly": "zaai dun zodat je niet hoeft uit te dunnen, zaai na de eerste vlucht (juni) en zet rijen uien of prei tussen de wortels - de geur brengt de vlieg in de war.",
    "bio.pest.cabbage_root_fly": "plant kolen stevig, aard ze wat aan en houd de grond levend met compost; loopkevers en kortschildkevers eten de eitjes.",
    "bio.pest.cabbage_white": "zaai Oost-Indische kers als vangplant, uit de buurt van de kolen, en laat sluipwespen hun werk doen - laat gele cocons op de bladeren met rust.",
    "bio.pest.onion_fly": "zet uien tussen wortels, zaai laat en gebruik geen verse mest; plantuitjes hebben minder last dan gezaaide uien.",
    "bio.pest.leek_moth": "plant prei tussen wortels of selder en houd vogels in de tuin (nestkastjes) - mezen eten de rupsjes.",
    "bio.pest.pea_moth": "zaai erwten vroeg of laat, buiten de vlucht (juni-juli), en laat een wilde hoek voor sluipwespen.",
    "bio.pest.flea_beetle": "houd de grond vochtig (daar houden ze niet van), mulch tussen de planten en dek jonge kolen af met vlies.",
    "bio.pest.aphids": "spuit koud brandnetelextract (1 kg brandnetels, 10 l water, 24 uur, onverdund) en zaai dille, goudsbloem en phacelia voor zweefvliegen, gaasvliegen en lieveheersbeestjes.",
    "bio.pest.black_bean_aphid": "knip de toppen van de tuinbonen af zodra de eerste peulen zetten, zaai tuinbonen vroeg en laat de lieveheersbeestjes hun gang gaan.",
    "bio.pest.colorado_beetle": "raap dagelijks, plant kattenkruid, koriander of vlas tussen de aardappels en laat ruimte voor loopkevers.",
    "bio.pest.asparagus_beetle": "raap de kevers 's ochtends en zet een paar tomatenplanten in de buurt - hun geur houdt ze weg.",
    "bio.pest.whitefly": "hang gele vangplaten, zet afrikaantjes (Tagetes) tussen de tomaten en zet Encarsia-sluipwespen uit in de serre.",
    "bio.pest.red_spider_mite": "houd de serrelucht vochtig (paden nevelen) en zet roofmijten (Phytoseiulus) uit bij de eerste vlekjes.",
    "bio.pest.slugs": "verwelkom egels, padden en loopkevers (takkenhoop, poel), geef 's ochtends water in plaats van 's avonds, en leg wol of een ring droge zemelen rond jonge planten.",
    "bio.disease": "Biologisch: spuit preventief heermoesthee (om de 1-2 weken), mulch zodat er geen aarde op de bladeren spat, en kies volgend jaar resistente rassen.",
    "maint.eco_flower_strip": "Bloemenstrook zaaien voor nuttige insecten",
    "maint.eco_flower_strip.desc": "Phacelia, goudsbloem, korenbloem, dille en boekweit langs de bedden voeden zweefvliegen, gaasvliegen en sluipwespen - zij houden bladluis en rupsen in toom.",
    "maint.eco_horsetail": "Heermoesthee maken (tegen schimmels)",
    "maint.eco_horsetail.desc": "Kook 150 g gedroogde (1 kg verse) heermoes 30 minuten in 10 l regenwater, laat een nacht staan, verdun 1:5 en spuit bij vochtig weer om de 1-2 weken op tomaten, aardappels en courgettes.",
    "maint.eco_no_dig": "De grond voeden in plaats van spitten (niet-spitten)",
    "maint.eco_no_dig.desc": "Leg 3-5 cm compost, bladeren of stro op de lege bedden. De wormen werken het in de winter onder; het bodemleven blijft intact en onkruid krijgt minder kans.",
    "maint.eco_wild_corner": "Een wilde hoek en zaadhoofden laten staan",
    "maint.eco_wild_corner.desc": "Een takkenril, bladeren onder de haag en holle stengels tot het voorjaar: egels, lieveheersbeestjes en solitaire bijen overwinteren er.",
    "maint.eco_insect_hotel": "Insectenhotel nakijken",
    "maint.eco_insect_hotel.desc": "Vervang gespleten of beschimmelde buisjes en voeg nieuw riet of geboord hardhout (gaatjes 3-8 mm) toe voor de solitaire bijen vliegen.",
    "maint.eco_stems": "Stengels van vorig jaar nu terugknippen",
    "maint.eco_stems.desc": "Insecten die in de holle stengels overwinterden, vliegen weer: knip de stengels terug en laat ze nog enkele weken op een hoopje liggen.",
    "maint.eco_water_dish": "Drinkschaal zetten voor vogels en bijen",
    "maint.eco_water_dish.desc": "Een ondiepe schaal met steentjes om op te landen, om de paar dagen ververst, helpt vogels en insecten door droge periodes.",
    "eco.month.1": "Plan voor verscheidenheid",
    "eco.month.1.text": "Meng families in elk bed, voeg bloemen en kruiden toe en plan een hoek met vaste planten - een gevarieerde tuin heeft minder plagen.",
    "eco.month.2": "Nestkasten schoon, de grond voeden",
    "eco.month.2.text": "De vogels zoeken een plek: hang schone nestkasten. Leg compost op de bedden in plaats van te spitten.",
    "eco.month.3": "Maak plaats voor helpers",
    "eco.month.3.text": "Laat de paardenbloemen in het gras staan: het eerste voedsel voor hommels. Kijk het insectenhotel na.",
    "eco.month.4": "Brandnetels: gratis voeding",
    "eco.month.4.text": "Jonge brandnetels geven de beste brandnetelgier (1:10 als voeding, koud extract onverdund tegen bladluis). Laat een plekje staan voor de vlinders.",
    "eco.month.5": "Mulchen en bloemen",
    "eco.month.5.text": "Mulch de warme grond met grasmaaisel en zaai een bloemenstrook - de zweefvliegen zijn er op tijd voor de eerste bladluis.",
    "eco.month.6": "Slim water geven",
    "eco.month.6.text": "Geef 's ochtends water aan de voet van de planten, vang regen op van elk dak en houd de grond bedekt.",
    "eco.month.7": "Laat maar even",
    "eco.month.7.text": "Een paar bladluizen voeden de larven van lieveheersbeestjes. Wacht een week voor je ingrijpt - de natuur lost het vaak zelf op.",
    "eco.month.8": "Groenbemester na de oogst",
    "eco.month.8.text": "Zaai phacelia, klaver of winterrogge op elke lege plek: geen kale grond, meer bodemleven, stikstof voor volgend jaar.",
    "eco.month.9": "Eigen zaad winnen",
    "eco.month.9.text": "Laat de beste bonen, tomaten en sla in zaad schieten - aangepast aan jouw tuin en gratis.",
    "eco.month.10": "Bladeren zijn goud",
    "eco.month.10.text": "Hark bladeren op de bedden of in een gaasbak voor bladaarde. Nooit verbranden.",
    "eco.month.11": "Bomen en struiken planten",
    "eco.month.11.text": "Wortelnaakte fruitbomen, bessen en inheemse hagen nu: de start van een voedselbos of een levende haag.",
    "eco.month.12": "Rust en terugblikken",
    "eco.month.12.text": "Laat zaadhoofden staan voor de vogels, kijk wat goed ging en plan meer vaste planten voor een makkelijkere tuin.",
    "forest.layer.canopy": "Kruinlaag",
    "forest.layer.sub_canopy": "Lage bomen",
    "forest.layer.shrub": "Struiken",
    "forest.layer.herb": "Kruiden & vaste planten",
    "forest.layer.ground": "Bodembedekkers",
    "forest.layer.root": "Wortels & knollen",
    "forest.layer.climber": "Klimplanten",
    "advice.food_forest": "Voedselbos {zone}: nog in te vullen: {layers}",
    "advice.food_forest.text": "Een voedselbos bootst een jonge bosrand na: elke laag heeft zijn planten en samen voeden, beschutten en beschermen ze elkaar. Ideeën: {plants}.",
    "advice.food_forest_try": "Maak van {zone} een voedselbos",
    "advice.food_forest_try.text": "Onder en tussen de fruitbomen is plaats voor bessen, kruiden, bodembedekkers en klimplanten. Zet het zonetype op voedselbos: Hortulus toont dan welke lagen nog ontbreken.",
    "advice.eco_month": "Ecologische tip: {title}",
    "advice.eco_month.text": "{text}",
    "advice.polyculture": "{bed}: maar één familie",
    "advice.polyculture.text": "Alles in {bed} is {family}. Meng er een andere familie, een kruid of een bloem tussen - gemengde bedden hebben minder plagen en benutten de grond beter.",
}
_FR = {
    "bio.prefix": "Bio :",
    "bio.pest.carrot_fly": "semez clair pour ne pas devoir éclaircir, semez après le premier vol (juin) et intercalez des rangs d'oignons ou de poireaux entre les carottes - l'odeur trompe la mouche.",
    "bio.pest.cabbage_root_fly": "plantez les choux bien fermement, buttez-les un peu et gardez le sol vivant avec du compost ; carabes et staphylins mangent les œufs.",
    "bio.pest.cabbage_white": "semez de la capucine comme plante-piège loin des choux et laissez travailler les guêpes parasitoïdes - ne touchez pas aux cocons jaunes sur les feuilles.",
    "bio.pest.onion_fly": "associez oignons et carottes, semez tard et évitez le fumier frais ; les bulbilles souffrent moins que les oignons semés.",
    "bio.pest.leek_moth": "plantez les poireaux entre carottes ou céleri et gardez les oiseaux au jardin (nichoirs) - les mésanges mangent les chenilles.",
    "bio.pest.pea_moth": "semez les pois tôt ou tard, en dehors du vol (juin-juillet), et laissez un coin sauvage pour les guêpes parasitoïdes.",
    "bio.pest.flea_beetle": "gardez le sol humide (elles détestent), paillez entre les plants et couvrez les jeunes choux d'un voile.",
    "bio.pest.aphids": "pulvérisez un macérat froid d'ortie (1 kg d'orties, 10 l d'eau, 24 h, pur) et semez aneth, souci et phacélie pour les syrphes, chrysopes et coccinelles.",
    "bio.pest.black_bean_aphid": "pincez les têtes des fèves dès la formation des premières gousses, semez les fèves tôt et laissez faire les coccinelles.",
    "bio.pest.colorado_beetle": "ramassez chaque jour, plantez cataire, coriandre ou lin entre les pommes de terre et laissez de la place aux carabes.",
    "bio.pest.asparagus_beetle": "ramassez les criocères le matin et placez quelques pieds de tomate à proximité - leur odeur les éloigne.",
    "bio.pest.whitefly": "suspendez des plaques jaunes engluées, plantez des œillets d'Inde (Tagetes) entre les tomates et lâchez des Encarsia dans la serre.",
    "bio.pest.red_spider_mite": "gardez l'air de la serre humide (brumisez les allées) et lâchez des acariens prédateurs (Phytoseiulus) dès les premières taches.",
    "bio.pest.slugs": "accueillez hérissons, crapauds et carabes (tas de bois, mare), arrosez le matin plutôt que le soir, et posez de la laine ou un anneau de son sec autour des jeunes plants.",
    "bio.disease": "Bio : pulvérisez de la tisane de prêle en prévention (toutes les 1-2 semaines), paillez pour que la terre n'éclabousse pas les feuilles, et choisissez des variétés résistantes l'an prochain.",
    "maint.eco_flower_strip": "Semer une bande fleurie pour les auxiliaires",
    "maint.eco_flower_strip.desc": "Phacélie, souci, bleuet, aneth et sarrasin le long des planches nourrissent syrphes, chrysopes et guêpes parasitoïdes - ils limitent pucerons et chenilles.",
    "maint.eco_horsetail": "Préparer une tisane de prêle (contre les champignons)",
    "maint.eco_horsetail.desc": "Faites bouillir 150 g de prêle sèche (1 kg fraîche) 30 minutes dans 10 l d'eau de pluie, laissez reposer une nuit, diluez à 1:5 et pulvérisez par temps humide toutes les 1-2 semaines sur tomates, pommes de terre et courgettes.",
    "maint.eco_no_dig": "Nourrir le sol au lieu de bêcher (sans labour)",
    "maint.eco_no_dig.desc": "Étalez 3-5 cm de compost, de feuilles ou de paille sur les planches vides. Les vers l'incorporent pendant l'hiver ; la vie du sol reste intacte et les adventices ont moins de chances.",
    "maint.eco_wild_corner": "Laisser un coin sauvage et les tiges sèches",
    "maint.eco_wild_corner.desc": "Un tas de branches, des feuilles sous la haie et des tiges creuses jusqu'au printemps : hérissons, coccinelles et abeilles solitaires y hivernent.",
    "maint.eco_insect_hotel": "Vérifier l'hôtel à insectes",
    "maint.eco_insect_hotel.desc": "Remplacez les tubes fendus ou moisis et ajoutez des roseaux ou du bois dur percé (trous de 3-8 mm) avant le vol des abeilles solitaires.",
    "maint.eco_stems": "Couper maintenant les tiges de l'an passé",
    "maint.eco_stems.desc": "Les insectes qui ont hiverné dans les tiges creuses volent à nouveau : coupez les tiges et laissez-les encore quelques semaines en tas.",
    "maint.eco_water_dish": "Installer un abreuvoir pour oiseaux et abeilles",
    "maint.eco_water_dish.desc": "Une coupelle peu profonde avec des pierres pour se poser, renouvelée tous les quelques jours, aide oiseaux et insectes pendant les sécheresses.",
    "eco.month.1": "Planifier la diversité",
    "eco.month.1.text": "Mélangez les familles dans chaque planche, ajoutez fleurs et aromatiques et prévoyez un coin de vivaces - un jardin varié a moins de ravageurs.",
    "eco.month.2": "Nichoirs propres, sol nourri",
    "eco.month.2.text": "Les oiseaux cherchent un nid : accrochez des nichoirs propres. Étalez du compost sur les planches au lieu de bêcher.",
    "eco.month.3": "Faire de la place aux auxiliaires",
    "eco.month.3.text": "Laissez les pissenlits dans la pelouse : la première nourriture des bourdons. Vérifiez l'hôtel à insectes.",
    "eco.month.4": "Orties : engrais gratuit",
    "eco.month.4.text": "Les jeunes orties donnent le meilleur purin (1:10 comme engrais, macérat froid pur contre les pucerons). Laissez un coin pour les papillons.",
    "eco.month.5": "Paillage et fleurs",
    "eco.month.5.text": "Paillez le sol réchauffé avec la tonte et semez une bande fleurie - les syrphes arrivent à temps pour les premiers pucerons.",
    "eco.month.6": "Arroser malin",
    "eco.month.6.text": "Arrosez le matin au pied des plantes, récupérez la pluie de chaque toit et gardez le sol couvert.",
    "eco.month.7": "Laisser faire",
    "eco.month.7.text": "Quelques pucerons nourrissent les larves de coccinelles. Attendez une semaine avant d'agir - la nature règle souvent le problème.",
    "eco.month.8": "Engrais vert après la récolte",
    "eco.month.8.text": "Semez phacélie, trèfle ou seigle d'hiver sur chaque place libre : pas de sol nu, plus de vie, de l'azote pour l'an prochain.",
    "eco.month.9": "Récolter ses graines",
    "eco.month.9.text": "Laissez monter en graines les meilleurs haricots, tomates et laitues - adaptés à votre jardin et gratuits.",
    "eco.month.10": "Les feuilles, c'est de l'or",
    "eco.month.10.text": "Ratissez les feuilles sur les planches ou dans un bac grillagé pour le terreau de feuilles. Ne les brûlez jamais.",
    "eco.month.11": "Planter arbres et arbustes",
    "eco.month.11.text": "Fruitiers à racines nues, petits fruits et haies indigènes maintenant : le début d'une forêt comestible ou d'une haie vivante.",
    "eco.month.12": "Repos et bilan",
    "eco.month.12.text": "Laissez les têtes de graines aux oiseaux, regardez ce qui a marché et prévoyez plus de vivaces pour un jardin plus facile.",
    "forest.layer.canopy": "Canopée",
    "forest.layer.sub_canopy": "Petits arbres",
    "forest.layer.shrub": "Arbustes",
    "forest.layer.herb": "Herbacées & vivaces",
    "forest.layer.ground": "Couvre-sol",
    "forest.layer.root": "Racines & bulbes",
    "forest.layer.climber": "Grimpantes",
    "advice.food_forest": "Forêt comestible {zone} : à compléter : {layers}",
    "advice.food_forest.text": "Une forêt comestible imite une jeune lisière : chaque strate a ses plantes et ensemble elles se nourrissent, s'abritent et se protègent. Idées : {plants}.",
    "advice.food_forest_try": "Faites de {zone} une forêt comestible",
    "advice.food_forest_try.text": "Sous et entre les fruitiers, il y a de la place pour petits fruits, aromatiques, couvre-sol et grimpantes. Choisissez le type de zone forêt comestible : Hortulus montre alors les strates qui manquent.",
    "advice.eco_month": "Conseil écologique : {title}",
    "advice.eco_month.text": "{text}",
    "advice.polyculture": "{bed} : une seule famille",
    "advice.polyculture.text": "Tout dans {bed} est de la famille {family}. Mélangez une autre famille, une aromatique ou une fleur - les planches mixtes ont moins de ravageurs et exploitent mieux le sol.",
}
MESSAGES["en"].update(_EN)
MESSAGES["nl"].update(_NL)
MESSAGES["fr"].update(_FR)


def layer_names(layers: Sequence[str], lang: str | None) -> str:
    return ", ".join(t(f"forest.layer.{layer}", lang).lower() for layer in layers)
