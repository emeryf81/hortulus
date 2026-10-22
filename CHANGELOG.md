# Changelog

## 2.2.0 – 2026-10

### Added
- **Arrange the wall screen yourself** (Dutch for now). *Aanpassen* on the wall screen turns every
  block into a tile you drag into place (or move with ◀ ▶), make narrower or wider (− +) or remove.
  Eighteen blocks to choose from: clock, weather now, forecast, rain radar, today's tasks, the
  agenda for the coming week, soil moisture, watering, ready to harvest, sowing and planting this
  week, pests, your garden in numbers, sunrise and sunset, a weather saying, an organic gardening
  fact, the organic tip of the month, a recipe tip with what the garden gives now and a garden
  saying. Text scales with each block, so the whole wall stays on one screen. The layout is kept
  with the garden (new `wall/data` and `wall/layout` commands, administrators only for saving); in
  other languages the wall keeps its default blocks.

## 2.1.0 – 2026-10

### Added
New extras, again **on by default** and switchable under *Settings → Extras*:
- **Battery as a start signal.** Energy-aware watering also starts the morning run as soon as the
  home battery is (nearly) full: the surplus then goes to the grid anyway. Works with or without a
  surplus sensor, and still never waits past the latest time.
- **Rain water first.** A pump that draws from the rain water butt is used while the butt holds more than
  a set level. Below that the mains pump (or plain mains pressure) takes over. Without the fallback the run
  waits for rain, with one notification a day. Every run records where its water came from.
- **Pump energy.** With the pump power filled in, every run records its kWh. New sensor *Pump energy
  (this year)*, with rain and mains litres as attributes. The water card in the diary shows them too.
- **Frost heating in the greenhouse or cold frame.** A heater (switch or climate entity) goes on below
  a set temperature (zone air sensor) and off 1.5 °C above it. An optional weekly energy budget stops it
  once the budget is used up. New sensor *Greenhouse heating (this week)*.
- **Self-learning watering.** About 90 minutes after a run, the bed's moisture sensor shows how much water
  really soaked in. After two runs the bed gets its own factor, so sandy or sloping beds get more water and
  heavy soil gets less. The water balance is credited with what soaked in, not with what ran off.
  The learned factor is shown per bed and can be reset.
- **Harvest expectations from your own years.** Your own kg/m² now weigh in against the book value, which
  counts as one extra season. The harvest start follows when your first harvests really came, at most a
  month earlier or later.
- **Photo diagnosis.** Under a diary photo, *What is wrong here?* asks Home Assistant's AI task, either your
  own or the preferred one. The AI chooses from the pests and diseases Hortulus knows, the crop's own ones
  first, and the answer comes with Hortulus' organic advice. One tap notes it in the diary as a problem.
- **German.** The integration, the panel, the notifications, the handbook and the plant data are now also
  available in German (Deutsch), next to English, Dutch and French.
- **Tasks in your own calendar.** The coming tasks (7 days by default) are copied into another calendar,
  for example Google or CalDAV, each task once.

### Improved
- **Accessibility.** The panel passes an automated WCAG 2.1 AA check (axe-core) on every tab, in light and
  dark. Contrast of warning and error chips, rain figures and links is fixed, tab buttons announce
  correctly, table drop-downs have names, and the calendar month reads as a list of days. CI now runs the
  check on every change.
- **CI on the oldest supported Home Assistant (2025.10)** next to the current release.
- What Hortulus measures and learns itself (flow from the meter, water factor, heater energy) is no longer
  undone when a planner draft that was opened earlier is saved.

## 2.0.0 – 2026-10

### Added
Optional extras, every one **on by default** and switched under *Settings → Extras*:
- **Changing garden sayings.** A small database of sayings about the garden, the kitchen
  garden, being outdoors, healthy vegetables, harvest, rest days, the weather and each season
  (English, Dutch, French). The daily digest, the weekly plan, the monthly weather message,
  the season report, the season book, the dashboard and the dashboard card each pick their own
  line every day, so no two reports read the same.
- **Soil temperature without a sensor.** Beds without a soil probe get a soil temperature
  estimated from the logged air (the soil follows the daily mean with a lag), used for sowing
  advice and shown on the bed card.
- **Water forecast.** Per bed: when it will be dry again with the forecast's evaporation and
  rain ("dry again in 3 days").
- **Silent sensors.** A mapped sensor that has said nothing for two days gets one warning.
- **The month and the season in words, against last year:** warmer or colder, wetter or
  drier, sunnier, frost nights. At the top of the climate history, in the season report and
  the season book, and as a notification on the 1st of every month.
- **Your own frost dates.** Once two full measured years put the last or first frost a week
  or more off the region's dates, the climate history offers *Use my frost dates* (nothing
  changes until you press it).
- **Weather station import.** A CSV export from Netatmo, Ecowitt, Davis or a spreadsheet
  fills the climate history: header, separator, columns and units (°F, inches, mph, m/s) are
  recognised in English, Dutch and French; days Hortulus measured itself are kept.
- **Energy-aware watering.** With a solar surplus sensor, the automatic morning run waits
  until there is enough surplus, but never past a latest time.
- **Climate on the dashboard card:** the last 7 days against last year, rain, sun and a small
  temperature band (`climate: false` / `slogan: false` per card).
- **Releases:** a new version on main is tagged and published as a GitHub release with its
  changelog notes and the integration as a zip.

### Fixed
- The last reading of a day no longer spills a few minutes into the next day (a phantom day
  in imported or recorder history).

## 1.8.1 – 2026-10

### Fixed
- **Measured days stay measured.** Days logged before 1.8 count as the garden's own
  measurements, so Open-Meteo no longer overwrites them (a measured frost night stayed a frost
  night). A recorder day that covers the whole day now beats a day of own samples cut short.
- **One task per heatwave or dry spell** instead of a new one every day while it lasts, and the
  after-care after a storm or a downpour stays on the list for its three days (also the slug
  patrol the forecast announced when there is no rain gauge).
- **Units:** a rain gauge in inches books millimetres, a water meter in gallons or cubic feet
  books litres (no more 25× watering or 264× water use).
- **Reloads:** a reload during a watering run can no longer write the old garden over the saved
  one; the panel and the dashboard card keep updating after the options are saved; saving the
  same option again still applies it when the panel changed it in between.
- **Greenhouses:** a zone that becomes a greenhouse gets its greenhouse entities (advice, heat,
  shading), and loses them again when it is turned back.
- Monthly means only weigh days with a temperature; the weather-delay tip names what really
  caused the delay; forecast days and the climate chart no longer shift a day west of UTC or
  around the change to summer time; the rain radar tries again after a failed load; Open-Meteo
  is asked for Home Assistant's home (latitude and longitude together).

## 1.8.0 – 2026-10

### Added
- **Climate history: what the weather really did here.** Every update folds the outdoor
  sensors - or the weather entity - into the day: minimum, maximum and mean temperature,
  humidity, wind and gusts, rain, global radiation and sunshine hours. **Every mapped
  temperature sensor** (greenhouse air, soil, air at a bed) gets its own daily minimum, maximum
  and mean. Days leave the daily logs after two seasons (outdoor) or 400 days (sensors), but
  their months stay for good, so year-on-year statistics survive.
- **Filling the days nobody watched.** Once a day Hortulus fills gaps from Home Assistant's
  **recorder** (the same sensors, while Hortulus was not running) and, with *Use Open-Meteo*
  on, from Open-Meteo's **observed daily weather** (temperature, rain, wind and gusts,
  radiation, sunshine, humidity, FAO ET₀). Own samples always win; recorder history combines
  extremes; observed weather only fills what was not measured well.
- **Weather tab → Climate history.** A daily chart (temperature range, mean, rain) for 30 days,
  90 days or a year; the last 7 days, the last 30 days and the season so far with the same
  period last year next to it (mean, lowest, highest, rain and rain days, frost nights, hot days,
  sunshine, strongest wind, degree days, evaporation and the water balance); all-time records;
  a table of every temperature sensor (now, today, 7-day mean, 30-day range, record low and high,
  a sparkline); month by month with the change against last year; and the **measured frost
  dates** per year against the regional preset.
- **A weather station in the settings:** wind speed, wind gusts and solar radiation (W/m²) as
  outdoor sensors next to temperature, humidity, rain and light.
- **New sensors:** `sensor.hortulus_rain_7_days`, `sensor.hortulus_mean_temperature_7_days`,
  `sensor.hortulus_sunshine_7_days` and `sensor.hortulus_frost_nights_this_season`, each with
  last year's value as an attribute. Websocket command `garden_manager/climate/stats`.

### Changed
- **Growth follows the weather that happened, not only the forecast.** Greenhouse crops count
  the degree days of their own air sensor (or the outdoor day with greenhouse buffering), not a
  flat +3; logged heat days (last month) and a run of dull days hold back fruiting crops; crops
  without a degree-day model are held back by logged cold days below their minimum. The crop
  popup shows the delay and why.
- **The water balance uses Penman-Monteith on the logged day** - humidity, wind and sunshine or
  radiation - instead of only the minimum and maximum temperature; windy, sunny days dry beds
  faster, as they do.
- **Disease risk looks back too:** two humid, warm days that already happened (Hutton
  criteria from the logged days) mean high blight pressure; several wet days raise the level.
- **Sowing waits for warm soil, not a warm afternoon:** the soil temperature is the lower of the
  reading now and the mean of the last days' log.
- **After-care tasks for weather that happened:** a check after a storm (gusts ≥ 60 km/h), the
  slug patrol after a downpour (the same task the forecast would have made, never twice) and
  deep watering after a dry week; an alert when it froze and tender crops were outside.
- **Documentation rewritten for the whole application.** The README (English, Dutch and the new
  French edition) now describes every module of the panel with screenshots in all three
  languages; Configuration, Entities & services and the FAQ are brought up to date with the code
  and exist in English, Dutch and French; the architecture blueprint and the design system
  describe the current engine, panel and themes. `frontend/dev/screenshots.mjs` regenerates the
  screenshots from the dev harness, which now also builds a French snapshot.

## 1.7.1 – 2026-10

### Changed
- **Cooking: every fridge item gets its own idea, only where it fits.** What you tick under
  "use up from the fridge" is no longer just spooned on top of every dish. Each item has its own
  preparations per kind of dish, and which one a dish gets depends on its vegetables, so the
  ideas vary: yoghurt becomes a tzatziki-style sauce, a honey-mustard dip, a lemon-garlic bed
  under roast vegetables, a raita, a soy-ginger or curry dip, a creamy herb dressing or
  honey-cinnamon yoghurt with a crumble; feta is baked soft among the vegetables, whipped into a
  cream, melted through pasta or crumbled into a frittata; parmesan turns into crisps on soup or
  a crunchy crust; eggs are baked in hollows on the oven tray, stirred into a carbonara or
  poached on a salad; mustard becomes a mustard butter, onion a quick pickle, breadcrumbs a
  garlic-lemon pangrattato ... Fresh herbs from the garden (dill, parsley, chives, coriander)
  go into sauces when there are any.
  - A dish takes at most three things from the fridge, one sauce, one dressing and one crunchy
    topping; never two cheeses on top of each other or two creams; a pan sauce only with meat or
    fish. Each step sits at the right moment in the method.

### Added
- **Cooking: 36 new dishes and complete menus**, collected from home-cooking sources on the seasonal
  kitchen garden (the methods are written out in our own words, in Dutch, English and French):
  - soups: roasted velouté, minestrone, green soup (peas, spinach, courgette ...), chowder;
  - starters: courgette and vegetable fritters, carpaccio, crunchy remoulade, tabbouleh, caprese,
    caponata, asparagus the Flemish way, warm vinaigrette (leek, beetroot ...), corn on the cob with
    herb butter;
  - main courses: ratatouille, Provençal tian, shakshuka, tart, gnudi, braised peas and beans,
    waterzooi (chicken, fish or vegetables), vegetable steaks with tahini sauce, stuffed cabbage rolls;
  - desserts: clafoutis, fools, sorbet, panna cotta, vegetable cakes (carrot, courgette, beetroot,
    pumpkin ...), baked fruit with honey, berry cream cups;
  - **a chapter "Preserving & pickles"** for the surplus: quick pickles, chutney, passata, pesto
    cubes, jam, blanching and freezing, sauerkraut (amounts are a batch, not one plate).
  Dishes made for certain plants only take those plants (no tomato cake), and each dish only gets
  the protein that suits it; some take it in their own way (chicken poached in the waterzooi,
  ham next to the asparagus).
- **Menus**: a soup or starter, a main course and a dessert that belong together, built from what
  is ready to pick – themed ones of the season (a Provençal garden dinner, a Sicilian evening,
  Levantine mezze, courgette glut, a Flemish spring menu, a winter comfort menu ...) and menus around a
  main course. One click puts all three dishes on the shopping list or in your cookbook.
- **Cooking: chapters.** Ideas, your cookbook and the cookbook PDF are split into Soups, Starters,
  Main courses and Desserts (a chapter page each in the PDF, a chapter filter in the cookbook). Ideas
  are spread over the chapters so none is crowded out. New dishes to fill them: chilled soup
  (gazpacho-style, from tomatoes, peppers and cucumber), crostini as a starter and a warm fruit
  compote; a salad without meat or fish and pesto on bread count as starters.
- **Light or dark** next to the colour theme: automatic (follows Home Assistant or the device),
  always light or always dark. In Home Assistant the choice follows your user to every device.
- **Cooking: your own version of a recipe.** "Edit" in a recipe adds, removes or changes
  ingredients (name, amount, unit, from the garden / at home / to buy) and adds, removes,
  rewrites or reorders the steps. Your version goes into your cookbook, the shopping list and
  the PDFs follow it, and "Back to the original" restores the generated recipe.

### Fixed
- **Whole-repository review (22 findings):**
  - **Food safety:** elderberries and beans (also chickpeas, edamame) are never offered raw or half-cooked
    (no elderberry sorbet, no raw-bean salad); a dish also refuses them when the spec is written by hand.
  - **Permissions:** exporting a shopping list or the seeds to a to-do list follows the user's own rights.
  - **Imports:** a refused plan file changes nothing (it used to wipe the live plan before failing on a
    bad `plant_overrides`); plans set aside now travel with an export and an import.
  - **Input checks:** NaN and infinity are refused for sizes, positions and harvest weights; a refused
    task change changes nothing; a custom plant a set-aside plan still needs cannot be deleted; autofill
    skips a bed too narrow for its margins.
  - **Watering:** a valve that stays closed ends the run and books no water, also without a pump; a
    valve that goes silent for a minute while the pump runs ends the run and stops the pump.
  - **Tasks:** a title or description you rewrote is kept when tasks are recalculated.
  - **Cooking:** a dish needs its main ingredient, not just herbs (no caprese of basil alone); more
    suitable vegetables no longer remove ratatouille or a tian; risotto, pasta, stoemp and stuffed
    vegetables keep their rice, pasta or potatoes (also for "no side"), and rice or potatoes are no longer
    cooked twice; dry lentils get a cooking step; honey, mustard and other things a fridge preparation
    needs join the ingredients and the shopping list; your own quantities stay as typed (1 g saffron stays
    1 g); new ingredients of different recipes no longer merge on a shopping list; the recipe editor
    refuses (and stops offering) more than 40 ingredients or 30 steps instead of cutting them off; a
    cookbook of more than 60 recipes prints in full (up to 200, with a message beyond that) and a long
    recipe continues on another page; a shopping-list reload can no longer bring back recipes you removed.
- **Second review round:** the garden's mint now reaches tzatziki and raita (the sauce herbs listed a
  plant id that does not exist); a green soup no longer takes shelling beans (borlotti, runner beans),
  which need far longer than its few minutes; garlic, lemon or vinegar a fridge preparation names joins
  the ingredients and the shopping list; a long step or ingredient that would run off the page moves to
  the next one whole; renaming an ingredient in your own version gives it a new identity (no merge with
  another recipe's row on the shopping list); an import with a present but wrongly typed `archived_plans`
  or `plant_overrides` is refused instead of ignored; a colour choice made while your saved choice is
  still loading is saved as a pair, and quick successive choices are sent one after the other.
- **Colour themes on iPhone (Home Assistant app, Safari):** the theme and the dark palette are now
  set as inline colours on the panel instead of `:host([theme])` rules, so they take effect at once
  in every browser; the dashboard no longer uses `:host-context`, which Safari does not support.
- **Cooking:** what you take from the fridge, and what you tick as always at home, shows as
  "at home" instead of "to buy", also before you save your choices.

## 1.7.0 – 2026-10

### Added
- **Cooking** (new menu place): a seasonal cookbook from what the garden gives right now.
  Hortulus looks at the crops that are ready to pick (plus anything you add from the cellar)
  and proposes dishes for them – soup, oven tray, stir-fry, pasta, risotto, salad, gratin,
  stew or curry, frittata, stoemp, stuffed vegetables, a plate with meat and fries, pesto and
  a fruit crumble. Lettuce, cucumber and radish only go in salads.
  - Tick what is in the fridge to use up, the meat or fish you like (chicken, chicken mince,
    beef, steak, stewing beef, pork, pork tenderloin, mince, burger, sweetbreads, sausage,
    bacon, ham, salmon, white fish, prawns – or tofu, chickpeas, lentils, egg, halloumi,
    goat's cheese) and the side: pasta, rice, bulgur, couscous, pearl couscous, gnocchi,
    potatoes, fries, bread or noodles. Every recipe can change its side, meat and servings.
  - Each dish gets a picture: the crops on a plate (or in a bowl, or an oven dish) with the
    side underneath and the meat in the middle.
  - Recipes in Dutch, French and English, with quantities per person, what comes from the
    garden and what to buy.
  - Your own cookbook: keep recipes, mark favourites, add notes, note when you cooked them.
  - One shopping list for the dishes you pick: print it, save it as PDF, send it to your
    phone or put it on a Home Assistant to-do list. A recipe, a whole cookbook or the list
    as PDF (with the dish pictures).
  - On the Hortulus website a recipe can be shared: whoever may see your garden sees it.

- **Look at a garden**: a read-only view of the plan alone (click a zone, bed, crop or element
  for its details, pick the year). The Hortulus website shows it to visitors without an account.

### Fixed (whole-code review)
- Services that change the plan, plant data or hardware need an administrator, like their
  websocket commands.
- Stop and Close end a running valve test; a run that is cancelled or fails during start-up
  stops the pump before any valve closes.
- Frost lockout looks at the next 12 hours on its own, so a colder night later in the forecast
  no longer hides tonight's frost.
- Impossible settings (a frost date of 13-01, a time of 25:00) are refused instead of breaking
  every calculation after a restart.
- A planner save goes to the garden it was made for, one request at a time; a draft opened
  before the first harvest no longer undoes it or reopens a finished crop.
- Archive pruning keeps edits made after a season was copied to the archive.
- Plant customisations add up (also per language) and keep extra sowing windows.
- Import accepts plantings of older seasons and brings back exported tasks; each bed is
  checked against its own plan.
- Deleting a plan set aside can be undone (also expenses and the cookbook are in the system log).
- A watering task ticked twice books its water once; water given on a day without
  temperatures still counts; crops of earlier seasons never ticked out stop counting as standing.
- A greenhouse vent or shade command that failed is tried again at the next update.
- null for a required field is refused; a soil test without a date is refused.
- A shared view whose tab list allows nothing shows no part of the garden; the narrow-screen
  Settings button follows the list too.
- A garden document whose empty objects came back as empty lists (PHP) loads again.

## 1.6.1 – 2026-10

### Added
- The panel can show a subset of its tabs (`panel.config.tabs`). The Hortulus website uses it
  to let visitors look around a garden its owner shares (read only, only the parts the owner
  chose); in Home Assistant nothing changes.

## 1.6.0 – 2026-10

### Added
- **Planner in five steps**: site, growing zones, beds, perennials, annuals. Each item can
  only be selected, moved and edited in its own step (the rest is dimmed and locked);
  tooltips explain every step. One click selects, a second click (or *Details*, or Enter)
  opens the details.
- **New season: what do you keep?** Keep everything (all elements, zones and perennials) or
  tick per element, zone and perennial.
- **Overlap**: a house, path, driveway, hedge or growing zone on a lawn (or terrace,
  border ...) takes that area away from it – on the map, in the print and in the m² shown.
  A tree or shrub does not.
- **Ecological gardening and permaculture** (recommended, never required; *Settings →
  Ecological tips*): an organic answer with every pest warning and disease check (nettle
  extract, horsetail tea, trap crops, natural enemies), work for a living garden in the
  calendar (flower strip, horsetail tea, no-dig mulch, wild corner, insect hotel, drinking
  dish), an eco tip of the month, mixed-bed advice and two new handbook chapters.
- **Food forest**: a new zone type, built in seven layers; the advice shows which layers are
  still missing and suggests plants. An orchard with trees is invited to grow into one.
- **Entity drop-downs** in the settings: every field (valve, pump, sensors, weather, TTS,
  speakers, notify services, vent, shade, water meter) lists only the entities that fit.

### Fixed
- Export → import of a plan now brings the site elements and the season layouts along,
  not only the zones.
- The *more* menu in the Garden Planner toolbar stays on the same row.
- Frost blueprint: two automations on different lamps no longer overwrite each other's
  saved state.

## 1.5.0 – 2026-10

### Added
- **Français**: the whole integration in French – panel, tasks and notifications, season
  book, handbook and glossary, plant names and tips, Assist sentences, the Home Assistant
  screens and the tasks card. Dates and numbers in Belgian formats (fr-BE, nl-BE).
- **Pest calendar**: when carrot fly, cabbage root fly, cabbage white, onion fly, leek
  moth, aphids, flea beetle, Colorado beetle and others fly, from this season's
  degree-days (calendar months while the climate log is still short), and slugs after a
  mild, damp spell. Only for crops that are (or soon will be) in the ground. Tasks to put
  insect mesh on a few days before a flight, weekly checks, an evening slug round, and a
  card on the dashboard.
- **Kitchen** (*Journal → Kitchen*): crops ready to pick with how to keep them, a surplus
  warning with ideas to store, preserve or share, and **cost and harvest**: the harvest at
  shop prices against your expenses and garden water. Own prices per crop and the water
  price under *Settings → Costs*; the season book shows what the garden gave.
- **Moisture sensors teach the model**: once a day the water balance is set from the
  sensor and each bed learns how fast it really dries out, so the advice stays right on
  days the sensor is offline.
- **Blueprints**: frost warning on a lamp (which returns to how it was), log a harvest with
  a button or an NFC tag, water a dry bed at a good moment, announce urgent garden jobs –
  import links in the README. `run_irrigation_plan` gets `only_if_needed`: an automation
  chooses the moment, Hortulus still decides whether the bed needs water.
- **Starter garden**: an empty garden shows a welcome screen – lay out a ready-made garden
  (2–4 raised beds, a herb pot, optionally a greenhouse, with a first plan), draw your own
  or read the handbook first.
- **Archive**: seasons older than the last three move to a separate file (crop rotation
  still knows them), which keeps the garden fast after years of use. A season leaves the
  garden file only after the archive holding it has been read back from disk. The season
  report and season book still open archived seasons, including crops carried over into them.

### Changed
- The season book preview only measures photos after the pages it shows; the weather tab
  ignores late forecasts of a replaced entity; the crop timeline groups by bed, not name.

## 1.4.0 – 2026-10

### Added
- **Season book** (*Print → Season book*, or *Season book (PDF)* in the season report): the
  whole garden year as a book to print – cover, epigraph, title page, the season's garden
  plan, contents with page numbers, an introduction written from the season's own figures,
  one chapter per month (what was sown, planted and done, the journal with your own photos,
  the harvest, water and weather), the year in numbers, a glossary, colophon and back cover.
  A5 by default, chapters open on a right-hand page, the page count is a multiple of four
  (folds into signatures), bookmarks per chapter; Dutch and English. The PDF writer gained
  Times, justified text, embedded JPEG photos and outlines.
- **More than one garden**: add Hortulus again for an allotment or a second plot. Each
  garden has its own data; the panel shows a garden switcher, every service accepts
  `garden:` (title or entry id), the tasks card `garden:`. The first garden keeps its data
  exactly as it was.
- **Water meter**: litres booked per run come from the meter, each bed learns its real
  flow (used when no flow is entered), and water counted for 15 minutes while every valve
  is closed is reported as a **leak** (banner, notification; can be turned off).
- **Valves with their own timer** (*Settings → Beds → Valve timer*): longer runs are split
  into openings that stay inside it; a valve that shuts by itself mid-run ends the run,
  books the real time and is reported.
- **Buttons on phone notifications** (companion app): *Done* and *Tomorrow* on the digest
  and reminders, *Water now* when beds need water, *Close valve* on a valve left open.
- **Quick harvest** on the dashboard: the crops that can be picked now, add the weight with
  big buttons, save. `log_harvest` accepts a plant **name** (`plant: Tomaat`) and finds the
  crop in the garden – handy for an NFC tag or a dashboard button.
- **Photo timeline** per crop and bed (in their popups) and *Your photos* in a plant's
  details: from the first picture to the last ("day 1", "day 40"), with a viewer.
- **Seeds to buy**: the seed list shows how many to buy and puts what is missing on a
  Home Assistant to-do list (e.g. the shopping list) in one click, without duplicates.
- **Tasks card**: watering today, a run in progress, a valve left open (with *Close*) and
  leaks.
- **Weather tab**: the weather now, a 24-hour chart (temperature over rain), the coming ten
  days with a temperature range bar and frost / heat tags, what it means for the garden
  (frost nights, hot days, rain so watering can wait, a dry spell, beds that need water) and a
  **rain radar** – a radar camera from Home Assistant when there is one (e.g. Buienradar),
  else Buienradar's public map for the Netherlands or Belgium, refreshed every 5 minutes.
- **A calmer menu**: seven places instead of thirteen tabs – *Today*, *Garden* (Planner,
  Garden plan, Crops), *Calendar*, *Weather*, *Journal*, *Knowledge* (Plants, Advice,
  Handbook) and *Manage* (Analysis, Print, Settings), with the tabs of a place in a row
  underneath; a place reopens on the tab you used last. Links and URLs stay the same.
- **Colour themes** (*Settings → Display*, per browser): classic green, earth, night (always
  dark), or one that follows the season.
- **Hortulus' own icons**: one hand-drawn line set for the menu and every task type.
- **Crops → Timeline**: the year per bed as bars (raising, growing, harvest) with a today line;
  drag a planned crop sideways to move its sowing and planting out.
- **Harvest over the years** (*Journal → Harvest*): the total per season with the best year in
  gold, and per crop a row of bars so good and bad years stand out (`harvest_years` in the
  records overview).
- **Wall screen** (*Today → Wall screen*, or `/hortulus/wall`): a calm, large kiosk view for a
  tablet – the time, the weather, today's tasks with big tick-boxes, the beds' moisture and
  alerts; no menus, dims at night.
- **Garden map**: beds cast a soft shadow, richer soil, timber edges on raised beds, a faint
  ground grain; crops are drawn smaller after planting and grow to full size by harvest for
  the date shown.
- **A burst of leaves** when a task is ticked off or a harvest saved (off with *reduce motion*).
- **A new look**: serif display type (the same voice as the season book), a dashboard hero in
  the colours of the season with botanical line art and stat tiles, a glass app bar, softer
  depth, refined buttons, alerts, tables and weather tiles, views that fade in, a skeleton
  while loading; all motion off with *reduce motion*. Dark theme tuned throughout.
- **Valve test** (*Settings*, next to every bed valve): opens it for 5 s with the pump in the
  safe order (the pump only after the valve reports open, never on its own) and checks it
  reports open and closed again. Websocket `irrigation/test`.
- **Valve left open**: after every run Hortulus checks the valve reports closed; a valve or
  the pump open far longer than any run (max runtime + 10 min) while Hortulus is not
  watering is reported – system log, notification, and a red banner on the dashboard with
  *Close valve* (`irrigation/close`).
- **Watering per bed** (*Journal → Water*, planner bed popup): soil moisture from Home
  Assistant's history, water given from Hortulus' log and rain from the rain sensor, for
  7, 14 or 30 days.
- **Crops tab: sowing plan, seeds, succession, harvest forecast** – what to sow, plant out
  and harvest week by week (*Done* fills in today's date); seeds the plan needs against the
  seed stock; beds that free up this season and what can follow there; expected kg per
  week. New engine module `planning`, websocket `planning`.
- **Crops on a phone**: one card per crop with the next date to fill in.
- **Quick note with photo** in the planner and crops popups (camera on a phone); the last
  notes about that crop or bed are shown below it.
- **Season report** (*Journal → Season report*, and in the year-end transition): crops,
  harvest against expectation, failures, problems from the journal, water; download as
  Markdown. Websocket `report/season`.
- **Why (not) here?** in the planner popup: per crop, why its bed does or does not suit it
  and which beds would; right after dropping a crop where it does not belong a warning
  says why.
- **Links between planner and crops list**: *Show on map* from the crops list (and from
  the analysis) opens the planner with that crop selected; *In Crops* from the planner
  highlights its row.
- **Crops list: several at once** – tick crops and set a status or a date for all of them
  (one system-log entry). Websocket `plantings/update_many`.
- **One popup everywhere** (`hl-modal`): same header, close button, backdrop click and
  Escape; previous/next with the arrow keys in the plant library and crops list. A plant's
  details open from the dashboard, calendar, advice, journal, planner and crops list, and
  show where it grows in your garden.
- **Compare plans** (*Analysis → Compare*, and *Garden plan → Plans → Compare*): zones,
  beds, elements and crops added, removed or changed between two plans. Websocket
  `plan/compare`.
- **Crop rotation strip** per bed in the planner: plant families of the last five years.
- **End of season banner** in the planner: what can still be sown or planted, with a
  jump to next year's plan. Websocket `analysis/still_possible`.
- **Analysis badge** on the tab with the number of problems, re-checked on every change
  (snapshot `diagnosis`); **one-click repairs** (copy a missing plan, put crops back on
  the plan or into their bed, move a bed into its zone, carry a forgotten perennial),
  logged and undoable – websocket `analysis/fix`; **export the diagnosis** as one JSON
  file to attach to a bug report.
- **Click-through UI test** in CI (Playwright, `npm run test:ui`).
- **Start over with a new plan** (*Garden plan → Plans*): from scratch, with the same zones
  but empty, or with zones and beds but no crops. The current plan becomes **inactive** and is
  kept with its beds and crops; activate it again later (swapping places with the active one)
  or delete it. Websocket `plan/new`, `plan/activate`, `plan/delete`.
- **Analysis** tab: *Check* explains inconsistencies (a year with crops but no plan, crops
  whose bed is not on their season's plan, beds outside their zone, overlapping or late crops,
  a missed year-end transition …) with a link to the right place; *Why not?* shows per bed why
  a plant does or does not fit; *Errors* lists every refused action with its reason (refused
  actions are now written to the system log); *System log* is the journal's log. Websocket
  `analysis`, `analysis/explain`.
- **Crops** tab: every crop of a season on one list, with method, status, count, notes and
  planned/actual dates editable in place – nothing to drag. Websocket `plantings/season`,
  `planting/update`.
- Plant icons on dashboard tasks and crop avatars, calendar tasks, the planner's details
  popup, the crops list and the analysis.
- **Garden plan per year** (new tab *Garden plan*): shape the garden without plants – zones
  (open ground, greenhouse, cold frame, planters & pots, orchard …), beds and elements
  (driveway, house, water butt, hedge, lawn, shed, paths – also inside the greenhouse). The
  plan is saved for one season; the *Planner* now only plants, on that season's plan (zones,
  beds and elements are locked there). A season without a plan offers to copy another year's
  or start empty.
- **Year-end transition** (button in Garden plan and Planner, and an advice card once the new
  year has started): **nothing carries into a new year by itself** – not the plan, not
  perennials. Choose which zones and elements go along (or keep the plan already designed for
  next year), which perennials and which overwintering crops (garlic, winter leeks …) move
  over, and whether the new year becomes the active garden right away. The old year's plan is
  archived; everything is in the system log and can be undone. Websocket `year/preview`,
  `year/apply`, `layout/delete`; `plan/save` takes a `season`.
- **System log** (Journal tab → *System log*): every change to the garden – from the panel,
  actions/automations, and what Hortulus adjusts itself (generated tasks, clean-up) – with
  time, who and what. **Every entry can be undone**; an item that was changed again since is
  only overwritten after confirmation, and an undo that would leave a planting without its
  bed is refused. The undo is logged too, so it can be reverted (redo). Kept in its own store
  (`garden_manager.garden.syslog`, last 500 entries); websocket `syslog/list`, `syslog/undo`.

- **Lay out the whole garden**: paths in **stone**, **wood**, **stepping stones** and **bark**
  (the old path is now *gravel path*), **decking**, **wall**, **carport / garage**, **shrub**,
  **swimming pool** and **seating area**, next to house, terrace, lawn, hedge … Elements are
  grouped (buildings & paving, paths, green, outdoor living) and **all** of them can now be
  drawn from a zone's own map too, not only six.
- Zone types **Ornamental garden** and **Planters & pots**; a **Planter / pot** tool draws a
  container bed (potting mix) you can plant like any bed.
- Planner toolbar button **Site & elements** jumps back to drawing the site from any step
  (the planner opens on *Plant* once there are crops, which hid the drawing tools).

- **Pictures everywhere**: every plant in the library has a picture (card and detail), as do
  advice suggestions and answers, and every handbook chapter has an illustrated garden scene
  (overview tiles and chapter header). Pictures are illustrations built from the plant
  stickers, so they work offline; on top of that the browser shows a **photo from
  Wikipedia**, looked up by scientific name (Settings → *Display*, per browser, on by default;
  cached for 30 days). Only photos under a licence Hortulus can honour (CC BY, CC BY-SA, CC0,
  public domain) are shown, credited with creator and licence and linked to the file page;
  small round thumbnails always use the illustration.

### Changed
- Date fields in the harvest form, new task and postpone-to-date also read day-month-year.
- *What can still go in* is sorted alphabetically in your language.
- Dates read day-month-year in the panel's language (13-04-2026) whatever the browser's
  locale; the calendar button still opens the browser's date picker.
- The pump (and bed valve) picker also lists `valve.*` and `input_boolean.*` entities, e.g.
  a smart garden tap.
- **Plants**: a plant's details open in a popup instead of a side panel; good and bad
  neighbours show their icon and open that plant when clicked.
- **Planner**: larger map at a fixed height; clicking a bed, crop or element opens its details
  in a popup instead of a side column.
- **Autofill** says per plant why it was not placed (too late, zone type, glass, frost,
  rotation, bad neighbour, no room) and offers to fill the next season; it uses the plan of
  the season it fills (or the latest earlier plan, copied on apply).
- **Perennials no longer stay in the plan automatically**: a planting belongs to its own season
  and to the seasons it was moved into at a year-end transition (`last_season`). On upgrade,
  perennials growing now are kept for the current season once. Storage version 1.6.
- Printouts use the garden plan of the chosen season.

### Fixed
- Crops list and planning re-anchor perennials carried into a year on that year (an apple
  tree planted in 2022 no longer shows as overdue for planting out).
- Autofill could hardly assign anything for another season: it proposed on today's beds, and
  applying refused beds of next year's plan as "unknown bed".
- Beds in orchards, herb, flower and the new garden zones now use the outdoor sensors (only
  greenhouses and cold frames have their own climate).
- **Companion check showed crops that are not in the plan you look at.** The planner also
  checks the previous and next season (for overwintering crops), but a crop added to this
  season after its sowing window was moved forward to "today" and so ran into next season,
  clashing with next season's plan – e.g. a chili added in October produced "Tomato and Chili
  pepper overlap", shading and "good neighbours" messages about a tomato and basil of next
  year's example plan. Crops of different seasons are now compared on their *planned* dates,
  and a finding that does involve another season names it ("Tomato (season 2027)").

## 1.3.0 – 2026-10

### Added
- **Journal tab**: garden diary with photos per bed, crop or the whole garden; harvest log in
  kg and pieces (also when ticking off a harvest task and from the planner) with totals per
  crop and **learned yields** (your own kg/m², used by Autofill); **seed box** with use-by
  years per family and the crops in the plan that still need seed (the shopping list skips
  seed you have); **water** use per day/week from a garden water meter and the rain butt level.
- **Year view** in the calendar (crop × month: sow indoors, sow, plant out, growing,
  harvest, plus tasks and hours per month) and a **year plan** printout (`document: year`).
- **Lovelace card** `custom:hortulus-tasks-card`: today's and overdue tasks with a tick box,
  loaded automatically on every dashboard.
- **Household**: assign tasks to people (`person.*`), automatic assignment by default and per
  task type, personal notify service per person for the digest and overdue reminders.
- **Soil analysis per bed** (pH, organic matter, P, K, Mg, lime): fertiliser plan, lime advice
  and shopping list follow the latest analysis.
- **Voice**: six Assist intents (tasks today, overdue, harvest, greenhouse, water, frost) with
  English and Dutch sentences, installed with one click.
- **Rain water first**: watering tasks say how many litres are still in the butts.
- Sensors *Harvest this season*, *Garden water (7 days)*, *Rain water available*.
- Actions `log_harvest`, `add_journal_entry`, `assign_task`, `save_soil_test`,
  `install_voice_sentences`; websocket `records/*`.

### Changed
- PDF exports are private: written to `/config/hortulus/exports/` and served through an
  authenticated view with a signed link valid for 7 days.

### Known limitations
- One garden per Home Assistant: the panel shows the first config entry. Use zones for a
  second plot. (Lifted in 1.4.0.)

## 1.2.0 – 2026-10

### Added
- **Garden plan in three steps**: draw zones and elements by dragging on the 10 cm grid,
  arrange every zone on its own map (double‑click a zone), then plant by hand or with
  Autofill. New zone types orchard, soft fruit, herb and flower garden; new elements house,
  driveway, street, parking, terrace, lawn, flower bed, fence, pond, play area, beehive.
- **Plant icons**: 45 vector icons coloured per crop instead of dots; dense crops are drawn
  as rows of seedlings with one large icon and a name label; legend for badges.
- **Perennials across seasons**: trees, bushes and perennial herbs carry over every year
  (`removed_season` for explicit removal) with season‑keyed yearly care; harvest tasks only
  once a tree bears (`years_to_bearing`).
- **Plant database 232 crops**: 92 new plants – fruit trees, soft, cane and vine fruit, more
  vegetables, herbs, flowers and green manures – plus icon, colour, emoji, pollination,
  harvest windows and eco tips for every plant.
- **Advice tab**: Q&A sentence builder (subject › target › question/problem) with live status,
  causes, actions, home remedies and prevention; garden suggestions (pollination partners,
  pollinator flowers, bad neighbours, shading, harvest gaps, empty beds, ecology) with
  one‑click apply; harvest per month; seasonal shopping list; tools per job.
- **Tasks**: 21 new yearly maintenance rules (greenhouse windows, biocontrol, nettle and
  comfrey feed, gutters, nest boxes, seed saving, orchard care …), weather episodes (heat,
  dry spell, storm, heavy rain), weather‑aware rescheduling, tools in the task dialog,
  new task types (protect, clean, tie in, thin fruit, pollinate, check, make feed).
- **Reminders**: evening reminder of overdue tasks with a verdict (still possible / too late /
  do now) and a weekly look‑ahead; times configurable in Settings.
- **Autofill preferences**: freedom of choice, respect neighbours, add pollinators, aim for
  year‑round harvests, perennials allowed, respect the zone type.
- **Handbook**: chapters on fruit, tools & materials, home remedies, year‑round harvest and
  choosing sensors; new glossary terms.
- **Websocket API**: `advice`, `qa/options`, `qa/ask`, `supplies`.

## 1.1.0 – 2026-10

### Added
- **Print module**: garden map, greenhouse/zone map, bed sheets, checklist, season chart,
  blank planning sheet and plant cards as PDF (dependency‑free writer) with live SVG
  preview. Paper A4, A3, A5, Letter and **reMarkable Paper Pro** (toolbar margin,
  portrait/landscape); colour, e‑ink and grayscale modes with hatch patterns per plant
  family, legend, scale bar, north arrow and dot‑grid notes areas.
  Service `export_pdf`, authenticated download at `/api/garden_manager/print`.
- **Handbook**: 16 chapters in English and Dutch, search, glossary, and ⓘ tooltips
  throughout the panel.
- **Autofill**: season proposal from beds, household, time, water and compost
  (service `autofill_plan`, planner dialog).
- **Seasonal calendar**: soil preparation with compost amounts, greenhouse spring and
  autumn clean, shading on/off, winter insulation, winter rest and covers, green manure,
  compost, mulch, soil test, tool care, perennial care (cut back, divide, protect).
- **Plant database**: 140 crops (69 vegetables, 60 herbs, fruit, companion flowers) with
  Kc per stage, N‑P‑K demand, height, root depth, yield and plants per person
  (generated by `scripts/build_plantdb.py`).
- **Agronomy**: FAO‑56 Penman‑Monteith ET₀ with Hargreaves fallback, stage Kc, daily
  root‑zone water balance, phenology with degree‑day harvest estimates, disease risk
  (Hutton, leaf wetness, greenhouse humidity), nutrient balance index from NPK/EC probes,
  feed doses in tasks.
- **Companion factors**: pest deterrence and trap crops, allelopathy, nutrient
  competition, hemisphere‑aware shading; better‑neighbour suggestions and alternative
  beds for rotation conflicts; family‑level relations.
- **Hardware**: irrigation controller (pump interlock, max runtime, frost lockout, rain
  skip, guaranteed shut‑off, run log), greenhouse vent and shade control with a shading
  mode per zone, optional Open‑Meteo enrichment.
- **Entities**: ET₀ and degree days today, nutrient balance and water deficit per bed,
  disease risk, degree days and frost risk per zone, irrigation lockout/running, irrigation
  mode select, shading select, automatic‑irrigation switch, irrigation limits as numbers,
  water now / stop buttons.
- **Services**: `add_planting`, `update_planting`, `remove_planting`,
  `run_irrigation_plan`, `stop_irrigation`, `set_shading_mode`, `autofill_plan`,
  `export_pdf`. Event `garden_manager_irrigation_run`.
- **Panel**: Handbook and Print tabs, season timeline, multi‑select with align and
  distribute, paths and garden elements, layers, habit‑shaped plant symbols, phenology in
  the inspector, swipe actions on tasks, live sensor context in the task dialog,
  water & climate card, extended settings.

### Changed
- Storage schema 1.5 (garden elements, water balance, irrigation log, irrigation and
  resource settings); migrated automatically.

## 1.0.0 – 2026-10

First release: planner, plant database, task engine, frost/greenhouse/irrigation advice,
calendar, to‑do list, notifications, EN/NL.
