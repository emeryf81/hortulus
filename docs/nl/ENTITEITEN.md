# Entiteiten, diensten en events

De entity‑id's hieronder gaan uit van een **Engelstalige** Home Assistant‑installatie en de
voorbeeldtuin (*Bed 1*, *Greenhouse Zone A*). Home Assistant leidt entity‑id's af van de
vertaalde entiteitsnaam en de apparaatnaam op het moment dat een entiteit voor het eerst wordt
aangemaakt. Op een Nederlandstalige installatie wordt `sensor.hortulus_frost_risk_next_48h`
dus `sensor.hortulus_vorstrisico_komende_48_uur`. Unieke id's veranderen nooit; hernoem gerust.
Een tweede tuin ([meerdere tuinen](CONFIGURATIE.md#9-meerdere-tuinen)) krijgt eigen apparaten en
entiteiten; haar item heet “Hortulus 2”, dus haar tuinbrede id's beginnen met `sensor.hortulus_2_`.

## Apparaten

| Apparaat | Aangemaakt voor | Bevat |
|---|---|---|
| **Hortulus** | de integratie | tuinbrede sensoren, kalender, takenlijst, knoppen, bewateringsbediening |
| **<Bednaam>** | elk bed | vocht, bewatering, buurplantenscore, heeft water nodig, voedingsbalans, watertekort |
| **<Zonenaam>** | elke zone | ziekterisico, vorstrisico 48u, graaddagen; kassen en koude bakken ook advies, hittestress, schaduw |

Bedden en zones die je in de planner toevoegt, krijgen meteen hun apparaten; als je een bed of
zone verwijdert, verdwijnen ook zijn apparaat en entiteiten.

Overzicht van de Nederlandse namen (zoals Home Assistant ze toont op een Nederlandstalige
installatie):

| Engels systeem | Nederlands systeem |
|---|---|
| `sensor.hortulus_frost_risk_next_48h` | `sensor.hortulus_vorstrisico_komende_48_uur` |
| `binary_sensor.hortulus_frost_warning` | `binary_sensor.hortulus_vorstwaarschuwing` |
| `sensor.hortulus_growing_degree_days` | `sensor.hortulus_graaddagen` |
| `sensor.hortulus_tasks_due_today` | `sensor.hortulus_taken_vandaag` |
| `sensor.hortulus_next_task` | `sensor.hortulus_volgende_taak` |
| `calendar.hortulus_garden_tasks` | `calendar.hortulus_tuintaken` |
| `todo.hortulus_this_week` | `todo.hortulus_deze_week` |
| `sensor.bed_1_moisture_status` | `sensor.bed_1_vochtstatus` |
| `sensor.bed_1_irrigation_recommendation` | `sensor.bed_1_beregeningsadvies` |
| `binary_sensor.bed_1_needs_water` | `binary_sensor.bed_1_heeft_water_nodig` |
| `sensor.greenhouse_zone_a_greenhouse_advice` | `sensor.greenhouse_zone_a_kasadvies` |
| `binary_sensor.greenhouse_zone_a_heat_stress` | `binary_sensor.greenhouse_zone_a_hittestress` |
| `sensor.hortulus_reference_evapotranspiration_today` | `sensor.hortulus_referentieverdamping_vandaag` |
| `sensor.bed_1_nutrient_balance` | `sensor.bed_1_voedingsbalans` |
| `sensor.greenhouse_zone_a_disease_risk` | `sensor.greenhouse_zone_a_ziekterisico` |
| `switch.hortulus_automatic_irrigation` | `switch.hortulus_automatisch_bewateren` |
| `select.greenhouse_zone_a_shading` | `select.greenhouse_zone_a_schaduw` |
| `sensor.hortulus_rain_7_days` | `sensor.hortulus_regen_7_dagen` |
| `sensor.hortulus_mean_temperature_7_days` | `sensor.hortulus_gemiddelde_temperatuur_7_dagen` |
| `sensor.hortulus_sunshine_7_days` | `sensor.hortulus_zonneschijn_7_dagen` |
| `sensor.hortulus_frost_nights_this_season` | `sensor.hortulus_vorstnachten_dit_seizoen` |

## Sensoren

### `sensor.hortulus_frost_risk_next_48h`
Enum: `none` · `low` · `moderate` · `high` · `unknown`.
Indeling van het minimum **op planthoogte** (verwachte temperatuur op 2 m + stralingscorrectie
bij heldere, windstille nachten): ≤ 0 °C *high*, ≤ 2 °C *moderate*, ≤ 4 °C *low*.

| Attribuut | Voorbeeld | Betekenis |
|---|---|---|
| `min_temperature` | `-2.0` | laagste verwachte luchttemperatuur (°C) |
| `plant_level_min_temperature` | `-4.0` | na correctie voor grondvorst |
| `min_at` | `2026-03-29T04:00:00+00:00` | wanneer het minimum optreedt |
| `first_below_zero_at` | … | eerste uur op of onder 0 °C op planthoogte |
| `hours_below_zero` | `5.0` | duur (zomer‑/wintertijdbestendig) |
| `source` | `hourly` | terugvalketen `hourly` → `daily` → `sensor` → `none` |
| `zones` | `{"gh_a": "low"}` | niveau per zone (kassen zijn gebufferd) |

De status is `unknown` als er geen verwachting en geen buitentemperatuur is.

### `sensor.hortulus_growing_degree_days`
Seizoenstotaal (°C·d, state class `total`) uit de buitendagen van de
[klimaatgeschiedenis](#klimaatgeschiedenis), sinds 30 dagen vóór de laatste vorst, basis 10 °C,
gewijzigde gemiddeldemethode met een bovengrens van 30 °C. Attributen: `base_temperature`,
`since`, `days_counted`.

### `sensor.hortulus_tasks_due_today`
Aantal open taken die vandaag of eerder verschuldigd zijn (eenheid `tasks`). Attributen:
`estimated_minutes`, `overdue`, `tasks` (tot 25 × `{id, title, type, priority, due}` – handig in
templates).

### `sensor.hortulus_next_task`
Titel van de volgende open taak (vroegste datum, hoogste prioriteit eerst; afgekapt op 255
tekens).

### `sensor.<bed>_moisture_status`  *(“garden.bed_moisture_status”)*
Enum: `dry` · `slightly_dry` · `optimal` · `wet` · `unknown`.

| Attribuut | Betekenis |
|---|---|
| `moisture` | huidig volumetrisch watergehalte (%) |
| `target_low` / `target_high` | optimale band voor het dorstigste actieve gewas, verschoven per grondsoort |
| `water_need` | `low` / `medium` / `high` |
| `soil_temperature` | °C, indien gekoppeld |
| `moisture_entity` | de bronsensor |

Banden (leem; zand −6, klei +6, löss +3, veen +8, kalk −2, potgrond +4):

| Waterbehoefte | droog onder | optimaal | nat boven |
|---|---|---|---|
| laag | 18 % | 22–38 % | 55 % |
| gemiddeld | 25 % | 30–45 % | 60 % |
| hoog | 32 % | 38–55 % | 68 % |

### `sensor.<bed>_irrigation_recommendation`  *(“garden.irrigation_recommendation”)*
Status: millimeters om nu te geven. Attributen: `bed_id`, `action` (`none`, `water`,
`skip_rain_expected`, `check_manually`), `amount_mm`, `liters`, `duration_min` (vereist een
debiet – ingevuld of geleerd van de watermeter), `status`, `moisture`, `target_low` /
`target_high`, `water_need`, `etc_24h_mm`, `rain_24h_mm`, `rain_48h_mm`, `confidence` (`high`
met een vochtsensor en een verwachting; `medium` met een sensor maar zonder verwachting, of
als de waterbalans van het bed beslist; `low` met geen van beide), `priority`, `reasons`,
`irrigation_entity`. Zonder vochtsensor wordt de waterbalans gebruikt (water geven zodra de
helft van het plantbeschikbare water op is).

### `sensor.<bed>_companion_score` *(standaard uitgeschakeld)*
0–100 % (50 = neutraal). Attributen: `conflicts`, `rotation_conflicts`.

### `sensor.<zone>_greenhouse_advice`
Enum: `none` · `ventilate` · `shade` · `close_up` · `heat`. Alleen voor omsloten zones (kas,
koude bak). Attributen: `action`, `inside_now_c`, `forecast_max_c`, `forecast_min_c`,
`limit_max_c`, `limit_min_c`, `limiting_plants`, `reasons`, `frost_risk`, `air_temperature`,
`temperature_unit`.

### `sensor.hortulus_reference_evapotranspiration_today`
ET₀ van vandaag in mm (FAO‑56 Penman‑Monteith als vochtigheid en wind bekend zijn,
anders Hargreaves‑Samani). Attributen: `method`, `tmin`, `tmax`, `rh_min`, `rh_max`,
`wind_kmh`, `cloud_fraction`, `rain_mm`, `forecast` (3 dagen: `{day, et0, rain}`).

### `sensor.hortulus_degree_days_today`
Graaddagen die vandaag verwacht worden (°C·d, dezelfde basis als de seizoenssensor).

### `sensor.<bed>_nutrient_balance`
0–100: NPK‑ (mg/kg) of EC‑metingen (mS/cm) vergeleken met de N‑P‑K‑behoefte van de actieve
gewassen (100 = alles binnen bereik). Attributen: `index`, `status` (`unknown`, `deficient`,
`balanced`, `excess`), `deficits` (`n`/`p`/`k`/`ec`), `excess`, `source` (`npk`/`ec`/`none`).
Koppel de sondes in Instellingen → Bedden & sensoren.

### `sensor.<bed>_soil_water_deficit` *(standaard uitgeschakeld)*
Uitputting van de wortelzone onder veldcapaciteit in mm, uit de dagelijkse waterbalans.
Attributen: `available_water_mm` (TAW voor de grond en wortelzonediepte), `crop_coefficient`
(Kc van het dorstigste actieve gewas). Water geven wordt geadviseerd zodra de helft van de TAW
gebruikt is.

### `sensor.<zone>_disease_risk`
Enum `none` · `low` · `moderate` · `high` · `unknown`. Attributen: `wet_hours_48h`,
`hutton_period` (aardappelziekteweer), `humidity`, `leaf_wet`, `reasons`.

### `sensor.<zone>_degree_days_this_season` *(standaard uitgeschakeld)*
Graaddagen van het seizoen voor de zone. Kassen en koude bakken tellen hun eigen
luchtsensor voor elke dag dat die gelogd werd; andere dagen (en omsloten zones zonder
sensor) nemen de buitendag met kasbuffering (+2 °C 's nachts, +4 °C overdag). Buitenzones
volgen het tuinbrede totaal.

### `sensor.hortulus_harvest_this_season`
Geoogste kg dit seizoen (uit het oogstlogboek; device class weight, state class `total`).
Attributen: `season`, `per_crop_kg` (grootste eerst).

### `sensor.hortulus_garden_water_7_days`
Liters leidingwater die de laatste 7 dagen in de tuin gebruikt zijn, volgens de watermeter in
Instellingen → Watermeter & regenton (één meting per dag wordt bewaard). Attributen:
`season_l`, `per_day`.

### `sensor.hortulus_rain_water_available`
Liters in de regentonnen nu (peil van de ton % × totale inhoud, beide ingesteld in
Instellingen → Watermeter & regenton). De omschrijvingen van watertaken zeggen hoeveel
daarvan je eerst kunt gebruiken.


### `sensor.hortulus_pump_energy_this_year` (2.1)
kWh die de bewateringspompen dit kalenderjaar gebruikten (device class energy, `total_increasing`), uit het pompvermogen
onder *Bewateringshardware*. Attributen: `rain_water_liters`, `mains_water_liters` (dit jaar bewaterd per bron).

### `sensor.hortulus_greenhouse_heating_this_week` (2.1)
kWh van de vorstverwarming deze ISO‑week (alleen als een zone een verwarming heeft). Attributen per zone: `kwh`,
`budget_left_kwh`.
### Klimaatgeschiedenis

Vier sensoren vatten samen wat het weer de laatste tijd echt deed, uit de
klimaatgeschiedenis (zie [Configuratie → Klimaatgeschiedenis](CONFIGURATIE.md#klimaatgeschiedenis)).
Elk heeft de waarde van **dezelfde periode vorig jaar** als attribuut.

| Entiteit | Nederlandse naam | Waarde | Eenheid |
|---|---|---|---|
| `sensor.hortulus_rain_7_days` | Regen (7 dagen) | regen van de laatste 7 dagen (vandaag inbegrepen) | mm |
| `sensor.hortulus_mean_temperature_7_days` | Gemiddelde temperatuur (7 dagen) | gemiddelde van de daggemiddelden (device class temperature) | °C |
| `sensor.hortulus_sunshine_7_days` | Zonneschijn (7 dagen) | zonuren (tijd met straling ≥ 120 W/m²) | h |
| `sensor.hortulus_frost_nights_this_season` | Vorstnachten dit seizoen | dagen met een buitenminimum onder 0 °C sinds 1 januari (zuidelijk halfrond: 1 juli); state class `total` | – |

De status is `unknown` zolang er in de periode nog geen dag gelogd is. Attributen (voor de
periode van de sensor):

| Attribuut | Betekenis |
|---|---|
| `days_logged` | aantal gelogde dagen in de periode |
| `last_year` | dezelfde waarde voor dezelfde periode een jaar geleden (`null` zonder gegevens) |
| `lowest` / `highest` | laagste en hoogste buitentemperatuur (°C) |
| `rain_mm` | regen (mm) |
| `sunshine_h` | zonuren |
| `gust_max_kmh` | hardste windstoot (of hardste wind zonder stotensensor), km/u |
| `et0_mm` | referentieverdamping (Penman‑Monteith op het gelogde weer, anders Hargreaves), mm |
| `water_balance_mm` | regen − verdamping (mm) |

```yaml
# Voorbeeld: een melding als de laatste week droger was dan vorig jaar
condition: template
value_template: >
  {{ states('sensor.hortulus_rain_7_days') | float(0)
     < state_attr('sensor.hortulus_rain_7_days', 'last_year') | float(0) }}
```

De volledige statistiek (grafiekreeks, periodes, records, maanden, vorstdata, per sensor) geeft
het websocket‑commando [`garden_manager/climate/stats`](#garden_managerclimatestats).

## Sensorkoppelingen

Een sensorkoppeling (per bed, per zone of `outdoor_sensors` voor de hele tuin, in de
instellingen en in plan‑exports) kent deze sleutels: `soil_moisture`, `soil_temperature`,
`air_temperature`, `air_humidity`, `light`, `rain`, `par`, `ec`, `npk_n`, `npk_p`, `npk_k`,
`leaf_wetness` en, nieuw voor een **weerstation** buiten:

| Sleutel | Eenheid | Gebruik |
|---|---|---|
| `wind_speed` | km/u, m/s, mph of kn (wordt naar km/u omgerekend) | gemiddelde en hardste wind van de dag, Penman‑Monteith, stormdagen |
| `wind_gust` | idem | hardste windstoot, taak *Na de storm* |
| `radiation` | W/m² | stralingssom (MJ/m²) en zonuren van de dag, verdamping, sombere dagen |

Zonder `radiation` wordt `light` van de buitensensoren (lux) omgerekend; zonder wind‑ of
stotensensor gebruikt Hortulus `wind_speed` en `wind_gust_speed` van de weerentiteit. Elke
gekoppelde temperatuursensor (buiten, zone, bed, bodem) krijgt zijn eigen dagreeks in de
klimaatgeschiedenis.

## Binaire sensoren

| Entiteit | Device class | Aan wanneer |
|---|---|---|
| `binary_sensor.hortulus_frost_warning` | cold | vorstrisico *moderate* of *high* (onbekend zonder verwachting); attributen `level`, `min_temperature` (planthoogte), `plants_at_risk` |
| `binary_sensor.<zone>_frost_risk_48h` | cold | het vorstrisico van die zone op planthoogte is *moderate* of *high*; attributen `level`, `min_temperature`, `min_at` |
| `binary_sensor.<bed>_needs_water` | problem | de beregeningsactie is `water` |
| `binary_sensor.<zone>_heat_stress` | heat | het advies voor kas / koude bak is `ventilate` of `shade` |
| `binary_sensor.hortulus_irrigation_frost_lockout` | safety | buitenkleppen zijn vergrendeld (vorst binnen 12 uur of nu te koud); attributen `temperature`, `limit` |
| `binary_sensor.hortulus_irrigation_running` | running | een beregeningsbeurt loopt; attributen `bed_id`, `ends_at`, `last_error` |

## Bewatering en klimaatbediening

| Entiteit | Opmerkingen |
|---|---|
| `switch.hortulus_automatic_irrigation` | aan = modus `auto` (kleppen openen op de starttijd), uit = `advise` |
| `select.hortulus_irrigation_mode` | `off` · `advise` · `auto` |
| `number.hortulus_irrigation_max_runtime` | minuten per klep (1–180, stap 1) |
| `number.hortulus_irrigation_frost_lockout_temperature` | °C (−5 tot 10, stap 0,5); buitenkleppen blijven dicht bij of onder deze waarde |
| `number.hortulus_skip_irrigation_above_rain` | mm verwacht in de komende 24 uur (0–30, stap 0,5) |
| `button.hortulus_water_now` / `button.hortulus_stop_watering` | nu elk bed water geven dat het nodig heeft (veiligheidsregels gelden) / stoppen en alles sluiten |
| `select.<zone>_shading` | `auto` (volgt het advies) · `on` · `off` voor het schaduwscherm van de zone (kassen en koude bakken) |

De modusselect, de drie getallen en de schakelaar bewerken dezelfde beregeningsinstellingen als
het paneel. De schakelaar heeft de attributen `start_time`, `pump` en `valves`; uitzetten stopt
ook een lopende beurt. De getallen en de modusselect zijn *configuratie*‑entiteiten.

**Veiligheidsregels** (ook bij handmatig starten): één klep tegelijk; de pomp draait alleen als
er een klep open is (klep → 1 s → pomp aan … pomp uit → *wachttijd* in seconden → klep dicht);
maximale looptijd (een klep met een eigen timer krijgt openingen die erbinnen blijven);
vorstvergrendeling voor buitenkleppen, met een blik op de komende 12 uur; regen overslaan; een
klep die dicht blijft beëindigt de beurt zonder water te boeken; een klep die een minuut niets
meldt terwijl de pomp draait, beëindigt de beurt en stopt de pomp; elke geopende klep en de pomp
worden aan het einde, na een fout en bij annuleren uitgeschakeld. Elke beurt wordt gelogd
(liters van de watermeter als die er is) en voedt de waterbalans van het bed. Na elke beurt
controleert Hortulus of de klep dicht meldt; een klep of pomp die langer dan de maximale
looptijd + 10 minuten openstaat terwijl er geen beurt actief is, geeft een dashboardbanner, een
melding en een regel in het systeemlogboek (*Kraan sluiten*). Minstens 5 L water die binnen 15 minuten geteld
wordt terwijl alle kranen dicht zijn, wordt als lek gemeld (uit te zetten in Instellingen).

## Kalender, takenlijst, knoppen

| Entiteit | Opmerkingen |
|---|---|
| `calendar.hortulus_garden_tasks` | Hele‑dag‑afspraken voor elke taak behalve overgeslagen taken (✓ = gedaan, ‼/! = dringend/hoog). De entiteit toont de huidige of volgende open taak; achterstallig werk telt als vandaag. Aanmaken, bewerken (de datum verplaatsen stelt de taak uit, afhankelijke taken schuiven mee; samenvatting en omschrijving wijzigen de taak) en verwijderen kan vanuit de HA‑kalender. |
| `todo.hortulus_this_week` | Open taken die binnen 7 dagen verschuldigd zijn (+ achterstallig), plus taken die de laatste 2 dagen zijn afgerond. Afvinken rondt de taak af, het vinkje weghalen heropent haar; aanmaken, hernoemen, de datum of omschrijving wijzigen en verwijderen worden ondersteund. |
| `button.hortulus_generate_tasks` | Taken nu opnieuw genereren (configuratie‑entiteit). |
| `button.hortulus_refresh_forecast` | De verwachting nu ophalen (diagnose‑entiteit). |

De kalender bevat ook het **seizoenswerk** (sleutels `m:…`): het seizoen plannen, zaad
bestellen, het zaaistation klaarzetten, compost omzetten, mulchen, elk bed klaarmaken vóór het
planten (met kg compost en g bemesting), groenbemester of winterafdekking voor lege bedden,
slangen leegmaken vóór de vorst, winterrust, om het derde seizoen een bodemanalyse,
gereedschapsonderhoud, en per kas: voorjaarspoets, schaduw aan/af, winterisolatie en de
najaarspoets (kuisen en ontsmetten). Meerjarigen krijgen terugsnoeien, scheuren (om de 3 jaar)
en winterbescherming volgens hun tags. Zet het uit in Instellingen → Middelen.

**Weertaken** (sleutels `w:…`, bron `weather`) komen uit de verwachting (hitte, droogte,
storm, zware regen) en uit het weer dat **al gevallen** is, volgens de klimaatgeschiedenis
(alleen als er gewassen in de grond staan):

| Sleutel | Taak | Wanneer |
|---|---|---|
| `w:after_storm:<dag>` | *Na de storm (dag): loop de tuin na* – controle, hoge prioriteit, 2 dagen | gisteren windstoten ≥ 60 km/u of wind ≥ 45 km/u |
| `w:rain:<dag>` | *Zware regen (… mm op dag): nazorg* – slakkenronde | ≥ 15 mm in een dag, verwacht **of gelogd** (regenmeter, recorder of Open‑Meteo; nooit alleen uit de verwachting van gisteren). Dezelfde sleutel als de verwachting, dus de taak verschijnt maar één keer |
| `w:dry_logged:<maandag>` | *Droge periode: … mm regen in … dagen* – één keer flink water geven | in de laatste 7 dagen minstens 6 dagen met bekende regen, samen < 3 mm, en minstens 4 dagen ≥ 20 °C; niet als de verwachting al een droogtetaak (`w:dry:…`) maakte |

---

## Diensten (acties)

Alle diensten staan in het domein `garden_manager` en geven gegevens terug als je ze aanroept
met `response_variable` (behalve `delete_task`, `remove_planting`, `stop_irrigation` en
`assign_task`, die niets teruggeven; `export_plan` geeft alleen gegevens terug).

Gemeenschappelijk voor alle diensten:

* **`garden`** (optioneel, tekst): de titel of het entry‑id van de tuin waarop je werkt als je
  er [meer dan één hebt](CONFIGURATIE.md#9-meerdere-tuinen). Zonder gaat het naar de eerste tuin.
* Diensten die het plan, de plantengegevens of de hardware wijzigen – `import_plan`,
  `add_planting`, `update_planting`, `remove_planting`, `run_irrigation_plan`,
  `stop_irrigation`, `set_shading_mode`, `autofill_plan`, `export_pdf`, `generate_tasks`,
  `recalculate_plan`, `install_voice_sentences` – vereisen een **beheerder** als een gebruiker
  ze aanroept (net als zijn websocket‑commando's). Automatiseringen en scripts draaien zonder
  gebruiker en zijn toegestaan.

| Groep | Diensten |
|---|---|
| Taken | `add_task`, `complete_task`, `postpone_task`, `delete_task`, `generate_tasks`, `recalculate_plan` |
| Plan | `export_plan`, `import_plan`, `add_planting`, `update_planting`, `remove_planting`, `autofill_plan`, `export_pdf` |
| Bewatering en klimaat | `run_irrigation_plan`, `stop_irrigation`, `set_shading_mode` |
| Registraties | `log_harvest`, `add_journal_entry`, `save_soil_test` |
| Huishouden en spraak | `assign_task`, `install_voice_sentences` |

### `garden_manager.add_task`
| Veld | Type | Opmerkingen |
|---|---|---|
| `title` | string | verplicht |
| `due_date` | date | standaard vandaag |
| `type` | enum | standaard `custom`; zie de lijst hieronder |
| `description` | string | |
| `priority` | `low`/`normal`/`high`/`urgent` | standaard `normal` |
| `estimated_minutes` | int | 1–1440 |
| `bed` | string | bed‑**id of ‑naam** (hoofdletterongevoelig) |
| `planting_id` | string | |
| `recurrence_days` | int | 1–365; N dagen na elke afronding herhalen |
| `until` | date | laatste datum voor de herhaling |

Taaksoorten: `custom`, `sow_indoor`, `sow_direct`, `harden_off`, `transplant`, `thin`, `stake`,
`prune`, `pinch`, `earth_up`, `feed`, `water`, `weed`, `pest_check`, `harvest`, `ventilate`,
`shade`, `frost_protect`, `soil_prep`, `compost`, `green_manure`, `mulch`, `clean_greenhouse`,
`winter_prep`, `plan_season`, `tool_care`, `soil_test`, `cut_back`, `divide`, `protect`, `clean`,
`tie_in`, `thin_fruit`, `pollinate`, `check`, `make_feed`.

Antwoord: `{task_id}`.

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
Velden: `task_id`, `note`, `photos` (lijst met afbeeldings‑id's/‑URL's), `skipped` (bool,
standaard false). Een **zaai‑**, **uitplant‑** of eerste **oogsttaak** afronden werkt de
beplanting bij (`sown_on`, `transplanted_on`, `harvest_started_on`, status), waardoor alle
verzorgingstaken opnieuw op de echte datums verankerd worden. Herhalende taken plannen hun
volgende voorkomen `interval` dagen na het *afronden*. Een watertaak die twee keer afgerond
wordt, boekt haar water één keer.
Antwoord: `{task_id, status, next_task_id, next_due}`.

### `garden_manager.postpone_task`
Velden: `task_id`, `days` (−365…365) **of** `to_date`, `reason`, `cascade` (standaard true).
Afhankelijke taken van dezelfde beplanting die je niet met de hand verschoof, schuiven met
hetzelfde aantal dagen mee (*tomaten zaaien* uitstellen verschuift *afharden* en *uitplanten*).
Antwoord: `{task_id, due, shifted: [ids], warnings: ["beyond_window", …]}`.

### `garden_manager.delete_task`
Verwijdert taken van gebruikers; gegenereerde taken worden als *overgeslagen* gemarkeerd (anders
zouden ze opnieuw worden aangemaakt).

### `garden_manager.assign_task`
Velden: `task_id`, `assignee` (`person.*`‑entiteit, leeg om los te koppelen). Nieuwe taken
worden automatisch toegewezen volgens Instellingen → Huishouden & spraak (een standaardpersoon
en één per taaksoort).

### `garden_manager.generate_tasks`
Idempotente herberekening uit plan + databank + sensoren + verwachting.
Antwoord: `{created, updated, removed, open_tasks}`.

### `garden_manager.recalculate_plan`
Haalt de verwachting opnieuw op en berekent alles opnieuw. Antwoord: `{frost_risk,
weather_available, alerts, season}`.

### `garden_manager.export_plan` *(alleen antwoord)*
Velden: `include_tasks` (standaard false), `seasons` (lijst met jaren; beperkt beplantingen en
opzijgezette plannen tot die seizoenen). Geeft het plandocument terug (zie
[configuratie](CONFIGURATIE.md#5-importeren-en-exporteren)).

### `garden_manager.import_plan`
Velden: `plan` (object, verplicht), `mode` (`merge` standaard | `replace`). Een geweigerd
bestand wijzigt niets. Antwoord: aantallen per collectie (`zones`, `beds`, `features`,
`layouts`, `plantings`, `custom_plants`, `rotation_history`, `tasks`, `archived_plans`).

### `garden_manager.add_planting` / `update_planting` / `remove_planting`
`add_planting`: `plant_id` en `bed` (id of naam) zijn verplicht; optioneel `season` (standaard
het huidige kalenderjaar), `layout` (`single` / `row` / `block`, standaard `row`), `x_cm`,
`y_cm`, `width_cm` (standaard de breedte van het bed), `length_cm` (standaard één rij), `count`,
`method` (`indoor_sow` / `direct_sow` / `transplant`), `status` (`planned`, `sown_indoors`,
`sown`, `transplanted`, `harvesting`, `finished`, `failed`), geplande data `sow_date` /
`transplant_date`, echte data `sown_on` / `transplanted_on`, `notes`. De beplanting moet op een
bed van het plan van haar eigen seizoen staan. Taken volgen automatisch. `update_planting`
accepteert `planting_id` plus elk van die velden (en `plant_id`, `bed`); `remove_planting`
accepteert `planting_id`. Antwoorden: `{planting_id, planting}` / `{planting}` / geen.

```yaml
action: garden_manager.add_planting
data: {plant_id: dill, bed: Bed 1, layout: row}
response_variable: added
```

### `garden_manager.autofill_plan`
Stelt een seizoensplan voor. Velden: `season`, `beds` (standaard: alle lege bedden), `replace`,
`apply` (opslaan), en middelen `household_size` (1–20), `hours_per_week` (0–80),
`water_liters_per_week`, `compost_kg`, `goals` (`fresh`, `storage`, `herbs`, `pollinators`,
`winter`, `perennials`, `easy`), `wanted`, `excluded`, `max_crops` (1–60, standaard 16).
Weggelaten middelen komen uit Instellingen → Middelen.
Antwoord: `plantings`, `placements` (gewas, bed, aantal, m², kg, min/week, L/week, zaaimomenten),
`skipped`, `warnings`, `summary`, en `applied: true` als het is opgeslagen.

### `garden_manager.run_irrigation_plan`
Velden: `dry_run`, `beds` (lijst met id's of namen), `amount_mm` (0,5–50), `only_if_needed`
(standaard false). Geeft het plan terug (`runs` met `bed_id, entity_id, minutes, mm, liters,
capped`; `skipped` en `skipped_reasons` per bed; `lockout`, `lockout_temp`, `total_minutes`,
`started`) en start het tenzij `dry_run`. Negeert de bewateringsmodus, nooit de
veiligheidsregels. Met `only_if_needed` kiest een automatisering het moment en beslist Hortulus
nog steeds of een bed water nodig heeft. Mislukt (tenzij `dry_run`) terwijl er een beurt loopt.
`garden_manager.stop_irrigation` stopt een beurt.

### `garden_manager.set_shading_mode`
Velden: `zone` (id of naam van een kas/koude bak), `mode` (`auto`/`on`/`off`).
Antwoord: `{zone_id, mode}`.

### `garden_manager.export_pdf`
Schrijft een PDF naar `/config/hortulus/exports/` (privé; het antwoord bevat een ondertekende
downloadlink die 7 dagen geldig is). Velden: `document` (`garden`, `zone`, `beds`, `tasks`,
`season`, `year`, `blank`, `plants`, `book`), `page` (`a4`, `a3`, `a5`, `letter`, `remarkable`),
`landscape`, `color_mode` (`color`, `eink`, `grayscale`), `season`, `zone_id`, `bed_ids`, `days`
(1–120, standaard 28, voor `tasks`), `notes` (stippelraster, standaard true), `grid` (raster van
10 cm op bedfiches, standaard true), `title`. `book` is het seizoensboek.
Antwoord: `{path, url, filename, bytes}`.

```yaml
# Elke maandagochtend: de checklist van deze week voor de reMarkable
action: garden_manager.export_pdf
data: {document: tasks, page: remarkable, color_mode: eink, days: 7}
```

### `garden_manager.log_harvest`
Voegt een oogst toe aan het logboek. Velden: `planting_id` *of* `plant_id` *of* `plant` (een id
**of een naam** zoals `Tomaat`; handig voor een NFC‑tag of een dashboardknop), `bed` (om de
teelt in de tuin te vinden), `kg` (0–500), `count` (minstens één van `kg` en `count` is
verplicht), `quality` (1–5), `day`, `note`. De eerste oogst van een beplanting zet haar op
*harvesting*. Antwoord: `{harvest}`. Na een seizoen met gegevens gebruikt Hortulus **jouw eigen
kg/m²** in plaats van de opbrengst uit de databank (Automatisch invullen, advies,
boodschappenlijst).

### `garden_manager.add_journal_entry`
Een dagboeknotitie met optionele foto's. Velden: `text` (verplicht), `kind` (`note` standaard,
`observation`, `problem`, `milestone`), `planting_id`, `bed` (id of naam), `photos`
(afbeeldings‑id's). De auteur is de aanroepende gebruiker. Antwoord: `{entry}`.

### `garden_manager.save_soil_test`
Bewaart een bodemanalyse voor een bed (één per datum; dezelfde datum vervangt). Velden: `bed`,
`date` (beide verplicht), `ph` (3–10), `organic_matter_pct`, `p_mg`, `k_mg` (mg per 100 g),
`notes`. Het bemestingsplan en het kalkadvies van het bed volgen de laatste analyse.
Antwoord: `{soil_test}`.

### `garden_manager.install_voice_sentences`
Kopieert de Assist‑zinnen (EN + NL + FR) naar `/config/custom_sentences/<taal>/hortulus.yaml`
en herlaadt de gespreksagent. Veld: `overwrite` (standaard false: bestanden die je bewerkte
blijven behouden). Antwoord: `{written: [paden]}`. Zie *Spraak* hieronder.

---

## Events

| Event | Afgevuurd wanneer | Data |
|---|---|---|
| `garden_manager_task_due` | ochtendoverzicht (elke verschuldigde taak) en wanneer overdag een sensor‑/weertaak verschijnt | `task_id, type, title, priority, due, bed_id, zone_id, planting_id` |
| `garden_manager_task_completed` | een taak is afgerond/overgeslagen | `task_id, type, title, skipped, planting_id, bed_id, next_task_id` |
| `garden_manager_frost_warning` | nieuwe vorstwaarschuwing (één keer per zone en nacht), en ook als het gevroren **heeft** terwijl tere gewassen buiten stonden (`key` `froze:<dag>`) | `key, severity, zone_id, level, temp, when, plants` |
| `garden_manager_heat_warning` | nieuwe hittewaarschuwing voor de kas (één keer per zone en dag) | `key, severity, zone_id, zone, temp, action` |
| `garden_manager_irrigation_recommended` | een bed heeft water nodig (één keer per bed en dag) | `bed_id` + elk attribuut van het beregeningsadvies |
| `garden_manager_plan_updated` | plan, planten, instellingen of import gewijzigd | `reason` (`plan`, `plants`, `settings`, `import`), `revision` |
| `garden_manager_irrigation_run` | een klep is klaar (of gestopt) | `bed_id, bed, minutes, liters, mm, source` |

`severity` is `info`, `warning` of `critical`; `zone_id` is leeg voor de tuinbrede
(buiten)vorstwaarschuwing.

**Gemelde vorst (`alert.frost_logged`).** Gaf de klimaatgeschiedenis vannacht (of gisteren) een
buitenminimum onder 0 °C en stonden er actieve gewassen buiten (niet in een kas of koude bak)
waarvan de minimumtemperatuur hoger ligt, dan verschijnt de waarschuwing *“Het heeft gevroren
(… °C): kijk deze gewassen na op vorstschade”* (`warning`, sleutel `froze:<dag>`, met `temp`
en `plants`). Ze vuurt eenmalig `garden_manager_frost_warning`, gaat als melding uit als
vorstwaarschuwingen aan staan en zet die gewassen in `plants_at_risk` van
`binary_sensor.hortulus_frost_warning`.

**Meldingsknoppen.** Het dagoverzicht, de herinneringen en de meldingen “bedden hebben water
nodig” en “kraan staat open” op gsm's met de companion‑app hebben actieknoppen: *Gedaan* (één
taak) en *Morgen* bij takenlijsten, *Nu water geven* als bedden water nodig hebben, *Kraan
sluiten* bij een kraan die openstaat. Een druk op een knop vuurt het
`mobile_app_notification_action`‑event van Home Assistant af (actienamen beginnen met
`HORTULUS_`), dat Hortulus zelf afhandelt; je hebt er geen automatisering voor nodig.

## Websocket‑API (gebruikt door het paneel)

Alle commando's staan in de namespace `garden_manager/` en accepteren `garden_id` (het config
entry‑id) om een tuin te kiezen. Lezen mag elke geauthenticeerde gebruiker; commando's met
**admin** vereisen een beheerder. Taakacties, registraties (oogst, dagboek, zaden, uitgaven,
bodemanalyses) en het kookboek zijn open voor iedereen.

| Groep | Commando's |
|---|---|
| Live gegevens | `subscribe` (pusht nu en na elke wijziging een volledige momentopname), `plants` (databank + overrides), `advice`, `supplies` |
| Planten | `plants/save` **admin** (`mode`: `custom` of `override`), `plants/delete` **admin** (zet een override terug of verwijdert een eigen plant), `plants/windows` (zaaivensters voor jouw vorstdata) |
| Plan | `plan/save` **admin** (met `base_revision` en optioneel `season`), `plan/check` (compatibiliteit van een ontwerp), `plan/succession`, `plan/export`, `plan/import` **admin**, `plan/autofill`, `plan/autofill/apply` **admin**, `plan/compare`, `layout/delete` **admin** |
| Opzijgezette plannen | `plan/new` **admin** (`start`: `empty`, `zones`, `zones_beds`), `plan/activate` **admin**, `plan/delete` **admin** |
| Jaarovergang | `year/preview`, `year/apply` **admin** (`from_season`, `layout`: `copy`/`keep`, `zone_ids`, `feature_ids`, `planting_ids`, `activate`) |
| Teelten | `plantings/season`, `planting/update` **admin**, `plantings/update_many` **admin**, `planning` (zaaiplan, zaden, opvolgteelt, oogstverwachting) |
| Taken | `tasks/add`, `tasks/action` (`complete`, `skip`, `postpone`, `update`, `delete`, `reopen`) |
| Instellingen | `settings/save` **admin** |
| Begintuin | `garden/starter` **admin** (`size`: `small`/`medium`/`large`, `greenhouse`) |
| Bewatering | `irrigation/plan`, `irrigation/run` **admin**, `irrigation/stop` **admin**, `irrigation/test` **admin** (een klep 5 s openen en controleren of hij open en dicht meldt), `irrigation/close` **admin** (een open gebleven klep sluiten) |
| Registraties | `records/overview` (oogst per gewas en jaar, geleerde opbrengsten, zaaddoos, water, jaarmatrix, keukenrapport, kosten en uitgaven), `records/harvest/add`, `records/journal/save`, `records/seeds/save`, `records/expense/save`, `records/soil/save`, `records/soil/delete`, `records/delete` (`kind`: `harvest`, `journal`, `seed`, `expense`), `seeds/to_todo` (ontbrekend zaad naar een takenlijst), `report/season` |
| Advies en handboek | `qa/options`, `qa/ask`, `handbook/index`, `handbook/chapter`, `handbook/search` |
| Afdrukken | `print/render` (SVG‑voorbeeldpagina's) |
| Klimaat | `climate/stats` (`days`: 7–800, standaard 400): de klimaatgeschiedenis – [zie hieronder](#garden_managerclimatestats); `climate/import_csv` **admin** (`text`: de CSV‑export van een weerstation, tot 20 MB; resultaat `{days, first, last, rows, columns, changed}`; fouten `invalid_csv`, `disabled`); `climate/apply_local_frost` **admin** (zonder argumenten: zet de regio op aangepast met de gemeten vorstdata; resultaat `{settings}`; fout `no_suggestion`) |
| Analyse | `analysis` (tuincontrole), `analysis/explain` (“waarom niet hier?”), `analysis/fix` **admin** (herstel met één klik), `analysis/still_possible` (wat dit seizoen nog kan) |
| Systeemlogboek | `syslog/list` (nieuwste eerst, gepagineerd met `before`), `syslog/entry` **admin** (één regel met voor/na per onderdeel), `syslog/undo` **admin** (`entry_id`, optioneel `force`) |
| Koken | `cooking/suggest` (oogstklare producten, gerechten, menu's, kookboek, keuzes), `cooking/render` (een recept opnieuw na een andere basis, vlees of aantal personen), `cooking/prefs`, `cooking/book/save`, `cooking/book/update`, `cooking/book/delete`, `cooking/pdf` (`kind`: `recipe`, `book`, `shopping`), `cooking/send` (een recept of de boodschappenlijst naar een `notify.*`‑dienst), `cooking/to_todo` (boodschappenlijst naar een takenlijst; je eigen rechten op die lijst gelden) |

`seeds/to_todo` en `cooking/to_todo` controleren de eigen rechten van de aanroepende gebruiker
op de doeltakenlijst.

### `garden_manager/climate/stats`

Geeft alles wat *Weer → Klimaatgeschiedenis* toont (lezen mag elke gebruiker):

| Sleutel | Inhoud |
|---|---|
| `today`, `season_start` | datum van vandaag en begin van het seizoen (1 januari, zuidelijk halfrond 1 juli) |
| `series` | één rij per buitendag binnen `days`: `d` (datum), `lo`/`hi`/`m` (min/max/gemiddelde °C), `r` (regen mm), `s` (zonuren), `w` (hardste stoot of wind km/u), `rh` (vochtigheid %), `et0` (mm), `src` (`sensor`, `history`, `model` of een combinatie met `+`) |
| `periods` | `d7`, `d30`, `season`, `d365`, `d7_last_year`, `d30_last_year`, `season_last_year`, elk met `days`, `tmean`, `tmin`/`tmin_day`, `tmax`/`tmax_day`, `frost_nights`, `hot_days` (≥ 25 °C), `very_hot_days` (≥ 30 °C), `gdd`, `rain_mm`, `rain_days` (≥ 1 mm), `wettest`, `sun_h`, `rs_mj`, `gust_max`/`gust_day`, `et0_mm`, `balance_mm`, `rh_mean` |
| `records` | `tmin`, `tmax`, `wettest`, `gust_max`, elk `{value, when}` (een dag of, uit de maandcijfers, een maand) |
| `months` | buiten, nieuwste eerst (tot 24): `month`, `days`, `tmin`, `tmax`, `tmean`, `rain_mm`, `frost_days`, `hot_days`, `sun_h`, `wind_max` |
| `frost` | `years` (per jaar `last_spring`, `first_autumn`, `spring_complete`, `autumn_complete`), `local` (gemiddelde gemeten data en het verschil in dagen met de regio, `null` zonder volledig jaar), `preset_last`, `preset_first` |
| `sensors` | per temperatuursensor: `entity_id`, `label`, `kind` (`outdoor`, `zone_air`, `bed_air`, `soil`), `now`, `today`, `d7`, `d30`, `record_low`, `record_high`, `days`, `series` (laatste 120 dagen), `months` (13) |
| `coverage` | `days`, `first_day`, `sources` (dagen per bron), `months_kept` |
| `summary` | *(extra `season_summary`)* `season`, `month` (lijsten met zinnen), `month_start` – het seizoen en de vorige maand tegenover dezelfde data vorig jaar |
| `local_frost_suggestion` | *(extra `local_frost_suggest`)* `last_frost`, `first_frost` (`MM-DD`), `spring_diff_days`, `autumn_diff_days`, `years`; `null` zolang de gemeten data minder dan 7 dagen van de regio afwijken |
| `station_import` | `true` als de CSV‑import (extra `station_import`) aanstaat |

## Lovelace-kaart

De integratie laadt een kleine kaart op elk dashboard – je hoeft geen resource met de hand toe
te voegen:

```yaml
type: custom:hortulus-tasks-card
title: Tuin vandaag   # optioneel
days: 0               # 0 = vandaag + achterstallig, 7 = de komende week
assignee: me          # optioneel: me | person.xyz | unassigned
max: 8                # optioneel, standaard 8
water: true           # optioneel, standaard true; false verbergt: water vandaag, een lopende beurt, een kraan die openstaat (Sluiten), lekken
garden: Volkstuin     # optioneel: welke tuin (titel of entry-id), als je er meer dan één hebt
climate: true         # optioneel, standaard true; false verbergt de klimaatregel (gemiddelde 7 dagen t.o.v. vorig jaar, regen, zon, band van 14 dagen)
slogan: true          # optioneel, standaard true; false verbergt de tuinspreuk
```

Vink een taak af op de kaart en ze wordt in Hortulus afgerond (met het volgende zaai‑ of
verzorgingsmoment gepland zoals gewoonlijk). `assignee: me` toont je eigen en niet‑toegewezen
taken; `person.xyz` toont de taken van die persoon en niet‑toegewezen taken; `unassigned` toont
alleen taken zonder eigenaar. Achterstallige taken zijn gemarkeerd; een link “+N meer” en het
scheutje‑icoon openen het paneel. De knop *Sluiten* bij een kraan die openstaat wordt alleen aan
beheerders getoond. De klimaatregel en de spreuk vragen de extra's `climate_card` en
`slogans` (Instellingen → Extra's); zonder taken vervangt de spreuk “niets te doen”. De kaart is beschikbaar in het
Engels, Nederlands en Frans.

## Spraak (Assist)

Voer één keer `garden_manager.install_voice_sentences` uit (of Instellingen → Huishouden &
spraak → *Spraakzinnen installeren*) en vraag daarna Assist:

| Intent | English | Nederlands |
|---|---|---|
| `HortulusTasksToday` | "what do I need to do in the garden today" | "wat moet ik vandaag in de tuin doen" |
| `HortulusOverdue` | "what did I forget in the garden" | "wat ben ik vergeten in de tuin" |
| `HortulusHarvest` | "what can I harvest today" | "wat kan ik vandaag oogsten" |
| `HortulusGreenhouse` | "how warm is it in the greenhouse" | "hoe warm is het in de serre" |
| `HortulusWater` | "do I need to water today" | "moet ik vandaag water geven" |
| `HortulusFrost` | "is there frost tonight" | "gaat het vriezen vannacht" |

Franse zinnen worden ook meegeleverd. Antwoorden worden uitgesproken in de taal van het
gesprek. De intents hebben geen slots en worden door de integratie zelf geregistreerd, dus je
kunt ze ook in je eigen zinnen of automatiseringen gebruiken (`conversation.process`). Met meer
dan één tuin antwoorden ze voor de eerste.

## PDF‑download

`GET /api/garden_manager/print?document=garden&page=remarkable&color_mode=eink`
(geauthenticeerd) maakt de PDF ter plekke. Het accepteert dezelfde parameters als `export_pdf`
(`document`, `page`, `landscape`, `color_mode`, `season`, `zone_id`, `bed_ids`, `days`, `notes`,
`grid`, `title`; lijsten kommagescheiden) plus `labels` (gewasnamen op de kaart, standaard true),
`plant_ids` (voor de plantkaarten) en `garden_id`. `&format=svg` geeft de SVG‑pagina's als JSON
terug (`{"pages": [...]}`) in plaats van een PDF.

`GET /api/garden_manager/exports/<bestand>.pdf` levert een PDF die door `export_pdf` of
*Opslaan* in het tabblad Afdrukken is geschreven (aanmelding of ondertekende link, 7 dagen geldig).

Kook‑PDF's (een recept, het kookboek, de boodschappenlijst) worden door het websocket‑commando
`cooking/pdf` als base64 teruggegeven.

## Diagnose

Instellingen → Apparaten & diensten → Hortulus → ⋮ → *Diagnose downloaden* geeft een
JSON‑bestand met de gegevens en opties van de config entry, de instellingen, aantallen (zones,
bedden, beplantingen, open en totale taken, eigen planten, klimaatdagen), de gevolgde
entity‑id's, de weertoestand (beschikbaar, fout, aantal uur‑ en dagpunten) en de huidige analyse.
Notify‑diensten, speakers, de breedtegraad en foto‑id's worden weggelaten. Een aparte
**Analyse → Controle → Diagnose exporteren** in het paneel schrijft de tuincontrole als één
JSON‑bestand voor bugmeldingen.

## Blueprints

Vier automatiserings‑blueprints staan in `blueprints/automation/hortulus/`: vorstwaarschuwing
op een lamp (`frost_flash_light.yaml`; de lamp keert terug naar hoe hij was), een oogst loggen
met een knop of een NFC‑tag (`button_log_harvest.yaml`), een droog bed op een goed moment
water geven (`water_when_dry.yaml`, gebruikt `run_irrigation_plan` met `only_if_needed`) en
dringende tuinklussen omroepen (`urgent_task_announce.yaml`). Importlinks staan in de README.
