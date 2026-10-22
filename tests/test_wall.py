# ruff: noqa: F811  (the garden fixture is imported from test_phase2)
"""Wall screen: the layout the gardener arranges and the reading blocks (Dutch)."""

from __future__ import annotations

from datetime import date

from homeassistant.core import HomeAssistant
import pytest

from custom_components.garden_manager.engine import wall

from .test_init import _result
from .test_phase2 import garden  # noqa: F401


def test_a_layout_from_the_panel_is_made_safe() -> None:
    assert wall.clean_layout(None) is None
    raw = [
        {"id": "tasks", "w": 9},
        {"id": "tasks", "w": 1},
        {"id": "bogus"},
        {"id": "radar"},
        "x",
        {"id": "saying", "w": "?"},
    ]
    assert wall.clean_layout(raw) == [{"id": "tasks", "w": 4}, {"id": "radar", "w": 1}, {"id": "saying", "w": 1}]
    assert len(wall.clean_layout([{"id": b} for b in wall.BLOCKS] * 3)) == len(wall.BLOCKS)
    with pytest.raises(ValueError):
        wall.clean_layout("tasks")
    # odd payloads from a client: an id that is not text, a width of infinity
    assert wall.clean_layout([{"id": ["x"]}, {"id": "radar", "w": float("inf")}]) == [{"id": "radar", "w": 1}]
    assert wall.clean_layout([]) == []
    assert {b["id"] for b in wall.default_layout()} <= set(wall.BLOCKS)


def test_every_month_has_sayings_and_the_texts_change_daily() -> None:
    assert sorted(wall.SAYINGS) == list(range(1, 13)) and all(len(v) >= 3 for v in wall.SAYINGS.values())
    may = {wall.saying(date(2026, 5, d)) for d in range(1, 8)}
    assert may <= set(wall.SAYINGS[5]) and len(may) > 1
    assert wall.saying(date(2026, 11, 1), south=True) in wall.SAYINGS[5]  # spring in the south
    assert wall.fact(date(2026, 5, 1)) != wall.fact(date(2026, 5, 2))
    recipe = {"title": "Soep", "minutes": 30, "course_name": "Soepen",
              "ingredients": [{"name": "Prei", "group": "garden"}, {"name": "ui", "group": "pantry"}]}  # fmt: skip
    assert wall.recipe_tip([recipe], date(2026, 5, 1)) == {
        "title": "Soep",
        "minutes": 30,
        "produce": ["Prei"],
        "course": "Soepen",
    }
    assert wall.recipe_tip([], date(2026, 5, 1)) is None


async def test_the_wall_is_arranged_and_kept_in_the_settings(hass: HomeAssistant, garden, hass_ws_client) -> None:
    entry, _ = garden
    data = entry.runtime_data.repo.data
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "garden_manager/wall/data"})
    msg = await _result(client)
    assert msg["success"], msg
    res = msg["result"]
    assert res["custom"] is False and res["layout"] == wall.default_layout()
    assert res["saying"] and res["fact"] and res["eco_month"]["text"]
    assert set(res["blocks"]) == set(wall.BLOCKS)

    layout = [{"id": "saying", "w": 1}, {"id": "radar", "w": 2}, {"id": "nope", "w": 1}]
    await client.send_json({"id": 2, "type": "garden_manager/wall/layout", "layout": layout})
    msg = await _result(client)
    assert msg["success"], msg
    assert msg["result"]["layout"] == [{"id": "saying", "w": 1}, {"id": "radar", "w": 2}]
    assert data.settings.wall_layout == msg["result"]["layout"]

    # a settings save from the panel leaves the wall alone
    await client.send_json(
        {"id": 3, "type": "garden_manager/settings/save", "settings": {"wall_layout": None, "mirror_days": 5}}
    )
    assert (await _result(client))["success"]
    assert data.settings.wall_layout == [{"id": "saying", "w": 1}, {"id": "radar", "w": 2}]

    await client.send_json({"id": 4, "type": "garden_manager/wall/data"})
    assert (await _result(client))["result"]["custom"] is True
    # every block removed: an empty wall stays empty
    await client.send_json({"id": 5, "type": "garden_manager/wall/layout", "layout": []})
    assert (await _result(client))["result"]["layout"] == []
    await client.send_json({"id": 6, "type": "garden_manager/wall/data"})
    res = (await _result(client))["result"]
    assert res["layout"] == [] and res["custom"] is True
    await client.send_json({"id": 7, "type": "garden_manager/wall/layout", "layout": None})
    assert (await _result(client))["result"]["layout"] is None
    assert data.settings.wall_layout is None


async def test_only_an_administrator_arranges_the_wall(
    hass: HomeAssistant, garden, hass_ws_client, hass_read_only_access_token
) -> None:
    client = await hass_ws_client(hass, hass_read_only_access_token)
    await client.send_json({"id": 1, "type": "garden_manager/wall/layout", "layout": [{"id": "clock", "w": 2}]})
    msg = await _result(client)
    assert not msg["success"] and msg["error"]["code"] == "unauthorized"
    await client.send_json({"id": 2, "type": "garden_manager/wall/data"})
    assert (await _result(client))["success"]  # reading the wall is for everyone
