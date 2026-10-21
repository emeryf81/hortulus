# Référence des entités, services et événements

Les identifiants d'entités ci-dessous supposent une installation de Home Assistant en **anglais** et
le jardin d'exemple (*Bed 1*, *Greenhouse Zone A*). Home Assistant dérive les identifiants d'entités
du nom d'entité traduit et du nom de l'appareil au moment où une entité est créée pour la première
fois ; sur une installation en français, `sensor.hortulus_frost_risk_next_48h` devient donc
`sensor.hortulus_risque_de_gel_dans_les_48_h`. Les identifiants uniques ne changent jamais ;
renommez librement. Un second jardin ([plusieurs jardins](CONFIGURATION.md#9-plusieurs-jardins))
reçoit ses propres appareils et entités ; son entrée s'appelle « Hortulus 2 », ses identifiants d'entités
propres au jardin commencent donc par `sensor.hortulus_2_`.

## Appareils

| Appareil | Créé pour | Contient |
|---|---|---|
| **Hortulus** | l'intégration | capteurs globaux du jardin, calendrier, liste de tâches, boutons, commandes d'irrigation |
| **<Nom de la planche>** | chaque planche | humidité, irrigation, score d'association, besoin d'eau, équilibre nutritif, déficit hydrique |
| **<Nom de la zone>** | chaque zone | risque de maladie, risque de gel 48 h, degrés-jours ; les serres et les châssis ont aussi conseil, stress thermique, ombrage |

Les planches et zones ajoutées dans le planificateur reçoivent aussitôt leurs appareils ; supprimer
une planche ou une zone supprime son appareil et ses entités.

## Capteurs

### `sensor.hortulus_frost_risk_next_48h`
Énumération : `none` · `low` · `moderate` · `high` · `unknown`.
Classification du minimum **au niveau des plantes** (température prévue à 2 m + correction de
rayonnement par nuit claire et calme) : ≤ 0 °C *high*, ≤ 2 °C *moderate*, ≤ 4 °C *low*.

| Attribut | Exemple | Signification |
|---|---|---|
| `min_temperature` | `-2.0` | température de l'air prévue la plus basse (°C) |
| `plant_level_min_temperature` | `-4.0` | après correction du gel au sol |
| `min_at` | `2026-03-29T04:00:00+00:00` | moment du minimum |
| `first_below_zero_at` | … | première heure à 0 °C ou moins au niveau des plantes |
| `hours_below_zero` | `5.0` | durée (insensible aux changements d'heure) |
| `source` | `hourly` | chaîne de repli `hourly` → `daily` → `sensor` → `none` |
| `zones` | `{"gh_a": "low"}` | niveau par zone (les serres sont tamponnées) |

L'état est `unknown` quand il n'y a ni prévision ni température extérieure.

### `sensor.hortulus_growing_degree_days`
Total de la saison (°C·j, state class `total`) depuis 30 jours avant les dernières gelées, base
10 °C, méthode de la moyenne modifiée plafonnée à 30 °C. Attributs : `base_temperature`, `since`,
`days_counted`.

### `sensor.hortulus_tasks_due_today`
Nombre de tâches ouvertes dues aujourd'hui ou en retard (unité `tasks`). Attributs :
`estimated_minutes`, `overdue`, `tasks` (jusqu'à 25 × `{id, title, type, priority, due}` – pratique
dans les templates).

### `sensor.hortulus_next_task`
Titre de la prochaine tâche ouverte (échéance la plus proche, priorité la plus haute d'abord ;
tronqué à 255 caractères).

### `sensor.<bed>_moisture_status`  *(« garden.bed_moisture_status »)*
Énumération : `dry` · `slightly_dry` · `optimal` · `wet` · `unknown`.

| Attribut | Signification |
|---|---|
| `moisture` | teneur volumique en eau actuelle (%) |
| `target_low` / `target_high` | plage optimale pour la culture active la plus gourmande en eau, décalée selon le type de sol |
| `water_need` | `low` / `medium` / `high` |
| `soil_temperature` | °C, si associée |
| `moisture_entity` | le capteur source |

Plages (limon ; sableux −6, argileux +6, limoneux fin +3, tourbeux +8, calcaire −2, terreau +4) :

| Besoin en eau | sec en dessous de | optimal | humide au-dessus de |
|---|---|---|---|
| low | 18 % | 22–38 % | 55 % |
| medium | 25 % | 30–45 % | 60 % |
| high | 32 % | 38–55 % | 68 % |

### `sensor.<bed>_irrigation_recommendation`  *(« garden.irrigation_recommendation »)*
État : millimètres à apporter maintenant. Attributs : `bed_id`, `action` (`none`, `water`,
`skip_rain_expected`, `check_manually`), `amount_mm`, `liters`, `duration_min` (exige un débit –
saisi ou appris à partir du compteur d'eau), `status`, `moisture`, `target_low` / `target_high`,
`water_need`, `etc_24h_mm`, `rain_24h_mm`, `rain_48h_mm`, `confidence` (`high` avec un capteur
d'humidité et une prévision ; `medium` avec un capteur mais sans prévision, ou quand c'est le bilan
hydrique de la planche qui décide ; `low` sans l'un ni l'autre), `priority`, `reasons`,
`irrigation_entity`. Sans capteur d'humidité, le bilan hydrique est utilisé (arroser quand la moitié
de l'eau disponible pour les plantes est épuisée).

### `sensor.<bed>_companion_score` *(désactivé par défaut)*
0–100 % (50 = neutre). Attributs : `conflicts`, `rotation_conflicts`.

### `sensor.<zone>_greenhouse_advice`
Énumération : `none` · `ventilate` · `shade` · `close_up` · `heat`. Seulement pour les zones fermées
(serre, châssis). Attributs : `action`, `inside_now_c`, `forecast_max_c`, `forecast_min_c`,
`limit_max_c`, `limit_min_c`, `limiting_plants`, `reasons`, `frost_risk`, `air_temperature`,
`temperature_unit`.

### `sensor.hortulus_reference_evapotranspiration_today`
ET₀ du jour en mm (Penman‑Monteith FAO‑56 quand l'humidité et le vent sont connus,
Hargreaves‑Samani sinon). Attributs : `method`, `tmin`, `tmax`, `rh_min`, `rh_max`, `wind_kmh`,
`cloud_fraction`, `rain_mm`, `forecast` (3 jours : `{day, et0, rain}`).

### `sensor.hortulus_degree_days_today`
Degrés-jours attendus aujourd'hui (°C·j, même base que le capteur de degrés-jours de la saison).

### `sensor.<bed>_nutrient_balance`
0–100 : mesures NPK (mg/kg) ou CE (mS/cm) comparées aux besoins en N‑P‑K des cultures actives (100 =
tout dans la plage). Attributs : `index`, `status` (`unknown`, `deficient`, `balanced`, `excess`),
`deficits` (`n`/`p`/`k`/`ec`), `excess`, `source` (`npk`/`ec`/`none`).
Associez les sondes dans Paramètres → Planches et capteurs.

### `sensor.<bed>_soil_water_deficit` *(désactivé par défaut)*
Épuisement de la zone racinaire sous la capacité au champ, en mm, d'après le bilan hydrique
quotidien. Attributs : `available_water_mm` (réserve utile pour le sol et la profondeur
d'enracinement), `crop_coefficient` (Kc de la culture active la plus gourmande en eau). L'arrosage
est conseillé quand la moitié de la réserve utile est consommée.

### `sensor.<zone>_disease_risk`
Énumération `none` · `low` · `moderate` · `high` · `unknown`. Attributs : `wet_hours_48h`,
`hutton_period` (temps à mildiou prévu), `humidity`, `leaf_wet`, `reasons`. Le risque regarde aussi
en arrière, dans l'[historique du climat](CONFIGURATION.md#historique-du-climat) (zones extérieures) :
une période de Hutton déjà passée d'après les jours enregistrés donne `high` (raison
`hutton_logged`), et au moins deux jours humides enregistrés sur les trois derniers (≥ 5 mm de pluie
ou humidité moyenne ≥ 90 %) relèvent le niveau (raison `wet_days_logged`). Autres raisons :
`hutton_period`, `long_wet_period`, `wet_hours`, `humid_greenhouse_air`, `leaf_wet_now`.

### `sensor.<zone>_degree_days_this_season` *(désactivé par défaut)*
Degrés-jours de la saison pour la zone. Les zones fermées comptent les jours enregistrés de leur
propre capteur de température de l'air ; les jours sans ce capteur (ou une serre sans capteur)
prennent la journée extérieure avec l'effet tampon de la serre (+2 °C la nuit, +4 °C le jour). Les
zones extérieures reprennent le total du jardin.

### `sensor.hortulus_harvest_this_season`
kg récoltés cette saison (d'après le journal des récoltes ; device class poids, state class
`total`). Attributs : `season`, `per_crop_kg` (les plus gros d'abord).

### `sensor.hortulus_garden_water_7_days`
Litres d'eau du réseau utilisés au jardin pendant les 7 derniers jours, d'après le compteur d'eau de
Paramètres → Compteur d'eau et tonneau de pluie (un relevé par jour est stocké). Attributs :
`season_l`, `per_day`.

### `sensor.hortulus_rain_water_available`
Litres dans les tonneaux de pluie maintenant (niveau du tonneau en % × capacité totale, tous deux
réglés dans Paramètres → Compteur d'eau et tonneau de pluie). Les descriptions des tâches d'arrosage
indiquent combien en utiliser d'abord.


### `sensor.hortulus_pump_energy_this_year` (2.1)
kWh consommés par les pompes d'arrosage cette année civile (device class energy, `total_increasing`), à partir de la
puissance des pompes sous *Matériel d'irrigation*. Attributs : `rain_water_liters`, `mains_water_liters` (arrosé cette année par source).

### `sensor.hortulus_greenhouse_heating_this_week` (2.1)
kWh du chauffage antigel cette semaine ISO (seulement si une zone a un chauffage). Attributs par zone : `kwh`,
`budget_left_kwh`.
### Capteurs de climat (historique du climat)
Quatre capteurs du jardin résument ce que la météo a vraiment fait, d'après l'[historique du
climat](CONFIGURATION.md#historique-du-climat), chacun avec la valeur de la même période l'an
dernier :

| Entité (nom français) | État | Période |
|---|---|---|
| `sensor.hortulus_rain_7_days` (*Pluie (7 jours)*) | pluie tombée, mm | les 7 derniers jours, aujourd'hui compris |
| `sensor.hortulus_mean_temperature_7_days` (*Température moyenne (7 jours)*) | moyenne des températures, °C (device class température) | les 7 derniers jours |
| `sensor.hortulus_sunshine_7_days` (*Ensoleillement (7 jours)*) | heures d'ensoleillement, h | les 7 derniers jours |
| `sensor.hortulus_frost_nights_this_season` (*Nuits de gel cette saison*) | nombre de nuits sous 0 °C (state class `total`) | depuis le début de la saison (1er janvier ; 1er juillet dans l'hémisphère sud) |

L'état est `unknown` tant qu'aucun jour n'est enregistré pour la période. Attributs (tous sur la
même période) :

| Attribut | Signification |
|---|---|
| `days_logged` | jours enregistrés dans la période |
| `last_year` | la valeur du capteur pour la même période il y a un an (`null` si elle n'a pas été enregistrée) |
| `lowest` / `highest` | température la plus basse / la plus haute (°C) |
| `rain_mm` | pluie (mm) |
| `sunshine_h` | heures d'ensoleillement |
| `gust_max_kmh` | rafale (ou vent) la plus forte (km/h) |
| `et0_mm` | évaporation de référence ET₀ (mm) |
| `water_balance_mm` | pluie moins évaporation (mm) |

```yaml
# Une semaine bien plus sèche que l'an dernier ?
condition: template
value_template: >
  {{ states('sensor.hortulus_rain_7_days') | float(0) <
     (state_attr('sensor.hortulus_rain_7_days', 'last_year') or 0) / 2 }}
```

## Capteurs binaires

| Entité | Classe d'appareil | Allumé quand |
|---|---|---|
| `binary_sensor.hortulus_frost_warning` | cold | risque de gel *moderate* ou *high* (inconnu sans prévision) ; attributs `level`, `min_temperature` (au niveau des plantes), `plants_at_risk` |
| `binary_sensor.<zone>_frost_risk_48h` | cold | le risque de gel de cette zone au niveau des plantes est *moderate* ou *high* ; attributs `level`, `min_temperature`, `min_at` |
| `binary_sensor.<bed>_needs_water` | problem | l'action d'irrigation est `water` |
| `binary_sensor.<zone>_heat_stress` | heat | le conseil serre / châssis est `ventilate` ou `shade` |
| `binary_sensor.hortulus_irrigation_frost_lockout` | safety | les vannes extérieures sont bloquées (gel dans les 12 h ou trop froid maintenant) ; attributs `temperature`, `limit` |
| `binary_sensor.hortulus_irrigation_running` | running | un arrosage est en cours ; attributs `bed_id`, `ends_at`, `last_error` |

## Commandes d'irrigation et de climat

| Entité | Remarques |
|---|---|
| `switch.hortulus_automatic_irrigation` | allumé = mode `auto` (les vannes s'ouvrent à l'heure de début), éteint = `advise` |
| `select.hortulus_irrigation_mode` | `off` · `advise` · `auto` |
| `number.hortulus_irrigation_max_runtime` | minutes par vanne (1–180, pas de 1) |
| `number.hortulus_irrigation_frost_lockout_temperature` | °C (−5 à 10, pas de 0,5) ; les vannes extérieures restent fermées à cette température ou en dessous |
| `number.hortulus_skip_irrigation_above_rain` | mm prévus dans les 24 prochaines heures (0–30, pas de 0,5) |
| `button.hortulus_water_now` / `button.hortulus_stop_watering` | arroser maintenant chaque planche qui en a besoin (les règles de sécurité s'appliquent) / arrêter et tout fermer |
| `select.<zone>_shading` | `auto` (suit le conseil) · `on` · `off` pour l'écran d'ombrage de la zone (serres et châssis) |

Le sélecteur de mode, les trois nombres et l'interrupteur modifient les mêmes réglages d'irrigation
que le panneau. L'interrupteur a les attributs `start_time`, `pump` et `valves` ; l'éteindre arrête
aussi un arrosage en cours. Les nombres et le sélecteur de mode sont des entités de
*configuration*.

**Règles de sécurité** (aussi pour les arrosages manuels) : une seule vanne à la fois ; la pompe ne
tourne que si une vanne est ouverte (vanne → 1 s → pompe en marche … pompe arrêtée → *avance* en
secondes → vanne fermée) ; durée maximale (une vanne avec sa propre minuterie reçoit des ouvertures
qui restent en dessous) ; blocage en cas de gel pour les vannes extérieures, sur les 12 prochaines
heures ; arrêt en cas de pluie ; une vanne qui reste fermée termine l'arrosage sans comptabiliser
d'eau ; une vanne qui ne répond plus pendant une minute alors que la pompe tourne termine l'arrosage
et arrête la pompe ; chaque vanne ouverte et la pompe sont éteintes à la fin, après une erreur et en
cas d'annulation. Chaque arrosage est enregistré (litres du compteur d'eau s'il y en a un) et
alimente le bilan hydrique de la planche. Après chaque arrosage, Hortulus vérifie que la vanne indique
fermée ; une vanne ou une pompe ouverte plus longtemps que la durée max. + 10 minutes alors qu'aucun
arrosage n'est actif déclenche un bandeau du tableau de bord, une notification et une entrée du
journal système (*Fermer la vanne*). Au moins 5 L d'eau comptés en 15 minutes alors que toutes les vannes
sont fermées sont signalés comme une fuite (peut être désactivé dans les Paramètres).

## Calendrier, liste de tâches, boutons

| Entité | Remarques |
|---|---|
| `calendar.hortulus_garden_tasks` | Événements sur la journée pour chaque tâche sauf celles passées (✓ = faite, ‼/! = urgente/haute). L'entité montre la tâche ouverte en cours ou la suivante ; le travail en retard compte comme étant aujourd'hui. Créez, modifiez (déplacer la date reporte la tâche, les tâches dépendantes suivent ; le résumé et la description modifient la tâche) et supprimez depuis le calendrier HA. |
| `todo.hortulus_this_week` | Tâches ouvertes dues dans les 7 jours (+ en retard), plus les tâches terminées au cours des 2 derniers jours. Cocher un élément termine la tâche, décocher la rouvre ; création, renommage, changement d'échéance ou de description et suppression sont pris en charge. |
| `button.hortulus_generate_tasks` | Régénérer les tâches maintenant (entité de configuration). |
| `button.hortulus_refresh_forecast` | Récupérer la prévision maintenant (entité de diagnostic). |

Le calendrier contient aussi les **travaux saisonniers du jardin** (clés `m:…`) : planifier la saison,
commander les graines, préparer la station de semis, retourner le compost, pailler, préparer chaque
planche avant la plantation (avec kg de compost et g d'engrais), engrais vert ou couverture
hivernale pour les planches vides, vidanger les tuyaux avant le gel, repos hivernal, analyse de sol
toutes les trois saisons, entretien des outils, et par serre : nettoyage de printemps, ombrage
activé / désactivé, isolation d'hiver et nettoyage et désinfection d'automne. Les vivaces sont
rabattues, divisées (tous les 3 ans) et protégées l'hiver selon leurs étiquettes. Désactivez-les dans
Paramètres → Ressources (remplissage auto).

---

## Services (actions)

Tous les services sont dans le domaine `garden_manager` et renvoient des données quand ils sont
appelés avec `response_variable` (sauf `delete_task`, `remove_planting`, `stop_irrigation` et
`assign_task`, qui ne renvoient rien ; `export_plan` ne renvoie que des données).

Commun à tous les services :

* **`garden`** (facultatif, texte) : le titre ou l'identifiant d'entrée du jardin visé quand vous en
  avez [plusieurs](CONFIGURATION.md#9-plusieurs-jardins). Sans lui, le premier jardin est utilisé.
* Les services qui modifient le plan, les données de plantes ou le matériel – `import_plan`,
  `add_planting`, `update_planting`, `remove_planting`, `run_irrigation_plan`, `stop_irrigation`,
  `set_shading_mode`, `autofill_plan`, `export_pdf`, `generate_tasks`, `recalculate_plan`,
  `install_voice_sentences` – exigent un **administrateur** quand ils sont appelés par un
  utilisateur (comme ses commandes websocket). Les automatisations et les scripts s'exécutent sans
  utilisateur et sont autorisés.

| Groupe | Services |
|---|---|
| Tâches | `add_task`, `complete_task`, `postpone_task`, `delete_task`, `generate_tasks`, `recalculate_plan` |
| Plan | `export_plan`, `import_plan`, `add_planting`, `update_planting`, `remove_planting`, `autofill_plan`, `export_pdf` |
| Irrigation et climat | `run_irrigation_plan`, `stop_irrigation`, `set_shading_mode` |
| Enregistrements | `log_harvest`, `add_journal_entry`, `save_soil_test` |
| Ménage et voix | `assign_task`, `install_voice_sentences` |

### `garden_manager.add_task`
| Champ | Type | Remarques |
|---|---|---|
| `title` | string | obligatoire |
| `due_date` | date | aujourd'hui par défaut |
| `type` | enum | `custom` par défaut ; voir la liste ci-dessous |
| `description` | string | |
| `priority` | `low`/`normal`/`high`/`urgent` | `normal` par défaut |
| `estimated_minutes` | int | 1–1440 |
| `bed` | string | **identifiant ou nom** de la planche (insensible à la casse) |
| `planting_id` | string | |
| `recurrence_days` | int | 1–365 ; répéter N jours après chaque réalisation |
| `until` | date | dernière date de la récurrence |

Types de tâches : `custom`, `sow_indoor`, `sow_direct`, `harden_off`, `transplant`, `thin`, `stake`,
`prune`, `pinch`, `earth_up`, `feed`, `water`, `weed`, `pest_check`, `harvest`, `ventilate`,
`shade`, `frost_protect`, `soil_prep`, `compost`, `green_manure`, `mulch`, `clean_greenhouse`,
`winter_prep`, `plan_season`, `tool_care`, `soil_test`, `cut_back`, `divide`, `protect`, `clean`,
`tie_in`, `thin_fruit`, `pollinate`, `check`, `make_feed`.

Réponse : `{task_id}`.

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
Champs : `task_id`, `note`, `photos` (liste d'identifiants/URL d'images), `skipped` (bool, false par
défaut). Terminer une tâche de **semis**, de **plantation** ou la première tâche de **récolte** met
à jour la culture (`sown_on`, `transplanted_on`, `harvest_started_on`, statut), ce qui réancre toutes
les tâches d'entretien sur les dates réelles. Les tâches récurrentes programment leur occurrence
suivante `interval` jours après la *réalisation*. Une tâche d'arrosage terminée deux fois ne
comptabilise son eau qu'une fois.
Réponse : `{task_id, status, next_task_id, next_due}`.

### `garden_manager.postpone_task`
Champs : `task_id`, `days` (−365…365) **ou** `to_date`, `reason`, `cascade` (true par défaut).
Les tâches dépendantes de la même culture que vous n'avez pas déplacées à la main se décalent du
même écart (reporter *semer les tomates* déplace *endurcir* et *planter*).
Réponse : `{task_id, due, shifted: [ids], warnings: ["beyond_window", …]}`.

### `garden_manager.delete_task`
Supprime les tâches de l'utilisateur ; les tâches générées sont marquées *passées* (sinon elles
seraient recréées).

### `garden_manager.assign_task`
Champs : `task_id`, `assignee` (entité `person.*`, vide pour retirer l'attribution). Les nouvelles
tâches sont attribuées automatiquement d'après Paramètres → Ménage et voix (une personne par défaut
et une par type de tâche).

### `garden_manager.generate_tasks`
Régénération idempotente à partir du plan + de la base + des capteurs + de la prévision.
Réponse : `{created, updated, removed, open_tasks}`.

### `garden_manager.recalculate_plan`
Récupère à nouveau la prévision et recalcule tout. Réponse : `{frost_risk,
weather_available, alerts, season}`.

### `garden_manager.export_plan` *(réponse uniquement)*
Champs : `include_tasks` (false par défaut), `seasons` (liste d'années ; limite les cultures et les
plans mis de côté à ces saisons). Renvoie le document de plan (voir la
[configuration](CONFIGURATION.md#5-format-dimportation-et-dexportation)).

### `garden_manager.import_plan`
Champs : `plan` (objet, obligatoire), `mode` (`merge` par défaut | `replace`). Un fichier refusé ne
change rien. Réponse : nombres par collection (`zones`, `beds`, `features`, `layouts`, `plantings`,
`custom_plants`, `rotation_history`, `tasks`, `archived_plans`).

### `garden_manager.add_planting` / `update_planting` / `remove_planting`
`add_planting` : `plant_id` et `bed` (identifiant ou nom) sont obligatoires ; facultatifs : `season`
(l'année civile en cours par défaut), `layout` (`single` / `row` / `block`, `row` par défaut), `x_cm`,
`y_cm`, `width_cm` (largeur de la planche par défaut), `length_cm` (un rang par défaut), `count`,
`method` (`indoor_sow` / `direct_sow` / `transplant`), `status` (`planned`, `sown_indoors`, `sown`,
`transplanted`, `harvesting`, `finished`, `failed`), dates planifiées `sow_date` /
`transplant_date`, dates réelles `sown_on` / `transplanted_on`, `notes`. La culture doit se trouver
sur une planche du plan de sa propre saison. Les tâches suivent automatiquement. `update_planting`
prend `planting_id` plus n'importe lequel de ces champs (et `plant_id`, `bed`) ; `remove_planting`
prend `planting_id`. Réponses : `{planting_id, planting}` / `{planting}` / aucune.

```yaml
action: garden_manager.add_planting
data: {plant_id: dill, bed: Bed 1, layout: row}
response_variable: added
```

### `garden_manager.autofill_plan`
Propose un plan de saison. Champs : `season`, `beds` (par défaut : toutes les planches vides),
`replace`, `apply` (l'enregistrer), et les ressources `household_size` (1–20), `hours_per_week`
(0–80), `water_liters_per_week`, `compost_kg`, `goals` (`fresh`, `storage`, `herbs`, `pollinators`,
`winter`, `perennials`, `easy`), `wanted`, `excluded`, `max_crops` (1–60, 16 par défaut). Les
ressources omises viennent de Paramètres → Ressources (remplissage auto).
Réponse : `plantings`, `placements` (culture, planche, nombre, m², kg, min/semaine, L/semaine,
semis), `skipped`, `warnings`, `summary`, et `applied: true` quand c'est enregistré.

### `garden_manager.run_irrigation_plan`
Champs : `dry_run`, `beds` (liste d'identifiants ou de noms), `amount_mm` (0,5–50), `only_if_needed`
(false par défaut). Renvoie le plan (`runs` avec `bed_id, entity_id, minutes, mm, liters, capped` ;
`skipped` et `skipped_reasons` par planche ; `lockout`, `lockout_temp`, `total_minutes`, `started`)
et le démarre sauf `dry_run`. Ignore le mode d'irrigation, jamais les règles de sécurité. Avec
`only_if_needed`, une automatisation choisit le moment et Hortulus décide encore si une planche a
besoin d'eau. Échoue (sauf `dry_run`) tant qu'un arrosage est en cours.
`garden_manager.stop_irrigation` arrête un arrosage.

### `garden_manager.set_shading_mode`
Champs : `zone` (identifiant ou nom d'une serre / d'un châssis), `mode` (`auto`/`on`/`off`).
Réponse : `{zone_id, mode}`.

### `garden_manager.export_pdf`
Écrit un PDF dans `/config/hortulus/exports/` (privé ; la réponse contient un lien de téléchargement
signé valable 7 jours). Champs :
`document` (`garden`, `zone`, `beds`, `tasks`, `season`, `year`, `blank`, `plants`, `book`),
`page` (`a4`, `a3`, `a5`, `letter`, `remarkable`), `landscape`, `color_mode` (`color`, `eink`,
`grayscale`), `season`, `zone_id`, `bed_ids`, `days` (1–120, 28 par défaut, pour `tasks`),
`notes` (grille de points, true par défaut), `grid` (grille de 10 cm sur les fiches de planches, true
par défaut), `title`. `book` est le livre de saison. Réponse : `{path, url, filename, bytes}`.

```yaml
# Every Monday morning: this week's checklist for the reMarkable
action: garden_manager.export_pdf
data: {document: tasks, page: remarkable, color_mode: eink, days: 7}
```

### `garden_manager.log_harvest`
Ajoute une récolte au journal. Champs : `planting_id` *ou* `plant_id` *ou* `plant` (un identifiant
**ou un nom** comme `Tomate` ; pratique pour un tag NFC ou un bouton de tableau de bord), `bed` (pour
retrouver la culture dans le jardin), `kg` (0–500), `count` (au moins l'un de `kg` et `count` est
obligatoire), `quality` (1–5), `day`, `note`. La première récolte d'une culture la passe à *en
récolte*. Réponse : `{harvest}`. Après une saison avec des données, Hortulus utilise **vos propres
kg/m²** à la place du rendement de la base (remplissage auto, conseils, liste de courses).

### `garden_manager.add_journal_entry`
Une note de carnet avec photos facultatives. Champs : `text` (obligatoire), `kind` (`note` par défaut,
`observation`, `problem`, `milestone`), `planting_id`, `bed` (identifiant ou nom), `photos`
(identifiants d'images). L'auteur est l'utilisateur appelant. Réponse : `{entry}`.

### `garden_manager.save_soil_test`
Enregistre une analyse de sol pour une planche (une par date ; la même date remplace). Champs :
`bed`, `date` (les deux obligatoires), `ph` (3–10), `organic_matter_pct`, `p_mg`, `k_mg` (mg pour
100 g), `notes`. Le plan de fertilisation et le conseil de chaulage de la planche suivent la dernière
analyse. Réponse : `{soil_test}`.

### `garden_manager.install_voice_sentences`
Copie les phrases Assist (EN + NL + FR) dans `/config/custom_sentences/<lang>/hortulus.yaml` et
recharge l'agent de conversation. Champ : `overwrite` (false par défaut : les fichiers que vous avez
modifiés sont conservés). Réponse : `{written: [paths]}`. Voir *Voix (Assist)* plus bas.

---

## Événements

| Événement | Déclenché quand | Données |
|---|---|---|
| `garden_manager_task_due` | récapitulatif du matin (chaque tâche due) et quand une tâche issue d'un capteur ou de la météo apparaît en cours de journée | `task_id, type, title, priority, due, bed_id, zone_id, planting_id` |
| `garden_manager_task_completed` | une tâche est terminée / passée | `task_id, type, title, skipped, planting_id, bed_id, next_task_id` |
| `garden_manager_frost_warning` | nouvelle alerte de gel (une fois par zone et par nuit) | `key, severity, zone_id, level, temp, when, plants` |
| `garden_manager_heat_warning` | nouvelle alerte de chaleur en serre (une fois par zone et par jour) | `key, severity, zone_id, zone, temp, action` |
| `garden_manager_irrigation_recommended` | une planche a besoin d'eau (une fois par planche et par jour) | `bed_id` + tous les attributs de la recommandation d'arrosage |
| `garden_manager_plan_updated` | le plan, les plantes, les paramètres ou une importation ont changé | `reason` (`plan`, `plants`, `settings`, `import`), `revision` |
| `garden_manager_irrigation_run` | une vanne a terminé (ou a été arrêtée) | `bed_id, bed, minutes, liters, mm, source` |

`severity` vaut `info`, `warning` ou `critical` ; `zone_id` est vide pour l'alerte de gel globale au
jardin (extérieur).

**Gel constaté (`alert.frost_logged`).** Quand l'historique du climat montre que la nuit dernière
est descendue sous 0 °C et que des cultures frileuses (minimum de la culture au-dessus de la
température mesurée) étaient en place hors serre, Hortulus lève l'alerte *« Il a gelé (… °C) :
vérifiez ces cultures pour les dégâts de gel »*. Elle suit le même chemin que les autres alertes de
gel : notification si les alertes de gel sont activées, et événement `garden_manager_frost_warning`
avec `key` = `froze:<date>`, `severity` = `warning`, `temp` et `plants`.

**Tâches météo.** Les tâches issues de la météo ont des clés stables (`w:<type>:<date>`), si bien
qu'une même situation ne crée jamais deux tâches. Outre celles des prévisions (`w:storm`, `w:dry`,
`w:rain` …), Hortulus crée des tâches de suivi pour le temps **déjà passé**, d'après l'historique du
climat, dès qu'il y a des cultures en place :

| Clé | Quand | Tâche |
|---|---|---|
| `w:after_storm:<date>` | hier, rafales ≥ 60 km/h (ou vent ≥ 45 km/h) | *Après la tempête (…) : faites le tour du jardin* – type `check`, priorité haute, à faire dans les 2 jours |
| `w:rain:<date>` | hier, une forte averse **enregistrée** (pas une simple prévision) | la ronde contre les limaces après l'averse – type `pest_check` ; même clé que la tâche créée à partir de la prévision, donc jamais deux fois |
| `w:dry_logged:<lundi>` | sur les 7 derniers jours : pluie connue pour au moins 6 jours, moins de 3 mm au total, et au moins 4 jours ≥ 20 °C | *Période sèche : … mm de pluie en … jours* – type `water`, un arrosage en profondeur ; pas créée si une tâche de sécheresse issue des prévisions (`w:dry:…`) existe déjà |

**Boutons de notification.** Le récapitulatif, les rappels, « des planches ont besoin d'eau » et
« vanne restée ouverte » envoyés aux téléphones avec l'application compagnon portent des boutons
d'action : *Fait* (une tâche) et *Demain* sur les listes de tâches, *Arroser maintenant* quand des
planches ont besoin d'eau, *Fermer la vanne* sur une vanne restée ouverte. Appuyer sur l'un d'eux
déclenche l'événement `mobile_app_notification_action` de Home Assistant (les noms d'actions
commencent par `HORTULUS_`), qu'Hortulus traite lui-même ; vous n'avez pas besoin d'automatisation.

## API websocket (utilisée par le panneau)

Toutes les commandes sont dans l'espace de noms `garden_manager/` et acceptent `garden_id`
(l'identifiant de la config entry) pour choisir un jardin. Les lectures sont ouvertes à tout
utilisateur authentifié ; les commandes marquées **admin** exigent un administrateur. Les actions sur
les tâches, les enregistrements (récolte, carnet, graines, dépenses, analyses de sol) et le livre de
cuisine sont ouverts à tous.

| Groupe | Commandes |
|---|---|
| Données en direct | `subscribe` (envoie un instantané complet maintenant et après chaque mise à jour), `plants` (base + surcharges), `advice`, `supplies` |
| Plantes | `plants/save` **admin** (`mode` : `custom` ou `override`), `plants/delete` **admin** (réinitialise une surcharge ou supprime une plante personnelle), `plants/windows` (périodes de semis pour vos dates de gel) |
| Plan | `plan/save` **admin** (avec `base_revision` et `season` facultatif), `plan/check` (compatibilité du brouillon), `plan/succession`, `plan/export`, `plan/import` **admin**, `plan/autofill`, `plan/autofill/apply` **admin**, `plan/compare`, `layout/delete` **admin** |
| Plans mis de côté | `plan/new` **admin** (`start` : `empty`, `zones`, `zones_beds`), `plan/activate` **admin**, `plan/delete` **admin** |
| Fin d'année | `year/preview`, `year/apply` **admin** (`from_season`, `layout` : `copy`/`keep`, `zone_ids`, `feature_ids`, `planting_ids`, `activate`) |
| Cultures | `plantings/season`, `planting/update` **admin**, `plantings/update_many` **admin**, `planning` (plan de semis, graines, succession, prévision de récolte) |
| Tâches | `tasks/add`, `tasks/action` (`complete`, `skip`, `postpone`, `update`, `delete`, `reopen`) |
| Paramètres | `settings/save` **admin** |
| Potager de départ | `garden/starter` **admin** (`size` : `small`/`medium`/`large`, `greenhouse`) |
| Irrigation | `irrigation/plan`, `irrigation/run` **admin**, `irrigation/stop` **admin**, `irrigation/test` **admin** (ouvre une vanne 5 s et vérifie qu'elle indique ouverte puis fermée), `irrigation/close` **admin** (ferme une vanne restée ouverte) |
| Climat | `climate/stats` : historique du climat et statistiques (`days` facultatif, 7–800, 400 par défaut) – voir ci-dessous ; `climate/import_csv` **admin** (`text` : l'export CSV d'une station météo, jusqu'à 20 Mo ; résultat `{days, first, last, rows, columns, changed}` ; erreurs `invalid_csv`, `disabled`) ; `climate/apply_local_frost` **admin** (sans argument : passe la région en personnalisé avec les dates de gel mesurées ; résultat `{settings}` ; erreur `no_suggestion`) |
| Enregistrements | `records/overview` (récolte par culture et par année, rendements appris, boîte à graines, eau, matrice annuelle, rapport cuisine, coûts et dépenses), `records/harvest/add`, `records/journal/save`, `records/seeds/save`, `records/expense/save`, `records/soil/save`, `records/soil/delete`, `records/delete` (`kind` : `harvest`, `journal`, `seed`, `expense`), `seeds/to_todo` (graines manquantes vers une liste de tâches), `report/season` |
| Conseils et manuel | `qa/options`, `qa/ask`, `handbook/index`, `handbook/chapter`, `handbook/search` |
| Impression | `print/render` (pages d'aperçu SVG) |
| Analyse | `analysis` (contrôle du jardin), `analysis/explain` (« pourquoi pas ici ? »), `analysis/fix` **admin** (correction en un clic), `analysis/still_possible` (ce qui peut encore être mis en terre cette saison) |
| Journal système | `syslog/list` (du plus récent au plus ancien, paginé avec `before`), `syslog/entry` **admin** (une entrée avec avant/après par élément), `syslog/undo` **admin** (`entry_id`, `force` facultatif) |
| Cuisine | `cooking/suggest` (produits prêts, plats, menus, livre de cuisine, choix), `cooking/render` (une recette recalculée après changement d'accompagnement, de viande ou de nombre de personnes), `cooking/prefs`, `cooking/book/save`, `cooking/book/update`, `cooking/book/delete`, `cooking/pdf` (`kind` : `recipe`, `book`, `shopping`), `cooking/send` (une recette ou la liste de courses vers un service `notify.*`), `cooking/to_todo` (liste de courses vers une liste de tâches ; vos propres droits sur cette liste s'appliquent) |

`seeds/to_todo` et `cooking/to_todo` vérifient les droits propres de l'utilisateur appelant sur la
liste de tâches cible.

**`garden_manager/climate/stats`** (lecture, ouverte à tout utilisateur) renvoie ce qu'affiche
*Météo → Historique du climat* :

| Clé | Contenu |
|---|---|
| `today`, `season_start` | dates de référence |
| `periods` | résumés `d7`, `d30`, `season` et `d365`, plus `d7_last_year`, `d30_last_year` et `season_last_year` : moyenne, minimum, maximum, pluie et jours de pluie, nuits de gel, jours ≥ 25 / ≥ 30 °C, ensoleillement, rafale max., degrés-jours, ET₀ et bilan hydrique |
| `records` | records absolus (le plus froid, le plus chaud, le jour le plus pluvieux, la rafale la plus forte) avec leur date, chiffres mensuels compris |
| `series` | un élément par jour (`d`, `lo`, `hi`, `m`, `r` pluie, `s` soleil, `w` vent, `rh`, `et0`, `src` source) sur les `days` derniers jours |
| `months` | chiffres mensuels extérieurs, avec l'écart par rapport à l'an dernier |
| `frost` | dates de gel mesurées par année (`years`), moyenne locale comparée au préréglage (`local`), `preset_last`, `preset_first` |
| `sensors` | une ligne par capteur de température associé (`entity_id`, `label`, `kind` : `outdoor` / `zone_air` / `bed_air` / `soil`, valeur actuelle, jour, moyenne 7 j, plage 30 j, records, mois) |
| `coverage` | jours dans le journal quotidien, premier jour, sources (`sensor`, `history`, `model`), mois conservés |
| `summary` | *(extra `season_summary`)* `season`, `month` (listes de phrases), `month_start` – la saison et le mois dernier comparés aux mêmes dates l'an dernier |
| `local_frost_suggestion` | *(extra `local_frost_suggest`)* `last_frost`, `first_frost` (`MM-DD`), `spring_diff_days`, `autumn_diff_days`, `years` ; `null` tant que les dates mesurées restent à moins de 7 jours du préréglage |
| `station_import` | `true` quand l'import CSV (extra `station_import`) est actif |

```yaml
type: garden_manager/climate/stats
days: 90
```

## Carte Lovelace

L'intégration charge une petite carte sur chaque tableau de bord – aucune ressource à ajouter à la main :

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

Cochez une tâche sur la carte et elle est terminée dans Hortulus (avec le semis ou l'entretien
suivant planifié comme d'habitude). `assignee: me` montre vos tâches et celles sans responsable ;
`person.xyz` montre celles de cette personne et celles sans responsable ; `unassigned` ne montre que
les tâches sans responsable. Les tâches en retard sont marquées, un lien « +N de plus » et l'icône de
pousse ouvrent le panneau. Le bouton *Fermer* d'une vanne restée ouverte n'est montré qu'aux
administrateurs. La ligne climat et le dicton demandent les extras `climate_card` et `slogans`
(Paramètres → Extras) ; sans tâche, le dicton remplace « rien à faire ». La carte est disponible en anglais, en
néerlandais et en français.

## Voix (Assist)

Lancez une fois `garden_manager.install_voice_sentences` (ou Paramètres → Ménage et voix →
*Installer les phrases vocales*), puis interrogez Assist :

| Intention | Français | English |
|---|---|---|
| `HortulusTasksToday` | « qu'est-ce que je dois faire aujourd'hui au jardin » | "what do I need to do in the garden today" |
| `HortulusOverdue` | « qu'est-ce que j'ai oublié au jardin » | "what did I forget in the garden" |
| `HortulusHarvest` | « qu'est-ce que je peux récolter aujourd'hui » | "what can I harvest today" |
| `HortulusGreenhouse` | « quelle est la température de la serre » | "how warm is it in the greenhouse" |
| `HortulusWater` | « dois-je arroser aujourd'hui » | "do I need to water today" |
| `HortulusFrost` | « va-t-il geler cette nuit » | "is there frost tonight" |

Des phrases en néerlandais sont fournies aussi. Les réponses sont prononcées dans la langue de la
conversation. Les intentions ne prennent aucun slot et sont enregistrées par l'intégration
elle-même ; vous pouvez donc aussi les utiliser dans vos propres phrases ou automatisations
(`conversation.process`). Avec plusieurs jardins, elles répondent pour le premier.

## Téléchargement de PDF

`GET /api/garden_manager/print?document=garden&page=remarkable&color_mode=eink`
(authentifié) génère le PDF à la volée. Il accepte les mêmes paramètres que `export_pdf`
(`document`, `page`, `landscape`, `color_mode`, `season`, `zone_id`, `bed_ids`, `days`, `notes`,
`grid`, `title` ; listes séparées par des virgules) plus `labels` (noms des cultures sur le plan, true
par défaut), `plant_ids` (pour les fiches de plantes) et `garden_id`. `&format=svg` renvoie les
pages SVG en JSON (`{"pages": [...]}`) au lieu d'un PDF.

`GET /api/garden_manager/exports/<file>.pdf` sert un PDF écrit par `export_pdf` ou par
*Enregistrer dans /config/hortulus/exports* dans l'onglet Imprimer (connexion ou lien signé, valable 7 jours).

Les PDF de cuisine (une recette, le livre de cuisine, la liste de courses) sont renvoyés en base64
par la commande websocket `cooking/pdf`.

## Diagnostic

Paramètres → Appareils et services → Hortulus → ⋮ → *Télécharger les diagnostics* donne un fichier
JSON avec les données et options de la config entry, les paramètres, des comptages (zones, planches,
cultures, tâches ouvertes et totales, plantes personnelles, jours de climat), les identifiants
d'entités suivis, l'état de la météo (disponible, erreur, nombre de points horaires et journaliers) et
l'analyse en cours. Les services notify, les haut-parleurs, la latitude et les identifiants de photos
sont masqués. Une fonction distincte du panneau, **Analyse → Contrôle → Exporter le diagnostic**,
écrit le contrôle du jardin dans un seul fichier JSON pour les rapports de bug.

## Blueprints

Quatre blueprints d'automatisation sont fournis dans `blueprints/automation/hortulus/` : alerte de
gel sur une lampe (`frost_flash_light.yaml` ; la lampe retrouve son état d'origine), enregistrer une
récolte avec un bouton ou un tag NFC (`button_log_harvest.yaml`), arroser une planche sèche au bon
moment (`water_when_dry.yaml`, utilise `run_irrigation_plan` avec `only_if_needed`) et annoncer les
travaux urgents du jardin (`urgent_task_announce.yaml`). Les liens d'importation sont dans le README.
