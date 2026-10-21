"""Q&A assistant: "I have a question about [subject] [target]: [problem]".

The panel builds the question from three dropdowns; :func:`options` says
which subjects, targets and problems exist, :func:`answer` returns a
structured answer that combines

* the **live status** (plantings, stage, harvest window, soil moisture, the
  greenhouse climate, frost and disease risk, open tasks),
* plant-specific facts from the database (sowing windows, care rules,
  pests, neighbours, tips),
* the generic knowledge base (causes, what to do now, home remedies,
  prevention) and a handbook chapter to read on.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from .advisor import harvest_coverage
from .i18n import t
from .models import GardenData, Plant, Relation, TaskType, present_in
from .plantdb import PlantDatabase
from .qa_kb import DISEASES, PESTS, PROBLEMS
from .supplies import TASK_TOOLS, shopping_list, tool_name

if TYPE_CHECKING:
    from .analysis import GardenAnalysis

SUBJECTS: dict[str, tuple[str, ...]] = {
    "plant": ("status", "what_to_do", "when_sow", "when_harvest", "growth", "yellow_leaves", "wilting", "no_fruit",
              "bolting", "pests", "disease", "feeding", "watering", "pruning", "companions"),
    "greenhouse": ("status", "what_to_do", "too_hot", "too_cold", "pests", "disease", "watering", "winter_crops"),
    "garden": ("status", "what_to_do", "year_round", "soil", "slugs", "pests", "frost", "watering"),
    "bed": ("status", "what_to_do", "what_next", "watering", "feeding", "soil"),
    "tools": ("for_task", "shopping"),
}  # fmt: skip
HANDBOOK = {
    "growth": "soil", "yellow_leaves": "fertilizing", "wilting": "watering", "no_fruit": "companions", "bolting": "sowing",
    "pests": "pests", "disease": "diseases", "slugs": "home_remedies", "too_hot": "greenhouse", "too_cold": "greenhouse",
    "frost": "seasons", "soil": "soil", "feeding": "fertilizing", "watering": "watering", "pruning": "fruit",
    "companions": "companions", "when_sow": "sowing", "when_harvest": "harvest", "year_round": "year_round",
    "winter_crops": "year_round", "what_next": "rotation", "for_task": "tools", "shopping": "tools",
}  # fmt: skip

L: dict[str, dict[str, str]] = {
    "en": {
        "not_planted": "{plant} is not in your plan this season.",
        "planting": "{bed}: {status}, {stage}.",
        "harvest": "Harvest window: {start} - {end}.",
        "not_bearing": "Too young to bear fruit yet (from {season}).",
        "moisture": "Soil in {bed}: {state}{pct}.",
        "next_tasks": "Next: {tasks}.",
        "no_tasks": "No open tasks for it right now.",
        "sow_window": "{kind}: {start} - {end}.",
        "maturity": "Ready {min}-{max} days after {from_}.",
        "pests": "Watch for: {list}.",
        "friends": "Good neighbours: {list}.",
        "enemies": "Keep away from: {list}.",
        "water_need": "Water need: {level}; give 10-20 l/m² at once rather than daily sips.",
        "feed_need": "Nutrient need: {level}{interval}.",
        "feed_interval": ", feed about every {days} days",
        "gh_temp": "Now {temp} °C in {zone}.",
        "gh_action": "Advice: {action}.",
        "frost_risk": "Frost risk: {level}.",
        "disease_risk": "Fungal risk: {level}.",
        "open_tasks": "{n} open tasks today or overdue.",
        "gaps": "No harvest in: {months}.",
        "coverage_ok": "Something to harvest in every month - well done!",
        "what_next": "Next in rotation after {families}: legumes, then leaf crops, then roots (or green manure in between).",
        "tools_for": "For {task}: {tools}.",
        "shopping_item": "{name}: {qty} {unit} ({reason})",
        "status_label": {
            "planned": "planned",
            "sown_indoors": "sown indoors",
            "sown": "sown",
            "transplanted": "planted",
            "harvesting": "harvesting",
            "finished": "finished",
            "failed": "failed",
        },
    },
    "nl": {
        "not_planted": "{plant} staat dit seizoen niet in je plan.",
        "planting": "{bed}: {status}, {stage}.",
        "harvest": "Oogstperiode: {start} - {end}.",
        "not_bearing": "Nog te jong om vruchten te dragen (vanaf {season}).",
        "moisture": "Grond in {bed}: {state}{pct}.",
        "next_tasks": "Volgende: {tasks}.",
        "no_tasks": "Op dit moment geen open taken.",
        "sow_window": "{kind}: {start} - {end}.",
        "maturity": "Oogstklaar {min}-{max} dagen na {from_}.",
        "pests": "Let op: {list}.",
        "friends": "Goede buren: {list}.",
        "enemies": "Uit de buurt houden van: {list}.",
        "water_need": "Waterbehoefte: {level}; geef liever 10-20 l/m² in één keer dan dagelijks een beetje.",
        "feed_need": "Voedingsbehoefte: {level}{interval}.",
        "feed_interval": ", ongeveer om de {days} dagen bijvoeden",
        "gh_temp": "Nu {temp} °C in {zone}.",
        "gh_action": "Advies: {action}.",
        "frost_risk": "Vorstrisico: {level}.",
        "disease_risk": "Schimmelrisico: {level}.",
        "open_tasks": "{n} open taken vandaag of achterstallig.",
        "gaps": "Geen oogst in: {months}.",
        "coverage_ok": "Elke maand iets te oogsten - goed bezig!",
        "what_next": "Volgende in de wisselteelt na {families}: peulvruchten, dan bladgewassen, dan wortelgewassen (of groenbemester ertussen).",
        "tools_for": "Voor {task}: {tools}.",
        "shopping_item": "{name}: {qty} {unit} ({reason})",
        "status_label": {
            "planned": "gepland",
            "sown_indoors": "binnen gezaaid",
            "sown": "gezaaid",
            "transplanted": "geplant",
            "harvesting": "in oogst",
            "finished": "afgelopen",
            "failed": "mislukt",
        },
    },
    "fr": {
        "not_planted": "{plant} ne figure pas dans votre plan cette saison.",
        "planting": "{bed} : {status}, {stage}.",
        "harvest": "Période de récolte : {start} - {end}.",
        "not_bearing": "Encore trop jeune pour porter des fruits (à partir de {season}).",
        "moisture": "Sol de {bed} : {state}{pct}.",
        "next_tasks": "Prochaines tâches : {tasks}.",
        "no_tasks": "Aucune tâche en cours pour le moment.",
        "sow_window": "{kind} : {start} - {end}.",
        "maturity": "Prêt {min}-{max} jours après {from_}.",
        "pests": "Surveillez : {list}.",
        "friends": "Bons voisins : {list}.",
        "enemies": "À tenir à l'écart de : {list}.",
        "water_need": "Besoin en eau : {level} ; apportez plutôt 10-20 l/m² en une fois que quelques gouttes chaque jour.",
        "feed_need": "Besoin en nutriments : {level}{interval}.",
        "feed_interval": ", fertiliser environ tous les {days} jours",
        "gh_temp": "Actuellement {temp} °C dans {zone}.",
        "gh_action": "Conseil : {action}.",
        "frost_risk": "Risque de gel : {level}.",
        "disease_risk": "Risque de maladies cryptogamiques : {level}.",
        "open_tasks": "{n} tâches pour aujourd'hui ou en retard.",
        "gaps": "Pas de récolte en : {months}.",
        "coverage_ok": "Quelque chose à récolter chaque mois - bravo !",
        "what_next": "Ensuite dans la rotation après {families} : légumineuses, puis légumes-feuilles, puis légumes-racines (ou un engrais vert entre les deux).",
        "tools_for": "Pour {task} : {tools}.",
        "shopping_item": "{name} : {qty} {unit} ({reason})",
        "status_label": {
            "planned": "prévu",
            "sown_indoors": "semé à l'abri",
            "sown": "semé",
            "transplanted": "planté",
            "harvesting": "en récolte",
            "finished": "terminé",
            "failed": "raté",
        },
    },
}
LEVEL = {
    "en": {"low": "low", "medium": "medium", "high": "high"},
    "nl": {"low": "laag", "medium": "matig", "high": "hoog"},
    "fr": {"low": "faible", "medium": "moyen", "high": "élevé"},
}
STAGE = {
    "en": {"not_planted": "not started", "germination": "germinating", "seedling": "seedling", "vegetative": "growing",
           "flowering": "flowering", "fruiting": "fruiting", "harvest": "ready to harvest", "finished": "finished"},
    "nl": {"not_planted": "nog niet gestart", "germination": "kiemt", "seedling": "zaailing", "vegetative": "groeit",
           "flowering": "bloeit", "fruiting": "zet vruchten", "harvest": "oogstklaar", "finished": "afgelopen"},
    "fr": {"not_planted": "pas encore commencé", "germination": "en germination", "seedling": "plantule",
           "vegetative": "en croissance", "flowering": "en fleur", "fruiting": "en fructification",
           "harvest": "prêt à récolter", "finished": "terminé"},
}  # fmt: skip


@dataclass(slots=True)
class Answer:
    subject: str
    problem: str
    target: str | None
    title: str
    status: list[str] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)
    causes: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    remedies: list[str] = field(default_factory=list)
    prevention: list[str] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    plants: list[str] = field(default_factory=list)
    handbook: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _lk(lang: str) -> str:
    """Catalogue key for ``lang``: the languages written out here, else English."""
    return lang if lang in ("nl", "fr") else "en"


def _l(key: str, lang: str, **kw: Any) -> str:
    table = L[_lk(lang)]
    return str(table.get(key, L["en"][key])).format(**kw)


def options(data: GardenData, db: PlantDatabase, season: int, lang: str) -> dict[str, Any]:
    planted = {p.plant_id for p in data.plantings if (pl := db.get(p.plant_id)) and present_in(p, pl.perennial, season)}
    plants = sorted(db.all(), key=lambda p: (p.id not in planted, p.name(lang)))
    return {
        "subjects": {k: list(v) for k, v in SUBJECTS.items()},
        "targets": {
            "plant": [
                {"id": p.id, "name": p.name(lang), "planted": p.id in planted, "category": p.category.value}
                for p in plants
            ],
            "greenhouse": [{"id": z.id, "name": z.name} for z in data.zones if z.is_enclosed],
            "garden": [{"id": "", "name": "*"}]
            + [{"id": z.id, "name": z.name} for z in data.zones if not z.is_enclosed],
            "bed": [{"id": b.id, "name": b.name} for b in data.beds],
            "tools": [
                {"id": tt.value, "name": t(f"task.{tt.value}", lang, plant="…", bed="…", zone="…")} for tt in TASK_TOOLS
            ],
        },
    }


def _kb(answer: Answer, problem: str, lang: str) -> None:
    entry = PROBLEMS.get(problem)
    if not entry:
        return
    block = entry.get(_lk(lang)) or entry["en"]
    answer.causes += block["causes"]
    answer.actions += block["actions"]
    answer.remedies += block["remedies"]
    answer.prevention += block["prevention"]


def _open_tasks(data: GardenData, pred, limit: int = 4) -> list[dict[str, Any]]:
    tasks = sorted((t_ for t_ in data.tasks if t_.is_open and pred(t_)), key=lambda t_: t_.due)
    return [{"id": t_.id, "title": t_.title, "due": t_.due.isoformat()} for t_ in tasks[:limit]]


def _plant_status(answer: Answer, plant: Plant, data: GardenData, analysis: GardenAnalysis, lang: str) -> None:
    season = analysis.season
    mine = [p for p in data.plantings if p.plant_id == plant.id and present_in(p, plant.perennial, season)]
    if not mine:
        answer.status.append(_l("not_planted", lang, plant=plant.name(lang)))
        return
    for p in mine:
        bed = data.bed(p.bed_id)
        ph = analysis.phenology.get(p.id)
        stage = STAGE[_lk(lang)].get(ph.stage, ph.stage) if ph else "-"
        answer.status.append(_l("planting", lang, bed=bed.name if bed else "?",
                                status=L[_lk(lang)]["status_label"].get(p.status.value, p.status.value),  # type: ignore[union-attr]
                                stage=stage))  # fmt: skip
        tl = analysis.timelines.get(p.id)
        if tl and plant.harvestable:
            if tl.bearing:
                answer.status.append(
                    _l("harvest", lang, start=tl.harvest_start.strftime("%d/%m"), end=tl.harvest_end.strftime("%d/%m"))
                )
            else:
                answer.status.append(_l("not_bearing", lang, season=p.season + plant.years_to_bearing))
        adv = analysis.advice.get(p.id)
        if adv:
            answer.status += [t(k, lang, **params) for k, params in adv.reasons if k != "reason.window_open"][:2]
        ba = analysis.beds.get(p.bed_id)
        if ba and ba.irrigation.status.value != "unknown" and bed:
            pct = f" ({round(ba.irrigation.moisture)}%)" if ba.irrigation.moisture is not None else ""
            answer.status.append(
                _l("moisture", lang, bed=bed.name, state=t(f"moisture.{ba.irrigation.status.value}", lang), pct=pct)
            )
    ids = {p.id for p in mine}
    answer.tasks = _open_tasks(data, lambda t_: t_.planting_id in ids)
    answer.status.append(_l("next_tasks", lang, tasks="; ".join(f"{x['title']} ({x['due'][8:10]}/{x['due'][5:7]})" for x in answer.tasks))
                         if answer.tasks else _l("no_tasks", lang))  # fmt: skip


def _plant_facts(
    answer: Answer, plant: Plant, problem: str, db: PlantDatabase, analysis: GardenAnalysis, lang: str
) -> None:
    anchors = analysis.anchors
    lv = LEVEL[_lk(lang)]
    if problem in ("when_sow", "status", "what_to_do"):
        for kind, windows in (("indoor_sow", plant.sowing.indoor_sow), ("direct_sow", plant.sowing.direct_sow),
                              ("transplant", plant.sowing.transplant)):  # fmt: skip
            for w in windows:
                start, end = anchors.window_dates(w)
                answer.facts.append(
                    _l(
                        "sow_window",
                        lang,
                        kind=t(f"method.{kind}", lang),
                        start=start.strftime("%d/%m"),
                        end=end.strftime("%d/%m"),
                    )
                )
    if problem in ("when_harvest", "status"):
        if plant.harvest_windows:
            for w in plant.harvest_windows:
                start, end = anchors.window_dates(w)
                answer.facts.append(_l("harvest", lang, start=start.strftime("%d/%m"), end=end.strftime("%d/%m")))
        else:
            answer.facts.append(_l("maturity", lang, min=plant.days_to_maturity[0], max=plant.days_to_maturity[1],
                                   from_=t(f"method.{'transplant' if plant.maturity_from == 'transplant' else 'direct_sow'}", lang)))  # fmt: skip
    if problem in ("pests", "disease", "what_to_do", "status"):
        if plant.pests:
            answer.facts.append(
                _l(
                    "pests",
                    lang,
                    list=", ".join(
                        t(f"pest.{x}", lang) if t(f"pest.{x}", lang) != f"pest.{x}" else x.replace("_", " ")
                        for x in plant.pests
                    ),
                )
            )
        for pest in plant.pests if problem in ("pests", "what_to_do") else ():
            if pest in PESTS:
                answer.remedies.insert(0, PESTS[pest].get(_lk(lang)) or PESTS[pest]["en"])
        for dis in plant.diseases if problem in ("disease", "what_to_do") else ():
            if dis in DISEASES:
                answer.remedies.insert(0, DISEASES[dis].get(_lk(lang)) or DISEASES[dis]["en"])
    if problem in ("companions", "status"):
        friends, enemies = [], []
        for other in db.all():
            if other.id == plant.id:
                continue
            rel = db.relation(plant.id, other.id)
            if rel.relation is Relation.FRIEND and rel.strength >= 2:
                friends.append(other.name(lang))
            elif rel.relation is Relation.ENEMY and rel.strength >= 2:
                enemies.append(other.name(lang))
        if friends:
            answer.facts.append(_l("friends", lang, list=", ".join(sorted(friends)[:10])))
        if enemies:
            answer.facts.append(_l("enemies", lang, list=", ".join(sorted(enemies)[:10])))
    if problem in ("watering", "wilting"):
        answer.facts.append(_l("water_need", lang, level=lv[plant.water_needs.value]))
    if problem in ("feeding", "yellow_leaves", "growth", "no_fruit"):
        interval = _l("feed_interval", lang, days=plant.feeding_interval_days) if plant.feeding_interval_days else ""
        answer.facts.append(_l("feed_need", lang, level=lv[plant.nutrient_needs.value], interval=interval))
    if problem in ("pruning", "what_to_do", "status"):
        for rule in plant.care:
            if (
                rule.task in (TaskType.PRUNE, TaskType.PINCH, TaskType.CUT_BACK, TaskType.THIN_FRUIT, TaskType.TIE_IN)
                or problem != "pruning"
            ):
                note = rule.notes.get(lang) or rule.notes.get("en")
                if note and note not in answer.actions:
                    answer.actions.append(note)
    if problem == "no_fruit" and plant.pollination in ("insects", "partner", "wind"):
        answer.facts.insert(
            0,
            t(f"pollination.{plant.pollination}", lang)
            if t(f"pollination.{plant.pollination}", lang) != f"pollination.{plant.pollination}"
            else plant.pollination,
        )
    tips = plant.tips.get(_lk(lang)) or plant.tips.get("en") or []
    answer.remedies += [tip for tip in tips if tip not in answer.remedies]


def answer(subject: str, problem: str, target: str | None, data: GardenData, db: PlantDatabase,
           analysis: GardenAnalysis, lang: str = "en") -> Answer:  # fmt: skip
    if subject not in SUBJECTS or problem not in SUBJECTS[subject]:
        raise ValueError(f"unknown question {subject}/{problem}")
    ans = Answer(subject, problem, target, title="", handbook=HANDBOOK.get(problem))
    if subject == "plant":
        plant = db.get(target or "")
        if plant is None:
            raise ValueError("unknown plant")
        ans.title = plant.name(lang)
        ans.plants = [plant.id]
        _plant_status(ans, plant, data, analysis, lang)
        _plant_facts(ans, plant, problem, db, analysis, lang)
        if problem not in ("status", "what_to_do", "when_sow", "when_harvest", "companions"):
            _kb(ans, problem, lang)
        if plant.category.value == "fruit" and problem in ("pruning", "no_fruit"):
            ans.handbook = "fruit"
    elif subject == "greenhouse":
        zone = data.zone(target or "") or next((z for z in data.zones if z.is_enclosed), None)
        if zone is None:
            raise ValueError("no greenhouse")
        ans.title = zone.name
        za = analysis.zones.get(zone.id)
        if za:
            if za.air_temperature is not None:
                ans.status.append(_l("gh_temp", lang, temp=round(za.air_temperature, 1), zone=zone.name))
            if za.greenhouse and za.greenhouse.action.value != "none":
                ans.status.append(
                    _l(
                        "gh_action",
                        lang,
                        action=t(
                            f"task.{'close_up' if za.greenhouse.action.value in ('close_up', 'heat') else za.greenhouse.action.value}",
                            lang,
                            zone=zone.name,
                        ),
                    )
                )
            ans.status.append(_l("frost_risk", lang, level=t(f"risk.{za.frost.level.value}", lang)))
            ans.status.append(_l("disease_risk", lang, level=t(f"risk.{za.disease.level}", lang)))
        beds = {b.id for b in data.beds if b.zone_id == zone.id}
        ans.tasks = _open_tasks(data, lambda t_: t_.zone_id == zone.id or t_.bed_id in beds)
        if problem == "winter_crops":
            ans.plants = ["lambs_lettuce", "winter_purslane", "spinach", "pak_choi", "mizuna", "rocket"]
            ans.actions = [t("maint.gh_winter_crops.desc", lang)]
        elif problem in ("status", "what_to_do"):
            ans.status.append(_l("open_tasks", lang, n=len(ans.tasks)))
        else:
            _kb(ans, problem if problem in PROBLEMS else "pests", lang)
    elif subject in ("garden", "bed"):
        bed = data.bed(target or "") if subject == "bed" else None
        zone = data.zone(target or "") if subject == "garden" else None
        ans.title = bed.name if bed else zone.name if zone else t("advice.whole_garden", lang)
        ans.status.append(_l("frost_risk", lang, level=t(f"risk.{analysis.frost.level.value}", lang)))
        if bed:
            ba = analysis.beds.get(bed.id)
            if ba and ba.irrigation.status.value != "unknown":
                pct = f" ({round(ba.irrigation.moisture)}%)" if ba.irrigation.moisture is not None else ""
                ans.status.append(
                    _l("moisture", lang, bed=bed.name, state=t(f"moisture.{ba.irrigation.status.value}", lang), pct=pct)
                )
            ans.tasks = _open_tasks(data, lambda t_: t_.bed_id == bed.id)
            here = [db.get(p.plant_id) for p in data.plantings if p.bed_id == bed.id and p.season == analysis.season]
            ans.plants = sorted({p.id for p in here if p})
            if problem == "what_next":
                fams = sorted({p.family for p in here if p})
                ans.actions.append(_l("what_next", lang, families=", ".join(fams) or "-"))
        else:
            beds = {b.id for b in data.beds if zone is None or b.zone_id == zone.id}
            ans.tasks = _open_tasks(data, lambda t_: t_.bed_id in beds or t_.bed_id is None, limit=6)
        ans.status.append(_l("open_tasks", lang, n=len(ans.tasks)))
        if problem == "year_round":
            cov = harvest_coverage(data, db, analysis)
            ans.status.append(
                _l("gaps", lang, months=", ".join(t(f"month.{m}", lang) for m in cov.gaps))
                if cov.gaps
                else _l("coverage_ok", lang)
            )
            ans.plants = ["kale", "leek", "lambs_lettuce", "winter_purslane", "parsnip", "brussels_sprouts"]
        elif problem in PROBLEMS:
            _kb(ans, problem, lang)
        elif problem == "feeding":
            _kb(ans, "yellow_leaves", lang)
    elif subject == "tools":
        ans.title = t("advice.tools", lang)
        if problem == "for_task":
            try:
                ttype = TaskType(target or "custom")
            except ValueError:
                ttype = TaskType.CUSTOM
            tools = [tool_name(x, lang) for x in TASK_TOOLS.get(ttype, ())]
            ans.facts.append(_l("tools_for", lang, task=ttype.value.replace("_", " "), tools=", ".join(tools) or "-"))
        else:
            for item in shopping_list(data, db, analysis, lang):
                ans.facts.append(
                    _l("shopping_item", lang, name=item.name, qty=item.quantity, unit=item.unit, reason=item.reason)
                )
    return ans
