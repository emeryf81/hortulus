"""Copy the coming garden tasks into another calendar (2.1, ``settings.calendar_mirror``).

Home Assistant can add events to another calendar (``calendar.create_event``) but not change or
remove them there, so every task goes over once per due date: the key in ``GardenData.notified``
remembers it.  A task that moves to another day is added again on its new day.
"""

from __future__ import annotations

from datetime import date, timedelta
import logging
from typing import TYPE_CHECKING

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from . import GardenRuntime

_LOGGER = logging.getLogger(__name__)
MAX_PER_RUN = 50  # a first run on a full garden does not flood the other calendar


def mirror_key(entity_id: str, task_id: str, due: date) -> str:
    return f"mirror:{entity_id}:{task_id}:{due.isoformat()}"


async def async_mirror_tasks(hass: HomeAssistant, runtime: GardenRuntime, today: date | None = None) -> int:
    """Add the open tasks of the coming days to the mirror calendar; returns how many were added."""
    from .calendar import PRIORITY_MARK

    data = runtime.repo.data
    settings = data.settings
    target = settings.mirror_calendar
    if not settings.calendar_mirror or not target:
        return 0
    state = hass.states.get(target)
    if state is None or state.state == STATE_UNAVAILABLE:
        return 0  # Home Assistant skips an unavailable calendar without an error: try again tomorrow
    today = today or dt_util.now().date()
    until = today + timedelta(days=settings.mirror_days)
    due = sorted((t for t in data.tasks if t.is_open and today <= t.due < until), key=lambda t: (t.due, t.id))
    added = 0
    for task in due:
        key = mirror_key(target, task.id, task.due)
        if key in data.notified:
            continue
        if added >= MAX_PER_RUN:
            break
        try:
            await hass.services.async_call(
                "calendar",
                "create_event",
                {
                    "entity_id": target,
                    "summary": f"{PRIORITY_MARK[task.priority.value]}🌱 {task.title}",
                    "description": task.description or "Hortulus",
                    "start_date": task.due.isoformat(),
                    "end_date": (task.due + timedelta(days=1)).isoformat(),
                },
                blocking=True,
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Could not copy task %s to %s: %s", task.id, target, err)
            runtime.repo.record_error("calendar_mirror", "create_failed", str(err), {"entity_id": target})
            break  # the calendar is unreachable: try again on the next run
        data.notified[key] = task.due.isoformat()  # kept until two weeks after the due date
        added += 1
    if added:
        runtime.repo.async_schedule_save()
    return added
