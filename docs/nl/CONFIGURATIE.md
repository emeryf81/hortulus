# Configuratie

Hortulus stel je op drie plekken in, elk met een eigen taak:

| Waar | Wat | Opgeslagen in |
|---|---|---|
| **Installatiewizard** (config flow) | Eerste keer: klimaat, weer, eerste bedden + sensoren, meldingen | config entry → vult de tuinopslag één keer |
| **Opties** (Instellingen → Apparaten & diensten → Hortulus → *Configureren*) | Klimaat, weer en buitensensoren, meldingen, geavanceerd | wordt in de tuinopslag geschreven |
| **Hortulus‑paneel** | De rest: bedden en zones tekenen, beplanting, sensorkoppelingen, plantendatabase, taken, koken | `.storage/garden_manager.garden` |

Na de installatie is de tuinopslag de enige bron van waarheid; de opties en het paneel
bewerken allebei dezelfde gegevens, dus ze spreken elkaar nooit tegen. Naast het tuinbestand
staan per tuin nog twee bestanden: `garden_manager.garden.syslog` (het systeemlogboek, de
laatste 500 regels) en `garden_manager.garden.archive` (oude seizoenen, zie
[sectie 8](#8-seizoenen-jaarovergang-en-archief)).

Inhoud: [1 Installatiewizard](#1-installatiewizard) · [2 Sensorkoppeling](#2-regels-voor-sensorkoppeling) ·
[3 Opties](#3-opties) · [4 Het paneel](#4-het-paneel) ·
[5 Importeren en exporteren](#5-importeren-en-exporteren) · [6 Eenheden, taal en tijd](#6-eenheden-taal-en-tijd) ·
[7 Prestaties](#7-prestaties) · [8 Seizoenen en archief](#8-seizoenen-jaarovergang-en-archief) ·
[9 Meerdere tuinen](#9-meerdere-tuinen) · [10 Hortulus Web](#10-hortulus-web-optionele-website)

---

## 1. Installatiewizard

De wizard heeft deze schermen, in deze volgorde: klimaatprofiel → klimaatdetails → weer →
bedden / kassen / bakken (herhaalbaar, elk gevolgd door zijn sensoren) → meldingen →
samenvatting.

### Stap 1 – Klimaatprofiel
Kies hoe Hortulus je **vorstdata** bepaalt. Alle zaai‑ en plantvensters in de
plantendatabase zijn daar relatief aan uitgedrukt. De wizard vraagt eerst naar het soort
profiel (voorgeselecteerd: *regionale voorinstelling* als het land van Home Assistant NL, BE,
GB, DE of FR is, anders *USDA‑zone*) en daarna naar de details; het halfrond wordt
voorgeselecteerd op basis van de breedtegraad van Home Assistant.

| Profiel | Wanneer | Voorbeeld |
|---|---|---|
| **Regionale voorinstelling** | Je regio staat in de lijst | *Nederland / Vlaanderen*: laatste vorst 20 apr, eerste vorst 25 okt |
| **USDA‑winterhardheidszone** | Noord‑Amerika, of je kent je zone | 7a → 8 apr / 1 nov (6 maanden verschoven op het zuidelijk halfrond) |
| **Eigen vorstdata** | Je hebt lokale gegevens (beste keuze) | `04-28` / `10-15` (formaat `MM-DD`) |

Beschikbare voorinstellingen:

| Voorinstelling | Halfrond | Laatste vorst | Eerste vorst |
|---|---|---|---|
| `nl_be` Nederland / Vlaanderen | N | 04‑20 | 10‑25 |
| `uk_south` | N | 04‑10 | 11‑01 |
| `uk_north` | N | 05‑01 | 10‑15 |
| `de_central` | N | 04‑30 | 10‑15 |
| `fr_north` | N | 04‑15 | 10‑31 |
| `scandinavia_south` | N | 05‑15 | 09‑30 |
| `mediterranean` | N | 03‑01 | 12‑01 |
| `au_melbourne` | Z | 09‑15 | 05‑15 |
| `nz_christchurch` | Z | 10‑10 | 04‑25 |
| `za_highveld` | Z | 09‑01 | 05‑15 |

De plantendatabase is zo opgezet dat vorstgevoelige gewassen in Nederland en Vlaanderen pas
rond de **IJsheiligen (11–15 mei)** buiten worden uitgeplant; in een kas kan dat 4 weken eerder.

**Afgehandelde randgevallen**: een eigen `02-29` wordt in een gewoon jaar 28 februari; op het
zuidelijk halfrond loopt een *seizoen* van juli tot juni en draagt het de naam van het jaar
waarin de lente begint (seizoen 2026 = sep 2026 – mei 2027); USDA‑zones 11 en hoger gelden
als vorstvrij. Onmogelijke data (zoals `13-01`) worden geweigerd.

### Stap 2 – Weer
* **Weerentiteit** (aanbevolen): moet een uur‑ en/of dagverwachting leveren. Hortulus roept
  elke 30 minuten `weather.get_forecasts` aan, en ook telkens wanneer de weerentiteit
  verandert (maximaal eens per 10 minuten). Eenheden worden automatisch omgerekend naar °C,
  mm en km/u.
* **Buitentemperatuur** (optioneel): gebruikt voor de
  [klimaatgeschiedenis](#klimaatgeschiedenis) en dus voor de graaddagen; valt terug op de
  huidige temperatuur van de weerentiteit. °F‑sensoren worden omgerekend.
* **Regensensor** (optioneel): een dagtotaal in mm (of een binaire regendetector).

Meer weerinvoer (buitenluchtvochtigheid, bladnat, de weerstationsensoren windsnelheid,
windstoten, zonnestraling en licht buiten, de optionele Open‑Meteo‑gegevens, hoogte) stel je
later in het paneel in onder *Instellingen → Weer & buitensensoren*.

### Stap 3 – Bedden, kassen en bakken
Voeg zoveel tuindelen toe als je wilt (menu *Nog een toevoegen…*). Elk tuindeel vraagt naar
naam, soort (*buitenbed*, *kas*, *bak*), breedte × lengte (meter, 0,1–100), grondsoort,
schaduw % (stappen van 5) en windblootstelling, gevolgd door een scherm met de sensoren
(allemaal optioneel):

| Veld | Typische entiteit | Getoond voor | Entiteitsfilter |
|---|---|---|---|
| Bodemvocht | `sensor.soil_moisture_bed_1` | alle | `sensor`, device class moisture |
| Bodemtemperatuur | `sensor.soil_temp_bed_1` | alle | `sensor`, device class temperature |
| Luchttemperatuur | `sensor.greenhouse_temp` | kas | `sensor`, device class temperature |
| Luchtvochtigheid | `sensor.greenhouse_humidity` | kas | `sensor`, device class humidity |
| Licht | `sensor.greenhouse_lux` | kas | `sensor`, device class illuminance |
| Beregening | `valve.bed_1` of `switch.drip_bed_1` | alle | `switch`, `valve` |
| Debiet | `4` L/min | alle | – |

Wat de wizard aanmaakt:

* **Buitenbedden en bakken** → verhoogde bedden (bakken: bakbedden) in één buitenzone
  (“Tuin”), van links naar rechts geplaatst met paden van 50 cm.
* **Kas** → een kaszone van de opgegeven grootte met één grondbed (“Greenhouse Zone A bed”)
  langs de lange zijde; luchtsensoren horen bij de zone, bodemsensoren en de klep bij het
  bed. Meerdere kassen komen naast elkaar te staan.

Alles kan later in het paneel opnieuw getekend worden.

### Stap 4 – Meldingen
Blijvende meldingen, een willekeurig aantal `notify.*`‑diensten (mobiele push), optioneel een
tekst‑naar‑spraak‑engine met speakers, en het tijdstip van het **dagelijkse overzicht**
(standaard 07:30). Vorstwaarschuwingen, hittewaarschuwingen en het uitgesproken vorstbericht
zet je aan of uit in de opties of bij Instellingen → Meldingen (vorst‑ en hittewaarschuwingen
staan standaard aan, het omroepen uit).

### Stap 5 – Samenvatting
Controleer alles en voeg eventueel een **voorbeeldplan** toe voor het komende seizoen:
tomaat + basilicum + afrikaantje in de kas, wortel naast ui (wortel‑ en uienvlieg raken in de
war) en drie opeenvolgende zaaironden sla. Een lege tuin kun je ook starten vanaf het
welkomstscherm van het paneel (zie *Vandaag*).

---

## 2. Regels voor sensorkoppeling

Elk bed zoekt zijn sensoren **veld voor veld** in deze volgorde:

1. sensoren die **op het bed** zijn ingesteld,
2. sensoren **op zijn zone** (bv. één kasthermometer voor alle bedden erin),
3. voor elke zone die **geen** kas of koude bak is (buiten, boomgaard, kruidentuin, bakken …):
   de **buitensensoren** uit de weerinstellingen.

Kassen en koude bakken hebben hun eigen klimaat en vallen nooit terug op de buitensensoren.
Ontbrekende, `unknown`‑ of `unavailable`‑sensoren verlagen alleen de nauwkeurigheid. Een sensor
die langer dan *sensor verouderd na* (standaard 360 minuten) niets heeft gemeld, wordt
genegeerd en geeft een waarschuwing “sensor verouderd”. Hortulus kijkt naar `last_reported`,
dus een sensor die steeds dezelfde waarde meldt maar wel leeft, geldt niet als verouderd.

Sensorsoorten die je in het paneel (Instellingen) kunt koppelen: bodemvocht, bodemtemperatuur,
EC en N / P / K‑sondes per bed; luchttemperatuur, luchtvochtigheid, licht, PAR en bladnat per
zone; voor de hele tuin buitentemperatuur, ‑vochtigheid, regen en bladnat, en als
**weerstation** ook windsnelheid, windstoten, zonnestraling (W/m²) en licht buiten (lux).

| Buitensensor | Eenheid | Waarvoor |
|---|---|---|
| Buitentemperatuur | °C of °F | dagminimum, ‑maximum en ‑gemiddelde, graaddagen, vorstnachten, vorstdata |
| Luchtvochtigheid | % | Penman‑Monteith‑verdamping, ziekterisico (Hutton uit de gelogde dagen) |
| Regensensor | mm per dag (of binair) | regen in de waterbalans en de geschiedenis; zonder meter boekt Hortulus de verwachting van vandaag |
| Windsnelheid | km/u, m/s, mph of kn (omgerekend) | verdamping, stormdagen |
| Windstoten | idem | hardste windstoot, nazorgtaak na een storm (≥ 60 km/u) |
| Zonnestraling | W/m² | stralingssom en zonuren (tijd boven 120 W/m², de WMO‑drempel), verdamping, sombere dagen |
| Licht buiten | lux | als er geen stralingssensor is: omgerekend naar straling (ongeveer 127 lux per W/m²) |
| Bladnat | % of binair | ziekterisico nu |

Zonder weerstation nemen de weerentiteit (temperatuur, vochtigheid, wind en windstoten) en,
als het aan staat, Open‑Meteo het over. Eén keer per dag
bepaalt een vochtsensor ook de waterbalans van het bed, en elk bed leert hoe snel het echt
uitdroogt.

---

## 3. Opties

| Menu | Velden |
|---|---|
| Klimaat en vorstdata | profiel, halfrond, voorinstelling / zone / eigen data |
| Weer en buitensensoren | weerentiteit, buitentemperatuur, regen (de andere buitensensoren stel je in het paneel in) |
| Meldingen | blijvend, pushdiensten, TTS, speakers, tijdstip overzicht, vorstwaarschuwingen, hittewaarschuwingen, TTS‑vorstbericht |
| Geavanceerd | taal van gegenereerde teksten (auto/en/nl/fr), bereik buurplanten (10–300 cm), sensor verouderd na (15–2880 min), diepte wortelzone (50–600 mm), maximale beregening per keer (2–60 mm) |

Elk menu‑item slaat alleen zijn eigen deel op in de tuinopslag. Opslaan herlaadt de
integratie; je plan en je taken blijven onaangeroerd. Bedden, zones en sensorkoppelingen
bewerk je in het paneel, niet hier.

---

## 4. Het paneel

Open **Hortulus** in de zijbalk (`/hortulus`). Gebruikers zonder beheerdersrechten kunnen alles
bekijken en met taken, het dagboek, oogsten en het kookboek werken; het plan, de
plantendatabase, de instellingen en de hardware wijzigen vraagt een beheerder. Tabbladen
hebben hun eigen URL (`/hortulus/calendar`, `/hortulus/wall` …); het Handboek accepteert een
hoofdstuk (`/hortulus/handbook/<hoofdstuk>`).

Het menu heeft acht plaatsen, met de verwante tabbladen van een plaats in een rij eronder.
Een plaats opent op het tabblad dat je er laatst gebruikte.

| Plaats | Tabbladen |
|---|---|
| **Vandaag** | Vandaag (dashboard) · Wandscherm (knop op het dashboard) |
| **Tuin** | Planner · Tuinplan · Teelten |
| **Kalender** | Kalender |
| **Weer** | Weer |
| **Logboek** | Logboek |
| **Koken** | Koken |
| **Kennis** | Planten (bibliotheek) · Advies · Handboek |
| **Beheer** | Analyse · Afdrukken · Instellingen |

Een negende tab, *Tuin* (een alleen‑lezen blik op het plan), bestaat enkel voor de website
([sectie 10](#10-hortulus-web-optionele-website)) en wordt nooit getoond in Home Assistant.

### Vandaag (dashboard)
Een hero in de kleuren van het seizoen met kerncijfers (taken vandaag, werk vandaag,
graaddagen), de taken van vandaag met een vinkje, de bedden met hun vocht, de kas, het weer
van de komende 48 uur, wat eraan komt, een kaart **Water & klimaat** (bewateringsmodus, bedden
die water nodig hebben, *Nu water geven* / *Stop*, ziekterisico, voeding), een kaart **Plagen
in de tuin** (welke plagen nu vliegen, alleen voor gewassen die in of binnenkort in de grond
staan) en **Snel oogsten** (de gewassen die nu te oogsten zijn: tel het gewicht op met de grote
knoppen en bewaar). Rode banners verschijnen bij een **kraan die openstaat** (met *Kraan
sluiten*) en bij een **lek**. Een lege tuin toont een **welkomstscherm**: leg een kant‑en‑klare
begintuin aan (2–4 verhoogde bakken, een kruidenpot, eventueel een kas, met een eerste plan),
teken zelf je tuin of lees eerst het handboek.

### Wandscherm
Een rustige, grote kioskweergave voor een tablet (`/hortulus/wall`, of *Vandaag →
Wandscherm*): de tijd, het weer, de taken van vandaag met grote vinkjes, het vocht van de
bedden en de meldingen. Zonder menu's; 's nachts dimt het scherm.

Met **Aanpassen** (rechtsboven) stelt iedereen zijn eigen wandscherm samen: kies uit achttien
blokken (klok, weer nu, weersverwachting, buienradar, taken van vandaag, agenda, bodemvocht,
bewatering, oogstklaar, zaaien en planten, plagen, je tuin in cijfers, zon, weerspreuk, weetje over
biologisch tuinieren, biologische tip van de maand, recepttip en tuinspreuk), sleep ze in de juiste
volgorde (of gebruik ◀ ▶) en maak ze smaller of breder (− +). De tekst schaalt mee met elk blok, zodat
alles op één scherm past. *Standaard* zet het oorspronkelijke wandscherm terug. Elke gebruiker houdt
zijn eigen indeling, op elk scherm waarop hij aangemeld is. Het samenstellen kan
voorlopig alleen in het Nederlands; in andere talen toont het wandscherm de vaste blokken.

### Tuinplan
Het tuinplan legt de vorm van de tuin vast voor **één seizoen**, zonder planten, in drie
stappen: **Terrein** (elementen: huis, oprit, straat, parking, carport, terras, vlonder, muur,
paden in grind / steen / hout / stapstenen / schors, gazon, bloemperk, haag, heester, boom,
vijver, zithoek, zwembad, speelhoek, omheining, klimrek, bijenkast, tuinhuis, composthoop,
regenton …), **Teeltzones** (buiten, siertuin, kas, koude bak, bloembakken & potten,
boomgaard, voedselbos, kleinfruit, kruidentuin, bloementuin) en **Bedden** (open een zone en
teken haar bedden en bakken op een eigen kaart; met het gereedschap *Bloembak / pot* teken je
een bakbed). Elementen teken je op een raster van 10 × 10 cm; een huis, pad, oprit, haag of
teeltzone op een gazon neemt die oppervlakte van het gazon af (kaart, afdruk en m²), een boom
of heester niet. Elk onderdeel kun je alleen in zijn eigen stap selecteren, verplaatsen en
bewerken. Werkbalk:

* **Seizoen**‑keuze. Een seizoen zonder plan biedt aan het plan van een ander jaar te kopiëren
  of leeg te beginnen.
* **Plannen**: begin opnieuw met een nieuw plan (vanaf nul, dezelfde zones maar leeg, of zones
  en bedden zonder gewassen). Het huidige plan wordt **niet‑actief** (opzijgezet met zijn
  bedden en gewassen), kan later weer geactiveerd worden (het actieve plan wisselt dan van
  plaats), vergeleken of verwijderd.
* **Jaarovergang**, zie [sectie 8](#8-seizoenen-jaarovergang-en-archief).
* **Meer**: exporteren (JSON / YAML), importeren, sneltoetsen.

### Planner
De Planner beplant alleen, op het plan van het gekozen seizoen (zones, bedden en elementen
liggen daar vast). Twee stappen: **Meerjarigen** (bomen, struiken, vaste kruiden, asperge,
rabarber – ze blijven van jaar tot jaar staan en dragen vruchten na *N* jaar) en
**Eenjarigen**. Eén klik selecteert een item, een tweede klik (of *Details*, of
<kbd>Enter</kbd>) opent de detailpopup.

* **Plantenpalet**: kies *Los*, *Blok* of *Rij* en sleep een plant op een bed (of druk
  <kbd>Enter</kbd> op een palletplant om hem aan het geselecteerde bed toe te voegen). Het
  palet toont de planten die passen bij het geopende zonetype. Tijdens het slepen vraagt
  Hortulus de backend om een live compatibiliteitscontrole en toont ♥ goede buren / ⚠
  conflicten / ⟲ wisselteeltproblemen in het label van de spooktekening.
* **Detailpopup**: indeling, methode (binnen zaaien / ter plaatse zaaien / planten), status,
  afmeting, een eigen geplande datum, een seizoenstijdlijn (zaaivenster, uitplantvenster,
  oogst), groeistadium, gewascoëfficiënt (Kc), graaddagen en de verwachte oogstdatum, alle
  waarschuwingen met uitleg, **betere buren** bij conflicten, **Past in**‑knoppen die een
  gewas naar een bed zonder wisselteeltconflict verplaatsen, **Waarom (niet) hier?** per gewas,
  de vruchtwisseling van de laatste vijf jaar, een **notitie met foto**, een fototijdlijn en
  het waterverbruik van het bed.
* **Opeenvolgend zaaien**: verdeel een blok in stroken die elke *N* dagen gezaaid worden
  (standaard uit de plant, bv. sla 21 dagen) of stapel zaaimomenten op dezelfde plek. Zaaimomenten
  buiten het zaaivenster worden overgeslagen en gemeld.
* **Automatisch invullen** (stap Eenjarigen): geef gezinsgrootte, uren per week, beschikbaar
  water en compost, doelen (verse groenten, bewaargroenten, kruiden, bestuivers, wintergroenten,
  vaste planten, weinig onderhoud), gewassen die er zeker bij moeten en nooit, voorkeuren
  (keuzevrijheid, rekening houden met plantenburen, bestuivingsbloemen toevoegen, oogst het
  hele jaar, meerjarigen toegestaan, zonetype respecteren) en welke bedden gevuld mogen worden.
  Het voorstel toont gewassen, aantallen, m², verwachte oogst, minuten per week, water in de
  piekweek en compost, plus een reden per plant die niet geplaatst werd (te laat, zonetype,
  glas, vorst, wisselteelt, slechte buur, geen plaats) en een aanbod om het volgende seizoen in
  te vullen. Er verandert niets tot je op **In het plan zetten** drukt. De regels:
  hoeveelheden per persoon uit de databank (of je eigen geleerde kg/m²); wisselteeltconflicten
  sluiten een bed uit; plantenburen, kasbehoefte en schaduwtolerantie bepalen de score van het
  bed; stroken worden gevuld met de hoogste gewassen aan de kant weg van de zon; snelle
  gewassen krijgen drie opeenvolgende zaaimomenten.
* **Meerdere selecteren**: <kbd>Shift</kbd>/<kbd>Ctrl</kbd>‑klik op bedden, gewassen of
  elementen; sleep ze samen, of gebruik **uitlijnen** (links, midden, rechts, boven, midden,
  onder) en **verdelen**.
* **Lagen**: zones, elementen en gewassen tonen of verbergen.
* **Overlays**: buurplanten (groen = goede buren, gestippeld groen = plaagwerend, rood
  gestreept = vijanden, paars = allelopathie, oranje = concurrentie of overlap, grijs
  gestippeld = schaduw), vocht (omtrek van het bed + %), bodemtemperatuur. Plantsymbolen
  volgen de groeivorm (schijf = struik, driehoek = klimmer, ruit = rechtop, ring = rank, bloem
  = rozet, ▼ = wortelgewas, druppel = bol), zodat het plan ook zonder kleur leesbaar is.
  Gewassen worden na het planten kleiner getekend en groeien tot volle grootte bij de oogst
  voor de getoonde datum.
* **Toon tuin op**: schuif door het seizoen – beplantingen die op die datum niet in de grond
  staan, worden vervaagd.
* **Banner einde seizoen**: wat nog gezaaid of geplant kan worden, met een sprong naar het plan
  van volgend jaar.
* **Automatisch opslaan**: wijzigingen worden ongeveer 1 seconde na elke bewerking opgeslagen
  met een optimistische revisiecontrole; is het plan elders gewijzigd, dan krijg je een melding
  en het nieuwste plan.

Sneltoetsen (druk op <kbd>?</kbd> in de planner):

| Toetsen | Actie |
|---|---|
| <kbd>←</kbd><kbd>↑</kbd><kbd>→</kbd><kbd>↓</kbd> | selectie één rasterstap verplaatsen (<kbd>Shift</kbd> = 10×) |
| <kbd>Alt</kbd> + pijltjes | selectie vergroten of verkleinen |
| <kbd>Ctrl/⌘</kbd>+<kbd>Z</kbd> / <kbd>Ctrl/⌘</kbd>+<kbd>Y</kbd> | ongedaan maken / opnieuw |
| <kbd>Delete</kbd> | selectie verwijderen |
| <kbd>Ctrl/⌘</kbd>+<kbd>D</kbd> | beplanting dupliceren |
| <kbd>[</kbd> <kbd>]</kbd> | vorig / volgend item selecteren (van de huidige stap) |
| <kbd>Enter</kbd> | details van de selectie openen |
| <kbd>G</kbd> <kbd>C</kbd> <kbd>M</kbd> <kbd>T</kbd> | raster, buurplanten, vocht, temperatuur aan/uit |
| <kbd>+</kbd> <kbd>−</kbd> <kbd>0</kbd> | inzoomen / uitzoomen / passend maken |
| <kbd>Esc</kbd> | selectie opheffen |

### Teelten
Alle gewassen van een seizoen op één lijst (*per bed*, *per gewas* of *op datum*), met methode,
status, aantal, notities en geplande / echte datums die je ter plekke aanpast – niets om te
slepen. Vink meerdere gewassen aan om voor allemaal tegelijk een status of datum te zetten.
Op een gsm is elk gewas een kaartje met de eerstvolgende in te vullen datum. Weergaven:

| Weergave | Toont |
|---|---|
| **Lijst** | de bewerkbare tabel; *Toon op kaart* opent de planner bij dat gewas |
| **Tijdlijn** | het jaar per bed als balken (voorkweek, groei, oogst) met een lijn voor vandaag; sleep een gepland gewas opzij om zaaien en uitplanten te verschuiven |
| **Zaaiplan** | wat je week per week zaait, uitplant en oogst (*Gedaan* vult de datum van vandaag in) |
| **Zaden** | het zaad dat het plan nodig heeft tegenover je zaadvoorraad; wat ontbreekt zet je met één klik op een takenlijst van Home Assistant, zonder dubbels |
| **Opvolgteelt** | bedden die dit seizoen vrijkomen en wat daar daarna past |
| **Oogstverwachting** | verwachte kg per week |

### Planten (bibliotheek)
Zoeken (accentongevoelig, in elke taal), filteren op familie, *kas*, *snelle gewassen* of *mijn
planten*. De ingebouwde databank bevat 232 gewassen (groenten, kruiden, fruit, bloemen,
groenbemesters), elk met afbeelding, een zaaikalender berekend voor **jouw** vorstdata, buren
en “waar het in je tuin groeit”. *Aanpassen* bewaart alleen de velden die je wijzigde als
override (per taal voor namen en teksten), zodat toekomstige updates van de ingebouwde data je
nog bereiken; *Terug naar standaard* verwijdert de override. *Nieuwe plant* maakt een eigen
plant (de code wordt afgeleid van de Engelse naam); een eigen plant die een plan of een
opzijgezet plan nog gebruikt, kan niet verwijderd worden. Met *Instellingen → Weergave →
foto's* aan toont de browser ook een foto van Wikipedia (CC BY, CC BY‑SA, CC0, publiek domein,
met bronvermelding); de tekeningen werken offline.

### Kalender
Weergaven maand, week, lijst, **tijdlijn** (een Gantt per bed met balken voor zaaien, groei en
oogst, de oogstverwachting op basis van graaddagen, vorstdata en een rij “tuinwerk” met het
seizoenswerk) en **Jaar**. Achterstallige open taken staan op vandaag, zodat niets in het
verleden verdwijnt. Op touchscreens veeg je een taak naar rechts om af te ronden of naar links
om een dag uit te stellen. Het taakvenster toont de live context (bodemvocht en ‑temperatuur,
waterbalans, voeding, luchttemperatuur, vochtigheid, ziekte‑ en vorstrisico, het weer van
vandaag en ET₀), het gereedschap voor de klus en links naar het bijpassende handboekhoofdstuk.
Open een taak om hem af te ronden, over te slaan, uit te stellen (+1 dag / +3 dagen / +1 week
of een datum; afhankelijke taken schuiven mee), de prioriteit te wijzigen, hem aan een persoon
toe te wijzen, notities en **foto's** toe te voegen (geüpload via de `image_upload` van Home
Assistant, lokaal bewaard). Een titel of omschrijving die je herschrijft, blijft behouden als
taken opnieuw berekend worden. De weergave **Jaar** toont elk gewas maand per maand (binnen
zaaien, zaaien, uitplanten, groeit, oogsten) met het aantal taken en uren per maand; druk haar
af als *Jaarplan*.

### Weer
Het weer nu, een grafiek van 24 uur (temperatuur over regen), de komende tien dagen met een
temperatuurbalk en labels voor vorst en hitte, wat het betekent voor de tuin (vorstnachten,
warme dagen, regen zodat water geven kan wachten, een droge periode, bedden die water nodig
hebben) en een **buienradar**: een radarcamera van Home Assistant als die er is (bv.
Buienradar), anders de publieke kaart van Buienradar voor Nederland of België (door je browser
geladen, elke 5 minuten ververst). Vereist een weerentiteit onder *Instellingen → Weer &
buitensensoren*.

#### Klimaatgeschiedenis
Onder de verwachting staat de **Klimaatgeschiedenis**: wat het weer hier echt deed (niet
zichtbaar in een alleen‑lezen gedeelde weergave).

* **Dagelijkse temperatuur en regen** – een band van de laagste tot de hoogste temperatuur
  van de dag, een lijn voor het daggemiddelde en balkjes voor de regen, voor **30 dagen**,
  **90 dagen** of **1 jaar**. Wijs een dag aan voor zon, wind en de herkomst van de gegevens
  (*eigen sensoren*, *recorder‑geschiedenis* of *Open‑Meteo (waargenomen)*).
* **Recent, vergeleken met vorig jaar** – de *Laatste 7 dagen*, de *Laatste 30 dagen* en
  *Dit seizoen* (sinds 1 januari; op het zuidelijk halfrond sinds 1 juli), elk met
  dezelfde periode vorig jaar ernaast: gemiddeld, laagste, hoogste, regen en dagen met regen
  (≥ 1 mm), vorstnachten (minimum onder 0 °C), dagen ≥ 25 °C (waarvan ≥ 30 °C),
  zonneschijn, hardste wind, graaddagen (met de basistemperatuur uit de instellingen) en
  verdamping (ET₀) met de waterbalans *regen − verdamping*.
* **Records** – koudst, warmst, natste dag en hardste windstoot sinds het begin van de
  geschiedenis (ook uit de bewaarde maandcijfers), met hoeveel dagen er in het daglogboek
  staan en waar ze vandaan komen; plus een korte lijst *Wat Hortulus ermee doet*.
* **Alle temperatuursensoren** – elke gekoppelde temperatuursensor (buitenlucht, lucht serre /
  zone, lucht bij het bed, bodem): *Nu*, *Vandaag*, *Gem. 7 d*, *Min–max 30 d*, *Laagste
  ooit*, *Hoogste ooit*, het aantal dagen en een sparkline.
* **Maand per maand** – de laatste 24 maanden met gemiddelde, laagste, hoogste, regen,
  vorstnachten, hete dagen, zon en hardste wind, en de verandering tegenover vorig jaar.
* **Vorstdata** – de gemeten laatste voorjaarsvorst en eerste herfstvorst per jaar, en hun
  gemiddelde tegenover de regionale voorinstelling (zie hieronder).
* **In het kort** (extra *season_summary*) – bovenaan: het seizoen en de vorige maand in
  een paar zinnen tegenover vorig jaar.
* **Mijn vorstdata gebruiken** (beheerder, extra *local_frost_suggest*) – zodra ≥ 2 volledige
  jaren een gemeten vorstdatum ≥ 7 dagen naast de regio leggen; de knop zet de regio op *eigen*
  met de gemeten data. Er verandert niets tot je erop drukt.
* **Weerstationdata importeren** (beheerder, extra *station_import*) – de export van een weerstation
  (Netatmo, Ecowitt, Davis, een rekenblad). Kopregel en scheidingsteken (`;`, `,`, tab) worden
  herkend; kolommen voor tijd (ook unix‑seconden), temperatuur, vochtigheid, regen (een
  oplopend dagtotaal → het maximum, regen per meting → opgeteld), wind en windstoten worden in
  het Nederlands, Engels en Frans herkend; °F, inch, mph, m/s en knopen worden omgerekend.
  Dagen die Hortulus zelf mat, blijven staan; geïmporteerde dagen tellen als *geschiedenis*.

**Hoe de geschiedenis wordt opgenomen.** Bij elke update (sensorwijzigingen, 10 s
gedebounced) legt Hortulus de buitenwaarden vast in de dag van vandaag: minimum en maximum
altijd, het gemiddelde met hoogstens één meting per 4 minuten. Zonder buitensensor gebruikt
het de weerentiteit. Zonnestraling telt op tot een dagsom en zonuren; een lux‑sensor wordt
omgerekend. Regen komt van de regenmeter; zonder meter wordt de verwachting voor vandaag
geboekt (die nooit een gemeten of uit de recorder gehaalde dag overschrijft). Elke gekoppelde
temperatuursensor krijgt zijn eigen dagminimum, ‑maximum en ‑gemiddelde.

**Aanvullen uit de recorder en Open‑Meteo.** Eén keer per dag (en bij het opstarten) vult
Hortulus de dagen aan die niemand goed volgde, bv. omdat Home Assistant uit stond of herstartte:

1. **Recorder** van Home Assistant: voor de laatste 30 dagen, als er gaten zijn, worden de
   bewaarde toestanden van de temperatuursensoren, de buitenvochtigheid, de windsnelheid en de
   windstoten omgezet in dagminimum, ‑maximum en tijdgewogen gemiddelde (°F en
   windeenheden omgerekend). De uitersten worden gecombineerd met wat Hortulus zelf mat; het
   gemiddelde vervangt alleen een onvolledige dag. Hoe lang de recorder terug gaat, hangt van
   zijn eigen bewaartermijn af (standaard 10 dagen).
2. **Open‑Meteo**, alleen met *Open‑Meteo gebruiken voor vocht, wind en zon* aan: het
   **waargenomen** dagweer van de laatste 31 dagen voor de (afgeronde) coördinaten van de
   tuin – temperatuur, regen, wind en windstoten, straling, zonneschijn, luchtvochtigheid en
   FAO‑ET₀. Dat vult alleen wat niet goed gemeten is (een dag met minder dan 12 uur eigen
   metingen of een ontbrekende waarde).

Eigen metingen winnen altijd. Voor regen geldt de volgorde regenmeter → recorder → Open‑Meteo
→ verwachting.

**Bewaartermijn.** Dagen blijven in het daglogboek: buiten **ruim twee seizoenen** (800
dagen), per temperatuursensor **400 dagen**. Daarna worden ze samengevoegd tot
**maandcijfers** (minimum, maximum, gemiddelde, regen, vorst‑ en hete dagen, zonuren, hardste
wind) die **voor altijd** blijven, zodat statistieken van jaar tot jaar overeind blijven. Alles
staat in het gewone tuinbestand.

**Gemeten vorstdata.** Per jaar onthoudt Hortulus de laatste dag met een buitenminimum onder
0 °C in de voorjaarshelft (januari–juni; zuidelijk halfrond juli–december) en de eerste in de
herfsthelft. Een halfjaar telt pas mee als het voorbij is en minstens 80 % van zijn dagen
gelogd is; onvolledige seizoenen krijgen een sterretje. Het gemiddelde van de volledige jaren
wordt naast de vorstdata van je regio gezet (*… dagen vroeger / later*). Wijkt het sterk af,
stel dan je eigen vorstdata in bij *Instellingen → Klimaat & regio*: alle zaaivensters schuiven
mee. Hortulus past ze nooit zelf aan.

### Logboek
Onderdelen:

| Onderdeel | Inhoud |
|---|---|
| **Dagboek** | notities, waarnemingen, problemen en mijlpalen met foto's (per bed, gewas of de hele tuin) |
| **Oogst** | het oogstlogboek in kg en stuks (registreer er een als je een oogsttaak afvinkt of vanuit de planner), totalen per gewas, je eigen **geleerde opbrengst per m²** (gebruikt door Automatisch invullen, advies en de boodschappenlijst), de oogst **door de jaren** (beste jaar in goud) |
| **Keuken** | gewassen die klaar zijn om te oogsten met bewaartips, een overschotmelding (meer dan 1,5× wat het gezin in een week eet) met ideeën om te bewaren, in te maken of te delen, en **kosten en opbrengst**: de oogst tegen winkelprijzen naast je uitgaven en het tuinwater |
| **Zaaddoos** | zaadzakjes met houdbaarheid per familie, en het zaad dat het plan nog nodig heeft (de boodschappenlijst slaat zaad over dat je hebt) |
| **Water** | bodemvocht uit de geschiedenis van Home Assistant, water gegeven volgens het logboek van Hortulus en regen, per bed over 7, 14 of 30 dagen; het tuinwaterverbruik van de meter en het peil van de regenton |
| **Seizoensrapport** | gewassen, oogst tegenover verwachting, mislukkingen, problemen uit het dagboek, water; te downloaden als Markdown, of als *Seizoensboek* (PDF) |
| **Systeemlogboek** | elke wijziging in de tuin (vanuit het paneel, acties, automatiseringen en wat Hortulus zelf aanpast) met tijd, wie en wat. **Elke regel kan teruggedraaid worden** (beheerder); een onderdeel dat sindsdien opnieuw gewijzigd is, wordt pas na bevestiging overschreven; het terugdraaien komt ook in het logboek, zodat je het weer kunt herstellen |

Selecteer een bed in de planner om een **bodemanalyse** toe te voegen (pH, organische stof, P,
K, Mg, kalk); het bemestingsplan, het kalkadvies en de boodschappenlijst volgen de laatste.

### Koken
Een seizoenskookboek op basis van wat de tuin nu geeft. Hortulus kijkt naar de gewassen binnen
hun oogstvenster (plus alles wat je zelf toevoegt uit de kelder, zoals bewaarde pompoenen of
ingevroren bonen) en stelt er gerechten voor voor. Sla, komkommer, radijs en dergelijke
gewassen komen alleen in salades en andere ongekookte gerechten; vlierbessen, bonen,
kikkererwten en edamame worden nooit rauw of half gaar aangeboden. Recepten zijn geschreven in
het Engels, Nederlands en Frans, met hoeveelheden per persoon en wat uit de tuin komt, wat in
huis is en wat je moet kopen. Drie delen: **Ideeën uit de tuin**, **Mijn kookboek** en
**Boodschappenlijst**.

* **Keuzes** (onthouden met *Onthoud deze keuzes*, bewaard in de tuin): aantal personen
  (1–12), een basis (wat bij het gerecht past, geen, of pasta, rijst, bulgur, couscous,
  parelcouscous, gnocchi, aardappelen, frieten, brood, noedels), vlees, vis of vegetarische
  eiwitbron (kip, rund, varken, gehakt, worst, spek, ham, zalm, witte vis, garnalen, tofu,
  kikkererwten, linzen, ei, halloumi, geitenkaas … of geen voor vegetarische gerechten),
  **Opgebruiken uit de ijskast** en **Altijd in huis**.
* **Ijskast**‑items (boter, room, melk, eieren, parmezaan, feta, mozzarella, yoghurt, mosterd,
  ui, paneermeel …) worden verwerkt in de gerechten waar ze bij passen: elk item heeft per soort
  gerecht zijn eigen bereiding (yoghurt als tzatziki, raita of honing‑mosterddip; feta gebakken
  of opgeklopt; parmezaan als chips of korst …). Een gerecht neemt hoogstens drie ijskastitems,
  één saus, één dressing en één krokante topping. Ze tellen als “in huis”. Items onder
  *Altijd in huis* komen nooit op de boodschappenlijst.
* **Gerechten**: soep, ovenschotel, wok, pasta, risotto, salade, gratin, stoof of curry,
  frittata, stoemp, gevulde groenten, een bord met vlees en frieten, pesto, fruitcrumble,
  koude soep, crostini, compote en de extra gerechten (ratatouille, tian, shakshuka, taart,
  gnudi, waterzooi, groentekoekjes, clafoutis, panna cotta …). Gerechten die voor bepaalde
  planten gemaakt zijn, nemen alleen die planten. Elk gerecht krijgt een afbeelding (de
  gewassen op een bord met de basis eronder en het vlees in het midden).
* **Hoofdstukken**: Soepen · Voorgerechten · Hoofdgerechten · Desserten · **Bewaren &
  inmaken** (snelle pickles, chutney, passata, pestoblokjes, confituur, invriezen, zuurkool;
  de hoeveelheden zijn een batch). Ideeën, het kookboek en de kookboek‑PDF zijn per hoofdstuk
  ingedeeld.
* **Menu's**: een soep of voorgerecht, een hoofdgerecht en een dessert die bij elkaar passen,
  gemaakt van wat nu te oogsten is (thema‑menu's van het seizoen, en menu's rond een
  hoofdgerecht). Met één klik komen alle drie op de boodschappenlijst of in het kookboek.
* **Een recept aanpassen**: voeg ingrediënten toe, schrap ze of wijzig ze (naam, hoeveelheid,
  eenheid, uit de tuin / in huis / kopen; tot 40) en voeg stappen toe, schrap, herschrijf of
  verplaats ze (tot 30). Je versie komt in je kookboek, de boodschappenlijst en de PDF's volgen
  haar, en *Terug naar het origineel* zet het gegenereerde recept terug.
* **Kookboek**: bewaar recepten (tot 500), markeer favorieten, voeg notities toe, noteer wanneer
  je ze kookte; filter op hoofdstuk en favorieten; zoek op recept of ingrediënt.
* **Boodschappenlijst**: zet gerechten vanuit hun recept op de lijst; ze scheidt wat je moet
  kopen van wat de tuin geeft. Druk haar af, bewaar haar als PDF (lijst, of lijst + recepten
  met de gerechtafbeeldingen), stuur haar naar een gsm (een `notify.*`‑dienst, standaard: de
  meldingsinstellingen van de tuin) of zet haar op een takenlijst van Home Assistant (wat er al
  op staat wordt overgeslagen; je eigen rechten op die lijst gelden).
* **PDF**: een recept, het hele kookboek (een hoofdstukpagina elk, lange recepten lopen door
  op een volgende pagina) of de lijst; tot 200 recepten per PDF, mail of export naar een takenlijst.

### Advies
Een zinsbouwer **Vraag het aan Hortulus** (*Ik heb een vraag/probleem met / over [onderwerp]
[welke]: [vraag]*) met live status, mogelijke oorzaken, wat nu te doen, **eco‑ en
huis‑tuin‑en‑keukenmiddeltjes**, voorkomen en gereedschap. Voorstellen voor je tuin
(bestuivingspartners, bestuivingsbloemen, slechte buren, schaduw, oogstgaten, lege bedden,
ecologie, lagen van een voedselbos) die je met één klik toepast; oogstdekking per maand; een
boodschappenlijst voor het seizoen; gereedschap per klus.

### Handboek
23 hoofdstukken (EN / NL / FR) met zoekfunctie en woordenlijst: plannen, bodem & compost,
zaaien, water geven (ET₀, Kc, waterbalans), voeden (NPK, EC), vruchtwisseling, plantenburen,
de kas, plagen, ziekten, het tuinjaar & winterrust, oogsten & bewaren, zaadwinning, no‑dig &
mulch, kruiden, meerjarigen, fruit, gereedschap & materiaal, huismiddeltjes, oogst het hele jaar,
sensoren kiezen, permacultuur en voedselbossen. De ⓘ‑knopjes in het hele paneel openen de
woordenlijst bij een begrip en verwijzen naar het hoofdstuk.

### Analyse
| Onderdeel | Inhoud |
|---|---|
| **Controle** | verklaart onregelmatigheden (een jaar met gewassen maar zonder plan, gewassen waarvan het bed niet op het plan van hun seizoen staat, bedden buiten hun zone, overlappende of te laat geplande gewassen, een gemiste jaarovergang …) met een link naar de juiste plek en **herstelknoppen met één klik** (gelogd en terug te draaien). Het tabblad toont een teller met het aantal problemen; *Diagnose exporteren* schrijft één JSON‑bestand om bij een bugmelding te voegen |
| **Waarom niet?** | per bed, waarom een plant wel of niet past |
| **Vergelijken** | zones, bedden, elementen en gewassen die tussen twee plannen zijn toegevoegd, verdwenen of veranderd |
| **Fouten** | elke geweigerde actie met de reden |
| **Systeemlogboek** | het logboek uit Logboek |

### Afdrukken
Kies een document – **tuinplan**, **serre / zone**, **bedfiches**, **takenlijst**,
**seizoensoverzicht**, **jaarplan**, **planningsblad** (omtrekken + stippelraster om op te
schetsen), **plantkaarten** of het **seizoensboek** – daarna papier (A4, A3, A5, Letter,
**reMarkable Paper Pro**), richting en kleuren (*volle kleur*, *e‑ink* met lichte tinten en een
arcering per familie, *grijstinten*). Het voorbeeld toont elke pagina; **PDF downloaden** haalt
haar op via de geauthenticeerde API van Home Assistant, **Opslaan** schrijft haar naar
`/config/hortulus/exports/` (privé; een ondertekende downloadlink, 7 dagen geldig). Kaarten
bevatten een legende (families, zones, elementen, symbolen, genummerde gewassen waar namen niet
passen), een schaalbalk met verhouding en een noordpijl; bedfiches voegen een raster van 10 cm,
de compost en bemesting voor de komende gewassen en de wisselteeltgeschiedenis toe. Het
**seizoensboek** (standaard A5) is het hele tuinjaar om af te drukken: voorblad, het plan van
het seizoen, een inleiding geschreven uit de cijfers van het seizoen, een hoofdstuk per maand
(gezaaid, geplant, gedaan, je dagboek met foto's, oogst, water, weer), het jaar in cijfers, een
woordenlijst en achterblad; het aantal bladzijden is een veelvoud van vier. Afdrukdocumenten
gebruiken het plan van het gekozen seizoen.

Een PDF op de reMarkable zetten: download hem en sleep hem in de reMarkable‑desktop‑ of
mobiele app, of stuur hem met *Send to reMarkable* per e‑mail. Het paginaformaat komt precies
overeen met het scherm van de Paper Pro, dus er wordt niets geschaald.

### Instellingen
Onderdelen, van boven naar beneden (beheerders kunnen bewerken; entiteitsvelden zijn
keuzelijsten die alleen passende entiteiten tonen):

| Onderdeel | Inhoud |
|---|---|
| **Klimaat & regio** | halfrond, profiel (voorinstelling / USDA / eigen), vorstdata |
| **Weer & buitensensoren** | weerentiteit, buitentemperatuur, regen, buitenluchtvochtigheid, bladnat, **windsnelheid**, **windstoten**, **zonnestraling (W/m²)**, **licht buiten (lux)**, **Open‑Meteo** (opt‑in: verdamping en het waargenomen weer voor de [klimaatgeschiedenis](#klimaatgeschiedenis)), hoogte |
| **Zones & microklimaat** | per zone: luchttemperatuur, vochtigheid, licht, bladnat, **PAR**; voor kassen en koude bakken ook **raamopener / ventilatie**‑ en **schaduwscherm**‑entiteiten met sturing *uit / advies / automatisch*, *thermische massa*; *tegen een warme muur*, *verwarmd* (+ minimumtemperatuur) |
| **Bedden & sensoren** | per bed: bodemvocht, bodemtemperatuur, **EC, N, P, K**‑sondes, klep, knop **Test (5 s)**, debiet (L/min; het gemeten debiet wordt getoond als de watermeter het leerde), **kraantimer** |
| **Bewateringshardware** | modus (*uit / advies / automatisch*), pomp, starttijd, maximale looptijd, vorstvergrendeling, regen overslaan, pomp stopt vóór klep; sensor **zonne‑overschot** (W of kW), *starten vanaf overschot* (W, standaard 500) en *ten laatste wachten tot* (standaard 11:00); laadtoestand **thuisbatterij** (%) en *of starten bij* (%, standaard 95); **eerst regenwater**: pomp uit de ton, *overschakelen op leidingwater onder* (%), *leidingwater als de ton leeg is*, vermogen van beide pompen (W) |
| **Middelen (automatisch invullen)** | gezinsgrootte, uren, water en compost voor Automatisch invullen, doelen; schakelaars voor *seizoenswerk in de kalender* en **Ecologische tips** (biologische antwoorden op plagen en ziekten, ecokalender, voedselbosadvies) |
| **Extra's** | optionele hulpjes, standaard allemaal aan – zie [Extra's](#extras) |
| **Meldingen** | blijvend, pushdiensten, TTS, speakers, tijdstip overzicht, vorst‑ en hittewaarschuwingen, uitgesproken vorstbericht; herinneringen (avondherinnering voor achterstallige taken, standaard 18:30 na 1 dag; weekoverzicht vooraf, standaard zondag 19:00); *taken plannen volgens het weer* (schuift weergevoelige klussen weg van regenachtige, vrieskoude of hete dagen) |
| **Watermeter & regenton** | de metersensor (m³ of L), het peil van de regenton in % en de totale inhoud van de tonnen; lekmeldingen |
| **Kosten** | munt, waterprijs per m³, eigen prijzen per gewas (€/kg) voor het overzicht van oogst tegenover kosten |
| **Huishouden & spraak** | wie nieuwe taken krijgt (standaard en per soort taak), een notify‑dienst per persoon, de spraakzinnen voor Assist installeren |
| **Algemeen** | taal (volg Home Assistant / English / Nederlands / Français), eenheden (metrisch), rastergrootte, bereik buurplanten, **importeren & exporteren** (JSON / YAML, inclusief taken) |
| **Weergave (deze browser)** | per browser: plantfoto's van Wikipedia; kleurthema (*klassiek groen*, *aarde*, *nacht*, *seizoen*) en licht / donker / automatisch. In Home Assistant volgen het thema en de keuze licht / donker je gebruiker naar elk toestel |

#### Bewateringshardware in 5 stappen
1. Instellingen → Bedden & sensoren: kies per bed de klep (`switch.*`, `valve.*` of
   `input_boolean.*`) en het debiet in L/min (meet het: hoe lang duurt het om een emmer van
   10 L te vullen, of laat de watermeter het leren). Druk op **Test (5 s)** om de klep 5 s te
   openen (de pomp pas als de klep open meldt) en controleer of hij open en weer dicht meldt.
   Heeft de klep een eigen timer, vul die dan in bij *Kraantimer (min)*: langere beurten worden
   opgesplitst in openingen die erbinnen blijven.
2. Instellingen → Bewateringshardware: optioneel de pomp (schakelaar of kraan) en *Pomp stopt
   vóór klep* (seconden dat de pomp uit is voordat de klep sluit).
3. Kies de starttijd en de grenzen (maximale looptijd, vorstvergrendeling, regen overslaan).
4. Probeer `garden_manager.run_irrigation_plan` met `dry_run: true` en bekijk het plan.
5. Zet **Automatisch bewateren** aan. In de modus *advies* krijg je alleen watertaken.

Een beurt eindigt als een klep dicht blijft, of een minuut lang niets meldt terwijl de pomp
draait (eerst gaat de pomp uit); een klep of pomp die veel langer open staat dan een beurt kan
duren (maximale looptijd + 10 minuten) geeft een banner met *Kraan sluiten*; met de lekmelding aan in Instellingen en een watermeter ingesteld wordt minstens 5 L die binnen
15 rustige minuten (geen beurt bezig, alle kranen dicht) geteld wordt als lek gemeld.

#### Extra's
Optionele hulpjes (2.0), elk een schakelaar onder *Instellingen → Extra's* en een instelling op
het hoogste niveau van het tuinbestand. Standaard staan ze allemaal aan; zet je er een uit, dan
verdwijnt of vervalt het gewoon.

| Instelling | Wat het doet |
|---|---|
| `slogans` | wisselende tuinspreuken (NL/EN/FR, per thema en seizoen, eigen spreuken voor het zuidelijk halfrond), gekozen per dag en per plaats: dagoverzicht, weekplan, maandelijks weerbericht, seizoensrapport, achterflap van het seizoensboek, de kopregel van het dashboard en de kaart |
| `soil_estimate` | bedden zonder bodemtemperatuursensor krijgen een bodemtemperatuur geschat uit de gelogde daggemiddelde luchttemperatuur (afgevlakt over de laatste 10 dagen, minstens 3 gelogde dagen nodig); gebruikt voor het zaaiadvies, op de bedkaart getoond als *≈ x °C* |
| `water_forecast` | per bed: wanneer de waterbalans het makkelijk opneembare water (p × TAW) voorbijgaat met de ET₀ en regen uit de verwachting voor de komende 7 dagen – *over N dagen weer droog* |
| `sensor_health` | een gekoppelde sensor die ≥ 2 dagen onbeschikbaar of onbekend is, geeft één waarschuwing (`alert.sensor_silent`, in plaats van de melding over een verouderde meting) |
| `season_summary` | het seizoen en de vorige maand in zinnen tegenover dezelfde data vorig jaar (warmer / kouder, natter / droger, zonniger / grijzer, vorstnachten): bovenaan de klimaatgeschiedenis, in het seizoensrapport en het seizoensboek, en als melding bij het overzicht op de 1e van elke maand |
| `local_frost_suggest` | na ≥ 2 volledige gemeten jaren waarin de laatste voorjaars‑ of eerste herfstvorst ≥ 7 dagen van de regio afwijkt: een infomelding en een knop **Mijn vorstdata gebruiken** in de klimaatgeschiedenis |
| `station_import` | de CSV‑export van een weerstation importeren in de klimaatgeschiedenis (zie daar) |
| `solar_irrigation` | automatisch bewateren wacht op zonne‑overschot (sensor en grenzen onder *Bewateringshardware*): de beurt start zodra het overschot het minimum haalt, ten laatste op *ten laatste wachten tot*; geen sensor of geen bruikbare waarde = niet wachten. Het dashboard toont *Wacht op zonne‑overschot* |
| `climate_card` | een klimaatregel op de `hortulus-tasks-card`: gemiddelde van 7 dagen en het verschil met vorig jaar, regen, zon, een temperatuurband van 14 dagen (kaartopties `climate: false`, `slogan: false`, zie [Entiteiten](ENTITEITEN.md#lovelace-kaart)) |
| `frost_heating` (2.1) | een verwarming per kas of bak (*Zones*: verwarmingsentiteit – schakelaar of climate –, verwarmen onder °C, vermogen, weekbudget in kWh): met klimaatsturing op *automatisch* gaat ze aan onder de temperatuur van de luchtsensor van de zone en uit 1,5 °C erboven; is het weekbudget op, dan blijft ze uit tot maandag. Energie: `sensor.hortulus_greenhouse_heating_this_week` |
| `adaptive_irrigation` (2.1) | ~90 minuten na een beurt toont de vochtsensor van het bed hoeveel water er echt introk; na twee beurten krijgt het bed een eigen factor (0,5–2×) op het geplande water, en de waterbalans telt wat introk. Zichtbaar per bed onder *Bedden*, met *Vergeten*. Beurten waarna het regende tellen niet |
| `own_yields` (2.1) | je geoogste kg/m² wegen mee tegen de boekwaarde (die telt als één seizoen), en de oogstverwachting begint wanneer je eerste oogsten echt kwamen (dagen na zaaien of uitplanten, hooguit een maand verschil) |
| `ai_diagnosis` (2.1) | *Wat scheelt er?* onder foto's in het dagboek: de foto gaat naar de AI‑taak van Home Assistant (je eigen keuze of de voorkeurstaak, `ai_task_entity`), die kiest uit de plagen en ziektes die Hortulus kent; het antwoord komt met het biologische advies en kan als probleem genoteerd worden |
| `calendar_mirror` (2.1) | kopieert de open taken van de komende `mirror_days` (standaard 7) naar `mirror_calendar` (Google, CalDAV, lokaal …), elke taak één keer per vervaldag; latere wijzigingen gaan niet mee (Home Assistant kan afspraken aan andere agenda's toevoegen, niet wijzigen) |

---

## 5. Importeren en exporteren

Exporteer via het Tuinplan / de Planner (menu Meer), Instellingen → Algemeen of
`garden_manager.export_plan`. Importeren (beheerder) kan vanuit hetzelfde menu of met
`garden_manager.import_plan`.

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
features:                  # tuinelementen: path, house, hedge, tree, shed, water_butt ...
  - {id: ft_1, name: Path, type: path, x_cm: 0, y_cm: 320, width_cm: 400, length_cm: 60}
layouts:                   # de tuinplannen van andere seizoenen (zones, beds, features)
  "2027": {zones: [], beds: [], features: []}
layout_season: 2026        # het seizoen waarvan het plan de live zones / beds / features hierboven is
archived_plans: []         # opzijgezette plannen ("niet actief"): zones, beds, features, plantings
plantings:
  - id: pl_carrots
    plant_id: carrot
    bed_id: bed_1
    season: 2026
    layout: row            # single | block | row
    x_cm: 0                # relatief aan het bed
    y_cm: 0
    width_cm: 200
    length_cm: 25
    method: direct_sow     # indoor_sow | direct_sow | transplant
custom_plants: []
plant_overrides: {tomato: {spacing_cm: 60}}
rotation_history:
  - {bed_id: bed_1, season: 2025, family: Solanaceae, source: manual}
# tasks: [...]             # alleen bij export met taken (include_tasks)
```

Importmodi: **samenvoegen** (bijwerken op id, niets wordt verwijderd; het live seizoen blijft)
of **vervangen** (indeling, plannen per seizoen en beplantingen worden vervangen). Wat
meereist: zones, bedden (met hun bodemanalyses; een bestand zonder die analyses laat de
reeds opgeslagen staan), tuinelementen, de plannen per seizoen, opzijgezette plannen,
beplantingen, eigen planten, **plantoverrides** en de wisselteeltgeschiedenis, plus taken als
die zijn meegenomen. Een ouder bestand zonder `features` of `archived_plans` laat de reeds
opgeslagen exemplaren met rust. Bestanden van oudere versies worden automatisch gemigreerd
(opslagversie 1.8); onbekende velden worden genegeerd. Verwijzingen worden gecontroleerd
tegen het plan waartoe ze behoren (een bed moet naar een zone van zijn eigen plan wijzen, een
beplanting naar een bestaand bed, ook in de opzijgezette plannen); een veld van het verkeerde
type (bijvoorbeeld een `plant_overrides` die geen mapping is) weigert het hele bestand, en een
geweigerd bestand wijzigt niets. Seizoenen die naar het archiefbestand verhuisd zijn, maken
**geen** deel uit van een export.

Recepten, de boodschappenlijst, uitgaven, het dagboek en het oogstlogboek zitten niet in het
planbestand; ze staan in de tuinopslag.

---

## 6. Eenheden, taal en tijd

* Intern metrisch (cm, °C, mm, L). Sensoren en verwachtingen in imperiale eenheden worden bij
  het lezen omgerekend.
* Het paneel, gegenereerde taaktitels, meldingen, kalenderafspraken, het handboek, plantnamen,
  recepten en Assist‑zinnen zijn beschikbaar in het **Engels, Nederlands en Frans**.
  Gegenereerde teksten volgen de taal van Home Assistant tenzij je dat overschrijft onder
  *Geavanceerd* / *Algemeen* (auto / en / nl / fr); het paneel volgt de taal van je gebruiker.
  Datums staan in de volgorde dag‑maand‑jaar in de taal van het paneel, met Belgische
  notaties voor Nederlands en Frans (nl‑BE, fr‑BE).
* Alle datums zijn lokaal (tijdzone van Home Assistant). Verwachtingsuren worden als absolute
  momenten verwerkt, dus zomer‑/wintertijdovergangen (nachten van 23 of 25 uur) vertekenen de
  vorstduur nooit.

## 7. Prestaties

* Geen sensorpolling – luisteraars voor statuswijzigingen op precies de gekoppelde entiteiten,
  10 s gedebounced; de verwachting is het enige tijdgestuurde ophaalmoment (30 min). De
  klimaatgeschiedenis wordt één keer per dag aangevuld (recorder, Open‑Meteo) en alleen als er
  gaten zijn; een fout daarbij houdt de tuin nooit tegen.
* Alle berekeningen zijn pure Python op gegevens in het geheugen (milliseconden voor een
  gewone tuin), schrijfacties naar de opslag zijn gedebounced (5 s, systeemlogboek 10 s) en
  blokkeren de event loop nooit.
* Seizoenen ouder dan de laatste drie gaan naar het archiefbestand, zodat het tuinbestand en
  elke analyse ook na jaren gebruik klein blijven (sectie 8).
* Het paneel is één JavaScript‑bundel (ongeveer 250 kB gzipped) met een inhoudshash als cache;
  de Lovelace‑kaart is een apart bestand van ~10 kB. Het paneel krijgt een volledige momentopname
  via één websocket‑abonnement dat na elke wijziging wordt ververst.

---

## 8. Seizoenen, jaarovergang en archief

* **Een plan per seizoen.** Het tuinplan (zones, bedden, elementen) wordt per seizoen bewaard;
  het plan van het *actieve* seizoen (`layout_season`) is de live tuin waarmee entiteiten,
  taken en beregening werken. Andere seizoenen (vorig jaar, een ontwerp voor volgend jaar)
  staan ernaast. Op het zuidelijk halfrond loopt een seizoen van juli tot juni.
* **Niets gaat vanzelf naar een nieuw jaar** – niet het plan, niet de meerjarigen. Zodra het
  nieuwe jaar begonnen is, bieden een Advies‑kaart en de werkbalkknop van Tuinplan en Planner de
  **jaarovergang** aan (de knop is ook eerder beschikbaar). Kies of je het plan kopieert (en
  welke zones en elementen meegaan) of een plan gebruikt dat je al voor volgend jaar
  ontwierp; welke meerjarigen en welke overwinterende gewassen (knoflook, winterprei …)
  overgaan; en of het nieuwe jaar meteen de actieve tuin wordt. Het plan van het oude jaar blijft
  als eigen seizoen bestaan; alles staat in het systeemlogboek en kan teruggedraaid worden.
  Een meerjarige hoort bij zijn eigen seizoen en bij de seizoenen waarnaar hij overgezet werd
  (`last_season`); “weg vanaf dit seizoen” bewaart de historiek.
* **Opnieuw beginnen** met *Tuinplan → Plannen*: het huidige plan wordt opzijgezet (niet‑actief,
  met zijn bedden en gewassen) en kan opnieuw geactiveerd of verwijderd worden.
* **Archief.** Seizoenen ouder dan het huidige en de twee ervoor (drie seizoenen blijven)
  verhuizen naar `.storage/garden_manager.garden.archive`: hun beplantingen en hun tuinplan.
  Gewassen die nog staan (een meerjarige die naar het huidige seizoen overgezet is) blijven.
  Dat gebeurt bij het opstarten en één keer per seizoen in twee stappen: eerst worden de
  seizoenen naar het archiefbestand gekopieerd; een seizoen verlaat het tuinbestand pas nadat het
  archief dat het bevat bij een latere start van schijf teruggelezen is, en alleen als het
  sindsdien ongewijzigd is. De wisselteelt blijft werken (elke gearchiveerde beplanting laat een
  wisselteeltregistratie achter), en het seizoensrapport en het seizoensboek openen gearchiveerde
  seizoenen nog, inclusief gewassen die ernaar zijn overgezet.

## 9. Meerdere tuinen

Voeg de integratie opnieuw toe (Instellingen → Apparaten & diensten → Integratie toevoegen →
Hortulus) voor een volkstuin of een tweede perceel. Elke tuin is een eigen config entry met
eigen gegevens, opslagbestanden, apparaten en entiteiten; de eerste tuin behoudt zijn gegevens
en entity‑id's precies zoals ze waren, verdere tuinen heten “Hortulus 2”, “Hortulus 3” …
(hernoem gerust).

* Het paneel toont bovenaan een **tuinkeuze** en onthoudt je keuze per browser.
* Elke dienst accepteert `garden:` (de titel of het entry‑id); zonder gaat het naar de eerste tuin.
* De takenkaart accepteert `garden:`; het PDF‑eindpunt `garden_id`.
* Websocket‑commando's accepteren `garden_id` (het entry‑id).
* Assist antwoordt over de eerste tuin.

## 10. Hortulus Web (optionele website)

Hortulus Web is een websiteversie van Hortulus die dezelfde Python‑engine in de browser draait
(Pyodide). Ze wordt apart geleverd en is geen onderdeel van deze integratie; niets in Home
Assistant hangt ervan af. Wat de repository zelf toont:

* Het paneel accepteert extra instellingen van een hostpagina: een lijst toegestane `tabs`, een
  `viewer`‑vlag (alleen lezen) en een `web`‑vlag. Home Assistant geeft er geen mee.
* Een tab **Tuin** (een alleen‑lezen blik op het plan: klik een zone, bed, gewas of element voor
  de details, kies het jaar) en een beperkte tablijst laten de website een gedeelde tuin aan
  bezoekers tonen, alleen de delen die de eigenaar koos. Een gedeelde weergave waarvan de
  tablijst niets toelaat, toont niets van de tuin.
* Kookrecepten kunnen als **gedeeld** gemarkeerd worden (zichtbaar voor wie de tuin mag zien) en
  gemaild worden in plaats van naar een gsm gestuurd.
* De website draait de websocket‑handlers, bewerkingen en opslag van de integratie op haar eigen
  vervangers voor de modules van Home Assistant, zodat de planbestanden uit
  [sectie 5](#5-importeren-en-exporteren) tussen beide uitgewisseld kunnen worden.
* **Klimaatgeschiedenis op de website.** De website rekent alleen terwijl iemand de tuin open
  heeft, dus ze vult de geschiedenis zelf aan: voor **elke tuin** uit het waargenomen weer van
  **Open‑Meteo**, en voor een tuin die aan een Home Assistant gekoppeld is ook uit de
  **recorder** van die Home Assistant, via het token van de tuin. Dezelfde regels gelden als
  hierboven ([Klimaatgeschiedenis](#klimaatgeschiedenis)): eigen metingen eerst, de recorder
  daarna, Open‑Meteo als aanvulling.
