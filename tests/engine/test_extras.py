"""The optional extras of 1.9 (all on by default): slogans, soil estimate, weather summaries,
measured frost dates, water forecast, silent sensors and weather-station CSV import."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.garden_manager.engine import climate, slogans
from custom_components.garden_manager.engine.analysis import analyze
from custom_components.garden_manager.engine.models import (
    ClimateDay,
    FrostYear,
    GardenSettings,
    SensorReading,
    WeatherSnapshot,
)
from custom_components.garden_manager.engine.waterbalance import days_until_dry
from custom_components.garden_manager.engine.weather import DailyOutlook

TZ = ZoneInfo("Europe/Amsterdam")


# --------------------------------------------------------------------------- #
# Slogans
# --------------------------------------------------------------------------- #
def test_every_theme_speaks_every_language():
    for theme, langs in slogans.SLOGANS.items():
        assert set(langs) == {"nl", "en", "fr"}, theme
        assert len(langs["nl"]) == len(langs["en"]) == len(langs["fr"]), theme


def test_a_slogan_is_stable_for_a_day_and_changes_the_next():
    day = date(2026, 5, 4)
    first = slogans.slogan("nl", day=day, salt="digest")
    assert first == slogans.slogan("nl", day=day, salt="digest")
    week = [slogans.slogan("nl", day=day + timedelta(days=i), salt="digest") for i in range(7)]
    assert len(set(week)) == len(week)  # no line twice in a week, so never twice running
    assert len(set(week)) == 7


def test_two_places_on_one_day_differ_and_the_season_joins_in():
    day = date(2026, 1, 10)
    lines = {slogans.slogan("en", day=day, salt=s) for s in ("digest", "weekly", "report", "panel")}
    assert len(lines) >= 3
    winter = set(slogans.SLOGANS["winter"]["en"])
    assert any(
        slogans.slogan("en", day=day + timedelta(days=i), topics=()) in winter for i in range(3)
    )  # with no other topic, only the season speaks
    assert slogans.season_theme(date(2026, 1, 10), south=True) == "summer"


def test_slogans_follow_the_setting_and_unknown_languages_fall_back():
    assert slogans.enabled(GardenSettings())
    assert not slogans.enabled(GardenSettings(slogans=False))
    assert slogans.slogan("de", day=date(2026, 6, 1)) in slogans.pool("en", ("garden", "veg", "outdoors", "summer"))


# --------------------------------------------------------------------------- #
# Soil temperature without a sensor
# --------------------------------------------------------------------------- #
def test_soil_estimate_follows_the_air_with_a_lag():
    today = date(2026, 4, 20)
    log = [ClimateDay(today - timedelta(days=i), 2.0, 10.0) for i in range(10, 3, -1)]  # a cold week (mean 6)
    log += [ClimateDay(today - timedelta(days=i), 12.0, 22.0) for i in range(3, 0, -1)]  # then warm (mean 17)
    est, n = climate.estimate_soil_temp(log, today)
    assert n == 10
    assert 6.0 < est < 17.0  # behind the warm air, ahead of the cold
    assert climate.estimate_soil_temp(log[:2], today) is None


def test_analysis_uses_the_estimate_only_without_a_soil_sensor(db, garden):
    now = datetime(2026, 5, 12, 8, tzinfo=TZ)
    garden.climate_log = [ClimateDay(now.date() - timedelta(days=i), 8.0, 16.0) for i in range(10, 0, -1)]
    analysis = analyze(garden, db, WeatherSnapshot(), {}, now=now, tz=TZ)
    estimates = {b: a.soil_temp_estimate for b, a in analysis.beds.items()}
    assert any(v is not None and v == pytest.approx(12.0, abs=0.5) for v in estimates.values()), estimates
    garden.settings.soil_estimate = False
    analysis = analyze(garden, db, WeatherSnapshot(), {}, now=now, tz=TZ)
    assert all(a.soil_temp_estimate is None for a in analysis.beds.values())


# --------------------------------------------------------------------------- #
# Season / month summary
# --------------------------------------------------------------------------- #
def test_month_compared_with_last_year_in_words(garden):
    start, end = climate.last_month(date(2026, 7, 3))
    assert (start, end) == (date(2026, 6, 1), date(2026, 6, 30))
    for i in range(30):
        garden.climate_log.append(ClimateDay(start + timedelta(days=i), 12.0, 24.0, rain_mm=1.0, sun_h=8.0))
        garden.climate_log.append(
            ClimateDay(start - timedelta(days=365) + timedelta(days=i), 10.0, 20.0, rain_mm=2.0, sun_h=5.0)
        )
    cmp = climate.compare_with_last_year(garden, start, end, latitude=52.0)
    assert cmp is not None
    assert cmp["tmean_diff"] == pytest.approx(3.0, abs=0.1)
    assert cmp["rain_pct"] == -50
    lines = climate.summary_lines(cmp, "nl")
    assert len(lines) >= 3 and "3.0" in lines[0]
    assert climate.compare_with_last_year(garden, date(2020, 1, 1), date(2020, 1, 31), latitude=52.0) is None
    assert climate.summary_lines(None, "en") == []


# --------------------------------------------------------------------------- #
# Own frost dates
# --------------------------------------------------------------------------- #
def test_measured_frost_dates_are_suggested_after_two_full_years(garden):
    today = date(2026, 12, 1)
    preset_last, preset_first = date(2026, 4, 15), date(2026, 10, 25)
    for year, last, first in ((2024, (5, 2), (10, 5)), (2025, (5, 6), (10, 9))):
        garden.frost_years[str(year)] = FrostYear(
            last_spring=date(year, *last), first_autumn=date(year, *first), spring_complete=True, autumn_complete=True
        )
    s = climate.local_frost_suggestion(garden, today, preset_last, preset_first)
    assert s is not None and s["years"] == 2
    assert s["last_frost"].startswith("05-") and s["first_frost"].startswith("10-0")
    garden.frost_years.pop("2025")
    assert climate.local_frost_suggestion(garden, today, preset_last, preset_first) is None


# --------------------------------------------------------------------------- #
# Water forecast
# --------------------------------------------------------------------------- #
def _outlook(start: date, n: int, *, rain: float = 0.0, et0: float = 4.0) -> list[DailyOutlook]:
    return [DailyOutlook(start + timedelta(days=i), 12.0, 24.0, rain, et0) for i in range(n)]


def test_days_until_dry():
    today = date(2026, 7, 1)
    days, on = days_until_dry(10.0, 60.0, kc=1.0, outlook=_outlook(today, 7), latitude=52.0)
    # p x TAW = 30 mm; 10 + 4/day passes 30 on the 5th forecast day (index 4)
    assert (days, on) == (4, today + timedelta(days=4))
    assert days_until_dry(40.0, 60.0, kc=1.0, outlook=_outlook(today, 7), latitude=52.0) == (0, today)
    assert days_until_dry(10.0, 60.0, kc=1.0, outlook=_outlook(today, 7, rain=6.0), latitude=52.0) is None
    assert days_until_dry(10.0, 60.0, kc=1.0, outlook=[], latitude=52.0) is None


# --------------------------------------------------------------------------- #
# Silent sensors
# --------------------------------------------------------------------------- #
def test_a_sensor_silent_for_days_gets_one_warning(db, garden):
    now = datetime(2026, 5, 12, 8, tzinfo=TZ)
    readings = {
        "sensor.greenhouse_temp": SensorReading("sensor.greenhouse_temp", None, now - timedelta(days=3), stale=True)
    }
    analysis = analyze(garden, db, WeatherSnapshot(), readings, now=now, tz=TZ)
    silent = [a for a in analysis.alerts if a.message_key == "alert.sensor_silent"]
    assert len(silent) == 1 and silent[0].params["days"] == 3
    assert not any(
        a.params.get("entity") == "sensor.greenhouse_temp" and a.kind != "sensor_silent" for a in analysis.alerts
    )
    garden.settings.sensor_health = False
    analysis = analyze(garden, db, WeatherSnapshot(), readings, now=now, tz=TZ)
    assert not any(a.message_key == "alert.sensor_silent" for a in analysis.alerts)


# --------------------------------------------------------------------------- #
# Weather station CSV
# --------------------------------------------------------------------------- #
NETATMO = """Name;Tuin
Timezone;Europe/Brussels
Timestamp;Timezone : Europe/Brussels;Temperature;Humidity
1717200000;2024/06/01 02:00:00;12,5;80
1717221600;2024/06/01 08:00:00;15,0;70
1717243200;2024/06/01 14:00:00;22,5;50
1717264800;2024/06/01 20:00:00;18,0;60
1717286400;2024/06/02 02:00:00;11,0;85
"""

ECOWITT = """Time,Outdoor Temperature(℉),Outdoor Humidity(%),Wind Speed(mph),Wind Gust(mph),Daily Rain(in)
2024-06-01 00:00,50.0,90,2.0,5.0,0.00
2024-06-01 12:00,77.0,50,10.0,20.0,0.10
2024-06-01 23:55,59.0,80,4.0,8.0,0.20
"""


def test_netatmo_export_with_semicolons_and_decimal_commas():
    parsed = climate.parse_station_csv(NETATMO, TZ)
    assert parsed["rows"] == 5
    day = next(r for r in parsed["records"] if r["day"] == "2024-06-01")
    assert day["tmin"] == 12.5 and day["tmax"] == 22.5
    assert day["rh_max"] == 80
    assert "temp" in parsed["columns"] and "rh" in parsed["columns"]


def test_ecowitt_export_in_fahrenheit_inches_and_mph():
    parsed = climate.parse_station_csv(ECOWITT, TZ)
    day = next(r for r in parsed["records"] if r["day"] == "2024-06-01")
    assert day["tmin"] == pytest.approx(10.0) and day["tmax"] == pytest.approx(25.0)
    assert day["rain_mm"] == pytest.approx(5.1, abs=0.1)  # the day's running total, 0.20 in
    assert day["gust_max"] == pytest.approx(32.2, abs=0.2)  # 20 mph


def test_a_file_without_a_time_column_is_refused():
    with pytest.raises(ValueError):
        climate.parse_station_csv("a,b\n1,2\n", TZ)


def test_imported_days_merge_and_fill_frost_years(garden):
    parsed = climate.parse_station_csv(ECOWITT, TZ)
    assert climate.merge_history(garden, parsed["records"], "history", date(2026, 6, 1))
    assert any(d.day == date(2024, 6, 1) and d.source == "history" for d in garden.climate_log)


def test_unix_seconds_and_milliseconds_both_read():
    text = "timestamp,temperature\n1717221600,15.0\n1717243200000,22.5\n99999999999999999999,40\n"
    parsed = climate.parse_station_csv(text, TZ)
    day = next(r for r in parsed["records"] if r["day"] == "2024-06-01")
    assert day["tmin"] == 15.0 and day["tmax"] == 22.5  # the absurd third row is skipped, not fatal
    assert parsed["rows"] == 2
