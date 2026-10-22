# Configuration

Hortulus is configured in three places, each with a clear job:

| Where | What | Stored in |
|---|---|---|
| **Setup wizard** (config flow) | First‑run: climate, weather, initial beds + sensors, notifications | config entry → seeds the garden store once |
| **Options** (Settings → Devices & services → Hortulus → *Configure*) | Climate, weather/outdoor sensors, notifications, advanced tuning | written into the garden store |
| **Hortulus panel** | Everything else: drawing beds/zones, plantings, sensor mapping, plant database, tasks, cooking | `.storage/garden_manager.garden` |

The garden store is the single source of truth after setup; the options flow and the
panel both edit it, so they never disagree. Next to the garden file there are two more
files per garden: `garden_manager.garden.syslog` (the system log, last 500 entries) and
`garden_manager.garden.archive` (old seasons, see [section 8](#8-seasons-year-end-transition-and-archive)).

Contents: [1 Setup wizard](#1-setup-wizard) · [2 Sensor mapping](#2-sensor-mapping-rules) ·
[3 Options flow](#3-options-flow) · [4 The panel](#4-the-panel) ·
[5 Import & export](#5-import--export-format) · [6 Units, language, time](#6-units-language-time) ·
[7 Performance](#7-performance) · [8 Seasons and archive](#8-seasons-year-end-transition-and-archive) ·
[9 More than one garden](#9-more-than-one-garden) · [10 Hortulus Web](#10-hortulus-web-optional-website)

---

## 1. Setup wizard

The wizard has these screens, in this order: climate profile → climate details → weather →
beds / greenhouses / containers (repeatable, each followed by its sensors) → notifications →
summary.

### Step 1 – Climate profile
Choose how Hortulus learns your **frost dates**. Every sowing/planting window in the
plant database is expressed relative to them. The wizard first asks for the profile type
(preselected: *regional preset* when Home Assistant's country is NL, BE, GB, DE or FR,
otherwise *USDA zone*), then for the details; the hemisphere is preselected from Home
Assistant's latitude.

| Profile | Use when | Example |
|---|---|---|
| **Regional preset** | You live in a covered region | *Netherlands / Flanders*: last frost 20 Apr, first frost 25 Oct |
| **USDA hardiness zone** | North America or you know your zone | 7a → 8 Apr / 1 Nov (shifted 6 months on the southern hemisphere) |
| **Custom frost dates** | You have local data (best) | `04-28` / `10-15` (format `MM-DD`) |

Available presets:

| Preset | Hemisphere | Last frost | First frost |
|---|---|---|---|
| `nl_be` Netherlands / Flanders | N | 04‑20 | 10‑25 |
| `uk_south` | N | 04‑10 | 11‑01 |
| `uk_north` | N | 05‑01 | 10‑15 |
| `de_central` | N | 04‑30 | 10‑15 |
| `fr_north` | N | 04‑15 | 10‑31 |
| `scandinavia_south` | N | 05‑15 | 09‑30 |
| `mediterranean` | N | 03‑01 | 12‑01 |
| `au_melbourne` | S | 09‑15 | 05‑15 |
| `nz_christchurch` | S | 10‑10 | 04‑25 |
| `za_highveld` | S | 09‑01 | 05‑15 |

**Edge cases handled**: a custom `02-29` resolves to Feb 28 in common years; on the
southern hemisphere a *season* runs July → June and is named after the year its spring
falls in (season 2026 = Sep 2026 – May 2027); USDA zones 11+ are treated as frost‑free.
Impossible dates (such as `13-01`) are refused.

### Step 2 – Weather
* **Weather entity** (recommended): must offer an hourly and/or daily forecast. Hortulus
  calls `weather.get_forecasts` every 30 minutes and whenever the weather entity
  updates (rate‑limited to once per 10 minutes). Forecast units are converted to °C,
  mm and km/h automatically.
* **Outdoor temperature** (optional): used for the climate history and the
  growing‑degree‑day log; falls back to the weather entity's current temperature. °F
  sensors are converted.
* **Rain sensor** (optional): a daily rain total in mm (or a binary rain detector). Without
  a rain gauge the climate history books the forecast rain of the day, and recorded or
  observed rain replaces it later.

More weather inputs (outdoor humidity, leaf wetness, wind speed, wind gusts, solar
radiation, outdoor light, the optional Open‑Meteo forecast, elevation) are set later in the
panel under *Settings → Weather*.

### Step 3 – Beds, greenhouses and containers
Add as many areas as you like (*Add another…* menu). Each area asks for name, type
(*outdoor bed*, *greenhouse*, *container*), width × length (metres, 0.1–100), soil, shade %
(steps of 5) and wind exposure, followed by a screen with the sensors (all optional):

| Field | Typical entity | Shown for | Entity filter |
|---|---|---|---|
| Soil moisture | `sensor.soil_moisture_bed_1` | all | `sensor`, device class moisture |
| Soil temperature | `sensor.soil_temp_bed_1` | all | `sensor`, device class temperature |
| Air temperature | `sensor.greenhouse_temp` | greenhouse | `sensor`, device class temperature |
| Air humidity | `sensor.greenhouse_humidity` | greenhouse | `sensor`, device class humidity |
| Light | `sensor.greenhouse_lux` | greenhouse | `sensor`, device class illuminance |
| Irrigation | `valve.bed_1` or `switch.drip_bed_1` | all | `switch`, `valve` |
| Flow rate | `4` L/min | all | – |

What the wizard creates:

* **Outdoor beds & containers** → raised beds (containers: container beds) inside one
  outdoor zone (“Garden”), laid out left‑to‑right with 50 cm paths.
* **Greenhouse** → a greenhouse *zone* of the given size with one in‑ground bed
  (“Greenhouse Zone A bed”) along the long side; air sensors attach to the zone, soil
  sensors and the valve to the bed. Several greenhouses stand side by side.

Everything can be redrawn later in the panel.

### Step 4 – Notifications
Persistent notifications, any number of `notify.*` services (mobile push), an optional
TTS engine + speakers, and the time of the **daily digest** (default 07:30). Frost alerts,
heat alerts and the spoken frost announcement are switched in the options flow or in
Settings → Notifications (frost and heat alerts on, announcement off by default).

### Step 5 – Summary
Review and optionally seed an **example plan** for the coming season: tomato + basil +
marigold under glass, carrots next to onions (carrot/onion‑fly masking) and three
succession sowings of lettuce. An empty garden can instead be started from the panel's
welcome screen (see *Today*).

---

## 2. Sensor mapping rules

Each bed resolves its sensors **field by field** in this order:

1. sensors set **on the bed**,
2. sensors set **on its zone** (e.g. one greenhouse thermometer for all its beds),
3. for every zone that is **not** a greenhouse or cold frame (outdoor, orchard, herb
   garden, containers …): the **outdoor sensors** from the weather settings.

Greenhouses and cold frames have their own climate and never fall back to the outdoor
sensors. Missing, `unknown` or `unavailable` sensors simply lower precision. A sensor that
has not reported for longer than *sensor stale minutes* (default 360) is ignored and raises
a “sensor stale” alert. Hortulus uses `last_reported`, so a flat‑lining but alive sensor
is not considered stale.

Sensor kinds you can map in the panel (Settings): soil moisture, soil temperature, EC and
N / P / K probes per bed; air temperature, air humidity, light, PAR and leaf wetness per
zone; outdoor temperature, humidity, rain, leaf wetness, **wind speed**, **wind gusts**,
**solar radiation** (W/m²) and **outdoor light** (lux) for the garden – together a small
weather station for the climate history. Once a day a moisture sensor also sets the bed's
water balance, and each bed learns how fast it really dries out.

The outdoor station in detail (all optional; without a sensor the weather entity's value is
used where it has one):

| Sensor | Used for |
|---|---|
| Outdoor temperature | daily minimum, maximum and mean; degree days, frost dates, frost nights |
| Outdoor humidity | daily minimum, maximum and mean humidity: Penman‑Monteith ET₀ and the logged Hutton criteria |
| Rain | the day's rain (a daily total in mm); the water balance, after‑care tasks, rain statistics |
| Wind speed | daily mean and maximum (km/h, m/s, mph and knots are converted to km/h); Penman‑Monteith ET₀ |
| Wind gusts | the strongest gust of the day; the *check after a storm* task (gusts ≥ 60 km/h or wind ≥ 45 km/h) |
| Solar radiation (W/m²) | radiation sum (MJ/m²) and sunshine hours (≥ 120 W/m²); Penman‑Monteith ET₀, dull days |
| Outdoor light (lux) | used as radiation (lux × 0.0079) when there is no radiation sensor |
| Leaf wetness | the disease model's wet‑leaf input |

Every mapped **temperature sensor** – outdoor air, outdoor soil, the air temperature of a
zone (greenhouse, cold frame), and the soil or air temperature of a bed – also gets its own
daily minimum, maximum and mean in the climate history.

---

## 3. Options flow

| Menu | Fields |
|---|---|
| Climate & frost dates | profile, hemisphere, preset/zone/custom dates |
| Weather & outdoor sensors | weather entity, outdoor temperature, rain (the other outdoor sensors are set in the panel) |
| Notifications | persistent, push services, TTS, speakers, digest time, frost alerts, heat alerts, TTS frost announcement |
| Advanced tuning | language of generated texts (auto/en/nl/fr), companion radius (10–300 cm), sensor stale minutes (15–2880), root‑zone depth (50–600 mm), max irrigation per session (2–60 mm) |

Each menu item saves only its own section into the garden store. Saving reloads the
integration; your plan and tasks are untouched. Beds, zones and sensor mapping are
edited in the panel, not here.

---

## 4. The panel

Open **Hortulus** in the sidebar (`/hortulus`). Non‑admin users can view everything and
work with tasks, the diary, harvests and the cookbook; editing the plan, plant database,
settings and hardware requires an admin. Tabs have their own URL (`/hortulus/calendar`,
`/hortulus/wall` …); the Handbook accepts a chapter (`/hortulus/handbook/<chapter>`).

The menu has eight places, the related tabs of a place in a row underneath it. A place
reopens on the tab you used last.

| Place | Tabs |
|---|---|
| **Today** | Today (dashboard) · Wall screen (button on the dashboard) |
| **Garden** | Planner · Garden plan · Crops |
| **Calendar** | Calendar |
| **Weather** | Weather |
| **Journal** | Journal |
| **Cooking** | Cooking |
| **Knowledge** | Plants (library) · Advice · Handbook |
| **Manage** | Analysis · Print · Settings |

A ninth tab, *Garden* (a read‑only look at the plan), exists only for the website
([section 10](#10-hortulus-web-optional-website)) and is never shown in Home Assistant.

### Today (dashboard)
A hero in the colours of the season with stat tiles (tasks today, work today, degree
days), today's tasks with a tick box, the beds with moisture, the greenhouse, the next
48 hours of weather, what comes up next, a **water & climate** card (irrigation mode, beds
needing water, *Water now* / *Stop*, disease risk, nutrients), a **pest calendar** card
(which pests fly now, only for crops in or soon in the ground) and **Quick harvest** (the
crops that can be picked now, add the weight with big buttons, save). Red banners appear
for a **valve left open** (with *Close valve*) and a **leak**. An empty garden shows a
**welcome screen**: lay out a ready‑made starter garden (2–4 raised beds, a herb pot,
optionally a greenhouse, with a first plan), draw your own or read the handbook first.

### Wall screen
A calm, large kiosk view for a tablet (`/hortulus/wall`, or *Today → Wall screen*): the
time, the weather, today's tasks with big tick boxes, the beds' moisture and alerts. No
menus; it dims at night. In Dutch, *Aanpassen* lets an administrator choose the blocks (forecast,
rain radar, agenda, weather saying, recipe tip, organic gardening fact, garden in numbers and more),
drag them in order and set their width; everything stays on one screen.

### Garden plan
The garden plan fixes the shape of the garden for **one season**, without plants, in three
steps: **Site** (elements: house, driveway, street, parking, carport, terrace, decking,
wall, paths in gravel / stone / wood / stepping stones / bark, lawn, flower bed, hedge,
shrub, tree, pond, seating, pool, play area, fence, trellis, beehive, shed, compost, water
butt …), **Growing zones** (open ground, ornamental garden, greenhouse, cold frame,
planters & pots, orchard, food forest, soft fruit, herb garden, flower garden) and
**Beds** (open a zone and draw its beds and planters on its own map; a *Planter / pot*
tool draws a container bed). Elements are drawn on a 10 × 10 cm grid; a house, path,
driveway, hedge or growing zone on a lawn takes that area away from it (map, print and
m²), a tree or shrub does not. Each item can only be selected, moved and edited in its own
step. Toolbar:

* **Season** picker. A season without a plan offers to copy another year's or start empty.
* **Plans**: start over with a new plan (from scratch, same zones but empty, or zones and
  beds without crops). The current plan becomes **inactive** (set aside with its beds and
  crops), can be activated again later (swapping places with the active one), compared or
  deleted.
* **Year‑end transition**, see [section 8](#8-seasons-year-end-transition-and-archive).
* **⋮ More**: export (JSON / YAML), import, keyboard shortcuts.

### Planner
The Planner only plants, on the plan of the chosen season (zones, beds and elements are
locked there). Two steps: **Perennials** (trees, bushes, perennial herbs, asparagus,
rhubarb – they stay from year to year, fruit after *N* years) and **Annuals**. One click
selects an item, a second click (or *Details*, or <kbd>Enter</kbd>) opens its details popup.

* **Plant palette**: choose *Single*, *Block* or *Row*, then drag a plant onto a bed (or
  press <kbd>Enter</kbd> on a palette plant to add it to the selected bed). The palette
  shows the plants that suit the open zone type. While you hover, Hortulus asks the backend
  for a live compatibility check and shows ♥ friends / ⚠ conflicts / ⟲ rotation issues in
  the ghost label.
* **Details popup**: layout, method (sow indoors / sow in place / plant), status, size,
  planned date override, a season timeline (sowing window, transplant window, harvest),
  growth stage, crop coefficient, degree days and the expected harvest date, all warnings
  with their explanation, **better neighbours** for conflicts, **fits in** buttons that move
  a crop to a bed without a rotation conflict, **Why (not) here?** per crop, the crop
  rotation of the last five years, a **quick note with photo**, a photo timeline and the
  bed's water use.
* **Succession sowing**: split a block into strips sown every *N* days (default from the
  plant, e.g. lettuce 21 days) or stack sowings on the same spot. Sowings outside the
  sowing window are skipped and reported.
* **Autofill** (Annuals step): enter household size, hours per week, water and compost you
  have, goals (fresh, storage, herbs, pollinators, winter, perennials, low maintenance),
  must‑have and never crops, preferences (freedom of choice, respect neighbours, add
  pollinators, year‑round harvests, perennials allowed, respect the zone type) and which
  beds to fill. The proposal shows crops, counts, m², expected harvest, minutes per
  week, peak‑week water and compost, plus a reason per plant that was not placed (too
  late, zone type, glass, frost, rotation, bad neighbour, no room) and an offer to fill the
  next season. Nothing changes until you press **Apply**. The rules: amounts per person
  from the database (or your own learned kg/m²); rotation conflicts exclude a bed;
  companions, greenhouse need and shade tolerance score the bed; strips are packed with the
  tallest crops on the side away from the sun; quick crops get three successive sowings.
* **Multi‑select**: <kbd>Shift</kbd>/<kbd>Ctrl</kbd>‑click beds, crops or elements; drag
  them together or use **align** (left, centre, right, top, middle, bottom) and
  **distribute**.
* **Layers**: show/hide zones, elements and crops.
* **Overlays**: companions (green = friends, dotted green = pest deterrence, red dashed =
  enemies, purple = allelopathy, orange = competition or overlap, grey dotted = shading),
  moisture (bed outline + %), soil temperature. Plant symbols follow the growth habit
  (disc = bush, triangle = climber, diamond = upright, ring = vine, flower = rosette,
  ▼ = root crop, drop = bulb), so the plan reads without colour too. Crops are drawn smaller
  after planting and grow to full size by harvest for the date shown.
* **Show garden on**: scrub through the season – plantings not in the ground on that date
  are faded.
* **End‑of‑season banner**: what can still be sown or planted, with a jump to next year's plan.
* **Autosave**: changes are saved ~1 s after each edit with an optimistic‑concurrency
  revision; if the plan changed elsewhere you get a notice and the latest plan.

Keyboard shortcuts (press <kbd>?</kbd> in the planner):

| Keys | Action |
|---|---|
| <kbd>←</kbd><kbd>↑</kbd><kbd>→</kbd><kbd>↓</kbd> | move selection by one grid step (<kbd>Shift</kbd> = 10×) |
| <kbd>Alt</kbd> + arrows | resize selection |
| <kbd>Ctrl/⌘</kbd>+<kbd>Z</kbd> / <kbd>Ctrl/⌘</kbd>+<kbd>Y</kbd> | undo / redo |
| <kbd>Delete</kbd> | remove selection |
| <kbd>Ctrl/⌘</kbd>+<kbd>D</kbd> | duplicate planting |
| <kbd>[</kbd> <kbd>]</kbd> | select previous / next item (of the current step) |
| <kbd>Enter</kbd> | open the details of the selection |
| <kbd>G</kbd> <kbd>C</kbd> <kbd>M</kbd> <kbd>T</kbd> | grid snap, companions, moisture, temperature overlays |
| <kbd>+</kbd> <kbd>−</kbd> <kbd>0</kbd> | zoom in / out / fit |
| <kbd>Esc</kbd> | clear the selection |

### Crops
Every crop of a season on one list (*by bed*, *by crop* or *by date*) with method, status,
count, notes and planned / actual dates editable in place – nothing to drag. Tick several
crops to set a status or a date for all of them at once. On a phone each crop is a card
with the next date to fill in. Views:

| View | Shows |
|---|---|
| **List** | the editable table; *Show on map* opens the planner on that crop |
| **Timeline** | the year per bed as bars (raising, growing, harvest) with a today line; drag a planned crop sideways to move its sowing and planting out |
| **Sowing plan** | what to sow, plant out and harvest week by week (*Done* fills in today's date) |
| **Seeds** | the seeds the plan needs against your seed stock; what is missing goes on a Home Assistant to‑do list in one click, without duplicates |
| **Succession** | beds that free up this season and what can follow there |
| **Harvest forecast** | expected kg per week |

### Plants (library)
Search (accent‑insensitive, any language), filter by family, *greenhouse*, *quick
crops* or *my plants*. The built‑in database has 232 crops (vegetables, herbs, fruit,
flowers, green manures), each with picture, sowing calendar computed for **your** frost
dates, neighbours and “where it grows in your garden”. *Customize* stores only the fields
you changed as an override (per language for names and texts), so future updates of the
built‑in data still reach you; *Reset to built‑in* removes the override. *New plant*
creates a custom plant (identifier derived from the English name); a custom plant that a
plan or a plan set aside still uses cannot be deleted. With *Settings → Display → photos*
on, the browser also shows a Wikipedia photo (CC BY, CC BY‑SA, CC0, public domain, with
credit); the illustrations work offline.

### Calendar
Month, week, list, **timeline** (a Gantt per bed with sowing, growing and harvest bars,
the degree‑day harvest estimate, frost dates and a “garden work” row with the seasonal
tasks) and **Year** views. Overdue open tasks are shown on today so nothing hides in
the past. On touch screens, swipe a task right to complete it or left to postpone it a
day. The task dialog shows the live context (soil moisture and temperature, water
balance, nutrients, air temperature, humidity, disease and frost risk, today's weather and
ET₀), the tools for the job and links to the matching handbook chapter. Open a task to
complete, skip, postpone (+1/+3/+7 days or a date; dependants follow), change priority,
assign it to a person, add notes and **photos** (uploaded through Home Assistant's
`image_upload`, stored locally). A title or description you rewrite is kept when tasks are
recalculated. The **Year** view shows every crop month by month (sow indoors, sow, plant
out, growing, harvest) with the number of tasks and hours per month; print it as the *Year
plan*.

### Weather
The weather now, a 24‑hour chart (temperature over rain), the coming ten days with a
temperature range bar and frost / heat tags, what it means for the garden (frost nights,
hot days, rain so watering can wait, a dry spell, beds that need water) and a **rain
radar**: a radar camera from Home Assistant when there is one (e.g. Buienradar), else
Buienradar's public map for the Netherlands or Belgium (loaded by your browser, refreshed
every 5 minutes). It needs a weather entity under *Settings → Weather*.

#### Climate history

Below the forecast (also without a weather entity) the **Climate history** card shows what
the weather really did here:

* a **daily chart** for 30 days, 90 days or a year: the band from lowest to highest
  temperature, the daily mean and rain bars; hover a day for sunshine, wind and where the
  data comes from (own sensors, recorder history, Open‑Meteo);
* **lately, compared with last year**: the last 7 days, the last 30 days and the season so
  far (from 1 January, or 1 July on the southern hemisphere), each with the same
  period last year next to it – mean, lowest, highest, rain and rain days, frost nights,
  days ≥ 25 °C (and ≥ 30 °C), sunshine, strongest wind, degree days, evaporation (ET₀) and the
  water balance (rain − evaporation);
* **records**: coldest, warmest, wettest day and strongest gust;
* **every temperature sensor**: now, today's range, the 7‑day mean, the 30‑day range, record
  low and high, and a 30‑day sparkline;
* **month by month** with the change against the same month last year;
* the **measured frost dates** per year against the regional preset, and *How Hortulus uses
  it*;
* **In a nutshell** (extra *season_summary*) at the top: the season and last month in a few
  sentences against last year;
* **Use my frost dates** (admin, extra *local_frost_suggest*): once ≥ 2 complete years put a
  measured frost date ≥ 7 days off the preset; it switches the region to custom with the
  measured dates – nothing changes until you press it;
* **Import weather station data** (admin, extra *station_import*): a weather station's export (Netatmo,
  Ecowitt, Davis, a spreadsheet). Header and separator (`;`, `,`, tab) are detected; time
  (also unix seconds), temperature, humidity, rain (a running daily total → its maximum,
  per‑reading rain → summed), wind and gust columns are recognised in English, Dutch and
  French; °F, inches, mph, m/s and knots are converted. Days Hortulus measured itself are kept;
  imported days count as *history*.

**How it is recorded.** Every update folds the outdoor sensors – or, without them, the
weather entity – into today's record: minimum, maximum and mean temperature, humidity, wind
and gusts, rain, radiation and sunshine hours. Means take at most one sample every 4 minutes
per series; the day also records how many hours own samples covered.

**How gaps are filled.** At start‑up and once a day Hortulus looks at the last 30 days:

1. **Home Assistant's recorder** – the same sensors (temperature sensors, outdoor humidity,
   wind and gusts) as the recorder kept them while Hortulus was not running. Units are
   converted; extremes are combined with what Hortulus logged itself; a recorded mean only
   replaces its own when the day was not covered for at least 20 hours.
2. **Open‑Meteo's observed daily weather** (only with *Use Open‑Meteo* on in *Settings →
   Weather*): temperature, rain, wind and gusts, radiation, sunshine, humidity and FAO ET₀
   for the garden's location, the last 31 days. It fills only what was not measured well:
   days that own samples covered for less than 12 hours, and values nobody measured.

Own samples always win; for rain a gauge beats the recorder, the recorder beats Open‑Meteo,
and Open‑Meteo beats the forecast. Today is always left to the own samples.

**Retention.** Outdoor days stay in the daily log for 800 days (two seasons and a bit),
temperature sensor days for 400 days. Older days are rolled up into **months** that are kept
for good (lowest, highest, mean, rain, frost and hot days, sunshine, strongest wind), so
records and year‑on‑year comparisons survive. Everything is stored in the garden file
(`climate_log`, `sensor_log`, `climate_months`, `frost_years`).

**Frost dates.** For every year Hortulus keeps the last spring frost and the first autumn
frost it measured (outdoor minimum below 0 °C; spring = January–June, autumn = July–December,
the other way round on the southern hemisphere). A half‑year counts once it is over and at
least 80 % of its days were logged; the average of those years is shown against the preset
(*x days earlier / later*). The measured dates are shown for comparison – the sowing
calendar keeps using the frost dates under *Settings → Region*.

**What the engine does with it.** Degree days per zone (greenhouses use their own air
sensor, otherwise the outdoor day + 2 °C at night and + 4 °C by day), heat, cold and dull days
that delay crops, the daily water balance (Penman‑Monteith ET₀ of the logged day), disease
risk from wet, warm days behind us, sowing on the soil temperature of the last days, the
after‑care tasks (after a storm, after a downpour, after a dry week) and the *it froze*
alert. The four climate sensors in Home Assistant come from the same log (see
[Entities](ENTITY_REFERENCE.md#climate-history)).
### Journal
Sections:

| Section | Content |
|---|---|
| **Diary** | notes, observations, problems and milestones with photos (per bed, crop or the whole garden) |
| **Harvest** | the harvest log in kg and pieces (log one when you tick off a harvest task or from the planner), totals per crop, your own **learned yield per m²** (used by Autofill, advice and the shopping list), the harvest **over the years** (best year in gold) |
| **Kitchen** | crops ready to pick with how to keep them, a surplus warning (more than 1.5× what the household eats in a week) with ideas to store, preserve or share, and **cost and harvest**: the harvest at shop prices against your expenses and garden water |
| **Seed box** | seed packets with use‑by years per family, and the seed still needed for the plan (the shopping list skips seed you have) |
| **Water** | soil moisture from Home Assistant's history, water given from Hortulus' log and rain, per bed for 7, 14 or 30 days; garden water use from the meter and the rain butt level |
| **Season report** | crops, harvest against expectation, failures, problems from the journal, water; download as Markdown, or as the *Season book* PDF |
| **System log** | every change to the garden (from the panel, actions, automations and what Hortulus adjusts itself) with time, who and what. **Every entry can be undone** (admin); an item changed again since is only overwritten after confirmation; the undo is logged too, so it can be redone |

Select a bed in the planner to add a **soil analysis** (pH, organic matter, P, K, Mg,
lime); the fertiliser plan, lime advice and shopping list follow the latest one.

### Cooking
A seasonal cookbook from what the garden gives right now. Hortulus looks at the crops
inside their harvest window (plus anything you add from the cellar, such as stored pumpkins
or frozen beans) and proposes dishes for them. Lettuce, cucumber, radish and similar
crops only go in salads and other uncooked dishes; elderberries, beans, chickpeas and
edamame are never offered raw or half‑cooked. Recipes are written in English, Dutch and
French, with quantities per person and what comes from the garden, what is at home and what
to buy. Three parts: **Ideas from the garden**, **My cookbook** and **Shopping list**.

* **Choices** (remembered with *Remember these choices*, stored in the garden):
  servings (1–12), a side (what suits the dish, none, or pasta, rice, bulgur, couscous,
  pearl couscous, gnocchi, potatoes, fries, bread, noodles), meat, fish or vegetarian
  protein (chicken, beef, pork, mince, sausage, bacon, ham, salmon, white fish, prawns, tofu,
  chickpeas, lentils, egg, halloumi, goat's cheese … or none for vegetarian dishes),
  **Use up from the fridge** and **Always in the house**.
* **Fridge** items (butter, cream, milk, eggs, parmesan, feta, mozzarella, yoghurt, mustard,
  onion, breadcrumbs …) are worked into the dishes where they fit: each item has its own
  preparation per kind of dish (yoghurt as tzatziki, raita or a honey‑mustard dip; feta baked
  or whipped; parmesan as crisps or a crust …). A dish takes at most three fridge items,
  one sauce, one dressing and one crunchy topping. They count as “at home”. Items under
  *Always in the house* never go on the shopping list.
* **Dishes**: soup, oven tray, stir‑fry, pasta, risotto, salad, gratin, stew or curry,
  frittata, stoemp, stuffed vegetables, a plate with meat and fries, pesto, fruit crumble,
  chilled soup, crostini, compote and the extra dishes (ratatouille, tian, shakshuka, tart,
  gnudi, waterzooi, vegetable cakes, clafoutis, panna cotta …). Dishes made for certain
  plants only take those plants. Each dish gets a picture (the crops on a plate with the
  side underneath and the meat in the middle).
* **Chapters**: Soups · Starters · Main courses · Desserts · **Preserving & pickles** (quick
  pickles, chutney, passata, pesto cubes, jam, freezing, sauerkraut; amounts are a batch).
  Ideas, the cookbook and the cookbook PDF are split by chapter.
* **Menus**: a soup or starter, a main course and a dessert that belong together, built
  from what is ready to pick (themed menus of the season, and menus around a main
  course). One click puts all three on the shopping list or into the cookbook.
* **Edit a recipe**: add, remove or change ingredients (name, amount, unit, from the garden
  / at home / to buy; up to 40) and add, remove, rewrite or reorder the steps (up to 30).
  Your version goes into your cookbook, the shopping list and the PDFs follow it, and
  *Back to the original* restores the generated recipe.
* **Cookbook**: keep recipes (up to 500), mark favourites, add notes, note when you cooked
  them; filter by chapter and favourites; search by recipe or ingredient.
* **Shopping list**: put dishes on it from their recipe; it separates what to buy from
  what the garden gives. Print it, save it as PDF (list, or list + recipes with the dish
  pictures), send it to a phone (a `notify.*` service, default: the garden's notification
  settings) or put it on a Home Assistant to‑do list (items already on it are skipped;
  your own permissions on that list apply).
* **PDF**: a recipe, the whole cookbook (a chapter page each, long recipes continue on
  another page) or the list; up to 200 recipes per PDF, mail or to‑do export.

### Advice
An **Ask Hortulus** sentence builder (*I have a question/problem about [subject] [which
one]: [question]*) with live status, likely causes, what to do now, **eco and home
remedies**, prevention and tools. Garden suggestions (pollination partners, pollinator
flowers, bad neighbours, shading, harvest gaps, empty beds, ecology, food‑forest layers)
with one‑click apply; harvest coverage per month; a seasonal shopping list; tools per job.

### Handbook
23 chapters (EN / NL / FR) with search and a glossary: planning, soil & compost, sowing,
watering (ET₀, Kc, water balance), feeding (NPK, EC), rotation, companion planting, the
greenhouse, pests, diseases, the garden year & winter rest, harvest & storage, seed
saving, no‑dig & mulch, herbs, perennials, fruit, tools & materials, home remedies,
year‑round harvest, choosing sensors, permaculture and food forests. The ⓘ buttons across
the panel open the glossary entry for a term and link into the chapter.

### Analysis
| Section | Content |
|---|---|
| **Check** | explains inconsistencies (a year with crops but no plan, crops whose bed is not on their season's plan, beds outside their zone, overlapping or late crops, a missed year‑end transition …) with a link to the right place and **one‑click repairs** (logged and undoable). The tab shows a badge with the number of problems; *Export diagnosis* writes one JSON file to attach to a bug report |
| **Why not?** | per bed, why a plant does or does not fit |
| **Compare** | zones, beds, elements and crops added, removed or changed between two plans |
| **Errors** | every refused action with its reason |
| **System log** | the journal's log |

### Print
Pick a document – **garden map**, **greenhouse / zone**, **bed sheets**, **checklist**,
**season chart**, **year plan**, **planning sheet** (outlines + dot grid to sketch on),
**plant cards** or the **season book** – then paper (A4, A3, A5, Letter, **reMarkable Paper
Pro**), orientation and colours (*full colour*, *e‑ink* with light tints and a hatch
pattern per family, *grayscale*). The preview shows every page; **Download PDF** fetches it
through Home Assistant's authenticated API, **Save** writes it to
`/config/hortulus/exports/` (private; a signed download link valid for 7 days).
Maps contain a legend (families, zones, elements, symbols, numbered crops where names
don't fit), a scale bar with ratio and a north arrow; bed sheets add a 10 cm grid, the
compost and fertiliser for the coming crops and the rotation history. The **season
book** (A5 by default) is the whole garden year to print: cover, the season's plan, an
introduction written from the season's figures, one chapter per month (sown, planted, done,
your journal with photos, harvest, water, weather), the year in numbers, a glossary and
back cover; the page count is a multiple of four. Print documents use the plan of the
chosen season.

To put a PDF on the reMarkable: download it and drag it into the reMarkable desktop or
mobile app, or send it with *Send to reMarkable* by email. The page size matches the
Paper Pro screen exactly, so nothing is scaled.

### Settings
Sections, top to bottom (admins can edit; entity fields are drop‑downs that list only the
entities that fit):

| Section | Content |
|---|---|
| **Region** | hemisphere, profile (preset / USDA / custom), frost dates |
| **Weather & outdoor sensors** | weather entity, outdoor temperature, rain, outdoor humidity, leaf wetness, **wind speed**, **wind gusts**, **solar radiation** (W/m²), **outdoor light** (lux), **Open‑Meteo** opt‑in (forecast and observed history for the climate history), elevation |
| **Zones** | per zone: air temperature, humidity, light, leaf wetness, **PAR**; for greenhouses and cold frames also **vent** and **shade screen** entities with *off / advise / auto* control, *thermal mass*; *against a warm wall*, *heated* (+ minimum temperature) |
| **Beds** | per bed: soil moisture, soil temperature, **EC, N, P, K** probes, valve, **Test** button, flow (L/min; the measured flow is shown when the water meter learned it), **valve timer** |
| **Irrigation hardware** | mode (*off / advise / auto*), pump, start time, max runtime, frost lockout, rain skip, pump lead time; **solar surplus** sensor (W or kW), *start from surplus* (W, default 500) and *wait at most until* (default 11:00); **home battery** charge (%) and *or start at* (%, default 95); **rain water first**: pump from the butt, *switch to mains below* (%), *use mains when the butt is empty*, power of both pumps (W) |
| **Resources** | household size, hours, water and compost for autofill, goals; switches for *seasonal garden work* and **Ecological tips** (organic answers to pests and diseases, eco calendar, food‑forest advice) |
| **Extras** | optional helpers, all on by default – see [Extras](#extras) |
| **Notifications** | persistent, push services, TTS, speakers, digest time, frost / heat alerts, spoken frost announcement; reminders (evening reminder of overdue tasks, default 18:30 after 1 day; weekly look‑ahead, default Sunday 19:00); *weather‑aware scheduling* (moves weather‑sensitive jobs off rainy, frosty or hot days) |
| **Water meter & rain butt** | the meter sensor (m³ or L), the butt level in % and the total butt capacity; leak alerts |
| **Costs** | currency, water price per m³, own prices per crop (€/kg) for the harvest‑versus‑cost overview |
| **Household & voice** | who gets new tasks (default and per task type), a notify service per person, install the Assist sentences |
| **General** | language (follow Home Assistant / English / Nederlands / Français), units (metric), grid size, companion radius, **export** (JSON / YAML, including tasks) |
| **Display** | per browser: plant photos from Wikipedia; colour theme (*classic green*, *earth*, *night*, *season*) and light / dark / automatic. In Home Assistant the theme and light / dark choice follow your user to every device |

#### Irrigation hardware in 5 steps
1. Settings → Beds: pick the valve (`switch.*`, `valve.*` or `input_boolean.*`) and the flow
   in L/min for each bed (measure it: time how long a 10 L bucket takes, or let the water
   meter learn it). Press **Test** to open the valve for 5 s (the pump only after the valve
   reports open) and check that it reports open and closed again. If the valve has its own
   timer, enter it under *Valve timer*: longer runs are split into openings that stay inside it.
2. Settings → Irrigation hardware: optional pump (switch or valve) and *pump stop before valve* (seconds the pump is off before the valve closes).
3. Choose the start time and the limits (max runtime, frost lockout, rain skip).
4. Try `garden_manager.run_irrigation_plan` with `dry_run: true` and check the plan.
5. Switch on **Automatic irrigation**. With *advise* you only get watering tasks.

A run ends when a valve stays closed, or goes silent for a minute while the pump runs
(the pump is stopped first); a valve or pump open far longer than any run (max runtime +
10 minutes) raises a banner with *Close valve*; with the leak notification on in Settings and a water meter set, at least 5 L counted
within 15 quiet minutes (no run in progress, every valve closed) is reported as a leak.

#### Extras
Optional helpers (2.0), each a switch under *Settings → Extras* and a top‑level setting in the
garden file. All are on by default; switching one off just hides or skips it.

| Setting | What it does |
|---|---|
| `slogans` | changing garden sayings (EN/NL/FR, by theme and season, own lines for the southern hemisphere), picked per day and place: digest, weekly plan, monthly weather message, season report, season book back cover, dashboard hero line and card |
| `soil_estimate` | beds without a soil temperature sensor get a soil temperature estimated from the logged daily mean air temperature (smoothed over the last 10 days, needs ≥ 3 logged days); used for sowing advice, shown on the bed card as *≈ x °C* |
| `water_forecast` | per bed: when the water balance will pass the readily available water (p × TAW) with the forecast's ET₀ and rain over the next 7 days – *dry again in N days* |
| `sensor_health` | a mapped sensor unavailable or unknown for ≥ 2 days gives one warning (`alert.sensor_silent`, instead of the stale‑reading alert) |
| `season_summary` | the season and last month in sentences against the same dates last year (warmer / colder, wetter / drier, sunnier / duller, frost nights): top of the climate history, season report and season book, and a notification with the digest on the 1st of each month |
| `local_frost_suggest` | after ≥ 2 complete measured years with the last spring or first autumn frost ≥ 7 days off the preset: an info alert and a **Use my frost dates** button in the climate history |
| `station_import` | import a weather station's CSV export in the climate history (see below) |
| `solar_irrigation` | automatic watering waits for solar surplus (sensor and limits under *Irrigation hardware*): the run starts once the surplus reaches the minimum, at the latest at *wait at most until*; no sensor or no usable reading = no waiting. The dashboard shows *Waiting for solar surplus* |
| `climate_card` | a climate line on the `hortulus-tasks-card`: 7‑day mean and the difference with last year, rain, sun, a 14‑day temperature band (card options `climate: false`, `slogan: false`, see [Entities](ENTITY_REFERENCE.md#lovelace-card)) |
| `frost_heating` (2.1) | a heater per greenhouse or cold frame (*Zones*: heater entity – switch or climate –, heat below °C, power, weekly budget in kWh): with climate control on *auto* it goes on below the temperature of the zone's air sensor and off 1.5 °C above it; once the week's budget is used it stays off until Monday. Energy: `sensor.hortulus_greenhouse_heating_this_week` |
| `adaptive_irrigation` (2.1) | ~90 minutes after a run the bed's moisture sensor shows how much of the water soaked in; after two runs the bed gets its own factor (0.5–2×) on the planned water, and the water balance is credited with what soaked in. Shown per bed under *Beds*, with *Forget*. Runs followed by rain are not counted |
| `own_yields` (2.1) | your harvested kg/m² weigh in against the book value (which counts as one season), and the harvest forecast starts when your first harvests really came (days after sowing or planting out, at most a month off) |
| `ai_diagnosis` (2.1) | *What is wrong here?* under diary photos: the photo goes to Home Assistant's AI task (your choice or the preferred one, `ai_task_entity`), which picks from the pests and diseases Hortulus knows; the answer comes with the organic advice and can be noted as a problem |
| `calendar_mirror` (2.1) | copies the open tasks of the next `mirror_days` (default 7) into `mirror_calendar` (Google, CalDAV, local …), each task once per due day; later changes are not carried over (Home Assistant can add events to other calendars, not edit them) |

---

## 5. Import & export format

Export from the Garden plan / Planner (⋮ menu), Settings → General, or
`garden_manager.export_plan`. Import (admin) from the same ⋮ menu or `garden_manager.import_plan`.

```yaml
format: hortulus-plan
version: "1.7"
exported_at: "2026-03-01T10:00:00+01:00"
zones:
  - id: zone_outdoor
    name: Garden
    type: outdoor          # outdoor | greenhouse | cold_frame | orchard | fruit | herbs | flowers | garden | containers | food_forest
    x_cm: 0
    y_cm: 0
    width_cm: 400
    length_cm: 300
    microclimate: {shade_pct: 0, wind: moderate, heated: false}
    sensors: {air_temperature: null}
beds:
  - id: bed_1
    name: Bed 1
    zone_id: zone_outdoor
    kind: raised           # in_ground | raised | container
    x_cm: 50
    y_cm: 50
    width_cm: 200
    length_cm: 100
    soil: loam
    sensors: {soil_moisture: sensor.soil_moisture_bed_1, soil_temperature: sensor.soil_temp_bed_1}
features:                  # garden elements: path, house, hedge, tree, shed, water_butt ...
  - {id: ft_1, name: Path, type: path, x_cm: 0, y_cm: 320, width_cm: 400, length_cm: 60}
layouts:                   # the garden plans of other seasons (zones, beds, features)
  "2027": {zones: [], beds: [], features: []}
layout_season: 2026        # the season whose plan is the live zones / beds / features above
archived_plans: []         # plans set aside ("not active"): zones, beds, features, plantings
plantings:
  - id: pl_carrots
    plant_id: carrot
    bed_id: bed_1
    season: 2026
    layout: row            # single | block | row
    x_cm: 0                # relative to the bed
    y_cm: 0
    width_cm: 200
    length_cm: 25
    method: direct_sow     # indoor_sow | direct_sow | transplant
custom_plants: []
plant_overrides: {tomato: {spacing_cm: 60}}
rotation_history:
  - {bed_id: bed_1, season: 2025, family: Solanaceae, source: manual}
# tasks: [...]             # only when exported with tasks (include_tasks)
```

Import modes: **merge** (upsert by id, nothing deleted; the live season stays) or
**replace** (layout, per‑season plans and plantings replaced). What travels: zones, beds
(with their soil analyses; a file without them keeps the ones already stored), garden
elements, the per‑season plans, plans set aside, plantings, custom plants, **plant
overrides** and the rotation history, plus tasks when included. An older file without
`features` or `archived_plans` leaves those already stored alone. Files from older versions
are migrated automatically (storage version 1.8); unknown fields are ignored. References
are validated against the plan they belong to (a bed must point to a zone of its own plan,
a planting to an existing bed, also in the plans set aside); a field of the wrong type
(for example a `plant_overrides` that is not a mapping) refuses the whole file, and a refused file changes
nothing. Seasons that moved to the archive file are **not** part of an export.

Recipes, the shopping list, expenses, the journal and harvest log are not part of the plan
file; they live in the garden store.

---

## 6. Units, language, time

* Units are metric internally (cm, °C, mm, L). Sensors and forecasts in imperial units are
  converted on read.
* The panel, generated task titles, notifications, calendar events, handbook, plant names,
  recipes and Assist sentences are available in **English, Dutch and French**. Generated
  texts follow Home Assistant's language unless overridden under *Advanced* / *General*
  (auto / en / nl / fr); the panel follows your user language. Dates read day‑month‑year in
  the panel's language, with Belgian formats for Dutch and French (nl‑BE, fr‑BE).
* All dates are local (Home Assistant time zone). Forecast hours are handled as absolute
  instants, so DST transitions (23‑ or 25‑hour nights) never skew frost durations.

## 7. Performance

* No sensor polling – state‑change listeners on exactly the mapped entities, debounced
  10 s; the forecast is the only timed fetch (30 min). Once a day (and at start‑up) the
  climate history asks the recorder – and Open‑Meteo when it is switched on – for the days
  of the last month it did not cover; a failure there never stops an update.
* All computation is pure Python on in‑memory data (milliseconds for a typical garden),
  storage writes are debounced (5 s, system log 10 s) and never block the event loop.
* Seasons older than the last three move to the archive file, which keeps the garden file
  and every analysis run small after years of use (section 8).
* The panel is one JavaScript bundle (roughly 250 kB gzipped) cached with a content hash;
  the Lovelace card is a separate ~10 kB file. The panel gets a full snapshot over one
  websocket subscription that is refreshed after every update.

---

## 8. Seasons, year-end transition and archive

* **A plan per season.** The garden plan (zones, beds, elements) is saved per season; the
  plan of the *active* season (`layout_season`) is the live garden that entities, tasks and
  irrigation work with. Other seasons (last year's, next year's draft) are stored next to it.
  On the southern hemisphere a season runs July → June.
* **Nothing carries into a new year by itself** – not the plan, not perennials. Once the new
  year has started an Advice card and the toolbar button of the Garden plan and the Planner
  offer the **year‑end transition** (the button is available earlier too). Choose
  whether to copy the plan (and which zones and elements go along) or keep a plan already
  designed for next year; which perennials and which overwintering crops (garlic, winter
  leeks …) move over; and whether the new year becomes the active garden right away. The old
  year's plan stays as its own season; everything is in the system log and can be undone.
  A perennial belongs to its own season and to the seasons it was moved into
  (`last_season`); “gone from this season on” keeps the history.
* **Start over** with *Garden plan → Plans*: the current plan is set aside (inactive, with its
  beds and crops) and can be activated again or deleted.
* **Archive.** Seasons older than the current one and the two before it (three seasons are
  kept) move to `.storage/garden_manager.garden.archive`: their plantings and their garden
  plan. Crops still standing (a perennial carried into the current season) stay. It happens
  at start‑up and once per season in two steps: first the seasons are copied to the archive
  file; a season leaves the garden file only after the archive holding it has been read back
  from disk at a later start‑up, and only if it is unchanged since. Crop rotation keeps
  working (every archived planting leaves a rotation record), and the season report and the
  season book still open archived seasons, including crops carried over into them.

## 9. More than one garden

Add the integration again (Settings → Devices & services → Add integration → Hortulus) for
an allotment or a second plot. Each garden is its own config entry with its own data, store
files, devices and entities; the first garden keeps its data and entity ids exactly as they
were, further gardens are titled “Hortulus 2”, “Hortulus 3” … (rename freely).

* The panel shows a **garden switcher** in the top bar and remembers your choice per browser.
* Every service accepts `garden:` (the title or the entry id); without it the first garden is used.
* The tasks card takes `garden:`; the PDF endpoint takes `garden_id`.
* Websocket commands take `garden_id` (the entry id).
* Assist answers about the first garden.

## 10. Hortulus Web (optional website)

Hortulus Web is a website version of Hortulus that runs the same Python engine in the
browser (Pyodide). It is delivered separately and is not part of this integration; nothing
in Home Assistant depends on it. What the repository itself shows:

* The panel accepts extra settings from a host page: a list of allowed `tabs`, a `viewer`
  flag (read only) and a `web` flag. Home Assistant passes none of them.
* A **Garden** tab (a read‑only look at the plan: click a zone, bed, crop or element for its
  details, pick the year) and a restricted tab list let the website show a shared garden to
  visitors, only the parts its owner chose. A shared view whose tab list allows nothing
  shows no part of the garden.
* Cooking recipes can be marked **shared** (visible to whoever may see the garden) and mailed
  instead of sent to a phone.
* The website runs the integration's websocket handlers, operations and storage on its own
  stand‑ins for Home Assistant's modules, so the plan files described in
  [section 5](#5-import--export-format) can be exchanged between the two.

**Climate history on the website.** The website only computes while someone has the garden
open, so it cannot sample the weather all day. It fills the same climate history from
**Open‑Meteo's observed weather** for every garden and, for a garden linked to Home
Assistant, from **that Home Assistant's recorder** through the garden's token (the linked
sensors' daily minimum, maximum and mean). The engine merges both with the same rules as in
Home Assistant (`merge_history`, `merge_sensor_history`), so the Climate history card,
growth, water and disease work the same way there. Visitors of a shared garden do not see
the climate history card.
