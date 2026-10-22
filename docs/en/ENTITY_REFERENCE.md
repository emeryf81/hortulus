# Entity, service & event reference

Entity ids below assume an **English** Home Assistant install and the example garden
(*Bed 1*, *Greenhouse Zone A*). Home Assistant derives entity ids from the translated
entity name and the device name at the moment an entity is first created, so on a Dutch
install `sensor.hortulus_frost_risk_next_48h` becomes
`sensor.hortulus_vorstrisico_komende_48_uur`. Unique ids never change; rename freely.
A second garden ([more than one garden](CONFIGURATION.md#9-more-than-one-garden)) gets its own
devices and entities; its entry is titled “Hortulus 2”, so its garden-wide entity ids start with `sensor.hortulus_2_`.

## Devices

| Device | Created for | Contains |
|---|---|---|
| **Hortulus** | the integration | garden‑wide sensors, calendar, to‑do list, buttons, irrigation controls |
| **<Bed name>** | every bed | moisture, irrigation, companion score, needs water, nutrient balance, water deficit |
| **<Zone name>** | every zone | disease risk, frost risk 48 h, degree days; greenhouses and cold frames also advice, heat stress, shading |

Beds and zones added in the planner get their devices immediately; deleting a bed or
zone removes its device and entities.

## Sensors

### `sensor.hortulus_frost_risk_next_48h`
Enum: `none` · `low` · `moderate` · `high` · `unknown`.
Classification of the **plant‑level** minimum (forecast 2 m temperature + radiative
adjustment on clear, calm nights): ≤ 0 °C *high*, ≤ 2 °C *moderate*, ≤ 4 °C *low*.

| Attribute | Example | Meaning |
|---|---|---|
| `min_temperature` | `-2.0` | lowest forecast air temperature (°C) |
| `plant_level_min_temperature` | `-4.0` | after ground‑frost adjustment |
| `min_at` | `2026-03-29T04:00:00+00:00` | when the minimum occurs |
| `first_below_zero_at` | … | first hour at/below 0 °C at plant level |
| `hours_below_zero` | `5.0` | duration (DST‑safe) |
| `source` | `hourly` | `hourly` → `daily` → `sensor` → `none` fallback chain |
| `zones` | `{"gh_a": "low"}` | per‑zone level (greenhouses are buffered) |

The state is `unknown` when there is neither a forecast nor an outdoor temperature.

### `sensor.hortulus_growing_degree_days`
Season total (°C·d, state class `total`) since 30 days before the last frost, base 10 °C,
modified average method capped at 30 °C. Attributes: `base_temperature`, `since`,
`days_counted`.

### `sensor.hortulus_tasks_due_today`
Count of open tasks due today or overdue (unit `tasks`). Attributes: `estimated_minutes`,
`overdue`, `tasks` (up to 25 × `{id, title, type, priority, due}` – handy in templates).

### `sensor.hortulus_next_task`
Title of the next open task (earliest due date, highest priority first; cut at 255
characters).

### `sensor.<bed>_moisture_status`  *(“garden.bed_moisture_status”)*
Enum: `dry` · `slightly_dry` · `optimal` · `wet` · `unknown`.

| Attribute | Meaning |
|---|---|
| `moisture` | current volumetric water content (%) |
| `target_low` / `target_high` | optimal band for the thirstiest active crop, shifted by soil type |
| `water_need` | `low` / `medium` / `high` |
| `soil_temperature` | °C, if mapped |
| `moisture_entity` | the source sensor |

Bands (loam; sandy −6, clay +6, silt +3, peat +8, chalk −2, potting mix +4):

| Water need | dry below | optimal | wet above |
|---|---|---|---|
| low | 18 % | 22–38 % | 55 % |
| medium | 25 % | 30–45 % | 60 % |
| high | 32 % | 38–55 % | 68 % |

### `sensor.<bed>_irrigation_recommendation`  *(“garden.irrigation_recommendation”)*
State: millimetres to apply now. Attributes: `bed_id`, `action` (`none`, `water`,
`skip_rain_expected`, `check_manually`), `amount_mm`, `liters`, `duration_min` (needs a
flow rate – entered or learned from the water meter), `status`, `moisture`,
`target_low` / `target_high`, `water_need`, `etc_24h_mm`, `rain_24h_mm`, `rain_48h_mm`,
`confidence` (`high` with a moisture sensor and a forecast; `medium` with a sensor but no
forecast, or when the bed's water balance decides; `low` with neither), `priority`,
`reasons`, `irrigation_entity`. Without a moisture sensor the water balance is used (water
once half of the plant‑available water is gone).

### `sensor.<bed>_companion_score` *(disabled by default)*
0–100 % (50 = neutral). Attributes: `conflicts`, `rotation_conflicts`.

### `sensor.<zone>_greenhouse_advice`
Enum: `none` · `ventilate` · `shade` · `close_up` · `heat`. Only for enclosed zones
(greenhouse, cold frame). Attributes: `action`, `inside_now_c`, `forecast_max_c`,
`forecast_min_c`, `limit_max_c`, `limit_min_c`, `limiting_plants`, `reasons`, `frost_risk`,
`air_temperature`, `temperature_unit`.

### `sensor.hortulus_reference_evapotranspiration_today`
ET₀ for today in mm (FAO‑56 Penman‑Monteith when humidity and wind are known,
Hargreaves‑Samani otherwise). Attributes: `method`, `tmin`, `tmax`, `rh_min`, `rh_max`,
`wind_kmh`, `cloud_fraction`, `rain_mm`, `forecast` (3 days: `{day, et0, rain}`).

### `sensor.hortulus_degree_days_today`
Degree days expected today (°C·d, same base as the season GDD sensor).

### `sensor.<bed>_nutrient_balance`
0–100: NPK (mg/kg) or EC (mS/cm) readings compared with the N‑P‑K demand of the active
crops (100 = everything in range). Attributes: `index`, `status` (`unknown`, `deficient`,
`balanced`, `excess`), `deficits` (`n`/`p`/`k`/`ec`), `excess`, `source`
(`npk`/`ec`/`none`).
Map the probes in Settings → Beds.

### `sensor.<bed>_soil_water_deficit` *(disabled by default)*
Root‑zone depletion below field capacity in mm from the daily water balance.
Attributes: `available_water_mm` (TAW for the soil and rooting depth), `crop_coefficient`
(Kc of the thirstiest active crop). Watering is advised once half of the TAW is used.

### `sensor.<zone>_disease_risk`
Enum `none` · `low` · `moderate` · `high` · `unknown`. Attributes: `wet_hours_48h`,
`hutton_period` (late‑blight weather), `humidity`, `leaf_wet`, `reasons`. Outdoor zones also
look back at the climate history: two humid, warm days that already happened (Hutton criteria
from the logged days: minimum ≥ 10 °C and mean humidity ≥ 90 %, two days in a row) set the
level to *high* (`reasons` contains `hutton_logged`); two or more wet days in the last three
(≥ 5 mm rain or mean humidity ≥ 90 %) raise it one step (`wet_days_logged`).

### `sensor.<zone>_degree_days_this_season` *(disabled by default)*
Season degree days for the zone. Greenhouses and cold frames count their own air
temperature sensor for the days it logged; other days (and enclosed zones without a sensor)
use the outdoor day with greenhouse buffering (+ 2 °C at night, + 4 °C by day).

### `sensor.hortulus_harvest_this_season`
kg harvested this season (from the harvest log; device class weight, state class `total`).
Attributes: `season`, `per_crop_kg` (largest first).

### `sensor.hortulus_garden_water_7_days`
Litres of mains water used in the garden during the last 7 days, from the water meter in
Settings → Water meter & rain butt (one reading per day is stored). Attributes: `season_l`,
`per_day`.

### `sensor.hortulus_rain_water_available`
Litres in the rain water butts now (butt level % × total capacity, both set in Settings →
Water meter & rain butt). Watering task descriptions say how much of it to use first.


### `sensor.hortulus_pump_energy_this_year` (2.1)
kWh the watering pumps used this calendar year (device class energy, `total_increasing`), from the pump power set
under *Irrigation hardware*. Attributes: `rain_water_liters`, `mains_water_liters` (watered this year by source).

### `sensor.hortulus_greenhouse_heating_this_week` (2.1)
kWh of the frost heaters this ISO week. Attributes per zone: `kwh`,
`budget_left_kwh`.
### Climate history

Four garden‑wide sensors summarise the climate history (outdoor days as logged by Hortulus
and filled from the recorder or Open‑Meteo, see
[Configuration → Climate history](CONFIGURATION.md#climate-history)). Each compares with the
same period a year earlier.

| Entity | Unit | Period | State |
|---|---|---|---|
| `sensor.hortulus_rain_7_days` | mm | last 7 days (today included) | rain total |
| `sensor.hortulus_mean_temperature_7_days` | °C (device class temperature) | last 7 days | mean of the daily means |
| `sensor.hortulus_sunshine_7_days` | h | last 7 days | sunshine hours (needs a radiation or light sensor, or Open‑Meteo) |
| `sensor.hortulus_frost_nights_this_season` | – (state class `total`) | season so far (from 1 January; 1 July on the southern hemisphere) | nights with a minimum below 0 °C |

The state is `unknown` when no day of the period is logged. Attributes (all for the same
period):

| Attribute | Meaning |
|---|---|
| `days_logged` | days of the period in the log |
| `last_year` | the same value for the same period a year ago |
| `lowest`, `highest` | lowest minimum and highest maximum (°C) |
| `rain_mm` | rain total |
| `sunshine_h` | sunshine hours |
| `gust_max_kmh` | strongest gust (or wind) |
| `et0_mm` | reference evaporation (Penman‑Monteith of the logged days, Hargreaves fallback) |
| `water_balance_mm` | rain − evaporation |

## Binary sensors

| Entity | Device class | On when |
|---|---|---|
| `binary_sensor.hortulus_frost_warning` | cold | frost risk *moderate* or *high* (unknown without forecast); attributes `level`, `min_temperature` (plant level), `plants_at_risk` |
| `binary_sensor.<zone>_frost_risk_48h` | cold | that zone's plant‑level frost risk is *moderate* or *high*; attributes `level`, `min_temperature`, `min_at` |
| `binary_sensor.<bed>_needs_water` | problem | irrigation action is `water` |
| `binary_sensor.<zone>_heat_stress` | heat | greenhouse / cold frame advice is `ventilate` or `shade` |
| `binary_sensor.hortulus_irrigation_frost_lockout` | safety | outdoor valves are locked (frost within 12 h or too cold now); attributes `temperature`, `limit` |
| `binary_sensor.hortulus_irrigation_running` | running | a watering run is in progress; attributes `bed_id`, `ends_at`, `last_error` |

## Irrigation & climate controls

| Entity | Notes |
|---|---|
| `switch.hortulus_automatic_irrigation` | on = mode `auto` (valves open at the start time), off = `advise` |
| `select.hortulus_irrigation_mode` | `off` · `advise` · `auto` |
| `number.hortulus_irrigation_max_runtime` | minutes per valve (1–180, step 1) |
| `number.hortulus_irrigation_frost_lockout_temperature` | °C (−5 to 10, step 0.5); outdoor valves stay shut at or below |
| `number.hortulus_skip_irrigation_above_rain` | mm forecast in the next 24 h (0–30, step 0.5) |
| `button.hortulus_water_now` / `button.hortulus_stop_watering` | water every bed that needs it now (safety rules apply) / stop and close everything |
| `select.<zone>_shading` | `auto` (follow the advice) · `on` · `off` for the zone's shade screen (greenhouses and cold frames) |

The mode select, the three numbers and the switch edit the same irrigation settings as the
panel. The switch has the attributes `start_time`, `pump` and `valves`; turning it off also
stops a run in progress. The numbers and the mode select are *configuration* entities.

**Safety rules** (also for manual runs): one valve at a time; pump only while a valve is
open (valve → 1 s → pump on … pump off → *lead* seconds → valve closed); max runtime (a
valve with its own timer gets openings that stay inside it); frost lockout for outdoor
valves, looking at the next 12 hours; rain skip; a valve that stays closed ends the run
without booking water; a valve that reports nothing for a minute while the pump runs ends
the run and stops the pump; every valve that was opened and the pump are switched off at the
end, after an error and on cancellation. Each run is logged (litres from the water meter when
there is one) and feeds the bed's water balance. After every run Hortulus checks that the
valve reports closed; a valve or pump open for more than max runtime + 10 minutes while no
run is active raises a dashboard banner, a notification and a system log entry (*Close
valve*). At least 5 L of water counted within 15 minutes while every valve is closed is reported as a leak
(can be switched off in Settings).

## Calendar, to‑do list, buttons

| Entity | Notes |
|---|---|
| `calendar.hortulus_garden_tasks` | All‑day events for every task except skipped ones (✓ = done, ‼/! = urgent/high). The entity shows the current or next open task; overdue work counts as happening today. Create, edit (moving the date postpones the task, dependants follow; summary and description change the task) and delete from the HA calendar. |
| `todo.hortulus_this_week` | Open tasks due within 7 days (+ overdue), plus tasks completed in the last 2 days. Ticking an item completes the task, un‑ticking reopens it; creating, renaming, changing the due date or description and deleting are supported. |
| `button.hortulus_generate_tasks` | Re‑generate tasks now (configuration entity). |
| `button.hortulus_refresh_forecast` | Fetch the forecast now (diagnostic entity). |

The calendar also contains the **seasonal garden work** (keys `m:…`): plan the season,
order seed, prepare the sowing station, turn compost, mulch, prepare each bed before
planting (with compost kg and fertiliser g), green manure or winter cover for empty beds,
drain hoses before frost, winter rest, soil test every third season, tool care, and per
greenhouse: spring clean, shading on/off, winter insulation and the autumn clean &
disinfection. Perennials get cut back, divided (every 3 years) and winter protection by
their tags. Switch it off in Settings → Resources.

---

## Services (actions)

All services live in the `garden_manager` domain and return data when called with
`response_variable` (except `delete_task`, `remove_planting`, `stop_irrigation` and
`assign_task`, which return nothing; `export_plan` returns data only).

Common to all services:

* **`garden`** (optional, text): the title or entry id of the garden to act on when you have
  [more than one](CONFIGURATION.md#9-more-than-one-garden). Without it the first garden is used.
* Services that change the plan, the plant data or the hardware – `import_plan`,
  `add_planting`, `update_planting`, `remove_planting`, `run_irrigation_plan`,
  `stop_irrigation`, `set_shading_mode`, `autofill_plan`, `export_pdf`, `generate_tasks`,
  `recalculate_plan`, `install_voice_sentences` – need an **administrator** when called by a
  user (like their websocket commands). Automations and scripts run without a user and are allowed.

| Group | Services |
|---|---|
| Tasks | `add_task`, `complete_task`, `postpone_task`, `delete_task`, `generate_tasks`, `recalculate_plan` |
| Plan | `export_plan`, `import_plan`, `add_planting`, `update_planting`, `remove_planting`, `autofill_plan`, `export_pdf` |
| Irrigation & climate | `run_irrigation_plan`, `stop_irrigation`, `set_shading_mode` |
| Records | `log_harvest`, `add_journal_entry`, `save_soil_test` |
| Household & voice | `assign_task`, `install_voice_sentences` |

### `garden_manager.add_task`
| Field | Type | Notes |
|---|---|---|
| `title` | string | required |
| `due_date` | date | default today |
| `type` | enum | default `custom`; see the list below |
| `description` | string | |
| `priority` | `low`/`normal`/`high`/`urgent` | default `normal` |
| `estimated_minutes` | int | 1–1440 |
| `bed` | string | bed **id or name** (case‑insensitive) |
| `planting_id` | string | |
| `recurrence_days` | int | 1–365; repeat N days after each completion |
| `until` | date | last date for the recurrence |

Task types: `custom`, `sow_indoor`, `sow_direct`, `harden_off`, `transplant`, `thin`, `stake`,
`prune`, `pinch`, `earth_up`, `feed`, `water`, `weed`, `pest_check`, `harvest`, `ventilate`,
`shade`, `frost_protect`, `soil_prep`, `compost`, `green_manure`, `mulch`, `clean_greenhouse`,
`winter_prep`, `plan_season`, `tool_care`, `soil_test`, `cut_back`, `divide`, `protect`, `clean`,
`tie_in`, `thin_fruit`, `pollinate`, `check`, `make_feed`.

Response: `{task_id}`.

```yaml
action: garden_manager.add_task
data:
  title: Check slug traps
  bed: Bed 1
  priority: high
  recurrence_days: 3
response_variable: created
```

### `garden_manager.complete_task`
Fields: `task_id`, `note`, `photos` (list of image ids/URLs), `skipped` (bool, default false).
Completing **sow**, **transplant** or the first **harvest** task updates the planting
(`sown_on`, `transplanted_on`, `harvest_started_on`, status), which re‑anchors all care
tasks to the real dates. Recurring tasks schedule their next occurrence
`interval` days after *completion*. A watering task completed twice books its water once.
Response: `{task_id, status, next_task_id, next_due}`.

### `garden_manager.postpone_task`
Fields: `task_id`, `days` (−365…365) **or** `to_date`, `reason`, `cascade` (default true).
Dependants of the same planting that you have not moved by hand shift by the same delta
(postponing *sow tomatoes* moves *harden off* and *plant out*).
Response: `{task_id, due, shifted: [ids], warnings: ["beyond_window", …]}`.

### `garden_manager.delete_task`
Deletes user tasks; generated tasks are marked *skipped* (otherwise they would be
re‑created).

### `garden_manager.assign_task`
Fields: `task_id`, `assignee` (`person.*` entity, empty to unassign). New tasks are
assigned automatically from Settings → Household (a default person and one per task type).

### `garden_manager.generate_tasks`
Idempotent regeneration from plan + database + sensors + forecast.
Response: `{created, updated, removed, open_tasks}`.

### `garden_manager.recalculate_plan`
Refetch the forecast and recompute everything. Response: `{frost_risk,
weather_available, alerts, season}`.

### `garden_manager.export_plan` *(response only)*
Fields: `include_tasks` (default false), `seasons` (list of years; limits plantings and the
plans set aside to those seasons). Returns the plan document (see
[configuration](CONFIGURATION.md#5-import--export-format)).

### `garden_manager.import_plan`
Fields: `plan` (object, required), `mode` (`merge` default | `replace`). A refused file changes
nothing. Response: counts per collection (`zones`, `beds`, `features`, `layouts`, `plantings`,
`custom_plants`, `rotation_history`, `tasks`, `archived_plans`).

### `garden_manager.add_planting` / `update_planting` / `remove_planting`
`add_planting`: `plant_id` and `bed` (id or name) are required; optional `season` (default the
current calendar year), `layout` (`single` / `row` / `block`, default `row`), `x_cm`, `y_cm`,
`width_cm` (default bed width), `length_cm` (default one row), `count`, `method`
(`indoor_sow` / `direct_sow` / `transplant`), `status` (`planned`, `sown_indoors`, `sown`,
`transplanted`, `harvesting`, `finished`, `failed`), planned dates `sow_date` /
`transplant_date`, actual dates `sown_on` / `transplanted_on`, `notes`. The planting must sit
on a bed of its own season's plan. Tasks follow automatically. `update_planting` takes
`planting_id` plus any of those fields (and `plant_id`, `bed`); `remove_planting` takes
`planting_id`. Responses: `{planting_id, planting}` / `{planting}` / none.

```yaml
action: garden_manager.add_planting
data: {plant_id: dill, bed: Bed 1, layout: row}
response_variable: added
```

### `garden_manager.autofill_plan`
Proposes a season plan. Fields: `season`, `beds` (default: all empty beds), `replace`,
`apply` (store it), and resources `household_size` (1–20), `hours_per_week` (0–80),
`water_liters_per_week`, `compost_kg`, `goals` (`fresh`, `storage`, `herbs`,
`pollinators`, `winter`, `perennials`, `easy`), `wanted`, `excluded`, `max_crops`
(1–60, default 16). Omitted resources come from Settings → Resources.
Response: `plantings`, `placements` (crop, bed, count, m², kg, min/week, L/week,
sowings), `skipped`, `warnings`, `summary`, and `applied: true` when stored.

### `garden_manager.run_irrigation_plan`
Fields: `dry_run`, `beds` (list of ids or names), `amount_mm` (0.5–50), `only_if_needed`
(default false). Returns the plan (`runs` with `bed_id, entity_id, minutes, mm, liters,
capped`; `skipped` and `skipped_reasons` per bed; `lockout`, `lockout_temp`,
`total_minutes`, `started`) and starts it unless `dry_run`. Ignores the irrigation mode,
never the safety rules. With `only_if_needed` an automation chooses the moment and
Hortulus still decides whether a bed needs water. Fails (unless `dry_run`) while a run is in progress.
`garden_manager.stop_irrigation` stops a run.

### `garden_manager.set_shading_mode`
Fields: `zone` (id or name of a greenhouse/cold frame), `mode` (`auto`/`on`/`off`).
Response: `{zone_id, mode}`.

### `garden_manager.export_pdf`
Writes a PDF to `/config/hortulus/exports/` (private; the response contains a signed download link valid for 7 days). Fields:
`document` (`garden`, `zone`, `beds`, `tasks`, `season`, `year`, `blank`, `plants`, `book`),
`page` (`a4`, `a3`, `a5`, `letter`, `remarkable`), `landscape`, `color_mode` (`color`, `eink`,
`grayscale`), `season`, `zone_id`, `bed_ids`, `days` (1–120, default 28, for `tasks`),
`notes` (dot grid, default true), `grid` (10 cm grid on bed sheets, default true), `title`.
`book` is the season book. Response: `{path, url, filename, bytes}`.

```yaml
# Every Monday morning: this week's checklist for the reMarkable
action: garden_manager.export_pdf
data: {document: tasks, page: remarkable, color_mode: eink, days: 7}
```

### `garden_manager.log_harvest`
Adds a harvest to the log. Fields: `planting_id` *or* `plant_id` *or* `plant` (an id **or a
name** such as `Tomaat`; handy for an NFC tag or a dashboard button), `bed` (to find the crop
in the garden), `kg` (0–500), `count` (at least one of `kg` and `count` is required),
`quality` (1–5), `day`, `note`. The first harvest of a planting sets it to *harvesting*.
Response: `{harvest}`. After a season with data, Hortulus uses **your own kg/m²** instead of
the database yield (Autofill, advice, shopping list).

### `garden_manager.add_journal_entry`
A diary note with optional photos. Fields: `text` (required), `kind` (`note` default,
`observation`, `problem`, `milestone`), `planting_id`, `bed` (id or name), `photos` (image
ids). The author is the calling user. Response: `{entry}`.

### `garden_manager.save_soil_test`
Stores a soil analysis for a bed (one per date; same date replaces). Fields: `bed`, `date`
(both required), `ph` (3–10), `organic_matter_pct`, `p_mg`, `k_mg` (mg per 100 g), `notes`. The
bed's fertiliser plan and lime advice follow the latest analysis. Response: `{soil_test}`.

### `garden_manager.install_voice_sentences`
Copies the Assist sentences (EN + NL + FR) to `/config/custom_sentences/<lang>/hortulus.yaml`
and reloads the conversation agent. Field: `overwrite` (default false: files you edited are
kept). Response: `{written: [paths]}`. See *Voice* below.

---

## Events

| Event | Fired when | Data |
|---|---|---|
| `garden_manager_task_due` | morning digest (every task due) and when a sensor/weather task appears during the day | `task_id, type, title, priority, due, bed_id, zone_id, planting_id` |
| `garden_manager_task_completed` | a task is completed/skipped | `task_id, type, title, skipped, planting_id, bed_id, next_task_id` |
| `garden_manager_frost_warning` | new frost alert (once per zone and night) | `key, severity, zone_id, level, temp, when, plants` |
| `garden_manager_heat_warning` | new greenhouse heat alert (once per zone and day) | `key, severity, zone_id, zone, temp, action` |
| `garden_manager_irrigation_recommended` | a bed needs water (once per bed and day) | `bed_id` + every attribute of the irrigation recommendation |
| `garden_manager_plan_updated` | plan, plants, settings or import changed | `reason` (`plan`, `plants`, `settings`, `import`), `revision` |
| `garden_manager_irrigation_run` | a valve finished (or was stopped) | `bed_id, bed, minutes, liters, mm, source` |

`severity` is `info`, `warning` or `critical`; `zone_id` is empty for the garden‑wide (outdoor)
frost alert. The *it froze* alert (`alert.frost_logged`, below) is a frost alert too: it fires
`garden_manager_frost_warning` with `key: froze:<date>`, `temp` and `plants`.

### Weather tasks and alerts

Weather tasks carry a key starting with `w:` (see the task engine); regeneration never makes
the same key twice. Besides the forecast tasks (`w:frost`, `w:heat`, `w:heat_gh`, `w:dry`,
`w:storm`, `w:rain`) Hortulus creates after‑care tasks for weather that already happened,
from the climate history (only while crops are in the ground):

| Key | Type | When |
|---|---|---|
| `w:after_storm:<day>` | `check` | yesterday's gusts reached 60 km/h (or the wind 45 km/h): check stakes, supports and covers |
| `w:rain:<day>` | `pest_check` | the slug patrol after a downpour: forecast ≥ 15 mm, **or** ≥ 15 mm logged yesterday by a gauge, the recorder or Open‑Meteo (not the forecast). Same key as the forecast task, so never twice |
| `w:dry_logged:<monday>` | `water` | deep watering after a dry week: ≥ 6 of the last 7 days with known rain, together < 3 mm, at least 4 days ≥ 20 °C; one per week, and not when the forecast already made a `w:dry` task |

| Alert key | Kind | When |
|---|---|---|
| `alert.frost_logged` | `frost` (warning) | last night (today's or yesterday's logged minimum) went below 0 °C and active crops outside a greenhouse cannot take that temperature; parameters `temp` and `plants`. The crops also appear in `plants_at_risk` of `binary_sensor.hortulus_frost_warning` |

**Notification buttons.** The digest, the reminders, “beds need water” and “valve left open”
notifications to phones with the companion app carry action buttons: *Done* (one task) and
*Tomorrow* on task lists, *Water now* when beds need water, *Close valve* on a valve left open.
Pressing one fires Home Assistant's `mobile_app_notification_action` event (action names start
with `HORTULUS_`), which Hortulus handles itself; you do not need an automation.

## Websocket API (used by the panel)

All commands are in the `garden_manager/` namespace and accept `garden_id` (the config entry id)
to pick a garden. Reads are open to every authenticated user; commands marked **admin** require
an administrator. Task actions, records (harvest, diary, seeds, expenses, soil tests) and the
cookbook are open to everyone.

| Group | Commands |
|---|---|
| Live data | `subscribe` (pushes a full snapshot now and after every update), `plants` (database + overrides), `advice`, `supplies` |
| Plants | `plants/save` **admin** (`mode`: `custom` or `override`), `plants/delete` **admin** (resets an override or deletes a custom plant), `plants/windows` (sowing windows for your frost dates) |
| Plan | `plan/save` **admin** (with `base_revision` and optional `season`), `plan/check` (draft compatibility), `plan/succession`, `plan/export`, `plan/import` **admin**, `plan/autofill`, `plan/autofill/apply` **admin**, `plan/compare`, `layout/delete` **admin** |
| Plans set aside | `plan/new` **admin** (`start`: `empty`, `zones`, `zones_beds`), `plan/activate` **admin**, `plan/delete` **admin** |
| Year‑end | `year/preview`, `year/apply` **admin** (`from_season`, `layout`: `copy`/`keep`, `zone_ids`, `feature_ids`, `planting_ids`, `activate`) |
| Crops | `plantings/season`, `planting/update` **admin**, `plantings/update_many` **admin**, `planning` (sowing plan, seeds, succession, harvest forecast) |
| Tasks | `tasks/add`, `tasks/action` (`complete`, `skip`, `postpone`, `update`, `delete`, `reopen`) |
| Settings | `settings/save` **admin** |
| Starter garden | `garden/starter` **admin** (`size`: `small`/`medium`/`large`, `greenhouse`) |
| Irrigation | `irrigation/plan`, `irrigation/run` **admin**, `irrigation/stop` **admin**, `irrigation/test` **admin** (open a valve for 5 s and check it reports open and closed), `irrigation/close` **admin** (close a valve left open) |
| Records | `records/overview` (harvest per crop and year, learned yields, seed box, water, year matrix, kitchen report, costs and expenses), `records/harvest/add`, `records/journal/save`, `records/seeds/save`, `records/expense/save`, `records/soil/save`, `records/soil/delete`, `records/delete` (`kind`: `harvest`, `journal`, `seed`, `expense`), `seeds/to_todo` (missing seed to a to‑do list), `report/season` |
| Advice & handbook | `qa/options`, `qa/ask`, `handbook/index`, `handbook/chapter`, `handbook/search` |
| Print | `print/render` (SVG preview pages) |
| Climate | `climate/stats` (climate history and statistics; optional `days` 7–800, default 400: how many days of the daily series to return), `climate/import_csv` **admin** (`text`: a weather station's CSV export, up to 20 MB; result `{days, first, last, rows, columns, changed}`; errors `invalid_csv`, `disabled`), `climate/apply_local_frost` **admin** (no arguments: switch the region to custom with the measured frost dates; result `{settings}`; error `no_suggestion`) |
| Analysis | `analysis` (garden check), `analysis/explain` (“why not here?”), `analysis/fix` **admin** (one‑click repair), `analysis/still_possible` (what can still go in this season) |
| System log | `syslog/list` (newest first, paged with `before`), `syslog/entry` **admin** (one entry with before/after per item), `syslog/undo` **admin** (`entry_id`, optional `force`) |
| Cooking | `cooking/suggest` (ready produce, dishes, menus, cookbook, choices), `cooking/render` (a recipe again after changing side, meat or servings), `cooking/prefs`, `cooking/book/save`, `cooking/book/update`, `cooking/book/delete`, `cooking/pdf` (`kind`: `recipe`, `book`, `shopping`), `cooking/send` (a recipe or the shopping list to a `notify.*` service), `cooking/to_todo` (shopping list to a to‑do list; your own permissions on that list apply) |

`seeds/to_todo` and `cooking/to_todo` check the calling user's own permissions on the target
to‑do list.

**Sensor mapping keys.** `settings/save` (`outdoor_sensors`) and `plan/save` (zone and bed
`sensors`) use the same keys: `soil_moisture`, `soil_temperature`, `air_temperature`,
`air_humidity`, `light`, `rain`, `par`, `ec`, `npk_n`, `npk_p`, `npk_k`, `leaf_wetness`, and
for the outdoor weather station `wind_speed`, `wind_gust` (km/h, m/s, mph or knots) and
`radiation` (W/m²).

**`climate/stats` result.** Temperatures in °C, rain and evaporation in mm, wind in km/h,
dates as ISO strings:

| Key | Content |
|---|---|
| `today`, `season_start` | today, and the start of the season (1 January / 1 July) |
| `periods` | `d7`, `d30`, `season`, `d365`, `d7_last_year`, `d30_last_year`, `season_last_year`; each `{days, days_with_temp, tmean, tmin, tmin_day, tmax, tmax_day, frost_nights, hot_days, very_hot_days, gdd, rain_mm, rain_days, wettest, wettest_day, sun_h, rs_mj, gust_max, gust_day, et0_mm, balance_mm, rh_mean}` (keys without data are missing or `null`) |
| `records` | `tmin`, `tmax`, `wettest`, `gust_max`, each `{value, when}` (`when` is a day, or a month for months kept for good) |
| `series` | one row per logged day of the last `days`: `{d, lo, hi, m, r, s, w, rh, et0, src}` (low, high, mean, rain, sunshine h, strongest wind, mean humidity, ET₀, source `sensor` / `history` / `model`, `+`‑joined when mixed) |
| `months` | newest first, up to 24: `{month, days, tmin, tmax, tmean, rain_mm, frost_days, hot_days, sun_h, wind_max}` |
| `frost` | `years` (per year `{last_spring, first_autumn, spring_complete, autumn_complete}`), `local` (average of the complete years: `last_spring`, `first_autumn` as `MM-DD`, `spring_diff_days`, `autumn_diff_days` against the preset, `years_spring`, `years_autumn`; `null` without a complete year), `preset_last`, `preset_first` |
| `sensors` | per mapped temperature sensor: `{entity_id, label, kind (outdoor / zone_air / bed_air / soil), now, days, first_day, today {tmin, tmax, tmean}, d7, d30, record_low {t, when}, record_high {t, when}, series [{d, lo, hi, m}] (last 120 days), months}` |
| `coverage` | `{days, first_day, sources {sensor, history, model: days}, months_kept}` |
| `summary` | *(extra `season_summary`)* `{season: [sentences], month: [sentences], month_start}` – the season and last month against the same dates last year |
| `local_frost_suggestion` | *(extra `local_frost_suggest`)* `{last_frost, first_frost (MM-DD), spring_diff_days, autumn_diff_days, years}`, or `null` while the measured dates stay within 7 days of the preset |
| `station_import` | `true` when the CSV import (extra `station_import`) is on |

## Lovelace card

The integration loads a small card on every dashboard – no resource to add by hand:

```yaml
type: custom:hortulus-tasks-card
title: Garden today   # optional
days: 0               # 0 = today + overdue, 7 = the coming week
assignee: me          # optional: me | person.xyz | unassigned
max: 8                # optional, default 8
water: true           # optional, default true; false hides it: watering today, a run in progress, a valve left open (Close), leaks
garden: Allotment     # optional: which garden (title or entry id), when you have more than one
climate: true         # optional, default true; false hides the climate line (7-day mean vs last year, rain, sun, 14-day band)
slogan: true          # optional, default true; false hides the garden saying
```

Tick a task off on the card and it is completed in Hortulus (with the next sowing or care
task planned as usual). `assignee: me` shows your own and unassigned tasks; `person.xyz` shows
that person's and unassigned tasks; `unassigned` shows only tasks without an owner. Overdue
tasks are marked, a “+N more” link and the sprout icon open the panel. The *Close* button on a
valve left open is shown to administrators only. The climate line and the saying need the
extras `climate_card` and `slogans` (Settings → Extras); with no tasks the saying replaces “nothing to do”.
The card is available in English, Dutch and French.

## Voice (Assist)

Run `garden_manager.install_voice_sentences` once (or Settings → Household & voice →
*Install voice sentences*), then ask Assist:

| Intent | English | Nederlands |
|---|---|---|
| `HortulusTasksToday` | "what do I need to do in the garden today" | "wat moet ik vandaag in de tuin doen" |
| `HortulusOverdue` | "what did I forget in the garden" | "wat ben ik vergeten in de tuin" |
| `HortulusHarvest` | "what can I harvest today" | "wat kan ik vandaag oogsten" |
| `HortulusGreenhouse` | "how warm is it in the greenhouse" | "hoe warm is het in de serre" |
| `HortulusWater` | "do I need to water today" | "moet ik vandaag water geven" |
| `HortulusFrost` | "is there frost tonight" | "gaat het vriezen vannacht" |

French sentences ship too. Answers are spoken in the language of the conversation. The
intents take no slots and are registered by the integration itself, so you can also use them in
your own sentences or automations (`conversation.process`). With more than one garden they
answer for the first one.

## PDF download

`GET /api/garden_manager/print?document=garden&page=remarkable&color_mode=eink`
(authenticated) renders the PDF on the fly. It takes the same parameters as `export_pdf`
(`document`, `page`, `landscape`, `color_mode`, `season`, `zone_id`, `bed_ids`, `days`, `notes`,
`grid`, `title`; lists comma separated) plus `labels` (crop names on the map, default true),
`plant_ids` (for the plant cards) and `garden_id`. `&format=svg` returns the SVG pages as JSON
(`{"pages": [...]}`) instead of a PDF.

`GET /api/garden_manager/exports/<file>.pdf` serves a PDF written by `export_pdf` or *Save* in
the Print tab (login or signed link, valid 7 days).

Cooking PDFs (a recipe, the cookbook, the shopping list) are returned by the websocket command
`cooking/pdf` as base64.

## Diagnostics

Settings → Devices & services → Hortulus → ⋮ → *Download diagnostics* gives a JSON file with
the config entry data and options, the settings, counts (zones, beds, plantings, open and total
tasks, custom plants, climate days), the tracked entity ids, the weather state (available,
error, number of hourly and daily points) and the current analysis. Notify services, speakers,
the latitude and photo ids are redacted. A separate **Analysis → Check → Export diagnosis** in
the panel writes the garden check as one JSON file for bug reports.

## Blueprints

Four automation blueprints ship in `blueprints/automation/hortulus/`: frost warning on a lamp
(`frost_flash_light.yaml`; the lamp returns to how it was), log a harvest with a button or an NFC
tag (`button_log_harvest.yaml`), water a dry bed at a good moment (`water_when_dry.yaml`, uses
`run_irrigation_plan` with `only_if_needed`) and announce urgent garden jobs
(`urgent_task_announce.yaml`). Import links are in the README.
