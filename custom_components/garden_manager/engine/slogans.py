"""Little garden sayings, so the digest, the reports and the panel do not read the same every day.

``slogan(lang, day=..., topics=...)`` picks one line from the themes asked for (plus the
season's own lines).  The pick is stable for a day and a context ``salt`` - the same digest
reads the same when it is rebuilt - but moves on every day, and two places on the same day
(digest, weekly plan, report) get different lines.  Everything follows
``GardenSettings.slogans`` (on by default): callers ask :func:`enabled` first.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
import hashlib

# theme -> language -> lines
SLOGANS: dict[str, dict[str, tuple[str, ...]]] = {
    "garden": {
        "nl": (
            "Een tuin is nooit af, en dat is net het mooie.",
            "Wie een tuin plant, plant hoop.",
            "Elke dag een beetje tuin maakt een heel jaar mooier.",
            "Goede grond is het halve werk.",
            "De beste mest is de voetstap van de tuinier.",
            "Kleine moestuin, groot plezier.",
            "Een uurtje in de tuin is nooit verloren tijd.",
            "Wat je met zorg zaait, oogst je met plezier.",
            "Tuinieren is geduld met een schepje erbij.",
            "Een levende bodem maakt sterke planten.",
            "Onkruid is gewoon een plant die nog geen naam heeft gekregen.",
            "In de moestuin groeit meer dan groente alleen.",
        ),
        "en": (
            "A garden is never finished, and that is the beauty of it.",
            "To plant a garden is to believe in tomorrow.",
            "A little garden every day makes the whole year brighter.",
            "Good soil is half the work.",
            "The best fertiliser is the gardener's footstep.",
            "Small plot, big joy.",
            "An hour in the garden is never time lost.",
            "Sow with care, harvest with joy.",
            "Gardening is patience with a trowel.",
            "Living soil grows strong plants.",
            "A weed is just a plant that has not been given a name yet.",
            "More than vegetables grows in a kitchen garden.",
        ),
        "fr": (
            "Un jardin n'est jamais fini, et c'est toute sa beauté.",
            "Planter un jardin, c'est croire en demain.",
            "Un peu de jardin chaque jour embellit toute l'année.",
            "Une bonne terre, c'est la moitié du travail.",
            "Le meilleur engrais, c'est le pas du jardinier.",
            "Petit potager, grand bonheur.",
            "Une heure au jardin n'est jamais perdue.",
            "Ce qu'on sème avec soin se récolte avec joie.",
            "Jardiner, c'est de la patience avec une truelle.",
            "Un sol vivant fait des plantes solides.",
            "Une mauvaise herbe n'est qu'une plante sans nom.",
            "Au potager pousse bien plus que des légumes.",
        ),
    },
    "veg": {
        "nl": (
            "Niets smaakt zo goed als groente die je zelf hebt geoogst.",
            "Van het bed naar je bord: verser bestaat niet.",
            "Gezond eten begint in de grond.",
            "Een handvol eigen sla zegt meer dan een volle winkelkar.",
            "Zelf gekweekt is dubbel gezond: voor jou en voor de tuin.",
            "Kleurrijke borden beginnen in een kleurrijke moestuin.",
            "Kruiden uit eigen tuin maken van elk gerecht een feest.",
        ),
        "en": (
            "Nothing tastes as good as vegetables you picked yourself.",
            "From bed to plate: fresher does not exist.",
            "Healthy eating starts in the soil.",
            "A handful of your own lettuce beats a full shopping trolley.",
            "Home-grown is twice as healthy: for you and for the garden.",
            "Colourful plates start in a colourful kitchen garden.",
            "Herbs from your own garden turn any meal into a feast.",
        ),
        "fr": (
            "Rien n'a meilleur goût que les légumes qu'on cueille soi-même.",
            "Du potager à l'assiette : impossible de faire plus frais.",
            "Bien manger commence dans la terre.",
            "Une poignée de sa propre salade vaut un caddie plein.",
            "Cultivé maison, deux fois plus sain : pour vous et pour le jardin.",
            "Les assiettes colorées naissent dans un potager coloré.",
            "Les herbes du jardin transforment chaque repas en fête.",
        ),
    },
    "outdoors": {
        "nl": (
            "Frisse lucht, vuile handen, blij hoofd.",
            "Even naar buiten doet wonderen.",
            "Buiten bezig zijn is de beste pauze van de dag.",
            "De tuin roept: trek je laarzen aan.",
            "Een dag zonder aarde aan je handen is een dag gemist.",
            "Luister even: de tuin zingt altijd een beetje.",
        ),
        "en": (
            "Fresh air, dirty hands, happy mind.",
            "A moment outside works wonders.",
            "Being busy outdoors is the best break of the day.",
            "The garden is calling: put your boots on.",
            "A day without soil on your hands is a day missed.",
            "Listen for a moment: the garden always sings a little.",
        ),
        "fr": (
            "Air frais, mains sales, tête heureuse.",
            "Un moment dehors fait des merveilles.",
            "S'activer dehors, c'est la meilleure pause de la journée.",
            "Le jardin appelle : enfilez vos bottes.",
            "Une journée sans terre sur les mains est une journée manquée.",
            "Écoutez un instant : le jardin chante toujours un peu.",
        ),
    },
    "harvest": {
        "nl": (
            "Oogsten is het feest van al je werk.",
            "Een volle mand is het mooiste verslag.",
            "Wie op tijd oogst, oogst langer.",
            "Deel je oogst: groente smaakt beter met buren.",
        ),
        "en": (
            "Harvest is the party for all your work.",
            "A full basket is the finest report.",
            "Pick on time and you will pick for longer.",
            "Share your harvest: vegetables taste better with neighbours.",
        ),
        "fr": (
            "La récolte, c'est la fête de tout votre travail.",
            "Un panier plein, c'est le plus beau des bilans.",
            "Qui récolte à temps récolte plus longtemps.",
            "Partagez votre récolte : les légumes ont meilleur goût entre voisins.",
        ),
    },
    "rest": {
        "nl": (
            "Vandaag geen klussen: geniet gewoon van je tuin.",
            "Een rustige tuindag: tijd voor een kop thee tussen de bedden.",
            "Niets te doen? Kijk eens wat er bloeit.",
            "Ook de tuin heeft rustdagen nodig.",
        ),
        "en": (
            "No jobs today: just enjoy your garden.",
            "A quiet garden day: time for a cup of tea between the beds.",
            "Nothing to do? Go and see what is flowering.",
            "Gardens need rest days too.",
        ),
        "fr": (
            "Pas de travaux aujourd'hui : profitez simplement du jardin.",
            "Une journée calme au jardin : le temps d'un thé entre les planches.",
            "Rien à faire ? Allez voir ce qui fleurit.",
            "Le jardin aussi a besoin de jours de repos.",
        ),
    },
    "weather": {
        "nl": (
            "Elke regenbui is gratis water voor je tuin.",
            "Na regen komt zonneschijn, en dan groeit alles.",
            "Het weer kies je niet, je tuin wel.",
            "Een goede tuinier kijkt eerst naar de lucht.",
        ),
        "en": (
            "Every shower is free water for your garden.",
            "After rain comes sunshine, and then everything grows.",
            "You cannot choose the weather, but you can choose your garden.",
            "A good gardener looks at the sky first.",
        ),
        "fr": (
            "Chaque averse, c'est de l'eau gratuite pour le jardin.",
            "Après la pluie, le beau temps, et tout pousse.",
            "On ne choisit pas la météo, mais on choisit son jardin.",
            "Un bon jardinier regarde d'abord le ciel.",
        ),
    },
    "spring": {
        "nl": (
            "De lente is de belofte van de hele zomer.",
            "Nu zaaien, straks smullen.",
            "Elk zaadje is een klein beetje toekomst.",
        ),
        "en": (
            "Spring is the promise of the whole summer.",
            "Sow now, feast later.",
            "Every seed is a little piece of the future.",
        ),
        "fr": (
            "Le printemps est la promesse de tout l'été.",
            "Semez maintenant, régalez-vous plus tard.",
            "Chaque graine est un petit bout d'avenir.",
        ),
    },
    "summer": {
        "nl": (
            "Zomer in de moestuin: elke dag wat te plukken.",
            "Water geven in de ochtend, genieten in de avond.",
            "Lange dagen, volle manden.",
        ),
        "en": (
            "Summer in the kitchen garden: something to pick every day.",
            "Water in the morning, enjoy in the evening.",
            "Long days, full baskets.",
        ),
        "fr": (
            "L'été au potager : chaque jour quelque chose à cueillir.",
            "Arrosez le matin, profitez le soir.",
            "Longues journées, paniers pleins.",
        ),
    },
    "autumn": {
        "nl": (
            "De herfst is de oogstmaand van je geduld.",
            "Bladeren vallen, de bodem eet mee.",
            "Wat je nu toedekt, bedankt je in de lente.",
        ),
        "en": (
            "Autumn is the harvest month of your patience.",
            "Leaves fall, the soil gets fed.",
            "What you mulch now will thank you in spring.",
        ),
        "fr": (
            "L'automne, c'est la récolte de votre patience.",
            "Les feuilles tombent, la terre se nourrit.",
            "Ce que vous paillez maintenant vous remerciera au printemps.",
        ),
    },
    "winter": {
        "nl": (
            "In de winter rust de tuin, en droomt de tuinier.",
            "Een goed plan is het beste zaad voor volgend jaar.",
            "Onder de grond is het al lente aan het worden.",
        ),
        "en": (
            "In winter the garden rests and the gardener dreams.",
            "A good plan is the best seed for next year.",
            "Under the ground, spring is already on its way.",
        ),
        "fr": (
            "En hiver, le jardin se repose et le jardinier rêve.",
            "Un bon plan est la meilleure graine pour l'an prochain.",
            "Sous la terre, le printemps se prépare déjà.",
        ),
    },
}

SEASON_OF_MONTH = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
                   6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}  # fmt: skip
_SOUTH = {"winter": "summer", "summer": "winter", "spring": "autumn", "autumn": "spring"}


def enabled(settings: object) -> bool:
    return bool(getattr(settings, "slogans", True))


def season_theme(day: date, south: bool = False) -> str:
    season = SEASON_OF_MONTH[day.month]
    return _SOUTH[season] if south else season


def pool(lang: str, topics: Iterable[str]) -> list[str]:
    """Every line of the themes, in the language (English when a language has none)."""
    out: list[str] = []
    for topic in topics:
        lines = SLOGANS.get(topic, {})
        out.extend(lines.get(lang) or lines.get("en") or ())
    return out


def slogan(
    lang: str,
    *,
    day: date,
    topics: Iterable[str] = ("garden", "veg", "outdoors"),
    salt: str = "",
    south: bool = False,
    season: bool = True,
) -> str:
    """One line for ``day``: the themes asked for plus the season's, never the same two days running."""
    themes = list(topics) + ([season_theme(day, south)] if season else [])
    lines = pool(lang, themes)
    if not lines:
        return ""
    # a stride coprime to the pool walks every line before one comes back
    offset = int(hashlib.sha256(f"{salt}|{lang}".encode()).hexdigest()[:8], 16)
    stride = _coprime_stride(len(lines), offset)
    return lines[(offset + day.toordinal() * stride) % len(lines)]


def _coprime_stride(n: int, seed: int) -> int:
    from math import gcd

    for step in range(3 + seed % 7, 3 + seed % 7 + n + 2):
        if gcd(step, n) == 1:
            return step
    return 1


def all_lines() -> dict[str, dict[str, list[str]]]:
    """The whole database (for the website's e-mails and the docs)."""
    return {topic: {lang: list(lines) for lang, lines in langs.items()} for topic, langs in SLOGANS.items()}
