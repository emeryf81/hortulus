"""The season book: a whole garden year as a printable book.

One PDF, laid out for printing as a book (A5 by default, an even page count
that folds into signatures of four, chapters opening on a right-hand page):

* cover, epigraph, title page, the garden plan of the season,
* table of contents (with page numbers and a one-line summary per month),
* an introduction written from the season's own figures,
* one chapter per month: what was sown, planted and done, the journal with
  its photos, the harvest, water and weather,
* the year in numbers, a glossary, the colophon and the back cover.

Everything is written from the garden data; photos come through
``PrintContext.photos`` (Home Assistant's image uploads, read by the caller).
Pure module: no Home Assistant imports.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
import unicodedata

from .i18n import normalize_lang, t
from .models import (
    HarvestEntry,
    Hemisphere,
    JournalEntry,
    Planting,
    PlantingStatus,
    SowMethod,
    Task,
    TaskStatus,
    TaskType,
    present_in,
)
from .pdf import _REPLACE, PT_TO_MM, Image, PdfDocument, Surface, SvgPage, text_width, to_gray, wrap
from .plantdb import FAMILIES
from .region import season_bounds, season_for_date
from .seasons import layout_for

BRAND = "#2F6B4F"
BRAND_DARK = "#1F4A37"
LEAF = "#7FB069"
SUN = "#E0A526"
INK = "#1F2A24"
MUTED = "#5E6B63"
FAINT = "#B9C2BC"
PAPER = "#F7F4EC"

PhotoLoader = Callable[..., Image | None]  # (photo_id, gray, probe=False)

# --------------------------------------------------------------------------- #
# Words
# --------------------------------------------------------------------------- #
MONTHS = {
    "nl": ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober",
           "november", "december"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
           "novembre", "décembre"],
}  # fmt: skip
WEEKDAYS = {
    "nl": ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "fr": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"],
}

TEXT: dict[str, dict[str, str]] = {
    "nl": {
        "book": "Tuinjaar {season}",
        "book_sub": "Het seizoen van {garden}",
        "made_with": "Samengesteld met Hortulus",
        "epigraph": "Wie een tuin aanlegt, plant geloof in morgen.",
        "epigraph_by": "Tuinierswijsheid",
        "title_lead": "Een jaar zaaien, planten, wachten, wieden en oogsten,\nopgeschreven door de tuin zelf.",
        "plan": "De tuin in {season}",
        "plan_none": "Voor dit seizoen is er geen tuinplan bewaard.",
        "plan_caption": "{beds} bedden in {zones} zones, samen {area} m² teeltoppervlak.",
        "toc": "Inhoud",
        "intro": "Inleiding",
        "chapter": "Hoofdstuk {n}",
        "numbers": "Het jaar in cijfers",
        "glossary": "Woordenlijst",
        "colophon": "Colofon",
        "notes": "Notities",
        "notes_hint": "Ruimte voor wat je nog wilt onthouden.",
        "story": "Het verhaal van de maand",
        "sown_planted": "Gezaaid en geplant",
        "work": "Werk in de tuin",
        "diary": "Uit het dagboek",
        "harvest": "Oogst",
        "water_weather": "Water en weer",
        "quiet": "Een stille maand",
        "sown_in": "binnen gezaaid",
        "sown_out": "buiten gezaaid",
        "planted": "uitgeplant",
        "first_harvest": "eerste oogst",
        "finished": "uit de grond",
        "failed": "mislukt",
        "harvest_total": "Deze maand {kg} geoogst, sinds het begin van het seizoen {total}.",
        "harvest_times": "{n} keer",
        "water_given": "Hortulus gaf {liters} liter water in {runs} beurten.",
        "water_none": "Er werd deze maand niet bewaterd door Hortulus.",
        "weather": "Warmste dag {tmax} °C, koudste nacht {tmin} °C, {rain} mm regen{frost}.",
        "frost_nights": ", {n} vorstnachten",
        "frost_night": ", één vorstnacht",
        "by": "door {who}",
        "photo_of": "Foto: {what}",
        "kind.note": "Notitie",
        "kind.observation": "Waarneming",
        "kind.problem": "Probleem",
        "kind.milestone": "Mijlpaal",
        "cat.care": "Verzorgen",
        "cat.garden": "Tuinwerk",
        "cat.sow": "Zaaien en planten",
        "cat.harvest": "Oogsten",
        "summary_sown": "{n} gezaaid",
        "summary_planted": "{n} uitgeplant",
        "summary_notes": "{n} notities",
        "summary_photos": "{n} foto's",
        "summary_kg": "{kg} oogst",
        "summary_quiet": "rustmaand",
        "and": "en",
        "and_more": "en nog {n} andere",
        "tbl_crop": "Gewas",
        "tbl_kg": "kg",
        "tbl_times": "keer",
        "tbl_best": "beste maand",
        "tbl_first": "eerste",
        "tbl_last": "laatste",
        "num_harvest": "Oogst per gewas",
        "num_harvest_none": "Er werd dit seizoen nog geen oogst genoteerd.",
        "num_worth": "Wat de tuin opbracht",
        "worth_text": "Tegen winkelprijzen was de oogst ongeveer {value} waard. De tuin kostte dit seizoen {cost} aan uitgaven en water. {verdict}",
        "worth_plus": "Dat is {balance} uitgespaard - nog los van de smaak, de beweging en de rust.",
        "worth_minus": "De tuin kostte dus {balance} meer dan hij in de winkel waard is; wat hij teruggeeft, staat niet op een kassabon.",
        "num_families": "Wat er groeide, per familie",
        "num_year": "Het seizoen in het kort",
        "num_lessons": "Wat lukte en wat niet",
        "num_failed": "Mislukt: {what}.",
        "num_above": "Beter dan verwacht: {what}.",
        "num_below": "Minder dan verwacht: {what}.",
        "num_none": "Geen opvallende uitschieters dit jaar: alles groeide ongeveer zoals verwacht.",
        "fact_crops": "gewassen",
        "fact_plantings": "teelten",
        "fact_kg": "kg geoogst",
        "fact_notes": "dagboeknotities",
        "fact_photos": "foto's",
        "fact_water": "liter water",
        "fact_tasks": "taken afgewerkt",
        "fact_sown": "keer gezaaid",
        "col_title": "Tuinjaar {season} · {garden}",
        "col_made": "Dit boek werd op {day} samengesteld door Hortulus {version} uit de gegevens van de tuin: het tuinplan, de teelten en hun data, de afgewerkte taken, het dagboek, de foto's, de oogst, de bewatering en het weer.",
        "col_people": "Tuiniers en schrijvers: {who}.",
        "col_photos": "Foto's: eigen werk ({n} foto's).",
        "col_region": "Streek: laatste vorst rond {last}, eerste vorst rond {first}.",
        "col_type": "Gezet in Times en Helvetica, op {page} ({w} × {h} mm).",
        "col_print": "Afdrukken als boek: dubbelzijdig, spiegelen langs de lange kant. Het aantal bladzijden is een veelvoud van vier, zodat je het boek in katernen kunt vouwen en binden.",
        "col_free": "Hortulus is vrije software. Je tuin, je gegevens en dit boek zijn van jou.",
        "back_quote": "Elk jaar begint de tuin opnieuw, maar nooit van nul: hij onthoudt wat jij erin legde.",
        "back_facts": "{crops} gewassen · {kg} geoogst · {notes} notities · {photos} foto's",
        "day_fmt": "{d} {month}",
        "date_long": "{weekday} {d} {month}",
        "rest_month": "Er werd deze maand niets genoteerd. Ook dat hoort bij een tuinjaar: de grond rust, de planner droomt, en wat er niet gebeurde, maakt ruimte voor wat komt.",
    },
    "en": {
        "book": "Garden year {season}",
        "book_sub": "The season of {garden}",
        "made_with": "Compiled with Hortulus",
        "epigraph": "To plant a garden is to believe in tomorrow.",
        "epigraph_by": "Gardener's saying",
        "title_lead": "A year of sowing, planting, waiting, weeding and harvesting,\nwritten down by the garden itself.",
        "plan": "The garden in {season}",
        "plan_none": "No garden plan was kept for this season.",
        "plan_caption": "{beds} beds in {zones} zones, {area} m² of growing space in all.",
        "toc": "Contents",
        "intro": "Introduction",
        "chapter": "Chapter {n}",
        "numbers": "The year in numbers",
        "glossary": "Glossary",
        "colophon": "Colophon",
        "notes": "Notes",
        "notes_hint": "Room for what you still want to remember.",
        "story": "The story of the month",
        "sown_planted": "Sown and planted",
        "work": "Work in the garden",
        "diary": "From the journal",
        "harvest": "Harvest",
        "water_weather": "Water and weather",
        "quiet": "A quiet month",
        "sown_in": "sown indoors",
        "sown_out": "sown outdoors",
        "planted": "planted out",
        "first_harvest": "first harvest",
        "finished": "cleared",
        "failed": "failed",
        "harvest_total": "{kg} harvested this month, {total} since the start of the season.",
        "harvest_times": "{n} times",
        "water_given": "Hortulus gave {liters} litres of water in {runs} runs.",
        "water_none": "Hortulus did not water this month.",
        "weather": "Warmest day {tmax} °C, coldest night {tmin} °C, {rain} mm of rain{frost}.",
        "frost_nights": ", {n} frosty nights",
        "frost_night": ", one frosty night",
        "by": "by {who}",
        "photo_of": "Photo: {what}",
        "kind.note": "Note",
        "kind.observation": "Observation",
        "kind.problem": "Problem",
        "kind.milestone": "Milestone",
        "cat.care": "Care",
        "cat.garden": "Garden work",
        "cat.sow": "Sowing and planting",
        "cat.harvest": "Harvesting",
        "summary_sown": "{n} sown",
        "summary_planted": "{n} planted",
        "summary_notes": "{n} notes",
        "summary_photos": "{n} photos",
        "summary_kg": "{kg} harvested",
        "summary_quiet": "a month of rest",
        "and": "and",
        "and_more": "and {n} more",
        "tbl_crop": "Crop",
        "tbl_kg": "kg",
        "tbl_times": "times",
        "tbl_best": "best month",
        "tbl_first": "first",
        "tbl_last": "last",
        "num_harvest": "Harvest per crop",
        "num_harvest_none": "No harvest was recorded this season yet.",
        "num_worth": "What the garden gave",
        "worth_text": "At shop prices the harvest was worth about {value}. This season the garden cost {cost} in expenses and water. {verdict}",
        "worth_plus": "That is {balance} saved - before counting the taste, the exercise and the calm.",
        "worth_minus": "So the garden cost {balance} more than it is worth in the shop; what it gives back is not on any receipt.",
        "num_families": "What grew, by family",
        "num_year": "The season at a glance",
        "num_lessons": "What worked and what did not",
        "num_failed": "Failed: {what}.",
        "num_above": "Better than expected: {what}.",
        "num_below": "Less than expected: {what}.",
        "num_none": "No outliers this year: everything grew roughly as expected.",
        "fact_crops": "crops",
        "fact_plantings": "plantings",
        "fact_kg": "kg harvested",
        "fact_notes": "journal notes",
        "fact_photos": "photos",
        "fact_water": "litres of water",
        "fact_tasks": "tasks done",
        "fact_sown": "sowings",
        "col_title": "Garden year {season} · {garden}",
        "col_made": "This book was compiled on {day} by Hortulus {version} from the garden's own records: the plan, the crops and their dates, the tasks done, the journal, the photos, the harvest, the watering and the weather.",
        "col_people": "Gardeners and writers: {who}.",
        "col_photos": "Photos: own work ({n} photos).",
        "col_region": "Region: last frost around {last}, first frost around {first}.",
        "col_type": "Set in Times and Helvetica, on {page} ({w} × {h} mm).",
        "col_print": "To print as a book: double-sided, flip on the long edge. The page count is a multiple of four, so the book folds into signatures for binding.",
        "col_free": "Hortulus is free software. Your garden, your records and this book are yours.",
        "back_quote": "Every year the garden starts again, but never from nothing: it remembers what you put into it.",
        "back_facts": "{crops} crops · {kg} harvested · {notes} notes · {photos} photos",
        "day_fmt": "{month} {d}",
        "date_long": "{weekday}, {month} {d}",
        "rest_month": "Nothing was written down this month. That too belongs to a garden year: the soil rests, the gardener dreams, and what did not happen makes room for what comes.",
    },
    "fr": {
        "book": "Année au jardin {season}",
        "book_sub": "La saison de {garden}",
        "made_with": "Composé avec Hortulus",
        "epigraph": "Planter un jardin, c'est croire en demain.",
        "epigraph_by": "Sagesse de jardinier",
        "title_lead": "Une année de semis, de plantations, d'attente, de désherbage et de récoltes,\nracontée par le jardin lui-même.",
        "plan": "Le jardin en {season}",
        "plan_none": "Aucun plan du jardin n'a été conservé pour cette saison.",
        "plan_caption": "{beds} planches dans {zones} zones, {area} m² de surface cultivée au total.",
        "toc": "Sommaire",
        "intro": "Introduction",
        "chapter": "Chapitre {n}",
        "numbers": "L'année en chiffres",
        "glossary": "Glossaire",
        "colophon": "Colophon",
        "notes": "Notes",
        "notes_hint": "De la place pour ce que vous voulez encore retenir.",
        "story": "Le récit du mois",
        "sown_planted": "Semé et planté",
        "work": "Travaux au jardin",
        "diary": "Extraits du journal",
        "harvest": "Récolte",
        "water_weather": "Eau et météo",
        "quiet": "Un mois calme",
        "sown_in": "semé à l'intérieur",
        "sown_out": "semé en pleine terre",
        "planted": "repiqué",
        "first_harvest": "première récolte",
        "finished": "arraché",
        "failed": "raté",
        "harvest_total": "{kg} récoltés ce mois-ci, {total} depuis le début de la saison.",
        "harvest_times": "{n} fois",
        "water_given": "Hortulus a donné {liters} litres d'eau en {runs} arrosages.",
        "water_none": "Hortulus n'a pas arrosé ce mois-ci.",
        "weather": "Journée la plus chaude {tmax} °C, nuit la plus froide {tmin} °C, {rain} mm de pluie{frost}.",
        "frost_nights": ", {n} nuits de gel",
        "frost_night": ", une nuit de gel",
        "by": "par {who}",
        "photo_of": "Photo : {what}",
        "kind.note": "Note",
        "kind.observation": "Observation",
        "kind.problem": "Problème",
        "kind.milestone": "Étape",
        "cat.care": "Soins",
        "cat.garden": "Travaux du jardin",
        "cat.sow": "Semis et plantations",
        "cat.harvest": "Récoltes",
        "summary_sown": "{n} semis",
        "summary_planted": "{n} repiquages",
        "summary_notes": "{n} notes",
        "summary_photos": "{n} photos",
        "summary_kg": "{kg} récoltés",
        "summary_quiet": "mois de repos",
        "and": "et",
        "and_more": "et {n} autres",
        "tbl_crop": "Culture",
        "tbl_kg": "kg",
        "tbl_times": "fois",
        "tbl_best": "meilleur mois",
        "tbl_first": "première",
        "tbl_last": "dernière",
        "num_harvest": "Récolte par culture",
        "num_harvest_none": "Aucune récolte n'a encore été notée cette saison.",
        "num_worth": "Ce que le jardin a rapporté",
        "worth_text": "Aux prix du magasin, la récolte valait environ {value}. Cette saison, le jardin a coûté {cost} en dépenses et en eau. {verdict}",
        "worth_plus": "Soit {balance} d'économisés - sans compter le goût, l'exercice et le calme.",
        "worth_minus": "Le jardin a donc coûté {balance} de plus que sa valeur en magasin ; ce qu'il rend ne figure sur aucun ticket de caisse.",
        "num_families": "Ce qui a poussé, par famille",
        "num_year": "La saison en bref",
        "num_lessons": "Ce qui a réussi et ce qui a raté",
        "num_failed": "Raté : {what}.",
        "num_above": "Mieux que prévu : {what}.",
        "num_below": "Moins bien que prévu : {what}.",
        "num_none": "Pas d'écart marquant cette année : tout a poussé à peu près comme prévu.",
        "fact_crops": "cultures",
        "fact_plantings": "plantations",
        "fact_kg": "kg récoltés",
        "fact_notes": "notes de journal",
        "fact_photos": "photos",
        "fact_water": "litres d'eau",
        "fact_tasks": "tâches accomplies",
        "fact_sown": "semis",
        "col_title": "Année au jardin {season} · {garden}",
        "col_made": "Ce livre a été composé le {day} par Hortulus {version} à partir des données du jardin : le plan, les cultures et leurs dates, les tâches accomplies, le journal, les photos, la récolte, l'arrosage et la météo.",
        "col_people": "Jardiniers et auteurs : {who}.",
        "col_photos": "Photos : travail personnel ({n} photos).",
        "col_region": "Région : dernières gelées vers le {last}, premières gelées vers le {first}.",
        "col_type": "Composé en Times et Helvetica, au format {page} ({w} × {h} mm).",
        "col_print": "Pour imprimer en livre : recto verso, retournement sur le bord long. Le nombre de pages est un multiple de quatre, pour plier le livre en cahiers et le relier.",
        "col_free": "Hortulus est un logiciel libre. Votre jardin, vos données et ce livre vous appartiennent.",
        "back_quote": "Chaque année, le jardin recommence, mais jamais de zéro : il se souvient de ce que vous y avez mis.",
        "back_facts": "{crops} cultures · {kg} récoltés · {notes} notes · {photos} photos",
        "day_fmt": "{d} {month}",
        "date_long": "{weekday} {d} {month}",
        "rest_month": "Rien n'a été noté ce mois-ci. Cela aussi fait partie d'une année au jardin : la terre se repose, le jardinier rêve, et ce qui n'est pas arrivé fait de la place à ce qui vient.",
    },
}  # fmt: skip

# What a month feels like, by its place in the growing year (index 0 = the
# first month after midwinter: January up north, July down south).
MONTH_INTRO: dict[str, list[str]] = {
    "nl": [
        "De tuin slaapt, maar de tuinier niet. Januari is de maand van zaadcatalogi en lange avonden, van plannen die nog alles kunnen worden. Buiten is het stil; binnen groeit het nieuwe jaar al in je hoofd.",
        "De dagen lengen merkbaar. In februari wordt het eerste zaad gezaaid op de vensterbank, worden fruitbomen gesnoeid en ruikt de grond op een zachte dag al naar lente. Geduld is nu de belangrijkste tuinvaardigheid.",
        "Maart is de maand van het ontwaken. De bodem warmt op, de eerste zaaisels gaan de koude grond in, en elke ochtend is er iets nieuws te zien. Het is vroeg, en dat is precies het mooie.",
        "April doet wat hij wil, en de tuinier doet mee. Zaaien, verspenen, afharden, beschermen tegen een late nachtvorst: het tempo gaat omhoog. Overal verschijnen kiemblaadjes, klein en vol belofte.",
        "In mei barst alles los. De ijsheiligen voorbij, gaan de tomaten, courgettes en bonen naar buiten. De tuin vult zich zichtbaar, en de eerste oogst van sla en radijs smaakt naar een beloning.",
        "Juni is overvloed in wording. Lange avonden in de tuin, wieden, opbinden, water geven, en de eerste aardbeien en peulen. Wat je in het voorjaar zaaide, begint nu terug te geven.",
        "Juli is volle zomer. Oogsten wordt een dagelijkse bezigheid, water geven een ritueel. Er is werk, maar het voelt licht, want overal hangt iets te rijpen.",
        "Augustus is de maand van de manden. Tomaten, bonen, courgettes: soms meer dan je op kunt. Het is ook tijd om vooruit te kijken: wat nu gezaaid wordt, oogst je in de herfst.",
        "September kleurt de tuin goud. De oogst gaat door, de ochtenden worden fris, en de eerste lege bedden vragen om een groenbemester of een wintergewas. Tijd om te bewaren, in te maken en te genieten.",
        "Oktober ruimt op en bereidt voor. Pompoenen binnenhalen, bedden afdekken, bollen planten voor het voorjaar. De tuin trekt zich terug, maar laat nog veel achter.",
        "November is stil en eerlijk. Wat overblijft is structuur: paden, bedden, kale takken. Een goede maand om te mulchen, compost om te zetten en het jaar te overdenken.",
        "December sluit het jaar af. De tuin rust onder blad en vorst. Bij de kachel kijk je terug op wat lukte en wat niet, en begin je al te dromen van volgend jaar.",
    ],
    "en": [
        "The garden sleeps, but the gardener does not. This is the month of seed catalogues and long evenings, of plans that can still become anything. Outside it is quiet; inside, the new year is already growing in your head.",
        "The days grow noticeably longer. The first seeds go into trays on the windowsill, fruit trees are pruned, and on a mild day the soil already smells of spring. Patience is the most important garden skill now.",
        "This is the month of waking up. The soil warms, the first sowings go into the cold ground, and every morning there is something new to see. It is early, and that is exactly the beauty of it.",
        "The weather does what it likes, and the gardener plays along. Sowing, pricking out, hardening off, guarding against a late frost: the pace picks up. Seedlings appear everywhere, small and full of promise.",
        "Now everything bursts open. Once the last frost is behind you, tomatoes, courgettes and beans move outside. The garden visibly fills up, and the first lettuce and radishes taste like a reward.",
        "Abundance is on its way. Long evenings in the garden, weeding, tying in, watering, and the first strawberries and peas. What you sowed in spring starts to give back.",
        "High summer. Harvesting becomes a daily habit, watering a ritual. There is work, but it feels light, because something is ripening everywhere.",
        "The month of baskets. Tomatoes, beans, courgettes: sometimes more than you can eat. It is also time to look ahead: what you sow now, you harvest in autumn.",
        "The garden turns golden. The harvest goes on, the mornings turn crisp, and the first empty beds ask for a green manure or a winter crop. Time to store, preserve and enjoy.",
        "Tidying up and getting ready. Bringing in the squash, covering beds, planting bulbs for spring. The garden withdraws, but leaves a lot behind.",
        "Quiet and honest. What remains is structure: paths, beds, bare branches. A good month to mulch, turn the compost and think the year over.",
        "The year comes to a close. The garden rests under leaves and frost. By the fire you look back at what worked and what did not, and begin to dream of next year.",
    ],
    "fr": [
        "Le jardin dort, mais pas le jardinier. C'est le mois des catalogues de graines et des longues soirées, des projets qui peuvent encore tout devenir. Dehors, tout est calme ; à l'intérieur, la nouvelle année pousse déjà dans votre tête.",
        "Les jours rallongent nettement. Les premières graines vont en caissette sur l'appui de fenêtre, on taille les fruitiers, et par une journée douce la terre sent déjà le printemps. La patience est maintenant la première qualité du jardinier.",
        "C'est le mois du réveil. Le sol se réchauffe, les premiers semis vont dans la terre encore froide, et chaque matin il y a du nouveau à voir. C'est tôt, et c'est justement ce qui est beau.",
        "Le temps fait ce qu'il veut, et le jardinier suit. Semer, repiquer, endurcir, protéger d'une gelée tardive : le rythme s'accélère. Les plantules apparaissent partout, petites et pleines de promesses.",
        "Tout explose. Une fois les dernières gelées passées, tomates, courgettes et haricots sortent. Le potager se remplit à vue d'œil, et les premières laitues et radis ont le goût d'une récompense.",
        "L'abondance est en route. Longues soirées au jardin, désherbage, palissage, arrosage, et les premières fraises et petits pois. Ce que vous avez semé au printemps commence à rendre.",
        "Plein été. Récolter devient une habitude quotidienne, arroser un rituel. Il y a du travail, mais il semble léger, car partout quelque chose mûrit.",
        "Le mois des paniers. Tomates, haricots, courgettes : parfois plus qu'on ne peut en manger. C'est aussi le moment de voir plus loin : ce que vous semez maintenant, vous le récolterez à l'automne.",
        "Le jardin se dore. La récolte continue, les matins deviennent frais, et les premières planches vides réclament un engrais vert ou une culture d'hiver. Le temps de conserver, de mettre en bocaux et de savourer.",
        "On range et on prépare. Rentrer les courges, couvrir les planches, planter les bulbes pour le printemps. Le jardin se retire, mais laisse beaucoup derrière lui.",
        "Calme et sincère. Il reste la structure : allées, planches, branches nues. Un bon mois pour pailler, retourner le compost et repenser l'année.",
        "L'année touche à sa fin. Le jardin se repose sous les feuilles et le gel. Au coin du feu, on repense à ce qui a réussi et à ce qui a raté, et l'on commence à rêver de l'année prochaine.",
    ],
}  # fmt: skip

FILLER_LINES = {
    "nl": [
        "Een tuin is nooit af. Gelukkig maar.",
        "Wie zaait, moet kunnen wachten.",
        "De beste mest is de voetstap van de tuinier.",
        "Elk zaadje is een kleine belofte aan de toekomst.",
        "Onkruid is een plant waarvan je de deugden nog niet kent.",
        "Oogsten is het mooiste werk dat met geduld begon.",
    ],
    "en": [
        "A garden is never finished. Thankfully.",
        "Who sows must learn to wait.",
        "The best fertiliser is the gardener's footstep.",
        "Every seed is a small promise to the future.",
        "A weed is a plant whose virtues have not yet been discovered.",
        "Harvesting is the finest work that started with patience.",
    ],
    "fr": [
        "Un jardin n'est jamais fini. Heureusement.",
        "Qui sème doit savoir attendre.",
        "Le meilleur engrais, c'est le pas du jardinier.",
        "Chaque graine est une petite promesse faite à l'avenir.",
        "Une mauvaise herbe est une plante dont on n'a pas encore découvert les vertus.",
        "Récolter est le plus beau des travaux, et il a commencé par la patience.",
    ],
}

GLOSSARY: dict[str, list[tuple[str, str]]] = {
    "nl": [
        ("Afharden", "Jonge planten die binnen werden opgekweekt een week of twee laten wennen aan buiten: overdag naar buiten, 's nachts weer binnen."),
        ("Bodembedekker", "Laag, breed groeiend gewas dat de grond bedekt en zo onkruid onderdrukt en vocht vasthoudt."),
        ("Compost", "Verteerd plantaardig materiaal dat de bodem voedt en de structuur verbetert."),
        ("Doorschieten", "Een gewas dat vroegtijdig in bloei gaat (bijvoorbeeld sla of spinazie bij hitte of lange dagen), waardoor de oogst minder lekker wordt."),
        ("Dunnen", "Overtollige zaailingen weghalen zodat de rest genoeg ruimte krijgt."),
        ("Eerste vorst", "De gemiddelde datum waarop het in de herfst voor het eerst vriest; vorstgevoelige gewassen moeten dan binnen of geoogst zijn."),
        ("Familie", "Groep verwante planten, zoals nachtschade, kruisbloemigen of vlinderbloemigen. Belangrijk voor de vruchtwisseling."),
        ("Groenbemester", "Gewas dat je niet oogst maar onderwerkt of laat liggen om de bodem te voeden en te beschermen, zoals facelia of klaver."),
        ("Kiemen", "Het moment waarop een zaad openbreekt en een wortel en kiemblaadjes vormt."),
        ("Laatste vorst", "De gemiddelde datum waarop het in het voorjaar voor het laatst vriest; daarna mogen vorstgevoelige gewassen naar buiten."),
        ("Mulchen", "De grond afdekken met stro, blad, gras of compost om vocht vast te houden, onkruid te remmen en het bodemleven te voeden."),
        ("Ophogen (aanaarden)", "Grond tegen de stengel aanhalen, zoals bij aardappelen en prei, voor steun en een betere oogst."),
        ("Opvolgteelt", "Een tweede of derde gewas in hetzelfde bed in hetzelfde seizoen, zodra het eerste geoogst is."),
        ("Pikeren (verspenen)", "Zaailingen uit een zaaibak overzetten naar een eigen potje zodat ze verder kunnen groeien."),
        ("Snoeien", "Takken of scheuten wegknippen voor een gezonde vorm en een betere oogst."),
        ("Teelt", "Eén gewas op één plek in één seizoen, van zaaien tot oogsten."),
        ("Toppen (dieven)", "Zijscheuten of de top van een plant uitknijpen, bijvoorbeeld bij tomaat, om de groei te sturen."),
        ("Uitplanten", "Een opgekweekte plant op zijn definitieve plek in de tuin zetten."),
        ("Vollegrond", "Gewoon buiten in de tuin, niet in een kas, tunnel of pot."),
        ("Voorzaaien", "Binnen of in de kas zaaien, zodat de plant al een voorsprong heeft wanneer hij naar buiten gaat."),
        ("Vruchtwisseling", "Elk jaar een andere plantenfamilie in een bed telen, zodat ziekten zich niet ophopen en de bodem in balans blijft."),
        ("Waterbalans", "Hoeveel water een bed kwijtraakt door zon en wind en terugkrijgt door regen en bewatering; Hortulus rekent ermee om te weten wanneer er water nodig is."),
        ("Zaaivenster", "De periode waarin een gewas het best gezaaid wordt in jouw streek."),
    ],
    "en": [
        ("Bolting", "A crop flowering too early (lettuce or spinach in heat or long days, for instance), which spoils the harvest."),
        ("Compost", "Decomposed plant material that feeds the soil and improves its structure."),
        ("Crop rotation", "Growing a different plant family in a bed every year, so diseases do not build up and the soil stays balanced."),
        ("Direct sowing", "Sowing seed straight into the bed where the plant will grow."),
        ("Earthing up", "Drawing soil up against the stem, as with potatoes and leeks, for support and a better harvest."),
        ("Family", "A group of related plants, such as nightshades, brassicas or legumes. Important for crop rotation."),
        ("First frost", "The average date of the first autumn frost; tender crops must be harvested or brought in by then."),
        ("Germination", "The moment a seed breaks open and forms a root and seed leaves."),
        ("Green manure", "A crop grown not to harvest but to dig in or leave on the surface to feed and protect the soil, such as phacelia or clover."),
        ("Ground cover", "A low, spreading crop that covers the soil, suppressing weeds and holding moisture."),
        ("Hardening off", "Letting plants raised indoors get used to the outdoors for a week or two: outside by day, back in at night."),
        ("Last frost", "The average date of the last spring frost; after it, tender crops can go outside."),
        ("Mulching", "Covering the soil with straw, leaves, grass clippings or compost to hold moisture, slow weeds and feed soil life."),
        ("Pinching out", "Removing side shoots or the tip of a plant, as with tomatoes, to steer its growth."),
        ("Planting", "One crop in one place in one season, from sowing to harvest."),
        ("Planting out", "Setting a plant raised elsewhere into its final place in the garden."),
        ("Pricking out", "Moving seedlings from a tray into their own pots so they can keep growing."),
        ("Pruning", "Cutting back branches or shoots for a healthy shape and a better crop."),
        ("Sowing window", "The period in which a crop is best sown in your region."),
        ("Starting indoors", "Sowing inside or in a greenhouse, so the plant has a head start when it goes outside."),
        ("Succession sowing", "A second or third crop in the same bed in the same season, once the first is harvested."),
        ("Thinning", "Removing surplus seedlings so the rest have enough room."),
        ("Water balance", "How much water a bed loses to sun and wind and gets back from rain and watering; Hortulus uses it to know when water is needed."),
    ],
    "fr": [
        ("Bilan hydrique", "La quantité d'eau qu'une planche perd par le soleil et le vent et regagne par la pluie et l'arrosage ; Hortulus s'en sert pour savoir quand arroser."),
        ("Butter", "Ramener de la terre contre le pied, comme pour les pommes de terre et les poireaux, pour le soutien et une meilleure récolte."),
        ("Compost", "Matière végétale décomposée qui nourrit le sol et améliore sa structure."),
        ("Couvre-sol", "Culture basse et étalée qui couvre le sol, limite les mauvaises herbes et retient l'humidité."),
        ("Culture", "Une plante à un endroit pendant une saison, du semis à la récolte."),
        ("Culture successive", "Une deuxième ou troisième culture dans la même planche la même saison, dès que la première est récoltée."),
        ("Dernières gelées", "La date moyenne des dernières gelées de printemps ; ensuite, les cultures frileuses peuvent sortir."),
        ("Éclaircir", "Retirer les semis en trop pour que les autres aient assez de place."),
        ("Endurcir", "Habituer pendant une ou deux semaines les plants élevés à l'intérieur à l'extérieur : dehors le jour, à l'abri la nuit."),
        ("Engrais vert", "Culture qu'on ne récolte pas mais qu'on incorpore ou laisse en surface pour nourrir et protéger le sol, comme la phacélie ou le trèfle."),
        ("Famille", "Groupe de plantes apparentées, comme les solanacées, les crucifères ou les légumineuses. Important pour la rotation des cultures."),
        ("Fenêtre de semis", "La période pendant laquelle une culture se sème le mieux dans votre région."),
        ("Germination", "Le moment où une graine s'ouvre et forme une racine et des cotylédons."),
        ("Monter en graine", "Une culture qui fleurit trop tôt (laitue ou épinard par forte chaleur ou jours longs, par exemple), ce qui gâche la récolte."),
        ("Paillage", "Couvrir le sol de paille, de feuilles, de tonte ou de compost pour garder l'humidité, freiner les mauvaises herbes et nourrir la vie du sol."),
        ("Pincer", "Supprimer les gourmands ou l'extrémité d'une plante, comme pour la tomate, pour orienter sa croissance."),
        ("Pleine terre", "Directement dehors au jardin, pas en serre, sous tunnel ni en pot."),
        ("Premières gelées", "La date moyenne des premières gelées d'automne ; les cultures frileuses doivent être récoltées ou rentrées avant."),
        ("Repiquer", "Installer un plant élevé ailleurs à sa place définitive au jardin."),
        ("Repiquer en godets", "Transférer les plantules d'une caissette dans leur propre godet pour qu'elles continuent à pousser."),
        ("Rotation des cultures", "Cultiver chaque année une autre famille dans une planche, pour que les maladies ne s'accumulent pas et que le sol reste équilibré."),
        ("Semis à l'abri", "Semer à l'intérieur ou en serre, pour que la plante ait de l'avance quand elle sort."),
        ("Semis direct", "Semer directement dans la planche où la plante poussera."),
        ("Taille", "Couper des branches ou des pousses pour une forme saine et une meilleure récolte."),
    ],
}  # fmt: skip

SOW_TYPES = {TaskType.SOW_INDOOR, TaskType.SOW_DIRECT, TaskType.TRANSPLANT, TaskType.HARDEN_OFF}
GARDEN_TYPES = {
    TaskType.SOIL_PREP, TaskType.COMPOST, TaskType.GREEN_MANURE, TaskType.MULCH, TaskType.CLEAN_GREENHOUSE,
    TaskType.WINTER_PREP, TaskType.PLAN_SEASON, TaskType.TOOL_CARE, TaskType.SOIL_TEST, TaskType.CUT_BACK,
    TaskType.DIVIDE,
}  # fmt: skip


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def safe(text: str) -> str:
    """Text the standard PDF fonts can show: accents kept, emoji and the like dropped."""
    out = []
    for ch in text.replace("\r", ""):
        ch = _REPLACE.get(ch, ch)
        try:
            ch.encode("cp1252")
            out.append(ch)
        except UnicodeEncodeError:
            base = unicodedata.normalize("NFKD", ch)[:1]
            if base and base.isascii() and base.isprintable():
                out.append(base)
    return "".join(out).strip()


def fmt_num(value: float, lang: str, digits: int = 1) -> str:
    text = f"{value:,.{digits}f}" if digits else f"{round(value):,}"
    if digits:
        text = text.rstrip("0").rstrip(".") if "." in text else text
    if lang in ("nl", "fr"):
        sep = "." if lang == "nl" else "\xa0"  # fr: non-breaking space between thousands
        text = text.replace(",", "\x00").replace(".", ",").replace("\x00", sep)
    return text


def fmt_kg(kg: float, lang: str) -> str:
    return f"{fmt_num(kg, lang, 1 if kg < 100 else 0)} kg"


def join_names(names: Sequence[str], lang: str, limit: int = 5) -> str:
    names = list(dict.fromkeys(n for n in names if n))
    words = TEXT[lang]
    if len(names) > limit:
        rest = len(names) - limit + 1
        return f"{', '.join(names[: limit - 1])} {words['and_more'].format(n=rest)}"
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} {words['and']} {names[-1]}"


@dataclass(slots=True)
class MonthData:
    year: int
    month: int
    sown: list[tuple[date, Planting, str]] = field(default_factory=list)  # (day, planting, how)
    events: list[tuple[date, Planting, str]] = field(default_factory=list)  # planted out, first harvest, done
    tasks: list[Task] = field(default_factory=list)
    journal: list[JournalEntry] = field(default_factory=list)
    harvests: list[HarvestEntry] = field(default_factory=list)
    liters: float = 0.0
    runs: int = 0
    tmax: float | None = None
    tmin: float | None = None
    rain: float = 0.0
    frost_nights: int = 0
    climate_days: int = 0

    @property
    def photos(self) -> int:
        return sum(len(e.photos) for e in self.journal)

    @property
    def kg(self) -> float:
        return sum(h.kg for h in self.harvests)

    @property
    def empty(self) -> bool:
        return not (self.sown or self.events or self.tasks or self.journal or self.harvests or self.runs)


def collect_months(data, season: int) -> list[MonthData]:
    """Everything that happened in the season, month by month."""
    region = data.settings.region
    start, _end = season_bounds(region, season)
    months = [
        MonthData((start.year * 12 + start.month - 1 + i) // 12, (start.month - 1 + i) % 12 + 1) for i in range(12)
    ]
    index = {(m.year, m.month): m for m in months}

    def at(day: date | None) -> MonthData | None:
        return index.get((day.year, day.month)) if day else None

    for p in data.plantings:
        if p.sown_on and (m := at(p.sown_on)):
            how = "sown_in" if p.method is SowMethod.INDOOR_SOW else "sown_out"
            m.sown.append((p.sown_on, p, how))
        if p.transplanted_on and (m := at(p.transplanted_on)):
            m.sown.append((p.transplanted_on, p, "planted"))
        if p.harvest_started_on and (m := at(p.harvest_started_on)):
            m.events.append((p.harvest_started_on, p, "first_harvest"))
        if p.finished_on and (m := at(p.finished_on)):
            m.events.append((p.finished_on, p, "failed" if p.status is PlantingStatus.FAILED else "finished"))
    covered = {(p.id, d) for m in months for d, p, _ in m.sown}
    for task in data.tasks:
        if task.status is not TaskStatus.DONE or task.completed_at is None:
            continue
        day = task.completed_at.date()
        if not (m := at(day)) or task.type is TaskType.HARVEST or task.type is TaskType.WATER:
            continue  # harvest and water have their own sections
        if task.type in SOW_TYPES and task.planting_id and any(pid == task.planting_id for pid, _ in covered):
            continue  # already listed from the planting's own dates
        m.tasks.append(task)
    for e in data.journal:
        if m := at(e.at.date()):
            m.journal.append(e)
    for h in data.harvest_log:
        if m := at(h.day):
            m.harvests.append(h)
    for ev in data.irrigation_log:
        if m := at(ev.at.date()):
            m.liters += ev.liters
            m.runs += 1
    for c in data.climate_log:
        if not (m := at(c.day)):
            continue
        m.climate_days += 1
        if c.tmax is not None:
            m.tmax = c.tmax if m.tmax is None else max(m.tmax, c.tmax)
        if c.tmin is not None:
            m.tmin = c.tmin if m.tmin is None else min(m.tmin, c.tmin)
            m.frost_nights += c.tmin < 0
        m.rain += c.rain_mm or 0.0
    for m in months:
        m.sown.sort(key=lambda x: x[0])
        m.events.sort(key=lambda x: x[0])
        m.tasks.sort(key=lambda x: x.completed_at)  # type: ignore[arg-type, return-value]
        m.journal.sort(key=lambda e: e.at)
        m.harvests.sort(key=lambda h: h.day)
    return months


# --------------------------------------------------------------------------- #
# Typesetting
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class BookPage:
    pdf: Surface
    kind: str  # cover, plain, body, opener, notes, back
    header: str = ""


class Book:
    """A flow of text and pictures over book pages with mirrored margins."""

    def __init__(
        self, factory: Callable[[float, float], Surface], width: float, height: float, lang: str, gray: bool, title: str
    ) -> None:
        self.factory = factory
        self.w, self.h = width, height
        self.k = max(1.0, min(1.35, width / 148))
        self.lang = lang
        self.gray = gray
        self.title = title
        self.pages: list[BookPage] = []
        self.inner, self.outer = 19 * self.k, 15 * self.k
        self.top, self.bottom = 17 * self.k, 19 * self.k
        self.y = 0.0
        self.header = ""
        self.filler = 0

    # -- geometry ------------------------------------------------------ #
    def c(self, color: str) -> str:
        return to_gray(color) if self.gray else color

    @property
    def s(self) -> Surface:
        return self.pages[-1].pdf

    @property
    def number(self) -> int:
        return len(self.pages)

    def recto(self, number: int | None = None) -> bool:
        return (number or self.number) % 2 == 1

    @property
    def x0(self) -> float:
        return self.inner if self.recto() else self.outer

    @property
    def width(self) -> float:
        return self.w - self.inner - self.outer

    @property
    def ymax(self) -> float:
        return self.h - self.bottom

    def fs(self, size: float) -> float:
        return size * self.k

    # -- pages --------------------------------------------------------- #
    def page(self, kind: str = "body", header: str | None = None) -> Surface:
        pdf = self.factory(self.w, self.h)
        pdf.grayscale = self.gray  # type: ignore[attr-defined]
        self.pages.append(BookPage(pdf, kind, self.header if header is None else header))
        self.y = self.top + (6 * self.k if kind == "body" else 0)
        return pdf

    def to_recto(self) -> None:
        """Make sure the next page is a right-hand page (filling with a notes page)."""
        if self.number % 2 == 1:
            self.notes_page()

    def notes_page(self) -> None:
        s = self.page("notes", header="")
        words = TEXT[self.lang]
        lines = FILLER_LINES[self.lang]
        quote = lines[self.filler % len(lines)]
        self.filler += 1
        x0 = self.x0
        s.text(x0, self.top + 6 * self.k, words["notes"], size=self.fs(11), font="serif-italic", color=self.c(MUTED))
        y = self.top + 14 * self.k
        pitch = 6 * self.k
        dots = []
        while y < self.ymax - 18 * self.k:
            x = x0
            while x <= x0 + self.width:
                dots.append((x, y))
                x += pitch
            y += pitch
        s.dots(dots, r=0.18, color=self.c(FAINT))
        s.text(self.w / 2, self.ymax - 6 * self.k, quote, size=self.fs(8.5), font="serif-italic", color=self.c(MUTED),
               anchor="middle")  # fmt: skip

    def need(self, h: float) -> None:
        if self.y + h > self.ymax:
            self.page("body")

    # -- text ---------------------------------------------------------- #
    def para(
        self, text: str, *, font: str = "serif", size: float = 10.0, lead: float = 1.42, justify: bool = True,
        color: str = INK, after: float = 2.6, indent: float = 0.0, align: str = "start",
    ) -> None:  # fmt: skip
        size = self.fs(size)
        step = size * lead * PT_TO_MM
        width = self.width - indent
        for block in safe(text).split("\n"):
            if not block.strip():
                continue
            lines = wrap(block.strip(), width, size, font=font)
            for i, line in enumerate(lines):
                self.need(step)
                self.y += step
                x = self.x0 + indent
                spacing = 0.0
                if justify and i < len(lines) - 1 and line.count(" "):
                    gap = (width - text_width(line, size, font=font)) / line.count(" ")
                    spacing = gap if 0 < gap < 2.8 * self.k else 0.0
                if align == "middle":
                    x = self.x0 + self.width / 2
                self.s.text(x, self.y - step * 0.28, line, size=size, font=font, color=self.c(color), spacing=spacing,
                            anchor=align)  # fmt: skip
            self.y += after * self.k

    def heading(self, text: str, *, keep: float = 24.0) -> None:
        self.need((12 + keep) * self.k)
        self.y += 5 * self.k
        size = self.fs(12.5)
        self.y += size * PT_TO_MM
        self.s.text(self.x0, self.y, safe(text), size=size, font="serif-bold", color=self.c(BRAND))
        self.y += 1.6 * self.k
        self.s.line(self.x0, self.y, self.x0 + 14 * self.k, self.y, stroke=self.c(SUN), width=0.6)
        self.y += 3.2 * self.k

    def label(self, text: str, *, keep: float = 12.0) -> None:
        """Small sans caption above an item (a date line in the journal)."""
        self.need((5 + keep) * self.k)
        self.y += 2.0 * self.k
        size = self.fs(7.4)
        self.y += size * PT_TO_MM
        self.s.text(self.x0, self.y, safe(text).upper(), size=size, font="sans-bold", color=self.c(MUTED))
        self.y += 1.4 * self.k

    def items(self, rows: Iterable[tuple[str, str]], *, key_width: float = 20.0) -> None:
        """Two-column list: a short key (a date) and its text, wrapped under itself."""
        size = self.fs(9.2)
        step = size * 1.38 * PT_TO_MM
        kw = key_width * self.k
        for key, text in rows:
            lines = wrap(safe(text), self.width - kw, size, font="serif")
            self.need(step * min(len(lines), 3))
            for i, line in enumerate(lines):
                self.need(step)
                self.y += step
                if i == 0:
                    self.s.text(self.x0, self.y - step * 0.28, safe(key), size=self.fs(7.6), font="sans",
                                color=self.c(MUTED))  # fmt: skip
                self.s.text(self.x0 + kw, self.y - step * 0.28, line, size=size, font="serif", color=self.c(INK))
        self.y += 2.2 * self.k

    def table(self, head: Sequence[str], rows: Sequence[Sequence[str]], widths: Sequence[float]) -> None:
        size = self.fs(8.6)
        step = size * 1.55 * PT_TO_MM
        total = sum(widths)
        cols = [w / total * self.width for w in widths]

        def row(cells: Sequence[str], *, bold: bool) -> None:
            self.need(step)
            self.y += step
            x = self.x0
            for i, (cell, w) in enumerate(zip(cells, cols, strict=False)):
                font = "sans-bold" if bold else ("serif" if i == 0 else "sans")
                text = safe(cell)
                while text and text_width(text, size, font=font) > w - 1.5:
                    text = text[:-1]
                if i == 0:
                    self.s.text(x, self.y - step * 0.3, text, size=size, font=font, color=self.c(INK))
                else:
                    self.s.text(x + w - 1, self.y - step * 0.3, text, size=size, font=font, color=self.c(INK),
                                anchor="end")  # fmt: skip
                x += w
            self.s.line(self.x0, self.y + 0.6, self.x0 + self.width, self.y + 0.6, stroke=self.c(FAINT), width=0.15)

        row(head, bold=True)
        for r in rows:
            row(r, bold=False)
        self.y += 3 * self.k

    # -- pictures ------------------------------------------------------ #
    def picture(self, s: Surface, img: Image, x: float, y: float, w: float, h: float) -> None:
        """Fill the box with the photo, cropping what sticks out (cover)."""
        iw, ih = w, w * img.aspect
        if ih < h:
            ih, iw = h, h / img.aspect
        with s.clip(x, y, w, h):
            s.image(x - (iw - w) / 2, y - (ih - h) / 2, iw, ih, img)

    def photos(self, images: Sequence[Image], caption: str = "") -> None:
        if not images:
            return
        gap = 2.5 * self.k
        if len(images) == 1:
            img = images[0]
            w = self.width
            h = min(w * img.aspect, 105 * self.k)
            if h < w * img.aspect:  # tall photo: narrower, centred
                w = h / img.aspect
            self.need(h + 8 * self.k)
            self.y += 1.5 * self.k
            x = self.x0 + (self.width - w) / 2
            self.s.image(x, self.y, w, h, img)
            self.y += h
        else:
            cols = 2 if len(images) in (2, 4) else 3
            w = (self.width - gap * (cols - 1)) / cols
            h = w * 0.75
            for start in range(0, len(images), cols):
                self.need(h + gap + 6 * self.k)
                self.y += gap if start else 1.5 * self.k
                for i, img in enumerate(images[start : start + cols]):
                    self.picture(self.s, img, self.x0 + i * (w + gap), self.y, w, h)
                self.y += h
        if caption:
            self.y += 3.2 * self.k
            self.s.text(self.x0, self.y, safe(caption), size=self.fs(7.2), font="serif-italic", color=self.c(MUTED))
        self.y += 3.5 * self.k

    def ornament(self) -> None:
        self.need(8 * self.k)
        self.y += 4 * self.k
        cx = self.x0 + self.width / 2
        self.s.line(cx - 12 * self.k, self.y, cx - 3 * self.k, self.y, stroke=self.c(FAINT), width=0.3)
        self.s.line(cx + 3 * self.k, self.y, cx + 12 * self.k, self.y, stroke=self.c(FAINT), width=0.3)
        self.s.circle(cx, self.y, 1.0 * self.k, fill=self.c(LEAF))
        self.y += 4 * self.k

    # -- running heads and folios ---------------------------------------- #
    def finish(self) -> None:
        for n, page in enumerate(self.pages, start=1):
            if page.kind not in ("body", "opener", "notes"):
                continue
            s = page.pdf
            recto = n % 2 == 1
            x_outer = self.w - self.outer if recto else self.outer
            anchor = "end" if recto else "start"
            s.text(x_outer, self.h - self.bottom + 9 * self.k, str(n), size=self.fs(8), font="serif",
                   color=self.c(MUTED), anchor=anchor)  # fmt: skip
            if page.kind == "body":
                head = page.header if recto else self.title
                y = self.top + 1.5 * self.k
                s.text(
                    x_outer, y, safe(head).upper(), size=self.fs(6.6), font="sans", color=self.c(MUTED), anchor=anchor
                )
                x1, x2 = (self.inner, self.w - self.outer) if recto else (self.outer, self.w - self.inner)
                s.line(x1, y + 1.8 * self.k, x2, y + 1.8 * self.k, stroke=self.c(FAINT), width=0.2)


# --------------------------------------------------------------------------- #
# The book
# --------------------------------------------------------------------------- #
class SeasonBook:
    def __init__(self, ctx, opts, factory: Callable[[float, float], Surface], preview_pages: int | None = None) -> None:
        from .printout import PAGE_SIZES

        self.ctx = ctx
        self.data = ctx.data
        self.db = ctx.db
        self.lang = normalize_lang(opts.lang)
        self.words = TEXT[self.lang]
        region = self.data.settings.region
        self.season = opts.season or season_for_date(region, ctx.today)
        self.south = region.hemisphere is Hemisphere.SOUTH
        width, height = PAGE_SIZES.get(opts.page, PAGE_SIZES["a5"])
        if opts.page in ("a3",):
            width, height = PAGE_SIZES["a4"]
        self.page_name = opts.page if opts.page in PAGE_SIZES else "a5"
        self.gray = opts.color_mode != "color"
        self.garden = ctx.garden_name or "Hortulus"
        title = opts.title or self.words["book"].format(season=self.season)
        self.title = title
        self.book = Book(factory, width, height, self.lang, self.gray, title)
        self.months = collect_months(self.data, self.season)
        self._figures: dict[str, float] | None = None
        self._opener_photo: str | None = None
        self._images: dict[str, Image | None] = {}
        self.preview_pages = preview_pages  # past these pages a photo only needs its size, not its pixels
        self.toc: list[tuple[str, str, int]] = []  # (title, summary, page number)

    # -- data helpers ---------------------------------------------------- #
    def plant_name(self, plant_id: str | None) -> str:
        plant = self.db.get(plant_id) if plant_id else None
        return safe(plant.name(self.lang)) if plant else (plant_id or "")

    def bed_name(self, bed_id: str | None) -> str:
        if not bed_id:
            return ""
        bed = self.data.bed(bed_id)
        if bed is None:
            for layout in self.data.layouts.values():
                bed = next((b for b in layout.beds if b.id == bed_id), None)
                if bed:
                    break
        return safe(bed.name) if bed else ""

    def crop(self, p: Planting) -> str:
        bed = self.bed_name(p.bed_id)
        return f"{self.plant_name(p.plant_id)} ({bed})" if bed else self.plant_name(p.plant_id)

    def day(self, d: date) -> str:
        return self.words["day_fmt"].format(d=d.day, month=MONTHS[self.lang][d.month - 1])

    def short_day(self, d: date) -> str:
        return self.words["day_fmt"].format(d=d.day, month=MONTHS[self.lang][d.month - 1][:3])

    def long_day(self, d: date) -> str:
        return self.words["date_long"].format(
            weekday=WEEKDAYS[self.lang][d.weekday()], d=d.day, month=MONTHS[self.lang][d.month - 1]
        )

    def image(self, photo_id: str) -> Image | None:
        if photo_id not in self._images:
            loader: PhotoLoader | None = getattr(self.ctx, "photos", None)
            probe = self.preview_pages is not None and self.book.number > self.preview_pages
            try:
                if loader is None:
                    self._images[photo_id] = None
                elif probe:
                    self._images[photo_id] = loader(photo_id, self.gray, probe=True)
                else:
                    self._images[photo_id] = loader(photo_id, self.gray)
            except Exception:
                self._images[photo_id] = None
        return self._images[photo_id]

    def entry_images(self, e: JournalEntry, limit: int = 6) -> list[Image]:
        return [img for img in (self.image(p) for p in e.photos[:limit]) if img]

    def task_title(self, task: Task) -> str:
        if task.title_key:
            text = t(task.title_key, self.lang, **task.title_params)
            if text != task.title_key:
                return safe(text)
        return safe(task.title)

    def month_title(self, m: MonthData) -> str:
        name = MONTHS[self.lang][m.month - 1]
        return name.capitalize() if self.lang in ("nl", "fr") else name

    def phase(self, m: MonthData) -> int:
        return (m.month - 1 + (6 if self.south else 0)) % 12

    # -- figures --------------------------------------------------------- #
    def figures(self) -> dict[str, float]:
        if self._figures is None:
            self._figures = self._count()
        return self._figures

    def _count(self) -> dict[str, float]:
        months = self.months
        season_plantings = [p for p in self.data.plantings if present_in(p, False, self.season)]
        return {
            "crops": len({p.plant_id for p in season_plantings}),
            "plantings": len(season_plantings),
            "kg": round(sum(m.kg for m in months), 1),
            "notes": sum(len(m.journal) for m in months),
            "photos": sum(m.photos for m in months),
            "liters": round(sum(m.liters for m in months)),
            "tasks": sum(len(m.tasks) for m in months),
            "sown": sum(sum(1 for _, _, how in m.sown if how != "planted") for m in months),
        }

    def summary(self, m: MonthData) -> str:
        w = self.words
        parts = []
        sown = sum(1 for _, _, how in m.sown if how != "planted")
        planted = sum(1 for _, _, how in m.sown if how == "planted")
        if sown:
            parts.append(w["summary_sown"].format(n=sown))
        if planted:
            parts.append(w["summary_planted"].format(n=planted))
        if m.journal:
            parts.append(w["summary_notes"].format(n=len(m.journal)))
        if m.photos:
            parts.append(w["summary_photos"].format(n=m.photos))
        if m.kg:
            parts.append(w["summary_kg"].format(kg=fmt_kg(m.kg, self.lang)))
        return " · ".join(parts) or w["summary_quiet"]

    # -- render ---------------------------------------------------------- #
    def render(self) -> list[tuple[str, int]]:
        """Lay out the book; returns the bookmarks (title, page index)."""
        b = self.book
        self.cover()
        self.epigraph()
        self.title_page()
        self.plan_page()
        toc_index = b.number  # the next page
        b.page("plain", header="")
        b.to_recto()
        self.introduction()
        for n, m in enumerate(self.months, start=1):
            self.chapter(n, m)
        self.numbers()
        self.glossary()
        # colophon on the inside of the back cover; page count a multiple of four
        while (b.number + 2) % 4:
            b.notes_page()
        self.colophon()
        self.back_cover()
        self.contents(b.pages[toc_index].pdf, toc_index + 1)
        b.finish()
        return [(title, page - 1) for title, _, page in self.toc]

    # -- front matter ---------------------------------------------------- #
    def cover_photo(self) -> Image | None:
        entries = [e for m in self.months for e in m.journal if e.photos]
        entries.sort(key=lambda e: (e.kind != "milestone", -len(e.photos)))
        for e in entries:
            for pid in e.photos:
                if img := self.image(pid):
                    return img
        return None

    def cover(self) -> None:
        b, w = self.book, self.words
        s = b.page("cover", header="")
        bg = b.c(BRAND)
        s.rect(0, 0, b.w, b.h, fill=bg)
        photo = self.cover_photo()
        band_y = b.h * 0.58
        if photo:
            b.picture(s, photo, 0, 0, b.w, band_y)
            s.rect(0, band_y - 1.2, b.w, 1.2, fill=b.c(SUN))
        else:
            for i, (r, color) in enumerate(((60, LEAF), (42, SUN), (26, PAPER))):
                s.circle(b.w * 0.62, b.h * 0.3, r * b.k, fill=b.c(color) if i < 2 else b.c(BRAND_DARK))
            self._leaf(s, b.w * 0.62, b.h * 0.3, 18 * b.k, b.c(PAPER))
        x = 16 * b.k
        y = band_y + 22 * b.k
        s.text(x, y, safe(self.title), size=b.fs(27), font="serif-bold", color="#FFFFFF")
        y += 10 * b.k
        s.text(
            x, y, safe(w["book_sub"].format(garden=self.garden)), size=b.fs(12.5), font="serif-italic", color="#FFFFFF"
        )
        figures = self.figures()
        facts = w["back_facts"].format(
            crops=int(figures["crops"]), kg=fmt_kg(figures["kg"], self.lang), notes=int(figures["notes"]),
            photos=int(figures["photos"]),
        )  # fmt: skip
        s.text(x, y + 9 * b.k, safe(facts), size=b.fs(8), font="sans", color=b.c("#DDE8E1"))
        self._leaf(s, x + 3 * b.k, b.h - 16 * b.k, 3.2 * b.k, "#FFFFFF")
        s.text(x + 8 * b.k, b.h - 14.8 * b.k, "Hortulus", size=b.fs(9), font="sans-bold", color="#FFFFFF")

    def _leaf(self, s: Surface, cx: float, cy: float, r: float, color: str) -> None:
        """A simple leaf: two arcs and a vein."""
        pts = []
        steps = 18
        for i in range(steps + 1):
            u = i / steps
            pts.append((cx - r + 2 * r * u, cy - r * 0.9 * (4 * u * (1 - u))))
        for i in range(steps, -1, -1):
            u = i / steps
            pts.append((cx - r + 2 * r * u, cy + r * 0.9 * (4 * u * (1 - u))))
        s.polygon(pts, fill=color)
        s.line(cx - r, cy, cx + r * 0.8, cy, stroke=self.book.c(BRAND_DARK), width=0.3 * self.book.k)

    def epigraph(self) -> None:
        b, w = self.book, self.words
        b.page("plain", header="")
        b.y = b.h * 0.42
        b.para(f"“{w['epigraph']}”", font="serif-italic", size=12, justify=False, align="middle", color=MUTED)
        b.para(f"– {w['epigraph_by']}", font="sans", size=7.5, justify=False, align="middle", color=MUTED)

    def title_page(self) -> None:
        b, w = self.book, self.words
        s = b.page("plain", header="")
        cx = b.w / 2
        self._leaf(s, cx, b.h * 0.27, 7 * b.k, b.c(LEAF))
        s.text(cx, b.h * 0.38, safe(self.title), size=b.fs(24), font="serif-bold", color=b.c(INK), anchor="middle")
        s.text(cx, b.h * 0.38 + 9 * b.k, safe(self.garden), size=b.fs(13), font="serif-italic", color=b.c(BRAND),
               anchor="middle")  # fmt: skip
        b.y = b.h * 0.38 + 18 * b.k
        b.para(w["title_lead"], font="serif", size=9.5, justify=False, align="middle", color=MUTED)
        s.text(cx, b.h - 26 * b.k, w["made_with"], size=b.fs(7.5), font="sans", color=b.c(MUTED), anchor="middle")

    def plan_page(self) -> None:
        from .printout import Box, Page, PrintOptions, Theme, draw_map

        b, w = self.book, self.words
        s = b.page("plain", header="")
        b.y = b.top
        s.text(b.x0, b.y + 8 * b.k, w["plan"].format(season=self.season), size=b.fs(15), font="serif-bold",
               color=b.c(INK))  # fmt: skip
        layout = layout_for(self.data, self.season)
        if layout is None or not layout.beds:
            b.y += 18 * b.k
            b.para(w["plan_none"], font="serif-italic", color=MUTED)
            return
        opts = PrintOptions(document="garden", page="a5", color_mode="color" if not self.gray else "grayscale",
                            season=self.season, lang=self.lang)  # fmt: skip
        page = Page(s, opts, self.ctx, Theme("color" if not self.gray else "grayscale"), self.title)
        box = Box(b.x0, b.top + 16 * b.k, b.width, b.h - b.top - b.bottom - 34 * b.k)
        try:
            draw_map(page, box, layout.zones, layout.beds, layout.features, self.season, plantings=True)
        except Exception:
            pass
        area = sum(bed.width_cm * bed.length_cm for bed in layout.beds) / 10_000
        b.y = b.ymax - 10 * b.k
        b.para(
            w["plan_caption"].format(beds=len(layout.beds), zones=len(layout.zones), area=fmt_num(area, self.lang)),
            font="serif-italic", size=8.5, justify=False, color=MUTED, align="middle",
        )  # fmt: skip

    def contents(self, s: Surface, number: int) -> None:
        b, w = self.book, self.words
        x0 = b.inner if number % 2 == 1 else b.outer
        y = b.top + 10 * b.k
        s.text(x0, y, w["toc"], size=b.fs(20), font="serif-bold", color=b.c(INK))
        y += 6 * b.k
        s.line(x0, y, x0 + 14 * b.k, y, stroke=b.c(SUN), width=0.6)
        y += 6 * b.k
        avail = b.ymax - y
        rows = len(self.toc) + sum(1 for _, sub, _ in self.toc if sub)
        step = min(5.6 * b.k, avail / max(rows, 1))
        size = min(b.fs(10), step / PT_TO_MM / 1.25)
        for title, sub, page in self.toc:
            y += step
            s.text(x0, y, safe(title), size=size, font="serif", color=b.c(INK))
            s.text(x0 + b.width, y, str(page), size=size, font="serif", color=b.c(INK), anchor="end")
            tw = text_width(safe(title), size, font="serif")
            dots = []
            x = x0 + tw + 2
            while x < x0 + b.width - 8:
                dots.append((x, y - 0.4))
                x += 1.6
            s.dots(dots, r=0.12, color=b.c(FAINT))
            if sub:
                y += step * 0.85
                s.text(x0 + 4 * b.k, y - step * 0.15, safe(sub), size=size * 0.74, font="sans", color=b.c(MUTED))

    # -- body ------------------------------------------------------------ #
    def chapter_title(self, title: str, kicker: str = "") -> None:
        b = self.book
        b.to_recto()
        s = b.page("opener", header=title)
        b.header = title
        b.y = b.top + 30 * b.k
        if kicker:
            s.text(b.x0, b.y, safe(kicker).upper(), size=b.fs(7.5), font="sans-bold", color=b.c(SUN))
            b.y += 11 * b.k
        s.text(b.x0, b.y, safe(title), size=b.fs(24), font="serif-bold", color=b.c(INK))
        b.y += 5 * b.k
        s.line(b.x0, b.y, b.x0 + 18 * b.k, b.y, stroke=b.c(SUN), width=0.8)
        b.y += 8 * b.k

    def introduction(self) -> None:
        b, w, lang = self.book, self.words, self.lang
        self.chapter_title(w["intro"])
        self.toc.append((w["intro"], "", b.number))
        f = self.figures()
        layout = layout_for(self.data, self.season)
        beds = len(layout.beds) if layout else 0
        zones = len(layout.zones) if layout else 0
        region = self.data.settings.region
        names = Counter(p.plant_id for p in self.data.plantings if p.season == self.season)
        top = join_names([self.plant_name(pid) for pid, _ in names.most_common(6)], lang)
        harvest = defaultdict(float)
        for m in self.months:
            for h in m.harvests:
                harvest[h.plant_id] += h.kg
        best = max(harvest.items(), key=lambda kv: kv[1]) if harvest else None
        busiest = max(self.months, key=lambda m: len(m.sown) + len(m.tasks) + len(m.journal) + len(m.harvests))
        first_sow = next((d for m in self.months for d, _, how in m.sown if how != "planted"), None)
        if lang == "nl":
            paras = [
                f"Dit is het verhaal van {self.garden} in {self.season}. Niet zoals we het ons in de winter voorstelden, maar zoals het werkelijk ging: wat er gezaaid werd en wanneer, wat er opkwam en wat niet, wat we zagen, opschreven en fotografeerden, en wat de tuin ons uiteindelijk teruggaf.",
                f"De tuin telde dit jaar {beds} bedden verdeeld over {zones} zones. Er groeiden {int(f['crops'])} verschillende gewassen in {int(f['plantings'])} teelten"
                + (f", met onder meer {top}" if top else "")
                + ". "
                + (f"Het seizoen begon met de eerste zaaiactie op {self.day(first_sow)}. " if first_sow else "")
                + f"In de streek valt de laatste vorst gemiddeld rond {self._mmdd(region.last_frost)} en de eerste rond {self._mmdd(region.first_frost)}; daartussen ligt het venster waarin alles moet gebeuren.",
                (
                    f"Er werd in totaal {fmt_kg(f['kg'], lang)} geoogst"
                    + (f", met {self.plant_name(best[0])} als koploper ({fmt_kg(best[1], lang)})" if best else "")
                    + ". "
                    if f["kg"]
                    else "Er werd dit seizoen (nog) geen oogst gewogen. "
                )
                + f"Het dagboek kreeg {int(f['notes'])} notities en {int(f['photos'])} foto's, en {int(f['tasks'])} taken werden afgevinkt. "
                + (f"Hortulus gaf de bedden samen {fmt_num(f['liters'], lang, 0)} liter water. " if f["liters"] else "")
                + (f"De drukste maand was {MONTHS[lang][busiest.month - 1]}." if not busiest.empty else ""),
                "Elk hoofdstuk in dit boek is één maand. Het begint met wat die tijd van het jaar typeert, en vertelt dan wat er in jouw tuin gebeurde: wat er gezaaid en geplant werd, welk werk er gedaan is, wat je in je dagboek schreef, met je eigen foto's, wat er geoogst werd en hoe het weer was. Achteraan vind je het jaar in cijfers, een woordenlijst en ruimte voor notities.",
                "Lees het als een herinnering, gebruik het als leidraad voor volgend jaar, of geef het door aan wie na jou in deze tuin komt werken. Een tuin onthoudt veel, maar niet alles: daarom dit boek.",
            ]
        elif lang == "fr":
            paras = [
                f"Voici l'histoire de {self.garden} en {self.season}. Pas telle que nous l'imaginions en hiver, mais telle qu'elle s'est vraiment passée : ce qui a été semé et quand, ce qui a levé et ce qui n'a pas levé, ce que nous avons vu, noté et photographié, et ce que le jardin nous a finalement rendu.",
                f"Cette année, le jardin comptait {beds} planches réparties en {zones} zones. {int(f['crops'])} cultures différentes ont poussé en {int(f['plantings'])} plantations"
                + (f", dont {top}" if top else "") + ". "
                + (f"La saison a commencé avec le premier semis le {self.day(first_sow)}. " if first_sow else "")
                + f"Dans la région, les dernières gelées tombent en moyenne vers le {self._mmdd(region.last_frost)} et les premières vers le {self._mmdd(region.first_frost)} ; entre les deux s'ouvre la fenêtre où tout doit se passer.",
                (f"Au total, {fmt_kg(f['kg'], lang)} ont été récoltés" + (f", avec {self.plant_name(best[0])} en tête ({fmt_kg(best[1], lang)})" if best else "") + ". " if f["kg"] else "Aucune récolte n'a (encore) été pesée cette saison. ")
                + f"Le journal a reçu {int(f['notes'])} notes et {int(f['photos'])} photos, et {int(f['tasks'])} tâches ont été cochées. "
                + (f"Hortulus a donné en tout {fmt_num(f['liters'], lang, 0)} litres d'eau aux planches. " if f["liters"] else "")
                + (f"Le mois le plus chargé a été {MONTHS[lang][busiest.month - 1]}." if not busiest.empty else ""),
                "Chaque chapitre de ce livre est un mois. Il s'ouvre sur ce qui caractérise ce moment de l'année, puis raconte ce qui s'est passé dans votre jardin : ce qui a été semé et planté, les travaux faits, ce que vous avez écrit dans votre journal, avec vos propres photos, ce qui a été récolté et le temps qu'il a fait. À la fin, vous trouverez l'année en chiffres, un glossaire et de la place pour vos notes.",
                "Lisez-le comme un souvenir, servez-vous-en comme guide pour l'an prochain, ou transmettez-le à qui jardinera ici après vous. Un jardin se souvient de beaucoup de choses, mais pas de tout : d'où ce livre.",
            ]  # fmt: skip
        else:
            paras = [
                f"This is the story of {self.garden} in {self.season}. Not the way we pictured it in winter, but the way it really went: what was sown and when, what came up and what did not, what we saw, wrote down and photographed, and what the garden gave back in the end.",
                f"This year the garden had {beds} beds in {zones} zones. {int(f['crops'])} different crops grew in {int(f['plantings'])} plantings"
                + (f", among them {top}" if top else "") + ". "
                + (f"The season began with the first sowing on {self.day(first_sow)}. " if first_sow else "")
                + f"Here the last frost comes around {self._mmdd(region.last_frost)} and the first around {self._mmdd(region.first_frost)}; in between lies the window in which everything has to happen.",
                (f"In all, {fmt_kg(f['kg'], lang)} was harvested" + (f", with {self.plant_name(best[0])} leading the way ({fmt_kg(best[1], lang)})" if best else "") + ". " if f["kg"] else "No harvest was weighed this season (yet). ")
                + f"The journal received {int(f['notes'])} notes and {int(f['photos'])} photos, and {int(f['tasks'])} tasks were ticked off. "
                + (f"Hortulus gave the beds {fmt_num(f['liters'], lang, 0)} litres of water in all. " if f["liters"] else "")
                + (f"The busiest month was {MONTHS[lang][busiest.month - 1]}." if not busiest.empty else ""),
                "Each chapter in this book is one month. It opens with what that time of year is like, then tells what happened in your garden: what was sown and planted, what work was done, what you wrote in your journal, with your own photos, what was harvested and what the weather was like. At the back you will find the year in numbers, a glossary and room for notes.",
                "Read it as a memory, use it as a guide for next year, or pass it on to whoever gardens here after you. A garden remembers a lot, but not everything: hence this book.",
            ]  # fmt: skip
        for text in paras:
            b.para(text)
        b.ornament()

    def _mmdd(self, value: str) -> str:
        try:
            month, day = (int(x) for x in value.split("-"))
            return self.day(date(2000, month, day))
        except (ValueError, AttributeError):
            return value

    def chapter(self, n: int, m: MonthData) -> None:
        b, w, lang = self.book, self.words, self.lang
        title = self.month_title(m)
        b.to_recto()
        s = b.page("opener", header=title)
        b.header = title
        self.toc.append((f"{n}. {title}", self.summary(m), b.number))
        photo_id = next((pid for e in m.journal for pid in e.photos if self.image(pid)), None)
        photo = self.image(photo_id) if photo_id else None
        self._opener_photo = photo_id
        y = b.top
        if photo:
            h = b.h * 0.34
            b.picture(s, photo, b.x0, y, b.width, h)
            y += h + 9 * b.k
        else:
            y += 18 * b.k
            s.circle(b.x0 + b.width - 14 * b.k, y + 2 * b.k, 13 * b.k, fill=b.c(_season_color(self.phase(m))))
            s.text(b.x0 + b.width - 14 * b.k, y + 6.5 * b.k, str(m.month), size=b.fs(22), font="serif-bold",
                   color="#FFFFFF", anchor="middle")  # fmt: skip
            y += 12 * b.k
        s.text(b.x0, y, w["chapter"].format(n=n).upper(), size=b.fs(7.5), font="sans-bold", color=b.c(SUN))
        y += 11 * b.k
        s.text(b.x0, y, title, size=b.fs(26), font="serif-bold", color=b.c(INK))
        s.text(b.x0 + b.width, y, str(m.year), size=b.fs(12), font="serif-italic", color=b.c(MUTED), anchor="end")
        y += 4 * b.k
        s.line(b.x0, y, b.x0 + 18 * b.k, y, stroke=b.c(SUN), width=0.8)
        b.y = y + 3 * b.k
        b.para(MONTH_INTRO[lang][self.phase(m)], font="serif-italic", size=9.6, color=MUTED)
        if m.empty:
            b.heading(w["quiet"])
            b.para(w["rest_month"])
            self.weather(m, heading=False)
            return
        self.story(m)
        self.sown_planted(m)
        self.work(m)
        self.diary(m)
        self.harvest(m)
        self.weather(m)

    def story(self, m: MonthData) -> None:
        b, w, lang = self.book, self.words, self.lang
        month = MONTHS[lang][m.month - 1]
        sown = [self.plant_name(p.plant_id) for _, p, how in m.sown if how != "planted"]
        planted = [self.plant_name(p.plant_id) for _, p, how in m.sown if how == "planted"]
        firsts = [(d, self.plant_name(p.plant_id)) for d, p, kind in m.events if kind == "first_harvest"]
        done = [self.plant_name(p.plant_id) for _, p, kind in m.events if kind == "failed"]
        crops = Counter()
        for h in m.harvests:
            crops[self.plant_name(h.plant_id)] += h.kg
        sentences = []
        if lang == "nl":
            if sown:
                sentences.append(f"In {month} werd er {len(sown)} keer gezaaid: {join_names(sown, lang)}.")
            if planted:
                sentences.append(
                    f"{join_names(planted, lang).capitalize()} {'ging' if len(set(planted)) == 1 else 'gingen'} naar {'zijn' if len(set(planted)) == 1 else 'hun'} vaste plek in de tuin."
                )
            if firsts:
                d, name = firsts[0]
                sentences.append(
                    f"Op {self.day(d)} was er een eerste oogst van {name}"
                    + (
                        f", later gevolgd door {join_names([x for _, x in firsts[1:]], lang)}."
                        if len(firsts) > 1
                        else "."
                    )
                )
            if crops:
                top = [name for name, _ in crops.most_common(3)]
                sentences.append(f"De manden vulden zich met {fmt_kg(m.kg, lang)}, vooral {join_names(top, lang)}.")
            if m.tasks:
                sentences.append(
                    f"{'Daarnaast werden' if sentences else 'Er werden'} {len(m.tasks)} klussen afgevinkt."
                )
            if m.journal:
                sentences.append(
                    f"Het dagboek kreeg {len(m.journal)} {'notitie' if len(m.journal) == 1 else 'notities'}"
                    + (f" en {m.photos} foto's." if m.photos else ".")
                )
            if done:
                sentences.append(
                    f"Niet alles lukte: {join_names(done, lang)} {'haalde' if len(done) == 1 else 'haalden'} het niet."
                )
            if m.liters:
                sentences.append(f"De bedden kregen {fmt_num(m.liters, lang, 0)} liter water.")
        elif lang == "fr":
            one = len(set(planted)) == 1
            if sown:
                sentences.append(f"En {month}, il y a eu {len(sown)} semis : {join_names(sown, lang)}.")
            if planted:
                names = join_names(planted, lang)
                sentences.append(
                    f"{names[:1].upper()}{names[1:]} {'a rejoint sa' if one else 'ont rejoint leur'} place définitive au jardin."
                )
            if firsts:
                d, name = firsts[0]
                sentences.append(
                    f"Le {self.day(d)}, première récolte de {name}"
                    + (
                        f", suivie plus tard de {join_names([x for _, x in firsts[1:]], lang)}."
                        if len(firsts) > 1
                        else "."
                    )
                )
            if crops:
                top = [name for name, _ in crops.most_common(3)]
                sentences.append(
                    f"Les paniers se sont remplis de {fmt_kg(m.kg, lang)}, surtout {join_names(top, lang)}."
                )
            if m.tasks:
                sentences.append(f"{'Par ailleurs, ' if sentences else ''}{len(m.tasks)} tâches ont été cochées.")
            if m.journal:
                sentences.append(
                    f"Le journal a reçu {len(m.journal)} {'note' if len(m.journal) == 1 else 'notes'}"
                    + (f" et {m.photos} photos." if m.photos else ".")
                )
            if done:
                sentences.append(
                    f"Tout n'a pas réussi : {join_names(done, lang)} {"n'a" if len(done) == 1 else "n'ont"} pas tenu."
                )
            if m.liters:
                sentences.append(f"Les planches ont reçu {fmt_num(m.liters, lang, 0)} litres d'eau.")
        else:
            if sown:
                sentences.append(f"In {month} there were {len(sown)} sowings: {join_names(sown, lang)}.")
            if planted:
                sentences.append(
                    f"{join_names(planted, lang)} moved to {'its' if len(set(planted)) == 1 else 'their'} place in the garden."
                )
            if firsts:
                d, name = firsts[0]
                sentences.append(
                    f"On {self.day(d)} the first {name} was harvested"
                    + (
                        f", followed later by {join_names([x for _, x in firsts[1:]], lang)}."
                        if len(firsts) > 1
                        else "."
                    )
                )
            if crops:
                top = [name for name, _ in crops.most_common(3)]
                sentences.append(f"The baskets filled with {fmt_kg(m.kg, lang)}, mostly {join_names(top, lang)}.")
            if m.tasks:
                sentences.append(f"{'Besides that, ' if sentences else ''}{len(m.tasks)} jobs were ticked off.")
            if m.journal:
                sentences.append(
                    f"The journal received {len(m.journal)} {'note' if len(m.journal) == 1 else 'notes'}"
                    + (f" and {m.photos} photos." if m.photos else ".")
                )
            if done:
                sentences.append(f"Not everything worked out: {join_names(done, lang)} did not make it.")
            if m.liters:
                sentences.append(f"The beds received {fmt_num(m.liters, lang, 0)} litres of water.")
        if sentences:
            b.heading(w["story"])
            b.para(" ".join(sentences))

    def sown_planted(self, m: MonthData) -> None:
        b, w = self.book, self.words
        events = sorted([*m.sown, *m.events], key=lambda x: x[0])
        if not events:
            return
        b.heading(w["sown_planted"])
        b.items((self.day(d), f"{self.crop(p)} – {w[how]}") for d, p, how in events)

    def work(self, m: MonthData) -> None:
        b, w = self.book, self.words
        if not m.tasks:
            return
        b.heading(w["work"])
        groups: dict[str, list[Task]] = defaultdict(list)
        for task in m.tasks:
            cat = "sow" if task.type in SOW_TYPES else "garden" if task.type in GARDEN_TYPES else "care"
            groups[cat].append(task)
        for cat in ("sow", "care", "garden"):
            if groups.get(cat):
                b.label(w[f"cat.{cat}"])
                b.items(
                    (self.day(task.completed_at.date()), self.task_title(task) + self._task_note(task))  # type: ignore[union-attr]
                    for task in groups[cat]
                )

    def _task_note(self, task: Task) -> str:
        notes = [safe(n.text) for n in task.notes if getattr(n, "text", "")]
        return f" – {notes[-1]}" if notes else ""

    def diary(self, m: MonthData) -> None:
        b, w = self.book, self.words
        if not m.journal:
            return
        b.heading(w["diary"])
        for e in m.journal:
            about = [x for x in (self.plant_name(e.plant_id) if e.plant_id else "", self.bed_name(e.bed_id)) if x]
            if e.planting_id and not about and (p := self.data.planting(e.planting_id)):
                about = [self.crop(p)]
            bits = [self.long_day(e.at.date()), w.get(f"kind.{e.kind}", "")]
            if about:
                bits.append(", ".join(about))
            if e.author:
                bits.append(w["by"].format(who=safe(e.author)))
            b.label(" · ".join(x for x in bits if x), keep=18)
            if e.text.strip():
                b.para(e.text, size=9.8, after=1.6)
            images = [img for pid in e.photos[:6] if pid != self._opener_photo and (img := self.image(pid))]
            if images:
                b.photos(images, w["photo_of"].format(what=", ".join(about)) if about else "")
            b.y += 1.5 * b.k

    def harvest(self, m: MonthData) -> None:
        b, w, lang = self.book, self.words, self.lang
        if not m.harvests:
            return
        b.heading(w["harvest"])
        per: dict[str, list[HarvestEntry]] = defaultdict(list)
        for h in m.harvests:
            per[h.plant_id].append(h)
        rows = []
        for pid, items in sorted(per.items(), key=lambda kv: -sum(h.kg for h in kv[1])):
            kg = sum(h.kg for h in items)
            count = sum(h.count or 0 for h in items)
            quality = [h.quality for h in items if h.quality]
            stars = "*" * round(sum(quality) / len(quality)) if quality else ""
            rows.append([
                self.plant_name(pid),
                fmt_num(kg, lang, 2) if kg else "–",
                str(count) if count else "–",
                str(len(items)),
                stars,
            ])  # fmt: skip
        head = [w["tbl_crop"], w["tbl_kg"], "#", w["tbl_times"], ""]
        b.table(head, rows, [44, 14, 10, 12, 12])
        total = sum(x.kg for mm in self.months if (mm.year, mm.month) <= (m.year, m.month) for x in mm.harvests)
        b.para(w["harvest_total"].format(kg=fmt_kg(m.kg, lang), total=fmt_kg(total, lang)), size=9.4)
        notes = [
            (self.day(h.day), f"{self.plant_name(h.plant_id)}: {safe(h.note)}") for h in m.harvests if h.note.strip()
        ]
        if notes:
            b.items(notes)

    def weather(self, m: MonthData, *, heading: bool = True) -> None:
        b, w, lang = self.book, self.words, self.lang
        lines = []
        if m.runs:
            lines.append(w["water_given"].format(liters=fmt_num(m.liters, lang, 0), runs=m.runs))
        if m.climate_days and m.tmax is not None and m.tmin is not None:
            frost = (
                w["frost_night"] if m.frost_nights == 1
                else w["frost_nights"].format(n=m.frost_nights) if m.frost_nights
                else ""
            )  # fmt: skip
            lines.append(
                w["weather"].format(
                    tmax=fmt_num(m.tmax, lang), tmin=fmt_num(m.tmin, lang), rain=fmt_num(m.rain, lang), frost=frost
                )
            )
        if not lines:
            return
        if heading:
            b.heading(w["water_weather"], keep=10)
        b.para(" ".join(lines), size=9.4)

    # -- back matter ----------------------------------------------------- #
    def numbers(self) -> None:
        from .planning import season_report

        b, w, lang = self.book, self.words, self.lang
        self.chapter_title(w["numbers"])
        self.toc.append((w["numbers"], "", b.number))
        f = self.figures()
        facts = [
            (f["crops"], w["fact_crops"]), (f["plantings"], w["fact_plantings"]), (f["sown"], w["fact_sown"]),
            (f["kg"], w["fact_kg"]), (f["tasks"], w["fact_tasks"]), (f["notes"], w["fact_notes"]),
            (f["photos"], w["fact_photos"]), (f["liters"], w["fact_water"]),
        ]  # fmt: skip
        self._fact_grid(facts)
        b.heading(w["num_harvest"])
        per: dict[str, list[HarvestEntry]] = defaultdict(list)
        for m in self.months:
            for h in m.harvests:
                per[h.plant_id].append(h)
        if per:
            rows = []
            for pid, items in sorted(per.items(), key=lambda kv: -sum(h.kg for h in kv[1])):
                by_month = Counter()
                for h in items:
                    by_month[h.day.month] += h.kg
                best = by_month.most_common(1)[0][0] if by_month else None
                rows.append([
                    self.plant_name(pid),
                    fmt_num(sum(h.kg for h in items), lang, 2),
                    str(len(items)),
                    self.short_day(min(h.day for h in items)),
                    self.short_day(max(h.day for h in items)),
                    MONTHS[lang][best - 1] if best else "",
                ])  # fmt: skip
            b.table(
                [w["tbl_crop"], w["tbl_kg"], w["tbl_times"], w["tbl_first"], w["tbl_last"], w["tbl_best"]],
                rows, [34, 12, 9, 15, 15, 17],
            )  # fmt: skip
        else:
            b.para(w["num_harvest_none"], font="serif-italic", color=MUTED)
        from .kitchen import economics

        eco = economics(self.data, self.db, self.season, lang)
        if eco["harvest_value"] > 0:

            def money(v: float) -> str:
                return f"{safe(eco['currency'])} {fmt_num(v, lang, 2)}"

            verdict = (w["worth_plus"] if eco["balance"] >= 0 else w["worth_minus"]).format(
                balance=money(abs(eco["balance"]))
            )
            b.heading(w["num_worth"])
            b.para(
                w["worth_text"].format(
                    value=money(eco["harvest_value"]), cost=money(eco["total_cost"]), verdict=verdict
                )
            )
        families: dict[str, set[str]] = defaultdict(set)
        for p in self.data.plantings:
            if p.season != self.season:
                continue
            plant = self.db.get(p.plant_id)
            if plant:
                families[plant.family].add(safe(plant.name(lang)))
        if families:
            b.heading(w["num_families"])
            rows = []
            for fam, names in sorted(families.items(), key=lambda kv: -len(kv[1])):
                label = FAMILIES.get(fam, {}).get(lang) or fam
                rows.append((safe(label), join_names(sorted(names), lang, limit=12)))
            for label, names in rows:
                b.label(label, keep=8)
                b.para(names, size=9.4, justify=False, after=1.2)
        report = season_report(self.data, self.db, self.season, today=self.ctx.today, lang=lang)
        names = {
            v: [self.plant_name(c["plant_id"]) for c in report["crops"] if c["verdict"] == v]
            for v in ("failed", "above", "below")
        }
        b.heading(w["num_lessons"])
        lines = [
            w[f"num_{v}"].format(what=join_names(names[v], lang, limit=8))
            for v in ("above", "below", "failed")
            if names[v]
        ]
        b.para(" ".join(lines) if lines else w["num_none"])
        problems = [e for m in self.months for e in m.journal if e.kind == "problem" and e.text.strip()]
        if problems:
            b.items((self.day(e.at.date()), safe(e.text).split("\n")[0]) for e in problems[:12])
        if report.get("weather"):  # the season's weather against last year (settings.season_summary)
            b.heading(w.get("num_weather") or TEXT["en"]["num_weather"])
            b.para(safe(" ".join(report["weather"])))

    def _fact_grid(self, facts: Sequence[tuple[float, str]]) -> None:
        b = self.book
        cols = 4
        gap = 2.5 * b.k
        cw = (b.width - gap * (cols - 1)) / cols
        ch = 17 * b.k
        rows = (len(facts) + cols - 1) // cols
        b.need(rows * (ch + gap) + 4 * b.k)
        for i, (value, label) in enumerate(facts):
            r, c = divmod(i, cols)
            x = b.x0 + c * (cw + gap)
            y = b.y + r * (ch + gap)
            b.s.rect(x, y, cw, ch, fill=b.c("#EEF3EF"), radius=1.5 * b.k)
            num = fmt_num(value, self.lang, 1 if 0 < value < 100 and value != int(value) else 0)
            b.s.text(
                x + cw / 2, y + 8.5 * b.k, num, size=b.fs(14), font="serif-bold", color=b.c(BRAND), anchor="middle"
            )
            b.s.text(x + cw / 2, y + 13.5 * b.k, safe(label), size=b.fs(6.4), font="sans", color=b.c(MUTED),
                     anchor="middle")  # fmt: skip
        b.y += rows * (ch + gap) + 2 * b.k

    def glossary(self) -> None:
        b, w = self.book, self.words
        self.chapter_title(w["glossary"])
        self.toc.append((w["glossary"], "", b.number))
        for term, text in GLOSSARY[self.lang]:
            size = b.fs(9.4)
            step = size * 1.4 * PT_TO_MM
            b.need(step * 2.4)
            b.y += step
            b.s.text(b.x0, b.y - step * 0.28, term, size=size, font="serif-bold", color=b.c(INK))
            b.para(text, size=9.2, after=1.8, indent=4 * b.k)

    def colophon(self) -> None:
        b, w = self.book, self.words
        b.page("plain", header="")
        self.toc.append((w["colophon"], "", b.number))
        region = self.data.settings.region
        people = sorted({safe(e.author) for m in self.months for e in m.journal if e.author})
        f = self.figures()
        from .printout import PAGE_SIZES

        pw, ph = PAGE_SIZES.get(self.page_name, (b.w, b.h))
        lines = [
            w["col_title"].format(season=self.season, garden=self.garden),
            w["col_made"].format(day=self.long_day(self.ctx.today) + f" {self.ctx.today.year}", version=_version()),
        ]
        if people:
            lines.append(w["col_people"].format(who=join_names(people, self.lang, limit=8)))
        if f["photos"]:
            lines.append(w["col_photos"].format(n=int(f["photos"])))
        lines.append(w["col_region"].format(last=self._mmdd(region.last_frost), first=self._mmdd(region.first_frost)))
        lines.append(
            w["col_type"].format(page=self.page_name.upper(), w=fmt_num(pw, self.lang), h=fmt_num(ph, self.lang))
        )
        lines.append(w["col_print"])
        lines.append(w["col_free"])
        b.y = b.h * 0.45
        s = b.s
        s.text(b.x0, b.y, w["colophon"].upper(), size=b.fs(7.5), font="sans-bold", color=b.c(MUTED))
        b.y += 3 * b.k
        for line in lines:
            b.para(line, font="serif", size=8, justify=False, color=MUTED, after=1.4)

    def back_cover(self) -> None:
        b, w = self.book, self.words
        s = b.page("back", header="")
        s.rect(0, 0, b.w, b.h, fill=b.c(BRAND))
        f = self.figures()
        b.y = b.h * 0.36
        x = 18 * b.k
        width = b.w - 36 * b.k
        size = b.fs(13)
        y = b.y
        quote = w["back_quote"]
        if getattr(self.data.settings, "slogans", True):  # a different saying for every book
            from .slogans import slogan

            quote = slogan(self.lang, day=self.ctx.today, topics=("garden", "harvest", "veg"), salt=f"book{self.season}",
                           season=False) or quote  # fmt: skip
        for line in wrap(f"“{safe(quote)}”", width, size, font="serif-italic"):
            y += size * 1.45 * PT_TO_MM
            s.text(x, y, line, size=size, font="serif-italic", color="#FFFFFF")
        y += 12 * b.k
        facts = w["back_facts"].format(
            crops=int(f["crops"]), kg=fmt_kg(f["kg"], self.lang), notes=int(f["notes"]), photos=int(f["photos"])
        )
        s.text(x, y, safe(facts), size=b.fs(8), font="sans", color=b.c("#DDE8E1"))
        self._leaf(s, b.w / 2 - 9 * b.k, b.h - 22 * b.k, 3.2 * b.k, "#FFFFFF")
        s.text(b.w / 2 - 4 * b.k, b.h - 20.8 * b.k, "Hortulus", size=b.fs(9), font="sans-bold", color="#FFFFFF")


def _season_color(phase: int) -> str:
    return [BRAND_DARK, BRAND_DARK, LEAF, LEAF, LEAF, SUN, SUN, SUN, "#C8742F", "#C8742F", MUTED, BRAND_DARK][phase]


def _version() -> str:
    import json
    from pathlib import Path

    try:
        return json.loads((Path(__file__).parent.parent / "manifest.json").read_text())["version"]
    except (OSError, ValueError, KeyError):
        return ""


def render_book(ctx, opts) -> bytes:
    """The season book as PDF bytes."""
    lang = normalize_lang(opts.lang)
    season = opts.season or season_for_date(ctx.data.settings.region, ctx.today)
    doc = PdfDocument(
        title=opts.title or TEXT[lang]["book"].format(season=season), author=ctx.garden_name or "Hortulus"
    )
    doc.outline = SeasonBook(ctx, opts, doc.add_page).render()
    return doc.to_bytes()


def render_book_svg(ctx, opts, limit: int = 16) -> list[str]:
    """The first pages of the season book as SVG (the on-screen preview).

    The whole book is still laid out, so the contents page shows the real page
    numbers, but photos past the preview are only measured, never decoded.
    """
    pages: list[SvgPage] = []

    def factory(w: float, h: float) -> Surface:
        page = SvgPage(w, h)
        if len(pages) >= limit:
            page.image = lambda *_a, **_k: None  # type: ignore[method-assign]  # not shown: skip the photo
        pages.append(page)
        return page

    SeasonBook(ctx, opts, factory, preview_pages=limit).render()
    return [p.to_svg(f"b{i}") for i, p in enumerate(pages[:limit])]


TEXT["en"]["num_weather"] = "The weather this season"
TEXT["nl"]["num_weather"] = "Het weer dit seizoen"
TEXT["fr"]["num_weather"] = "La météo de la saison"
