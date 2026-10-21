"""Assist (voice) support: intents answered from the live garden analysis.

The sentences ship in ``data/sentences/<lang>/hortulus.yaml``.  Home Assistant
loads custom sentences only from ``<config>/custom_sentences``, so the service
``garden_manager.install_voice_sentences`` copies them there (once; existing
files you edited are kept unless ``overwrite`` is set).
"""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import intent

from .const import DOMAIN
from .engine.i18n import normalize_lang, t
from .engine.models import RiskLevel
from .engine.tasks import overdue_report, tasks_due

if TYPE_CHECKING:
    from . import GardenRuntime

SENTENCES = Path(__file__).parent / "data" / "sentences"
INTENTS = (
    "HortulusTasksToday",
    "HortulusHarvest",
    "HortulusGreenhouse",
    "HortulusWater",
    "HortulusFrost",
    "HortulusOverdue",
)
_REGISTERED = f"{DOMAIN}_intents"


def _runtime(hass: HomeAssistant) -> GardenRuntime | None:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    return entries[0].runtime_data if entries else None


def _join(items: list[str], lang: str) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + {"nl": " en ", "fr": " et "}.get(lang, " and ") + items[-1]


def answer(runtime: GardenRuntime, intent_type: str, lang: str) -> str:
    """Spoken answer for one of the Hortulus intents (pure, for tests)."""
    data = runtime.repo.data
    analysis = runtime.coordinator.data
    if analysis is None:
        return t("voice.not_ready", lang)
    today = analysis.today
    if intent_type == "HortulusTasksToday":
        due = tasks_due(data.tasks, today)
        if not due:
            return t("voice.no_tasks", lang)
        minutes = sum(task.estimated_minutes for task in due)
        return t(
            "voice.tasks", lang, count=len(due), minutes=minutes, tasks=_join([task.title for task in due[:4]], lang)
        )
    if intent_type == "HortulusOverdue":
        items = overdue_report(data.tasks, today, 1)
        if not items:
            return t("voice.no_overdue", lang)
        return t("voice.overdue", lang, count=len(items), tasks=_join([i.task.title for i in items[:4]], lang))
    if intent_type == "HortulusHarvest":
        names = sorted(
            {
                runtime.repo.db.get(p.plant_id).name(lang)  # type: ignore[union-attr]
                for p in data.plantings
                if (tl := analysis.timelines.get(p.id)) is not None
                and runtime.repo.db.get(p.plant_id) is not None
                and runtime.repo.db.get(p.plant_id).harvestable  # type: ignore[union-attr]
                and tl.bearing
                and tl.harvest_start <= today <= tl.harvest_end
            }
        )
        return t("voice.harvest", lang, plants=_join(names[:6], lang)) if names else t("voice.no_harvest", lang)
    if intent_type == "HortulusGreenhouse":
        parts = []
        for zone in data.zones:
            za = analysis.zones.get(zone.id)
            if not zone.is_enclosed or za is None:
                continue
            temp = za.air_temperature
            text = (
                t("voice.gh_temp", lang, zone=zone.name, temp=round(temp, 1))
                if temp is not None
                else t("voice.gh_no_sensor", lang, zone=zone.name)
            )
            if za.greenhouse and za.greenhouse.action.value != "none":
                text += " " + t(f"voice.gh_action.{za.greenhouse.action.value}", lang)
            parts.append(text)
        return " ".join(parts) or t("voice.no_greenhouse", lang)
    if intent_type == "HortulusWater":
        dry = [
            data.bed(bid).name
            for bid, b in analysis.beds.items()
            if b.irrigation.action.value == "water" and data.bed(bid)
        ]  # type: ignore[union-attr]
        return t("voice.water", lang, beds=_join(dry, lang)) if dry else t("voice.no_water", lang)
    if intent_type == "HortulusFrost":
        f = analysis.frost
        if f.level in (RiskLevel.MODERATE, RiskLevel.HIGH) and f.min_temp_c is not None:
            return t("voice.frost", lang, temp=round(f.min_temp_c, 1))
        return t("voice.no_frost", lang)
    return t("voice.not_ready", lang)


class HortulusIntent(intent.IntentHandler):
    def __init__(self, intent_type: str) -> None:
        self.intent_type = intent_type

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        hass = intent_obj.hass
        lang = normalize_lang(intent_obj.language or hass.config.language)
        runtime = _runtime(hass)
        response = intent_obj.create_response()
        speech = answer(runtime, self.intent_type, lang) if runtime else t("voice.not_ready", lang)
        response.async_set_speech(speech)
        return response


@callback
def async_setup_intents(hass: HomeAssistant) -> None:
    if hass.data.get(_REGISTERED):
        return
    for name in INTENTS:
        intent.async_register(hass, HortulusIntent(name))
    hass.data[_REGISTERED] = True


async def async_install_sentences(hass: HomeAssistant, *, overwrite: bool = False) -> dict[str, Any]:
    target = Path(hass.config.path("custom_sentences"))

    def _copy() -> list[str]:
        written = []
        for src in sorted(SENTENCES.glob("*/hortulus.yaml")):
            dest = target / src.parent.name / "hortulus.yaml"
            if dest.exists() and not overwrite:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            written.append(str(dest))
        return written

    written = await hass.async_add_executor_job(_copy)
    if written and hass.services.has_service("conversation", "reload"):
        await hass.services.async_call("conversation", "reload", {}, blocking=True)
    return {"written": written}
