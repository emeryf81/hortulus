<!-- Generated from the sources by a script: code excerpts below are verbatim. -->
[← 10. Documentation Files (README etc.)](10-documentation-files-readme-etc.md) · [↑ Blueprint contents](../BLUEPRINT.md)

## 11. Version 1.1 additions and release map

### 11.1 Agronomy

FAO‑56 Penman‑Monteith (eq. 6) with radiation from cloud cover via Angström; verified
against FAO example 18 (Brussels, 6 July → 3.9 mm/day). Hargreaves‑Samani is the
fallback when humidity or wind are missing.

```python
def et0_penman_monteith(
    tmin: float,
    tmax: float,
    latitude_deg: float,
    day: date,
    *,
    rh_min: float | None = None,
    rh_max: float | None = None,
    rh_mean: float | None = None,
    u2: float | None = None,
    wind_kmh_10m: float | None = None,
    rs: float | None = None,
    sunshine_fraction: float | None = None,
    elevation_m: float = 0.0,
) -> float | None:
    """FAO-56 Penman-Monteith reference ET (mm/day), eq. 6.

    Needs humidity and wind; solar radiation comes from ``rs`` (MJ/m²/day, e.g.
    Open-Meteo) or is estimated with the Angström formula from the sunshine
    fraction n/N - which an HA forecast gives us via cloud cover (n/N ≈ 1 -
    clouds).  Returns ``None`` when inputs are insufficient; callers then fall
    back to Hargreaves-Samani.
    """
    if tmax < tmin:
        tmin, tmax = tmax, tmin
    if u2 is None and wind_kmh_10m is not None:
        u2 = wind_kmh_10m / 3.6 * 4.87 / math.log(67.8 * 10 - 5.42)  # eq. 47, measured at 10 m
    if u2 is None or (rh_min is None and rh_mean is None):
        return None
    ra, _daylight = _solar(latitude_deg, day)
    if rs is None:
        if sunshine_fraction is None:
            return None
        rs = (0.25 + 0.50 * max(0.0, min(1.0, sunshine_fraction))) * ra  # eq. 35
    tmean = (tmax + tmin) / 2
    delta = 4098 * _svp(tmean) / (tmean + 237.3) ** 2  # eq. 13
    pressure = 101.3 * ((293 - 0.0065 * elevation_m) / 293) ** 5.26  # eq. 7
    gamma = 0.000665 * pressure  # eq. 8
    es = (_svp(tmax) + _svp(tmin)) / 2  # eq. 12
    if rh_min is not None and rh_max is not None:
        ea = (_svp(tmin) * rh_max / 100 + _svp(tmax) * rh_min / 100) / 2  # eq. 17
    else:
        rh = rh_mean if rh_mean is not None else rh_min
        ea = (rh or 70.0) / 100 * es  # eq. 19
    rso = (0.75 + 2e-5 * elevation_m) * ra  # eq. 37
    rns = 0.77 * rs  # eq. 38 (albedo 0.23)
    rel_shortwave = min(rs / rso, 1.0) if rso > 0 else 0.0
    rnl = (
        4.903e-9
        * (((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2)
        * (0.34 - 0.14 * math.sqrt(max(ea, 0.0)))
        * (1.35 * rel_shortwave - 0.35)
    )  # eq. 39
    rn = rns - rnl
    num = 0.408 * delta * rn + gamma * 900 / (tmean + 273) * u2 * (es - ea)
    return max(round(num / (delta + gamma * (1 + 0.34 * u2)), 2), 0.0)
```

Crop coefficient by growth stage (FAO‑56 stage lengths 15/25/40/20 %):

```python
def stage_kc(plant: Plant, tl: PlantingTimeline, today: date) -> float:
    """Interpolated FAO-56 Kc for ``today`` (perennials: mid-season value)."""
    kc_ini, kc_mid, kc_end = (plant.kc + [0.5, 1.0, 0.8])[:3]
    if plant.perennial:
        return kc_mid
    total = max((tl.harvest_end - tl.in_ground).days, 1)
    elapsed = (today - tl.in_ground).days
    if elapsed < 0:
        return 0.0
    f = elapsed / total
    ini, dev, mid, _late = STAGE_FRACTIONS
    if f <= ini:
        return kc_ini
    if f <= ini + dev:
        return kc_ini + (kc_mid - kc_ini) * (f - ini) / dev
    if f <= ini + dev + mid:
        return kc_mid
    if f <= 1.0:
        return kc_mid + (kc_end - kc_mid) * (f - ini - dev - mid) / (1 - ini - dev - mid)
    return kc_end
```

Root‑zone bucket (FAO‑56 eq. 85, no capillary rise); TAW = available water per metre of
soil × rooting depth; water when depletion ≥ 0.5 × TAW:

```python
def update_water_balance(
    depletion_mm: float,
    *,
    et0_mm: float,
    kc: float,
    rain_mm: float,
    irrigation_mm: float,
    taw_mm: float,
    enclosed: bool = False,
) -> float:
    """One day of the root-zone bucket (FAO-56 eq. 85, no capillary rise).

    Depletion grows with crop ET and shrinks with effective rain and
    irrigation; it never drops below 0 (field capacity - excess drains) nor
    rises above TAW (wilting point).
    """
    effective_rain = 0.0 if enclosed else RAIN_EFFICIENCY * rain_mm
    depletion = depletion_mm + et0_mm * kc * (ENCLOSED_ET_FACTOR if enclosed else 1.0)
    depletion -= effective_rain + irrigation_mm
    return round(max(0.0, min(taw_mm, depletion)), 1)
```

Disease pressure (Hutton criteria, wet hours, greenhouse humidity, leaf wetness):

```python
def assess_disease(
    weather: WeatherSnapshot,
    now: datetime,
    tz: tzinfo,
    *,
    humidity_now: float | None = None,
    leaf_wetness_now: float | None = None,
    enclosed: bool = False,
    horizon_hours: int = 48,
    recent: dict[str, Any] | None = None,
) -> DiseaseAssessment:
    """Fungal disease pressure from humidity, temperature and leaf wetness.

    * **Hutton period** (late blight): two consecutive days with a minimum of
      at least 10 °C and at least 6 hours of RH >= 90 %.
    * **Wet hours**: RH >= 90 % at 10-25 °C - when spores of downy mildew,
      botrytis and blight germinate.
    * A wet leaf right now (sensor) or stagnant greenhouse air (RH >= 85 %)
      raises the level.
    * ``recent`` - the logged last days (:func:`.climate.recent_wetness`): spores
      that landed in a wet spell are already at work, so a Hutton period that just
      happened counts as high pressure and wet days raise the level.
    """
    out = DiseaseAssessment(humidity_now=humidity_now)
    if leaf_wetness_now is not None:
        out.leaf_wet_now = leaf_wetness_now >= 50 or leaf_wetness_now == 1.0
    horizon = now + timedelta(hours=horizon_hours)
    pts = [p for p in weather.hourly if now - timedelta(hours=1) <= p.at <= horizon and p.temperature is not None]
    has_forecast = weather.available and any(p.humidity is not None for p in pts)
    if has_forecast and not enclosed:
        per_day: dict[date, list[float]] = {}  # day -> [tmin, humid hours]
        for idx, p in enumerate(pts):
            nxt = pts[idx + 1].at if idx + 1 < len(pts) else p.at + timedelta(hours=1)
            hours = min((nxt - p.at).total_seconds() / 3600, 3.0)
            temp = float(p.temperature)  # type: ignore[arg-type]
            day = per_day.setdefault(p.at.astimezone(tz).date(), [99.0, 0.0])
            day[0] = min(day[0], temp)
            if p.humidity is not None and p.humidity >= 90:
                day[1] += hours
                if 10 <= temp <= 25:
                    out.wet_hours += hours
        days = sorted(per_day)
        for a, b in itertools.pairwise(days):
            consecutive = b - a == timedelta(days=1)
            if consecutive and min(per_day[a][0], per_day[b][0]) >= 10 and min(per_day[a][1], per_day[b][1]) >= 6:
                out.hutton_period = True
        out.wet_hours = round(out.wet_hours, 1)
    elif (
        not has_forecast
        and humidity_now is None
        and out.leaf_wet_now is None
        and (enclosed or not (recent and recent.get("days")))
    ):
        return out  # unknown (the outdoor log says nothing about an enclosed zone)

    order = ["none", "low", "moderate", "high"]
    level = 0
    if out.hutton_period:
        level = 3
        out.reasons.append("hutton_period")
    elif out.wet_hours >= 10:
        level = 2
        out.reasons.append("long_wet_period")
    elif out.wet_hours >= 4:
        level = 1
        out.reasons.append("wet_hours")
    if recent and not enclosed:
        if recent.get("hutton") and level < 3:
            level = 3
            out.reasons.append("hutton_logged")
        elif recent.get("wet_days", 0) >= 2:
            level = max(level, 1) + (1 if level >= 1 else 0)
            out.reasons.append("wet_days_logged")
    if enclosed and humidity_now is not None and humidity_now >= 85:
        level = max(level, 1) + (1 if humidity_now >= 92 else 0)
        out.reasons.append("humid_greenhouse_air")
    if out.leaf_wet_now:
        level += 1
        out.reasons.append("leaf_wet_now")
    out.level = order[min(level, 3)]
    return out
```

### 11.2 Companion factors beyond the relation table

```python
def _secondary_factors(
    pa: Planting,
    ra: Rect,
    plant_a: Plant,
    pb: Planting,
    rb: Rect,
    plant_b: Plant,
    influence: float,
    gap: float,
    lang: str,
    hemisphere: Hemisphere,
    rel: Any,
) -> list[PairFinding]:
    """Factors derived from plant traits rather than explicit relations."""
    out: list[PairFinding] = []
    name_a, name_b = plant_a.name(lang), plant_b.name(lang)

    # -- pest deterrence / trap crops ------------------------------------ #
    for helper, helper_p, target, target_p in ((plant_a, pa, plant_b, pb), (plant_b, pb, plant_a, pa)):
        deterred = sorted(set(helper.deters) & set(target.pests))
        trapped = sorted(set(helper.trap_for) & set(target.pests))
        if deterred or trapped:
            pests = ", ".join(pest_label(p, lang) for p in (deterred or trapped))
            out.append(
                PairFinding(
                    helper_p.id, target_p.id, "pest_synergy", "info", 6 * influence, gap,
                    "compat.deters" if deterred else "compat.trap",
                    {"a": helper.name(lang), "b": target.name(lang), "pests": pests},
                )
            )  # fmt: skip

    if rel.relation is Relation.FRIEND:
        return out

    # -- allelopathy ------------------------------------------------------ #
    for culprit, culprit_p, victim, victim_p in ((plant_a, pa, plant_b, pb), (plant_b, pb, plant_a, pa)):
        if culprit.allelopathic and not victim.allelopathic:
            out.append(
                PairFinding(
                    culprit_p.id, victim_p.id, "allelopathy", "warning", -10 * influence, gap,
                    "compat.allelopathy", {"a": culprit.name(lang), "b": victim.name(lang)},
                )
            )  # fmt: skip
            break

    # -- nutrient competition -------------------------------------------- #
    if plant_a.nutrient_needs is Level.HIGH and plant_b.nutrient_needs is Level.HIGH and influence > 0.5:
        out.append(
            PairFinding(
                pa.id, pb.id, "competition", "info", -4 * influence, gap,
                "compat.competition", {"a": name_a, "b": name_b},
            )
        )  # fmt: skip

    # -- shading (canvas y grows to the south; sun from the equator side) -- #
    tall, short = (plant_a, plant_b) if plant_a.height_cm >= plant_b.height_cm else (plant_b, plant_a)
    tall_r, short_r = (ra, rb) if tall is plant_a else (rb, ra)
    tall_p, short_p = (pa, pb) if tall is plant_a else (pb, pa)
    if tall.height_cm >= 80 and tall.height_cm >= 1.6 * short.height_cm:
        sun_side = (
            tall_r.center[1] > short_r.center[1]
            if hemisphere is Hemisphere.NORTH
            else tall_r.center[1] < short_r.center[1]
        )
        x_overlap = min(tall_r.x2, short_r.x2) - max(tall_r.x, short_r.x)
        dy = abs(tall_r.center[1] - short_r.center[1])
        if sun_side and x_overlap > -20 and dy <= tall.height_cm:
            if short.shade_tolerant:
                out.append(
                    PairFinding(
                        tall_p.id, short_p.id, "shading", "info", 3 * influence, gap,
                        "compat.shade_benefit", {"a": tall.name(lang), "b": short.name(lang)},
                    )
                )  # fmt: skip
            else:
                out.append(
                    PairFinding(
                        tall_p.id, short_p.id, "shading", "warning", -8 * influence, gap,
                        "compat.shading", {"a": tall.name(lang), "b": short.name(lang), "height": tall.height_cm},
                    )
                )  # fmt: skip
    return out
```

### 11.3 Seasonal work and fertiliser

```python
def bed_fertilizer_plan(
    area_m2: float, plants: Sequence[Plant], lang: str = "en", soil: SoilTest | None = None
) -> BedFertilizerPlan:
    """Base dressing for a bed before the given crops go in.

    With a soil test the rates are adjusted: little organic matter means more
    compost, high P/K means less fertiliser, a low pH gives a lime dose.
    """
    demand = dominant_demand(plants)
    only_legumes = bool(plants) and all(is_legume(p) for p in plants)
    compost = 0.5 if only_legumes else COMPOST_KG_M2[demand]
    fert = BASE_FERTILIZER_G_M2[demand]
    brassicas = any("brassica" in p.tags or p.family == "Brassicaceae" for p in plants)
    lime = 0.0
    adjustments: list[str] = []
    if soil is not None:
        if soil.organic_matter_pct is not None:
            if soil.organic_matter_pct < 2.0:
                compost *= 1.5
                adjustments.append("om_low")
            elif soil.organic_matter_pct > 6.0:
                compost *= 0.6
                adjustments.append("om_high")
        high_p = soil.p_mg is not None and soil.p_mg > P_HIGH
        high_k = soil.k_mg is not None and soil.k_mg > K_HIGH
        if high_p and high_k:
            fert *= 0.5
            adjustments.append("pk_high")
        elif (soil.p_mg is not None and soil.p_mg < P_LOW) or (soil.k_mg is not None and soil.k_mg < K_LOW):
            fert = max(fert, 30.0) * 1.3
            adjustments.append("pk_low")
        if soil.ph is not None:
            target = 7.0 if brassicas else 6.5
            if soil.ph < target - 0.2:
                lime = (target - soil.ph) * LIME_G_PER_PH_M2 * area_m2
                adjustments.append("lime")
            elif soil.ph > 7.5:
                adjustments.append("ph_high")
    return BedFertilizerPlan(
        compost_kg=round(compost * area_m2, 1),
        base_fertilizer_g=round(fert * area_m2),
        lime_check=brassicas and (soil is None or soil.ph is None),
        demand=demand,
        crops=sorted({p.name(lang) for p in plants}),
        lime_g=round(lime),
        adjustments=adjustments,
    )
```

Maintenance rules are anchored on frost dates (`GARDEN_RULES`, `GREENHOUSE_RULES`,
`PERENNIAL_RULES` in `engine/maintenance.py`); bed turnover adds *prepare soil* two
weeks before the next crop and *green manure* / *cover for winter* when a bed falls empty.

### 11.4 Irrigation safety

```python
def plan_irrigation(
    data: GardenData,
    recommendations: Mapping[str, IrrigationRecommendation],
    *,
    now: datetime,
    frost_by_zone: Mapping[str, FrostAssessment],
    outdoor_frost: FrostAssessment | None,
    outdoor_temp: float | None,
    zone_air: Mapping[str, float | None] | None = None,
    force: bool = False,
    bed_ids: set[str] | None = None,
    override_mm: float | None = None,
    only_if_needed: bool = False,
) -> IrrigationPlan:
    """Build today's run list.

    ``force`` (a manual run) ignores the mode switch and the "no water needed"
    check - never the safety rules.  ``only_if_needed`` keeps that check for a
    forced run (an automation that picks the moment, not the amount).
    ``override_mm`` waters a fixed depth.
    """
    cfg = data.settings.irrigation
    plan = IrrigationPlan()
    locked, lock_temp = frost_lockout(outdoor_frost, outdoor_temp, cfg.frost_lockout_c, now)
    plan.lockout, plan.lockout_temp = locked, lock_temp
    zone_air = zone_air or {}

    for bed in data.beds:
        if bed_ids is not None and bed.id not in bed_ids:
            continue
        rec = recommendations.get(bed.id)
        zone = data.zone(bed.zone_id)
        enclosed = bool(zone and zone.is_enclosed)
        if cfg.mode != "auto" and not force:
            plan.skipped[bed.id] = ("irrigation.skip.disabled", {})
            continue
        if not bed.irrigation_entity:
            plan.skipped[bed.id] = ("irrigation.skip.no_valve", {})
            continue
        flow = bed.flow_lpm
        if flow is None:
            plan.skipped[bed.id] = ("irrigation.skip.no_flow", {})
            continue
        # -- safety ------------------------------------------------------- #
        if enclosed:
            air = zone_air.get(bed.zone_id)
            if air is not None and air <= cfg.frost_lockout_c:
                plan.skipped[bed.id] = ("irrigation.skip.frost", {"temp": air, "limit": cfg.frost_lockout_c})
                continue
        else:
            z_locked, z_temp = frost_lockout(frost_by_zone.get(bed.zone_id), outdoor_temp, cfg.frost_lockout_c, now)
            if locked or z_locked:
                temp = z_temp if z_locked else lock_temp
                plan.skipped[bed.id] = ("irrigation.skip.frost", {"temp": temp, "limit": cfg.frost_lockout_c})
                continue
            rain = rec.rain_24h_mm if rec else 0.0
            if rain >= cfg.rain_skip_mm:
                plan.skipped[bed.id] = ("irrigation.skip.rain", {"mm": rain, "limit": cfg.rain_skip_mm})
                continue
        # -- amount ------------------------------------------------------- #
        if override_mm is not None:
            mm = override_mm
        elif rec is not None and rec.action is IrrigationAction.WATER and rec.amount_mm > 0:
            mm = rec.amount_mm
        elif force and not only_if_needed and rec is not None and rec.etc_24h_mm:
            mm = rec.etc_24h_mm  # manual run without need: replace one day of ET
        else:
            plan.skipped[bed.id] = ("irrigation.skip.not_needed", {})
            continue
        if override_mm is None:
            mm *= water_factor(data.settings, bed)  # what this bed really takes up (learned)
        liters = round(mm * bed.area_m2, 1)
        minutes = liters / flow
        capped = minutes > cfg.max_runtime_min
        minutes = round(min(minutes, cfg.max_runtime_min), 1)
        if capped:
            liters = round(minutes * flow, 1)
            mm = round(liters / bed.area_m2, 1) if bed.area_m2 else mm
        plan.runs.append(IrrigationRun(bed.id, bed.irrigation_entity, minutes, round(mm, 1), liters, capped))
    return plan
```

The controller (`controllers.py`) executes a plan under an `asyncio.Lock`: valve open →
(reports open) → settle → pump on → hold in 30 s steps (watching the valve) → pump off → lead
time → valve closed, and a `finally` block switches off every touched valve and the pump
(errors, cancellation, unload). Valve timers, lost/early‑closed/stuck valves, the valve test
and the leak watch were added in 1.4 – see 4.11.

### 11.5 Autofill

Greedy and explainable: crop demand from goals and plants per person, scaled to the
available area; bed score from rotation, glass need, companions, shade and containers;
shelf packing with tall crops away from the sun; neighbours trimmed by whole rows when a
crop does not fit; time, water and compost budgets; quick crops are split into three successive
sowings; a crop that is not placed gets its reason (too late, zone type, glass, frost, rotation,
bad neighbour, no room); the plan of the season being filled is used (the latest earlier plan,
copied on apply); learned yields (`records.learned_yields`) replace the generic yield once there is data.
A proposal is never stored until applied (`autofill_plan` with `apply`, `plan/autofill/apply`).

```python
def _bed_score(
    demand: CropDemand,
    bed: GardenBed,
    zone: Zone | None,
    placed: Sequence[CropDemand],
    db: PlantDatabase,
    history: list[Any],
    season: int,
    respect: bool = True,
    why: list[dict[str, Any]] | None = None,
) -> float | None:
    plant = demand.plant
    enclosed = bool(zone and zone.is_enclosed)
    score = 0.0
    if _prefers_glass(plant):
        score += 40 if enclosed else -10
    elif enclosed:
        score -= 25  # keep greenhouse space for crops that need it
    probe = Planting("probe", plant.id, bed.id, season)
    for finding in check_rotation(probe, bed, history, db):
        if finding.severity == "error":
            if why is not None:
                why.append({"code": "rotation", "params": {"family": finding.family, "season": finding.conflicting_season,
                                                           "years": finding.years_required}})  # fmt: skip
            return None
        score -= 20
    for other in placed:
        rel = db.relation(plant.id, other.plant.id)
        if rel.relation is Relation.ENEMY and respect:
            if rel.strength >= 2:
                if why is not None:
                    why.append({"code": "bad_neighbour", "params": {"plant_id": other.plant.id}})
                return None
            score -= 15
        elif rel.relation is Relation.FRIEND:
            score += 6 * rel.strength
        if other.plant.family == plant.family:
            score -= 2  # monoculture beds spread pests
    shade = bed.shade_pct if bed.shade_pct is not None else (zone.microclimate.shade_pct if zone else 0)
    if shade >= 30:
        score += 5 if plant.shade_tolerant else -15
    if bed.kind is BedKind.CONTAINER:
        score += 10 if "container" in plant.tags or plant.category is PlantCategory.HERB else -20
    if plant.perennial and bed.kind is not BedKind.CONTAINER:
        score -= 3  # perennials block a bed for years; prefer an edge bed
    return score
```

### 11.6 Printouts

`engine/pdf.py` implements one drawing API (`Surface`) twice: `PdfPage` (Helvetica and, since 1.4,
Times with WinAnsi, justified text, embedded JPEG photos and outlines; Flate streams, clipping
for hatch patterns, round‑cap dots) and `SvgPage` (panel preview). `engine/printout.py` lays out
each document once in millimetres; the full pipeline, the documents and the season book are in 4.18.

| Format | Size (mm) | Margins |
|---|---|---|
| A4 / A3 / A5 / Letter | ISO / US | 12 mm |
| reMarkable Paper Pro | 179.6 × 239.5 (4:3, 2160 × 1620 px @ 229 ppi) | left 13 mm (toolbar), others 6–7 mm |

Colour modes: *color* (family tints), *eink* (lighter tints + pattern per family),
*grayscale* (luminance conversion in the surface, patterns carry meaning).

### 11.7 Tests added in 1.1

ET₀ against FAO example 18 and the Hargreaves fallback, GDD accumulation and degree‑day
harvest shifts, stage Kc, water balance, fertiliser and nutrient index, Hutton/greenhouse
disease risk, irrigation frost lockout / rain skip / max runtime / advise mode, seasonal
and greenhouse tasks, soil prep with compost amount, green manure vs. winter cover,
perennial care, autofill (bounds, glass for tender crops, tall crops north, rotation,
budgets, containers), new companion factors, rotation alternatives, PDF validity
(xref offsets, operators, page sizes incl. reMarkable), e‑ink/grayscale rendering,
handbook EN/NL parity and glossary links; HA tests for every new service, the pump
interlock order, the frost lockout entity, shading control, autofill, the PDF view and the
new websocket commands.

```python
async def test_irrigation_dry_run_and_run_with_pump_interlock(
    hass: HomeAssistant, garden, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, calls = garden
    repo = entry.runtime_data.repo
    repo.data.settings.irrigation.pump_entity = "switch.pump"
    repo.data.settings.irrigation.max_runtime_min = 2
    sleeps: list[float] = []
    real_sleep = asyncio.sleep

    async def fast_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        await real_sleep(0)

    monkeypatch.setattr(controllers.asyncio, "sleep", fast_sleep)
    switched: list[tuple[str, bool]] = []

    async def fake_switch(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        # The switch domain belongs to Hortulus' own platform in this test,
        # so record at the controller boundary instead of mocking services.
        switched.append((entity_id, on))
        hass.states.async_set(entity_id, "on" if on else "off")  # the valve reports open: the pump may start

    monkeypatch.setattr(controllers, "_switch", fake_switch)

    dry = await hass.services.async_call(
        DOMAIN, "run_irrigation_plan", {"dry_run": True, "amount_mm": 10}, blocking=True, return_response=True
    )
    assert dry["started"] is False and len(dry["runs"]) == 2
    assert all(run["minutes"] <= 2 for run in dry["runs"]) and any(run["capped"] for run in dry["runs"])
    assert calls == []

    run = await hass.services.async_call(
        DOMAIN, "run_irrigation_plan", {"beds": ["Bed 1"], "amount_mm": 1}, blocking=True, return_response=True
    )
    assert run["started"] is True
    await hass.async_block_till_done(wait_background_tasks=True)
    # valve open -> pump on -> pump off -> valve closed, and nothing left on.
    assert switched[:4] == [
        ("switch.valve_bed_1", True),
        ("switch.pump", True),
        ("switch.pump", False),
        ("switch.valve_bed_1", False),
    ]
    assert switched[-1] == ("switch.pump", False)  # final safety sweep
    assert 0.5 * 60 in sleeps  # 1 mm x 2 m² = 2 L at 4 L/min = 0.5 min
    event = repo.data.irrigation_log[-1]
    assert event.source == "service" and event.liters == 2.0
    assert not entry.runtime_data.irrigation.running
```

### 11.8 New entities, services and storage

See [ENTITY_REFERENCE](../en/ENTITY_REFERENCE.md). Storage schema 1.5 added `features`,
`water_balance`, `irrigation_log`, `settings.irrigation` and `settings.resources`
(migration `_v1_4_to_1_5`); later minors are listed in 3.6 (current: 1.8).

### 11.9 Release map 1.0 → 2.2.0

Where each release put its code (details per release in [`CHANGELOG.md`](../../CHANGELOG.md)).

| Release | Theme | Main code |
|---|---|---|
| 1.0 | planner, plant database, task engine, frost / greenhouse / irrigation advice, calendar, to‑do, notifications, EN/NL | `engine/{models,schedule,compatibility,weather,watering,tasks}`, `coordinator`, panel |
| 1.1 | print module, handbook, Autofill, seasonal calendar, 140 crops, agronomy (Penman‑Monteith, Kc, water balance, phenology), companion factors, irrigation controller, vent / shade control | `engine/{pdf,printout,handbook,autoplan,maintenance,phenology,waterbalance,fertilizer,irrigation}`, `controllers.py`, `printing.py` |
| 1.2 | three‑step garden plan, perennials across seasons, 232 crops, Advice tab and Q&A, 21 yearly rules, weather episodes, reminders | `engine/{advisor,qa,qa_kb,supplies,weather_tasks}` |
| 1.3 | Journal (diary, harvest, seeds, water), year view, Lovelace card, household assignment, soil analysis, Assist, private PDF exports | `engine/records`, `voice.py`, `frontend/src/card`, `printing.ExportView` |
| 1.4 | season book, more than one garden, water meter and leaks, valve timers / test / left‑open watch, phone buttons, quick harvest, photo timeline, seeds to buy, weather tab, wall screen, colour themes, crops tab + planning, season report, analysis and one‑click repairs, plan per year + year‑end transition, system log with undo, plan compare, new elements | `engine/{seasonbook,planning,diagnose,seasons,syslog}`, `gardens.py`, `actions.py`, storage schema 1.6 and 1.7 |
| 1.5 | French, pest calendar, Kitchen (ready to pick, surplus, cost and harvest), sensor‑taught water balance, blueprints, starter garden, season archive | `engine/{pests,kitchen,archive}`, `engine/texts_garden`, `blueprints/`, `op_starter_garden` |
| 1.6 | planner in five steps, overlap (coverage), ecological gardening and food forest, entity drop‑downs, new‑season choices | `engine/{eco,coverage}`, `util/entities.ts` |
| 1.6.1 | `panel.config.tabs` for a read‑only subset of the panel | `hortulus-panel.ts`, `garden-viewer.ts` |
| 1.7 | Cooking (cookbook, own recipes, shopping list, PDFs), "look at a garden", whole‑code review fixes (admin‑only services, valve safety, input checks) | `engine/{cooking,cooking_dishes,cooking_extras}`, `cooking-view.ts` |
| 1.7.1 | per‑item fridge ideas, 36 more dishes in four courses plus menus and a preserving chapter, light/dark appearance, own version of a recipe, review findings (food safety, imports, permissions) | `cooking_extras.py` (`USES` / `PREP` / `DEPENDS`), `cooking_dishes.py`, `util/theme.ts` |
| 1.8.0 | climate history and statistics (every temperature sensor, recorder and Open‑Meteo gap filling, months kept for good, measured frost dates), weather station sensors, four climate sensors; growth, water balance, disease and tasks follow the logged weather | `engine/climate.py`, `climate_history.py`, `components/climate-history.ts`, storage schema 1.8 |
| 1.8.1 | review round: measured days stay measured, one task per weather episode, rain gauge and water meter units, reload and options fixes, greenhouse entities follow the zone type | `engine/climate.py`, `engine/weather_tasks.py`, `coordinator.py`, `entity.py`, `websocket_api.py` |
| 2.0.0 | extras, all on and switchable in Settings → Extras: garden sayings, estimated soil temperature, water forecast per bed, silent‑sensor alert, season and month summary against last year, own frost dates in one click, weather station CSV import, solar‑aware watering, climate line on the card; release workflow | `engine/slogans.py`, `engine/climate.py`, `engine/waterbalance.py`, `controllers.py`, `card/hortulus-tasks-card.ts`, `.github/workflows/release.yml` |
| 2.1.0 | battery as a start signal, rain water first with pump energy, frost heating with a weekly budget, self‑learning water factor per bed, harvest expectations from own years, photo diagnosis through an AI task, tasks copied into another calendar; WCAG 2.1 AA check and CI on the oldest supported Home Assistant | `engine/adaptive.py`, `engine/photo_diagnosis.py`, `engine/records.py`, `controllers.py`, `calendar_mirror.py`, `frontend/test-ui/a11y.mjs` |
| 2.2.0 | the wall screen as a grid of blocks the gardener arranges (drag, width, 18 blocks incl. rain radar, agenda, weather saying, recipe tip, organic fact; Dutch for now), kept in `settings.wall_layout` | `engine/wall.py`, `frontend/src/views/wall-view.ts`, `websocket_api.py` (`wall/data`, `wall/layout`) |

---

[← 10. Documentation Files (README etc.)](10-documentation-files-readme-etc.md) · [↑ Blueprint contents](../BLUEPRINT.md)
