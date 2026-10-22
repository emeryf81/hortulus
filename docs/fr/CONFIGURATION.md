# Configuration

Hortulus se configure à trois endroits, chacun avec un rôle bien défini :

| Où | Quoi | Stocké dans |
|---|---|---|
| **Assistant de configuration** (config flow) | Premier démarrage : climat, météo, premières planches + capteurs, notifications | config entry → alimente une seule fois le stockage du jardin |
| **Options** (Paramètres → Appareils et services → Hortulus → *Configurer*) | Climat, météo et capteurs extérieurs, notifications, réglages avancés | écrites dans le stockage du jardin |
| **Panneau Hortulus** | Tout le reste : dessin des planches et zones, cultures, association des capteurs, base de plantes, tâches, cuisine | `.storage/garden_manager.garden` |

Après l'installation, le stockage du jardin est l'unique source de vérité ; le flux
d'options et le panneau le modifient tous deux, ils ne peuvent donc jamais se contredire.
À côté du fichier du jardin, il y a deux autres fichiers par jardin :
`garden_manager.garden.syslog` (le journal système, les 500 dernières entrées) et
`garden_manager.garden.archive` (les anciennes saisons, voir la [section 8](#8-saisons-passage-à-la-nouvelle-année-et-archive)).

Sommaire : [1 Assistant de configuration](#1-assistant-de-configuration) ·
[2 Association des capteurs](#2-règles-dassociation-des-capteurs) ·
[3 Options](#3-options-de-lintégration) · [4 Le panneau](#4-le-panneau) ·
[5 Importation et exportation](#5-format-dimportation-et-dexportation) ·
[6 Unités, langue, heure](#6-unités-langue-heure) ·
[7 Performances](#7-performances) · [8 Saisons et archive](#8-saisons-passage-à-la-nouvelle-année-et-archive) ·
[9 Plusieurs jardins](#9-plusieurs-jardins) · [10 Hortulus Web](#10-hortulus-web-site-web-facultatif)

---

## 1. Assistant de configuration

L'assistant comporte ces écrans, dans cet ordre : profil climatique → votre climat → météo →
planches / serres / bacs (répétable, chacun suivi de ses capteurs) → notifications →
récapitulatif.

### Étape 1 – Profil climatique
Choisissez comment Hortulus apprend vos **dates de gel**. Chaque fenêtre de semis ou de
plantation de la base de plantes est exprimée par rapport à elles. L'assistant demande d'abord
le type de profil (présélectionné : *préréglage régional* lorsque le pays de Home Assistant est
NL, BE, GB, DE ou FR, sinon *zone de rusticité USDA*), puis les détails ; l'hémisphère est
présélectionné d'après la latitude de Home Assistant.

| Profil | À choisir quand | Exemple |
|---|---|---|
| **Préréglage régional** | Vous habitez une région couverte | *Pays-Bas / Flandre* : dernières gelées le 20 avr., premières gelées le 25 oct. |
| **Zone de rusticité USDA** | Amérique du Nord, ou vous connaissez votre zone | 7a → 8 avr. / 1er nov. (décalé de 6 mois dans l'hémisphère sud) |
| **Dates de gel personnalisées** | Vous avez des données locales (le mieux) | `04-28` / `10-15` (format `MM-JJ`) |

Préréglages disponibles :

| Préréglage | Hémisphère | Dernières gelées | Premières gelées |
|---|---|---|---|
| `nl_be` Pays-Bas / Flandre | N | 04‑20 | 10‑25 |
| `uk_south` Royaume-Uni (sud) | N | 04‑10 | 11‑01 |
| `uk_north` Royaume-Uni (nord) | N | 05‑01 | 10‑15 |
| `de_central` Allemagne (centre) | N | 04‑30 | 10‑15 |
| `fr_north` France (nord) | N | 04‑15 | 10‑31 |
| `scandinavia_south` Scandinavie du Sud | N | 05‑15 | 09‑30 |
| `mediterranean` Méditerranée | N | 03‑01 | 12‑01 |
| `au_melbourne` Australie (Melbourne) | S | 09‑15 | 05‑15 |
| `nz_christchurch` Nouvelle-Zélande (Christchurch) | S | 10‑10 | 04‑25 |
| `za_highveld` Afrique du Sud (Highveld) | S | 09‑01 | 05‑15 |

**Cas limites gérés** : un `02-29` personnalisé devient le 28 février les années ordinaires ;
dans l'hémisphère sud, une *saison* va de juillet à juin et porte le nom de l'année où tombe son
printemps (saison 2026 = sept. 2026 – mai 2027) ; les zones USDA 11 et plus sont traitées comme
sans gel. Les dates impossibles (comme `13-01`) sont refusées.

### Étape 2 – Météo
* **Entité météo** (recommandée) : doit fournir une prévision horaire et/ou journalière.
  Hortulus appelle `weather.get_forecasts` toutes les 30 minutes et à chaque mise à jour de
  l'entité météo (au plus une fois toutes les 10 minutes). Les unités des prévisions sont
  converties automatiquement en °C, mm et km/h.
* **Température extérieure** (facultatif) : alimente l'[historique du climat](#historique-du-climat)
  (minimum, maximum et moyenne du jour) et donc les degrés-jours de croissance ; à défaut, la
  température actuelle de l'entité météo est utilisée. Les capteurs en °F sont convertis.
* **Capteur de pluie** (facultatif) : un cumul de pluie journalier en mm (ou un détecteur de
  pluie binaire).

D'autres entrées météo (humidité extérieure, humectation des feuilles, une **station météo** avec
vitesse du vent, rafales et rayonnement solaire, lumière extérieure, Open‑Meteo facultatif,
altitude) se règlent ensuite dans le panneau sous *Paramètres → Météo et capteurs extérieurs*.

### Étape 3 – Planches, serres et bacs
Ajoutez autant de zones que vous voulez (menu *Ajouter une autre planche, serre ou bac*). Chaque
zone demande le nom, le type (*planche extérieure*, *serre*, *bac / pot*), largeur × longueur
(mètres, 0,1–100), sol, ombre en % (par pas de 5) et exposition au vent, suivis d'un écran de
capteurs (tous facultatifs) :

| Champ | Entité typique | Affiché pour | Filtre d'entités |
|---|---|---|---|
| Humidité du sol | `sensor.soil_moisture_bed_1` | tous | `sensor`, classe d'appareil humidité |
| Température du sol | `sensor.soil_temp_bed_1` | tous | `sensor`, classe d'appareil température |
| Température de l'air | `sensor.greenhouse_temp` | serre | `sensor`, classe d'appareil température |
| Humidité de l'air | `sensor.greenhouse_humidity` | serre | `sensor`, classe d'appareil humidité |
| Lumière (éclairement) | `sensor.greenhouse_lux` | serre | `sensor`, classe d'appareil éclairement |
| Interrupteur ou vanne d'arrosage | `valve.bed_1` ou `switch.drip_bed_1` | tous | `switch`, `valve` |
| Débit d'arrosage | `4` L/min | tous | – |

Ce que l'assistant crée :

* **Planches extérieures et bacs** → carrés potagers surélevés (bacs : planches en bac) dans une
  seule zone de plein air (« Jardin »), disposés de gauche à droite avec des allées de 50 cm.
* **Serre** → une *zone* serre de la taille indiquée avec une planche en pleine terre
  (« Greenhouse Zone A bed ») le long du grand côté ; les capteurs d'air se rattachent à la zone,
  les capteurs de sol et la vanne à la planche. Plusieurs serres se placent côte à côte.

Tout peut être redessiné plus tard dans le panneau.

### Étape 4 – Notifications
Notifications persistantes, autant de services `notify.*` que vous voulez (push mobile), un moteur
de synthèse vocale facultatif + haut-parleurs, et l'heure du **récapitulatif quotidien** (7 h 30 par
défaut). Les alertes de gel, les alertes de chaleur et l'annonce vocale du gel se règlent dans le
flux d'options ou dans Paramètres → Notifications (alertes de gel et de chaleur activées,
annonce désactivée par défaut).

### Étape 5 – Récapitulatif
Relisez et, si vous voulez, ajoutez un **plan d'exemple** pour la saison à venir : tomate + basilic
+ œillet d'Inde sous verre, carottes à côté des oignons (masquage de la mouche de la carotte et de
l'oignon) et trois semis échelonnés de laitue. Un jardin vide peut aussi être démarré depuis
l'écran d'accueil du panneau (voir *Aujourd'hui*).

---

## 2. Règles d'association des capteurs

Chaque planche résout ses capteurs **champ par champ**, dans cet ordre :

1. les capteurs définis **sur la planche**,
2. les capteurs définis **sur sa zone** (p. ex. un seul thermomètre de serre pour toutes ses planches),
3. pour toute zone qui **n'est pas** une serre ni un châssis (plein air, verger, jardin
   d'aromatiques, bacs …) : les **capteurs extérieurs** des paramètres météo.

Les serres et les châssis ont leur propre climat et ne se rabattent jamais sur les capteurs
extérieurs. Un capteur manquant, `unknown` ou `unavailable` réduit simplement la précision. Un
capteur qui n'a rien transmis depuis plus longtemps que *les minutes avant qu'un capteur soit
obsolète* (360 par défaut) est ignoré et déclenche une alerte « capteur obsolète ». Hortulus
utilise `last_reported` : un capteur qui affiche une valeur constante mais qui est bien vivant
n'est donc pas considéré comme obsolète.

Types de capteurs que vous pouvez associer dans le panneau (Paramètres) : humidité du sol,
température du sol, CE et sondes N / P / K par planche ; température de l'air, humidité de l'air,
lumière, PAR et humectation des feuilles par zone ; pour le jardin, les capteurs extérieurs :
température extérieure, humidité, pluie, humectation des feuilles et, pour une **station météo**,
vitesse du vent, rafales, rayonnement solaire (W/m²) et lumière extérieure (lux). Les vitesses
de vent en m/s, mph ou nœuds sont converties en km/h ; sans capteur de rayonnement, la lumière
extérieure en lux sert d'estimation (environ 127 lux par W/m²). Chaque capteur de température
associé (extérieur, air d'une zone, air près d'une planche, sol) est aussi suivi jour par jour
dans l'[historique du climat](#historique-du-climat). Une fois par jour, un capteur d'humidité règle aussi le
bilan hydrique de la planche, et chaque planche apprend à quelle vitesse elle se dessèche vraiment.

---

## 3. Options de l'intégration

| Menu | Champs |
|---|---|
| Climat et dates de gel | profil, hémisphère, préréglage / zone / dates personnalisées |
| Météo et capteurs extérieurs | entité météo, température extérieure, pluie |
| Notifications | notifications persistantes, services push, synthèse vocale, haut-parleurs, heure du récapitulatif, alertes de gel, alertes de chaleur, annonce vocale du gel |
| Réglages avancés | langue des tâches générées (auto/en/nl/fr), rayon d'interaction des associations (10–300 cm), minutes avant qu'un capteur soit obsolète (15–2880), profondeur de la zone racinaire (50–600 mm), arrosage maximal par session (2–60 mm) |

Chaque entrée de menu n'enregistre que sa propre section dans le stockage du jardin.
L'enregistrement recharge l'intégration ; votre plan et vos tâches ne sont pas touchés. Les
planches, les zones et l'association des capteurs se modifient dans le panneau, pas ici.

---

## 4. Le panneau

Ouvrez **Hortulus** dans la barre latérale (`/hortulus`). Les utilisateurs non administrateurs
peuvent tout consulter et travailler avec les tâches, le carnet, les récoltes et le livre de
cuisine ; modifier le plan, la base de plantes, les paramètres et le matériel exige un
administrateur. Chaque onglet a sa propre URL (`/hortulus/calendar`, `/hortulus/wall` …) ; le
Manuel accepte un chapitre (`/hortulus/handbook/<chapitre>`).

Le menu compte huit rubriques ; les onglets liés d'une rubrique s'affichent en ligne dessous. Une
rubrique se rouvre sur le dernier onglet utilisé.

| Rubrique | Onglets |
|---|---|
| **Aujourd'hui** | Aujourd'hui (tableau de bord) · Écran mural (bouton du tableau de bord) |
| **Jardin** | Planificateur · Plan du jardin · Cultures |
| **Calendrier** | Calendrier |
| **Météo** | Météo |
| **Journal** | Journal |
| **Cuisine** | Cuisine |
| **Savoir** | Plantes (bibliothèque) · Conseils · Manuel |
| **Gestion** | Analyse · Imprimer · Paramètres |

Un neuvième onglet, *Jardin* (un aperçu en lecture seule du plan), n'existe que pour le site web
([section 10](#10-hortulus-web-site-web-facultatif)) et n'apparaît jamais dans Home Assistant.

### Aujourd'hui (tableau de bord)
Un bandeau aux couleurs de la saison avec des tuiles de chiffres (tâches aujourd'hui, travail
aujourd'hui, degrés-jours), les tâches du jour avec une case à cocher, les planches avec leur
humidité, la serre, les 48 prochaines heures de météo, ce qui vient ensuite, une carte **Eau et
climat** (mode d'irrigation, planches qui ont besoin d'eau, *Arroser maintenant* / *Arrêter*,
risque de maladie, nutriments), une carte **Ravageurs au jardin** (quels ravageurs volent en ce
moment, seulement pour les cultures en terre ou bientôt en terre) et **Récolte rapide** (les
cultures qui peuvent être cueillies maintenant : ajoutez le poids avec de gros boutons, puis
enregistrez). Des bandeaux rouges apparaissent pour une **vanne restée ouverte** (avec *Fermer la
vanne*) et pour une **fuite**. Un jardin vide affiche un **écran de bienvenue** : aménager un
potager de départ prêt à l'emploi (2 à 4 carrés surélevés, un pot d'aromates, une serre en option,
avec un premier plan), dessiner le vôtre ou lire d'abord le manuel.

### Écran mural
Une vue kiosque calme et en grand format pour une tablette (`/hortulus/wall`, ou *Aujourd'hui →
Écran mural*) : l'heure, la météo, les tâches du jour avec de grosses cases à cocher, l'humidité
des planches et les alertes. Pas de menus ; l'écran s'assombrit la nuit. En néerlandais,
*Aanpassen* permet à chacun d'arranger son propre écran : choisir les blocs (prévisions, radar de
pluie, agenda, dicton météo, idée de recette, fait sur le jardinage bio, le jardin en chiffres…), les
glisser dans l'ordre et en régler la largeur ; tout tient sur un seul écran. Chaque utilisateur garde
son propre écran, sur chaque appareil où il est connecté.

### Plan du jardin
Le plan du jardin fixe la forme du jardin pour **une saison**, sans plantes, en trois étapes :
**Terrain** (éléments : maison, allée carrossable, rue, parking, carport, terrasse, terrasse en
bois, mur, allées en gravier / pierre / bois / pas japonais / écorces, pelouse, parterre de
fleurs, haie, arbuste, arbre, mare, coin salon, piscine, aire de jeux, clôture, treillis, ruche,
abri de jardin, compost, tonneau d'eau de pluie …), **Zones de culture** (plein air, jardin
d'agrément, serre, châssis, jardinières et pots, verger, forêt-jardin, petits fruits, jardin
d'aromatiques, jardin de fleurs) et **Planches** (ouvrez une zone et dessinez ses planches et
jardinières sur sa propre carte ; l'outil *Jardinière / pot* dessine une planche en bac). Les
éléments se dessinent sur une grille de 10 × 10 cm ; une maison, une allée, une allée carrossable,
une haie ou une zone de culture posée sur une pelouse lui retire cette surface (carte, impression
et m²), pas un arbre ni un arbuste. Chaque élément ne peut être sélectionné, déplacé et modifié que
dans sa propre étape. Barre d'outils :

* Sélecteur de **Saison**. Une saison sans plan propose de copier le plan d'une autre année ou de
  commencer vide.
* **Plans** : recommencer avec un nouveau plan (à partir de zéro, mêmes zones mais vides, ou zones
  et planches sans cultures). Le plan actuel devient **inactif** (mis de côté avec ses planches et
  ses cultures) ; il peut être réactivé plus tard (en échangeant sa place avec le plan actif),
  comparé ou supprimé.
* **Passage à la nouvelle année**, voir la [section 8](#8-saisons-passage-à-la-nouvelle-année-et-archive).
* **⋮ Plus** : exporter (JSON / YAML), importer, raccourcis clavier.

### Planificateur
Le planificateur ne fait que planter, sur le plan de la saison choisie (zones, planches et éléments
y sont verrouillés). Deux étapes : **Vivaces** (arbres, arbustes, aromatiques vivaces, asperges,
rhubarbe – elles restent d'une année à l'autre, fruits après *N* ans) et **Annuelles**. Un clic
sélectionne un élément, un second clic (ou *Détails*, ou <kbd>Entrée</kbd>) ouvre sa fenêtre de détails.

* **Palette de plantes** : choisissez *Unique*, *Bloc* ou *Rang*, puis faites glisser une plante
  sur une planche (ou appuyez sur <kbd>Entrée</kbd> sur une plante de la palette pour l'ajouter à la
  planche sélectionnée). La palette montre les plantes qui conviennent au type de la zone ouverte.
  Pendant le survol, Hortulus interroge le serveur pour une vérification de compatibilité en
  direct et affiche ♥ amis / ⚠ conflits / ⟲ problèmes de rotation dans l'étiquette fantôme.
* **Fenêtre de détails** : disposition, méthode (semer à l'abri / semer en place / planter), statut,
  taille, date planifiée forcée, une chronologie de la saison (période de semis, période de
  plantation, récolte), stade de croissance, coefficient cultural, degrés-jours et date de récolte
  attendue, tous les avertissements avec leur explication, **meilleurs voisins** en cas de conflit,
  boutons **convient dans** qui déplacent une culture vers une planche sans conflit de rotation,
  **Pourquoi (pas) ici ?** par culture, la rotation des cinq dernières années, une **note rapide
  avec photo**, une chronologie de photos et la consommation d'eau de la planche.
* **Semis échelonnés** : divisez un bloc en bandes semées tous les *N* jours (par défaut selon la
  plante, p. ex. laitue 21 jours) ou superposez les semis au même endroit. Les semis hors de la
  période de semis sont ignorés et signalés.
* **Remplissage auto** (étape Annuelles) : indiquez le nombre de personnes du ménage, les heures par
  semaine, l'eau et le compost dont vous disposez, vos objectifs (légumes frais, légumes de garde,
  aromatiques, pollinisateurs, récolte d'hiver, vivaces, peu d'entretien), les cultures
  indispensables et celles à éviter, vos préférences (liberté de choix, respecter les voisinages,
  ajouter des pollinisateurs, récoltes toute l'année, vivaces autorisées, respecter le type de
  zone) et les planches à remplir. La proposition montre cultures, nombres, m², récolte attendue,
  minutes par semaine, eau et compost en semaine de pointe, plus une raison pour chaque plante non
  placée (trop tard, type de zone, verre, gel, rotation, mauvais voisin, pas de place) et la
  possibilité de remplir la saison suivante. Rien ne change tant que vous n'appuyez pas sur
  **Appliquer au plan**. Les règles : les quantités par personne viennent de la base (ou de vos propres
  kg/m² appris) ; les conflits de rotation excluent une planche ; les associations, le besoin de
  serre et la tolérance à l'ombre notent la planche ; les bandes sont remplies avec les cultures les
  plus hautes du côté opposé au soleil ; les cultures rapides reçoivent trois semis successifs.
* **Sélection multiple** : <kbd>Maj</kbd>/<kbd>Ctrl</kbd>-clic sur des planches, cultures ou
  éléments ; faites-les glisser ensemble ou utilisez **aligner** (à gauche, centrer, à droite, en
  haut, au milieu, en bas) et **répartir**.
* **Calques** : afficher / masquer les zones, les éléments et les cultures.
* **Calques d'information** : associations (vert = amis, vert pointillé = répulsion des ravageurs,
  rouge tireté = ennemis, violet = allélopathie, orange = concurrence ou chevauchement, gris
  pointillé = ombrage), humidité (contour de la planche + %), température du sol. Les symboles des
  plantes suivent le port (disque = buissonnant, triangle = grimpant, losange = dressé, anneau =
  coureur, fleur = rosette, ▼ = légume-racine, goutte = bulbe), si bien que le plan se lit aussi sans
  couleur. Les cultures sont dessinées plus petites après la plantation et atteignent leur taille
  finale à la récolte pour la date affichée.
* **Afficher le jardin au** : parcourez la saison – les cultures qui ne sont pas en terre à cette
  date sont estompées.
* **Bandeau de fin de saison** : ce qui peut encore être semé ou planté, avec un accès direct au plan
  de l'an prochain.
* **Enregistrement automatique** : les modifications sont enregistrées environ 1 s après chaque
  changement, avec une révision en concurrence optimiste ; si le plan a changé ailleurs, vous
  recevez un avis et le plan le plus récent.

Raccourcis clavier (appuyez sur <kbd>?</kbd> dans le planificateur) :

| Touches | Action |
|---|---|
| <kbd>←</kbd><kbd>↑</kbd><kbd>→</kbd><kbd>↓</kbd> | déplacer la sélection d'un pas de grille (<kbd>Maj</kbd> = 10×) |
| <kbd>Alt</kbd> + flèches | redimensionner la sélection |
| <kbd>Ctrl/⌘</kbd>+<kbd>Z</kbd> / <kbd>Ctrl/⌘</kbd>+<kbd>Y</kbd> | annuler / rétablir |
| <kbd>Suppr</kbd> | retirer la sélection |
| <kbd>Ctrl/⌘</kbd>+<kbd>D</kbd> | dupliquer la culture |
| <kbd>[</kbd> <kbd>]</kbd> | sélectionner l'élément précédent / suivant (de l'étape en cours) |
| <kbd>Entrée</kbd> | ouvrir les détails de la sélection |
| <kbd>G</kbd> <kbd>C</kbd> <kbd>M</kbd> <kbd>T</kbd> | alignement sur la grille, calques associations, humidité, température |
| <kbd>+</kbd> <kbd>−</kbd> <kbd>0</kbd> | zoom avant / arrière / ajuster |
| <kbd>Échap</kbd> | effacer la sélection |

### Cultures
Toutes les cultures d'une saison dans une seule liste (*par planche*, *par culture* ou *par date*)
avec méthode, statut, nombre, notes et dates planifiées / réelles modifiables sur place – rien à
faire glisser. Cochez plusieurs cultures pour définir un statut ou une date pour toutes à la fois.
Sur téléphone, chaque culture est une carte avec la prochaine date à renseigner. Vues :

| Vue | Contenu |
|---|---|
| **Liste** | le tableau modifiable ; *Afficher sur le plan* ouvre le planificateur sur cette culture |
| **Chronologie** | l'année par planche sous forme de barres (élevage, croissance, récolte) avec une ligne d'aujourd'hui ; faites glisser une culture planifiée sur le côté pour déplacer son semis et sa plantation |
| **Plan de semis** | ce qu'il faut semer, planter et récolter semaine par semaine (*Fait* inscrit la date du jour) |
| **Semences** | les graines dont le plan a besoin par rapport à votre stock ; ce qui manque va sur une liste de tâches Home Assistant en un clic, sans doublons |
| **Succession** | les planches qui se libèrent cette saison et ce qui peut y suivre |
| **Prévision de récolte** | kg attendus par semaine |

### Plantes (bibliothèque)
Recherche (insensible aux accents, dans n'importe quelle langue), filtres par famille, *serre*,
*cultures rapides* ou *mes plantes*. La base intégrée compte 232 cultures (légumes, aromatiques,
fruits, fleurs, engrais verts), chacune avec image, calendrier de semis calculé pour **vos** dates de
gel, voisins et « où elle pousse dans votre jardin ». *Personnaliser* ne stocke que les champs que
vous avez modifiés comme surcharge (par langue pour les noms et les textes), de sorte que les
futures mises à jour des données intégrées vous parviennent toujours ; *Revenir aux données
d'origine* supprime la surcharge. *Nouvelle plante* crée une plante personnelle (identifiant dérivé
du nom anglais) ; une plante personnelle encore utilisée par un plan ou par un plan mis de côté ne
peut pas être supprimée. Avec *Paramètres → Affichage → photos* activé, le navigateur affiche aussi
une photo de Wikipédia (CC BY, CC BY‑SA, CC0, domaine public, avec crédit) ; les illustrations
fonctionnent hors ligne.

### Calendrier
Vues mois, semaine, liste, **chronologie** (un Gantt par planche avec barres de semis, de croissance
et de récolte, l'estimation de récolte en degrés-jours, les dates de gel et une ligne « Travaux au
jardin » avec les tâches saisonnières) et **Année**. Les tâches ouvertes en retard s'affichent sur
aujourd'hui pour que rien ne se perde dans le passé. Sur écran tactile, balayez une tâche vers la
droite pour la terminer ou vers la gauche pour la reporter d'un jour. La fenêtre de tâche montre le
contexte en direct (humidité et température du sol, bilan hydrique, nutriments, température de
l'air, humidité, risque de maladie et de gel, météo du jour et ET₀), les outils nécessaires pour le
travail et des liens vers le chapitre correspondant du manuel. Ouvrez une tâche pour la terminer, la
passer, la reporter (+1 jour / +3 jours / +1 semaine ou une date ; les tâches dépendantes suivent),
changer sa priorité, l'attribuer à une personne, ajouter des notes et des **photos** (envoyées via
l'`image_upload` de Home Assistant, stockées localement). Un titre ou une description que vous
réécrivez est conservé lors du recalcul des tâches. La vue **Année** montre chaque culture mois par
mois (semer à l'abri, semer, planter, en culture, récolter) avec le nombre de tâches et d'heures par
mois ; imprimez-la comme *Plan annuel*.

### Météo
La météo actuelle, un graphique sur 24 heures (température au-dessus de la pluie), les dix prochains
jours avec une barre d'amplitude de température et des étiquettes gel / chaleur, ce que cela signifie
pour le jardin (nuits de gel, journées chaudes, pluie qui permet d'attendre pour arroser, période
sèche, planches qui ont besoin d'eau) et un **radar des pluies** : une caméra radar de Home Assistant
s'il y en a une (p. ex. Buienradar), sinon la carte publique de Buienradar pour les Pays-Bas ou la
Belgique (chargée par votre navigateur, actualisée toutes les 5 minutes). Il faut une entité météo
sous *Paramètres → Météo et capteurs extérieurs*.

#### Historique du climat
Sous les prévisions, la section **Historique du climat** montre ce que la météo a vraiment fait
chez vous :

* **Températures et pluie par jour** – sur *30 jours*, *90 jours* ou *1 an* : une bande de la
  température la plus basse à la plus haute du jour, une ligne pour la moyenne et des barres pour
  la pluie. Survolez un jour pour le soleil, le vent et la source des données (*capteurs propres*,
  *historique de l'enregistreur* ou *Open-Meteo (observé)*).
* **Ces derniers temps, comparé à l'an dernier** – les *7 derniers jours*, les *30 derniers jours*
  et *Cette saison* (chacun à côté de la même période l'an dernier, dès qu'elle a été
  enregistrée) : moyenne, minimum, maximum,
  pluie et jours de pluie, nuits de gel, jours ≥ 25 °C (dont ≥ 30 °C), ensoleillement, vent le
  plus fort, degrés-jours, évaporation (ET₀) et le bilan pluie − évaporation.
* **Records** – le plus froid, le plus chaud, le jour le plus pluvieux et la rafale la plus forte.
* **Ce que Hortulus en fait** – un rappel de l'usage de ces données (degrés-jours, bilan hydrique,
  maladies, tâches, retards et gel ; voir ci-dessous).
* **Tous les capteurs de température** – chaque capteur associé (air extérieur, air serre / zone,
  air près de la planche, sol) avec *Maintenant*, *Aujourd'hui*, *Moy. 7 j*, *Min–max 30 j*,
  *Record bas*, *Record haut*, le nombre de jours et une petite courbe.
* **Mois par mois** – les mêmes chiffres par mois, avec l'écart par rapport à l'an dernier.
* **Dates de gel** – la dernière gelée de printemps et la première gelée d'automne **mesurées**
  chaque année, et leur moyenne comparée au préréglage régional (*n jours plus tôt / plus tard*).
  En cas de grand écart, indiquez vos propres dates de gel dans *Paramètres → Climat et région* :
  toutes les fenêtres de semis suivent.
* **En bref** (extra *season_summary*) – en tête : la saison et le mois dernier en quelques
  phrases, comparés à l'an dernier.
* **Utiliser mes dates de gel** (admin, extra *local_frost_suggest*) – dès que ≥ 2 années
  complètes placent une date de gel mesurée à ≥ 7 jours du préréglage ; le bouton passe la région
  en *personnalisé* avec les dates mesurées. Rien ne change tant que vous n'appuyez pas.
* **Importer les données d'une station météo** (admin, extra *station_import*) – l'export d'une station météo (Netatmo,
  Ecowitt, Davis, un tableur). L'en-tête et le séparateur (`;`, `,`, tabulation) sont détectés ;
  les colonnes d'heure (aussi en secondes unix), de température, d'humidité, de pluie (un cumul
  journalier → son maximum, une pluie par mesure → additionnée), de vent et de rafales sont
  reconnues en français, néerlandais et anglais ; °F, pouces, mph, m/s et nœuds sont convertis.
  Les jours déjà mesurés par Hortulus sont conservés ; les jours importés comptent comme
  *historique*.

**Comment l'historique se remplit.** À chaque mise à jour, Hortulus intègre à la journée les
capteurs extérieurs – ou, à défaut, l'entité météo : températures minimale, maximale et moyenne,
humidité, vent et rafales, pluie, rayonnement et heures d'ensoleillement (≥ 120 W/m², le seuil de
l'OMM). Chaque capteur de température associé reçoit son propre minimum, maximum et moyenne par
jour. Une fois par jour (et au démarrage), les jours qui n'ont pas été bien couverts sur les
30 derniers jours sont complétés :

1. depuis l'**enregistreur** (recorder) de Home Assistant – les mêmes capteurs, pendant que
   Hortulus ne tournait pas (redémarrage, mise à jour) ; il faut que le recorder conserve ces
   entités ;
2. avec l'option *Utiliser Open-Meteo* activée, depuis la **météo quotidienne observée**
   d'Open-Meteo pour l'emplacement du jardin (température, pluie, vent et rafales, rayonnement,
   ensoleillement, humidité, ET₀ FAO) – les coordonnées arrondies sont envoyées à
   api.open-meteo.com.

Les mesures propres priment toujours ; l'historique de l'enregistreur combine les extrêmes ; la
météo observée ne remplit que ce qui n'a pas été bien mesuré. Une prévision de pluie ne remplace
jamais un pluviomètre ou une pluie enregistrée du même jour.

**Conservation.** Les jours extérieurs restent dans le journal quotidien pendant **deux saisons**
(800 jours), les jours par capteur pendant **400 jours**. Ensuite, ils sont regroupés en
**chiffres mensuels conservés pour toujours** (moyenne, extrêmes, pluie, nuits de gel, jours
chauds, ensoleillement, vent), si bien que les comparaisons d'une année sur l'autre survivent.
Les **dates de gel mesurées** (minimum extérieur sous 0 °C) sont gardées par année ; une
demi-année ne compte comme complète qu'une fois terminée et enregistrée à au moins 80 %. Tout cela
vit dans le stockage du jardin (pas dans le fichier de plan) ; la commande websocket
`garden_manager/climate/stats` le met à disposition (voir [Entités](ENTITES.md)).

**Ce que le moteur en fait.** Les degrés-jours enregistrés déplacent les dates de récolte, et les
serres comptent les degrés-jours de leur propre capteur d'air (sinon la journée extérieure avec
l'effet tampon de la serre) ; chaleur, froid et jours sombres enregistrés retardent les cultures
(la fiche de la culture indique pourquoi). Le bilan hydrique utilise Penman-Monteith sur la journée
enregistrée (humidité, vent, ensoleillement ou rayonnement). Deux jours chauds et humides passés
(critères de Hutton) signifient un risque de mildiou élevé, plusieurs jours humides relèvent le
niveau. Le semis attend un sol durablement chaud (la plus basse entre la mesure actuelle et la
moyenne des derniers jours). Après une tempête (rafales ≥ 60 km/h), une averse ou une semaine
sèche, vous recevez une tâche de suivi ; s'il a gelé alors que des cultures frileuses étaient
dehors, une alerte vous le signale.

### Journal
Sections :

| Section | Contenu |
|---|---|
| **Carnet** | notes, observations, problèmes et étapes marquantes avec photos (par planche, par culture ou pour tout le jardin) |
| **Récolte** | le journal des récoltes en kg et en pièces (notez-en une en cochant une tâche de récolte ou depuis le planificateur), les totaux par culture, votre propre **rendement appris par m²** (utilisé par le remplissage auto, les conseils et la liste de courses), la récolte **au fil des années** (meilleure année en or) |
| **Cuisine** | les cultures prêtes à cueillir avec la façon de les conserver, un avertissement de surplus (plus de 1,5 fois ce que le ménage mange en une semaine) avec des idées pour stocker, conserver ou partager, et **coûts et récolte** : la récolte aux prix du magasin face à vos dépenses et à l'eau du jardin |
| **Boîte à graines** | les sachets de graines avec leurs années limites par famille, et les graines encore nécessaires pour le plan (la liste de courses ignore les graines que vous avez) |
| **Eau** | l'humidité du sol d'après l'historique de Home Assistant, l'eau apportée d'après le journal d'Hortulus et la pluie, par planche sur 7, 14 ou 30 jours ; la consommation d'eau du jardin d'après le compteur et le niveau du tonneau de pluie |
| **Bilan de saison** | cultures, récolte par rapport à l'attendu, échecs, problèmes du carnet, eau ; à télécharger en Markdown, ou en PDF *Livre de saison* |
| **Journal système** | chaque modification du jardin (depuis le panneau, les actions, les automatisations et ce qu'Hortulus ajuste lui-même) avec l'heure, l'auteur et l'objet. **Chaque entrée peut être annulée** (admin) ; un élément modifié à nouveau depuis n'est écrasé qu'après confirmation ; l'annulation est elle aussi enregistrée, et peut donc être rétablie |

Sélectionnez une planche dans le planificateur pour ajouter une **analyse de sol** (pH, matière
organique, P, K, Mg, calcaire) ; le plan de fertilisation, le conseil de chaulage et la liste de
courses suivent la plus récente.

### Cuisine
Un livre de cuisine de saison à partir de ce que le jardin donne en ce moment. Hortulus regarde les
cultures dans leur période de récolte (plus tout ce que vous ajoutez de la cave, comme des courges
stockées ou des haricots congelés) et leur propose des plats. La laitue, le concombre, le radis et
les cultures semblables ne vont que dans des salades et d'autres plats crus ; les baies de sureau,
les haricots, les pois chiches et les edamames ne sont jamais proposés crus ou à moitié cuits. Les
recettes sont écrites en anglais, en néerlandais et en français, avec les quantités par personne et
ce qui vient du jardin, ce qu'il y a à la maison et ce qu'il faut acheter. Trois parties : **Idées du
jardin**, **Mon livre de cuisine** et **Liste de courses**.

* **Choix** (mémorisés avec *Retenir ces choix*, stockés dans le jardin) : nombre de personnes (1–12),
  un accompagnement (ce qui convient au plat, aucun, ou pâtes, riz, boulgour, couscous, couscous
  perlé, gnocchis, pommes de terre, frites, pain, nouilles), une protéine de viande, de poisson ou
  végétarienne (poulet, bœuf, porc, haché, saucisse, lard, jambon, saumon, poisson blanc, crevettes,
  tofu, pois chiches, lentilles, œuf, halloumi, fromage de chèvre … ou aucune pour des plats
  végétariens), **À utiliser du frigo** et **Toujours à la maison**.
* Les produits du **frigo** (beurre, crème, lait, œufs, parmesan, feta, mozzarella, yaourt, moutarde,
  oignon, chapelure …) sont intégrés aux plats là où ils conviennent : chaque produit a sa propre
  préparation selon le genre de plat (yaourt en tzatziki, raïta ou sauce miel-moutarde ; feta cuite
  au four ou fouettée ; parmesan en chips ou en croûte …). Un plat prend au plus trois produits du
  frigo, une sauce, une vinaigrette et une garniture croquante. Ils comptent comme « à la maison ».
  Ce qui figure sous *Toujours à la maison* n'apparaît jamais sur la liste de courses.
* **Plats** : soupe, plat au four, sauté, pâtes, risotto, salade, gratin, ragoût ou curry, frittata,
  stoemp, légumes farcis, assiette avec viande et frites, pesto, crumble aux fruits, soupe froide,
  crostini, compote et les plats supplémentaires (ratatouille, tian, shakshuka, tarte, gnudi,
  waterzooi, galettes de légumes, clafoutis, panna cotta …). Les plats conçus pour certaines plantes
  n'utilisent que celles-ci. Chaque plat reçoit une image (les cultures dans une assiette, avec
  l'accompagnement dessous et la viande au milieu).
* **Chapitres** : Soupes · Entrées · Plats · Desserts · **Conserves** (pickles express, chutney,
  passata, cubes de pesto, confiture, congélation, choucroute ; les quantités sont celles d'une
  fournée). Les idées, le livre de cuisine et le PDF du livre sont découpés par chapitre.
* **Menus** : une soupe ou une entrée, un plat et un dessert qui vont ensemble, construits à partir
  de ce qui est prêt à cueillir (menus à thème de la saison, et menus autour d'un plat). Un clic met
  les trois sur la liste de courses ou dans le livre de cuisine.
* **Modifier une recette** : ajoutez, supprimez ou changez des ingrédients (nom, quantité, unité,
  jardin / à la maison / à acheter ; jusqu'à 40) et ajoutez, supprimez, réécrivez ou réordonnez les
  étapes (jusqu'à 30). Votre version va dans votre livre de cuisine, la liste de courses et les PDF
  la suivent, et *Revenir à l'original* rétablit la recette générée.
* **Livre de cuisine** : gardez des recettes (jusqu'à 500), marquez des favoris, ajoutez des notes,
  notez quand vous les avez cuisinées ; filtrez par chapitre et par favoris ; cherchez par recette ou
  par ingrédient.
* **Liste de courses** : mettez-y des plats depuis leur recette ; elle sépare ce qu'il faut acheter de
  ce que donne le jardin. Imprimez-la, enregistrez-la en PDF (liste, ou liste + recettes avec les
  images des plats), envoyez-la sur un téléphone (un service `notify.*`, par défaut : les réglages de
  notification du jardin) ou mettez-la sur une liste de tâches Home Assistant (les éléments déjà
  présents sont ignorés ; vos propres droits sur cette liste s'appliquent).
* **PDF** : une recette, tout le livre de cuisine (une page de chapitre chacun, les longues recettes
  continuent sur une autre page) ou la liste ; jusqu'à 200 recettes par PDF, export par mail ou vers
  une liste de tâches.

### Conseils
Un constructeur de phrase **Demandez à Hortulus** (*J'ai une question/un problème à propos de [sujet]
[lequel] : [question]*) avec l'état en direct, les causes probables, que faire maintenant, **remèdes
écologiques et maison**, prévention et outils. Des suggestions pour le jardin (partenaires de
pollinisation, fleurs pour pollinisateurs, mauvais voisins, ombrage, trous dans la récolte, planches
vides, écologie, strates de forêt-jardin) à appliquer en un clic ; la couverture de la récolte par
mois ; une liste de courses de la saison ; des outils par travail.

### Manuel
23 chapitres (EN / NL / FR) avec recherche et glossaire : planification, sol et compost, semis,
arrosage (ET₀, Kc, bilan hydrique), fertilisation (NPK, CE), rotation, associations de plantes, la
serre, ravageurs, maladies, l'année au jardin et le repos hivernal, récolte et conservation,
récolte de graines, culture sans labour et paillage, aromatiques, vivaces, fruits, outils et
matériaux, remèdes maison, récolte toute l'année, choisir ses capteurs, permaculture et
forêts-jardins. Les boutons ⓘ dans tout le panneau ouvrent l'entrée du glossaire pour un terme et
renvoient vers le chapitre.

### Analyse
| Section | Contenu |
|---|---|
| **Contrôle** | explique les incohérences (une année avec des cultures mais sans plan, des cultures dont la planche n'est pas sur le plan de leur saison, des planches hors de leur zone, des cultures qui se chevauchent ou trop tardives, un passage à la nouvelle année oublié …) avec un lien vers le bon endroit et des **corrections en un clic** (enregistrées et annulables). L'onglet affiche une pastille avec le nombre de problèmes ; *Exporter le diagnostic* écrit un fichier JSON à joindre à un rapport de bug |
| **Pourquoi pas ?** | par planche, pourquoi une plante convient ou non |
| **Comparer** | zones, planches, éléments et cultures ajoutés, retirés ou modifiés entre deux plans |
| **Erreurs** | chaque action refusée avec sa raison |
| **Journal système** | le journal du Journal |

### Imprimer
Choisissez un document – **plan du jardin**, **serre / zone**, **fiches de planches**, **liste de
contrôle**, **tableau de saison**, **plan annuel**, **feuille de planification** (contours + grille de
points pour esquisser), **fiches de plantes** ou le **livre de saison** – puis le papier (A4, A3, A5,
Letter, **reMarkable Paper Pro**), l'orientation et les couleurs (*Couleur*, *E-ink (clair + motifs)*
avec des teintes claires et un motif hachuré par famille, *Niveaux de gris*). L'aperçu montre
chaque page ; **Télécharger le PDF** le récupère via l'API authentifiée de Home Assistant,
**Enregistrer dans /config/hortulus/exports** l'écrit dans `/config/hortulus/exports/` (privé ; un
lien de téléchargement signé valable 7 jours). Les plans contiennent une légende (familles, zones,
éléments, symboles, cultures numérotées quand les noms ne tiennent pas), une échelle graphique avec
rapport et une rose des vents ; les fiches de planches ajoutent une grille de 10 cm, le compost et
l'engrais pour les cultures à venir et l'historique de rotation. Le **livre de saison** (A5 par
défaut) est toute l'année au jardin à imprimer : couverture, le plan de la saison, une introduction
rédigée d'après les chiffres de la saison, un chapitre par mois (semé, planté, fait, votre journal
avec photos, récolte, eau, météo), l'année en chiffres, un glossaire et une quatrième de couverture ;
le nombre de pages est un multiple de quatre. Les documents imprimés utilisent le plan de la saison
choisie.

Pour mettre un PDF sur le reMarkable : téléchargez-le et faites-le glisser dans l'application
reMarkable pour ordinateur ou mobile, ou envoyez-le avec *Send to reMarkable* par e-mail. Le format
de page correspond exactement à l'écran du Paper Pro, rien n'est donc mis à l'échelle.

### Paramètres
Sections, de haut en bas (les administrateurs peuvent modifier ; les champs d'entité sont des listes
déroulantes qui n'affichent que les entités adaptées) :

| Section | Contenu |
|---|---|
| **Climat et région** | hémisphère, profil (préréglage / USDA / personnalisé), dates de gel |
| **Météo et capteurs extérieurs** | entité météo, température extérieure, capteur de pluie, humidité extérieure, humectation des feuilles, **station météo** (vitesse du vent, rafales, rayonnement solaire en W/m², lumière extérieure en lux), option **Open‑Meteo** (humidité, vent et ensoleillement pour l'évaporation, et météo observée pour compléter l'[historique du climat](#historique-du-climat)), altitude |
| **Zones et microclimats** | par zone : température de l'air, humidité, lumière, humectation des feuilles, **PAR** ; pour les serres et les châssis aussi les entités d'**ouvrant** et d'**écran d'ombrage** avec commande *désactivé / conseiller / automatique*, *masse thermique* ; *contre un mur chaud*, *chauffée* (+ température minimale) |
| **Planches et capteurs** | par planche : humidité du sol, température du sol, sondes **CE, N, P, K**, vanne, bouton **Tester**, débit (L/min ; le débit mesuré s'affiche quand le compteur d'eau l'a appris), **minuterie de la vanne** |
| **Matériel d'irrigation** | mode (*désactivé / conseiller / automatique*), pompe, heure de début, durée max., blocage en cas de gel, arrêt en cas de pluie, arrêt de la pompe avant la vanne ; capteur de **surplus solaire** (W ou kW), *démarrer à partir de* (W, 500 par défaut) et *attendre au plus tard jusqu'à* (11:00 par défaut) ; charge de la **batterie domestique** (%) et *ou démarrer à* (%, 95 par défaut) ; **l'eau de pluie d'abord** : pompe du récupérateur, *passer à l'eau du réseau sous* (%), *eau du réseau quand le récupérateur est vide*, puissance des deux pompes (W) |
| **Ressources (remplissage auto)** | taille du ménage, heures, eau et compost pour le remplissage auto, objectifs ; interrupteurs pour les *travaux saisonniers dans le calendrier* et les **Conseils écologiques** (solutions bio contre ravageurs et maladies, calendrier écologique, conseils forêt-jardin) |
| **Extras** | aides facultatives, toutes activées par défaut – voir [Extras](#extras) |
| **Notifications** | notifications persistantes, services push, synthèse vocale, haut-parleurs, heure du récapitulatif, alertes de gel / de chaleur, annonce vocale du gel ; **Rappels** (rappel du soir des tâches en retard, 18 h 30 après 1 jour par défaut ; **Aperçu de la semaine**, dimanche 19 h par défaut) ; *Planification selon la météo* (déplace les travaux sensibles à la météo hors des jours de pluie, de gel ou de chaleur) |
| **Compteur d'eau et tonneau de pluie** | le capteur du compteur (m³ ou L), le niveau du tonneau en % et la capacité totale des tonneaux ; alertes de fuite |
| **Coûts** | devise, prix de l'eau par m³, prix propres par culture (€/kg) pour l'aperçu récolte contre coûts |
| **Ménage et voix** | qui reçoit les nouvelles tâches (par défaut et par type de tâche), un service notify par personne, installation des phrases Assist |
| **Général** | langue (suivre Home Assistant / English / Nederlands / Français), unités (métrique), taille de la grille, rayon d'association, **importation et exportation** (JSON / YAML, tâches comprises) |
| **Affichage (ce navigateur)** | par navigateur : photos de plantes de Wikipédia ; thème de couleurs (*Vert classique*, *Terre*, *Nuit*, *Saison*) et clair / sombre / automatique. Dans Home Assistant, le thème et le choix clair / sombre suivent votre utilisateur sur tous les appareils |

#### Matériel d'irrigation en 5 étapes
1. Paramètres → Planches et capteurs : choisissez la vanne (`switch.*`, `valve.*` ou `input_boolean.*`)
   et le débit en L/min pour chaque planche (mesurez-le : chronométrez un seau de 10 L, ou laissez le
   compteur d'eau l'apprendre). Appuyez sur **Tester (5 s)** pour ouvrir la vanne 5 s (la pompe seulement
   quand la vanne indique qu'elle est ouverte) et vérifier qu'elle indique bien ouverte puis refermée.
   Si la vanne a sa propre minuterie, indiquez-la sous *Minuterie de la vanne (min)* : les arrosages plus
   longs sont découpés en ouvertures qui restent en dessous.
2. Paramètres → Matériel d'irrigation : pompe facultative (interrupteur ou vanne) et *Arrêt de la pompe
   avant la vanne (s)* (secondes pendant lesquelles la pompe est arrêtée avant la fermeture de la vanne).
3. Choisissez l'heure de début et les limites (durée max., blocage en cas de gel, arrêt en cas de pluie).
4. Essayez `garden_manager.run_irrigation_plan` avec `dry_run: true` et vérifiez le plan.
5. Activez **Arrosage automatique**. Avec *Conseiller*, vous ne recevez que des tâches d'arrosage.

Un arrosage se termine quand une vanne reste fermée, ou ne répond plus pendant une minute alors que la
pompe tourne (la pompe est alors arrêtée en premier) ; une vanne ou une pompe ouverte bien plus
longtemps que n'importe quel arrosage (durée max. + 10 minutes) déclenche un bandeau avec *Fermer la
vanne* ; avec la notification de fuite activée dans les Paramètres et un compteur d'eau défini, au moins 5 L comptés en
15 minutes calmes (aucun arrosage en cours, toutes les vannes fermées) sont signalés comme une fuite.

#### Extras
Aides facultatives (2.0), chacune un interrupteur sous *Paramètres → Extras* et un réglage de
premier niveau du fichier du jardin. Toutes sont activées par défaut ; en désactiver une la masque
ou la saute, simplement.

| Réglage | Effet |
|---|---|
| `slogans` | dictons de jardin variés (FR/NL/EN, par thème et par saison, lignes propres à l'hémisphère sud), choisis par jour et par endroit : récapitulatif, plan de la semaine, message météo mensuel, rapport de saison, 4e de couverture du livre de saison, accroche du tableau de bord et carte |
| `soil_estimate` | les planches sans sonde de température du sol reçoivent une température estimée à partir de la moyenne journalière de l'air enregistrée (lissée sur les 10 derniers jours, au moins 3 jours enregistrés) ; utilisée pour les conseils de semis, affichée sur la fiche de la planche comme *≈ x °C* |
| `water_forecast` | par planche : quand le bilan hydrique dépassera la réserve facilement utilisable (p × TAW) avec l'ET₀ et la pluie prévues sur 7 jours – *de nouveau sèche dans N jours* |
| `sensor_health` | un capteur associé indisponible ou inconnu depuis ≥ 2 jours donne un seul avertissement (`alert.sensor_silent`, à la place de l'alerte de mesure périmée) |
| `season_summary` | la saison et le mois dernier en phrases, comparés aux mêmes dates l'an dernier (plus chaud / plus froid, plus humide / plus sec, plus ou moins ensoleillé, nuits de gel) : en tête de l'historique du climat, dans le rapport et le livre de saison, et en notification avec le récapitulatif le 1er de chaque mois |
| `local_frost_suggest` | après ≥ 2 années complètes mesurées où la dernière gelée de printemps ou la première d'automne s'écarte de ≥ 7 jours du préréglage : une alerte d'information et un bouton **Utiliser mes dates de gel** dans l'historique du climat |
| `station_import` | importer l'export CSV d'une station météo dans l'historique du climat (voir ce chapitre) |
| `solar_irrigation` | l'arrosage automatique attend le surplus solaire (capteur et limites sous *Matériel d'irrigation*) : il démarre dès que le surplus atteint le minimum, au plus tard à l'heure limite ; sans capteur ou sans valeur exploitable, pas d'attente. Le tableau de bord affiche *Attend un surplus solaire* |
| `climate_card` | une ligne climat sur la `hortulus-tasks-card` : moyenne sur 7 jours et écart avec l'an dernier, pluie, soleil, bande de température sur 14 jours (options de carte `climate: false`, `slogan: false`, voir [Entités](ENTITES.md#carte-lovelace)) |
| `frost_heating` (2.1) | un chauffage par serre ou châssis (*Zones* : entité de chauffage – interrupteur ou climate –, chauffer sous °C, puissance, budget hebdomadaire en kWh) : avec la régulation en *automatique*, il s'allume sous la température du capteur d'air de la zone et s'éteint 1,5 °C au‑dessus ; budget de la semaine épuisé, il reste éteint jusqu'au lundi. Énergie : `sensor.hortulus_greenhouse_heating_this_week` |
| `adaptive_irrigation` (2.1) | ~90 minutes après un arrosage, le capteur d'humidité de la planche montre combien d'eau a pénétré ; après deux arrosages, la planche reçoit son propre facteur (0,5–2×) sur l'eau prévue, et le bilan hydrique compte ce qui a pénétré. Affiché par planche sous *Planches*, avec *Oublier*. Les arrosages suivis de pluie ne comptent pas |
| `own_yields` (2.1) | vos kg/m² récoltés pèsent face à la valeur de référence (qui compte pour une saison), et la prévision de récolte commence quand vos premières récoltes sont vraiment venues (jours après le semis ou la plantation, au plus un mois d'écart) |
| `ai_diagnosis` (2.1) | *Qu'est‑ce qui ne va pas ?* sous les photos du journal : la photo part vers la tâche IA de Home Assistant (votre choix ou la tâche préférée, `ai_task_entity`), qui choisit parmi les ravageurs et maladies connus de Hortulus ; la réponse vient avec le conseil bio et peut être notée comme problème |
| `calendar_mirror` (2.1) | copie les tâches ouvertes des `mirror_days` prochains jours (7 par défaut) dans `mirror_calendar` (Google, CalDAV, local …), chaque tâche une fois par échéance ; les modifications ultérieures ne suivent pas (Home Assistant peut ajouter des événements à d'autres agendas, pas les modifier) |

---

## 5. Format d'importation et d'exportation

Exportez depuis le Plan du jardin / le Planificateur (menu ⋮), Paramètres → Général, ou
`garden_manager.export_plan`. Importez (admin) depuis le même menu ⋮ ou avec `garden_manager.import_plan`.

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

Modes d'importation : **merge** (*Fusionner*, ajout ou mise à jour par identifiant, rien n'est
supprimé ; la saison active reste) ou **replace** (*Remplacer*, l'aménagement, les plans par saison et
les cultures sont remplacés). Ce qui voyage : zones, planches (avec leurs analyses de sol ; un fichier
sans elles conserve celles déjà stockées), éléments du jardin, les plans par saison, les plans mis de
côté, les cultures, les plantes personnelles, les **surcharges de plantes** et l'historique de
rotation, plus les tâches si elles sont incluses. Un fichier plus ancien sans `features` ni
`archived_plans` laisse tranquilles ceux déjà stockés. Les fichiers de versions plus anciennes sont
migrés automatiquement (version de stockage 1.8) ; les champs inconnus sont ignorés. Les références
sont validées par rapport au plan auquel elles appartiennent (une planche doit pointer vers une zone
de son propre plan, une culture vers une planche existante, y compris dans les plans mis de côté) ;
un champ du mauvais type (par exemple un `plant_overrides` qui n'est pas un dictionnaire) fait refuser
tout le fichier, et un fichier refusé ne change rien. Les saisons passées dans le fichier d'archive
ne font **pas** partie d'un export.

Les recettes, la liste de courses, les dépenses, le carnet, le journal des récoltes et
l'historique du climat ne font pas partie du fichier de plan ; ils vivent dans le stockage du jardin.

---

## 6. Unités, langue, heure

* Les unités sont métriques en interne (cm, °C, mm, L). Les capteurs et prévisions en unités
  impériales sont convertis à la lecture.
* Le panneau, les titres de tâches générés, les notifications, les événements du calendrier, le
  manuel, les noms de plantes, les recettes et les phrases Assist sont disponibles en **anglais,
  néerlandais et français**. Les textes générés suivent la langue de Home Assistant sauf si vous la
  remplacez sous *Réglages avancés* / *Général* (auto / en / nl / fr) ; le panneau suit la langue de
  votre utilisateur. Les dates se lisent jour-mois-année dans la langue du panneau, avec des formats
  belges pour le néerlandais et le français (nl‑BE, fr‑BE).
* Toutes les dates sont locales (fuseau horaire de Home Assistant). Les heures de prévision sont
  traitées comme des instants absolus : les changements d'heure (nuits de 23 ou 25 heures) ne
  faussent donc jamais la durée du gel.

## 7. Performances

* Pas d'interrogation des capteurs – des écouteurs de changement d'état sur exactement les entités
  associées, avec 10 s d'anti-rebond ; la prévision est la seule récupération planifiée (30 min).
  Le complément de l'historique du climat (enregistreur et, si activé, Open-Meteo) tourne au plus
  une fois par jour, et une erreur à ce moment-là n'empêche jamais la mise à jour du jardin.
* L'historique du climat reste petit : au plus deux saisons de jours extérieurs et 400 jours par
  capteur, puis une ligne par mois.
* Tous les calculs sont du Python pur sur des données en mémoire (quelques millisecondes pour un
  jardin typique) ; les écritures de stockage sont différées (5 s, journal système 10 s) et ne
  bloquent jamais la boucle d'événements.
* Les saisons plus anciennes que les trois dernières passent dans le fichier d'archive, ce qui garde
  petits le fichier du jardin et chaque analyse après des années d'utilisation (section 8).
* Le panneau est un seul bundle JavaScript (environ 250 ko compressés) mis en cache avec un hash de
  contenu ; la carte Lovelace est un fichier séparé d'environ 10 ko. Le panneau reçoit un instantané
  complet via un seul abonnement websocket, actualisé après chaque mise à jour.

---

## 8. Saisons, passage à la nouvelle année et archive

* **Un plan par saison.** Le plan du jardin (zones, planches, éléments) est enregistré par saison ; le
  plan de la saison *active* (`layout_season`) est le jardin vivant avec lequel travaillent les
  entités, les tâches et l'irrigation. Les autres saisons (celle de l'an dernier, le brouillon de
  l'an prochain) sont stockées à côté. Dans l'hémisphère sud, une saison va de juillet à juin.
* **Rien ne passe tout seul à une nouvelle année** – ni le plan, ni les vivaces. Une fois la nouvelle
  année commencée, une carte des Conseils et le bouton de la barre d'outils du Plan du jardin et du
  Planificateur proposent le **Passage à la nouvelle année** (le bouton est disponible plus tôt aussi).
  Choisissez s'il faut copier le plan (et quelles zones et quels éléments suivent) ou garder un plan
  déjà conçu pour l'an prochain ; quelles vivaces et quelles cultures qui hivernent (ail, poireaux
  d'hiver …) passent ; et si la nouvelle année devient tout de suite le jardin actif. Le plan de
  l'ancienne année reste une saison à part ; tout figure dans le journal système et peut être annulé.
  Une vivace appartient à sa propre saison et aux saisons dans lesquelles elle a été reportée
  (`last_season`) ; « disparue à partir de cette saison » conserve l'historique.
* **Recommencer** avec *Plan du jardin → Plans* : le plan actuel est mis de côté (inactif, avec ses
  planches et ses cultures) et peut être réactivé ou supprimé.
* **Archive.** Les saisons plus anciennes que la saison en cours et les deux précédentes (trois
  saisons sont conservées) passent dans `.storage/garden_manager.garden.archive` : leurs cultures et
  leur plan de jardin. Les cultures encore en place (une vivace reportée dans la saison en cours)
  restent. Cela se produit au démarrage et une fois par saison, en deux temps : d'abord les saisons
  sont copiées dans le fichier d'archive ; une saison ne quitte le fichier du jardin qu'après que
  l'archive qui la contient a été relue sur le disque lors d'un démarrage ultérieur, et seulement si
  elle n'a pas changé depuis. La rotation des cultures continue de fonctionner (chaque culture
  archivée laisse un enregistrement de rotation), et le bilan de saison et le livre de saison
  ouvrent toujours les saisons archivées, y compris les cultures reportées dedans.

## 9. Plusieurs jardins

Ajoutez à nouveau l'intégration (Paramètres → Appareils et services → Ajouter une intégration →
Hortulus) pour un jardin ouvrier ou une seconde parcelle. Chaque jardin est sa propre config entry
avec ses propres données, fichiers de stockage, appareils et entités ; le premier jardin garde ses
données et ses identifiants d'entités exactement comme avant, les jardins suivants s'appellent
« Hortulus 2 », « Hortulus 3 » … (renommez librement).

* Le panneau affiche un **sélecteur de jardin** dans la barre du haut et mémorise votre choix par navigateur.
* Chaque service accepte `garden:` (le titre ou l'identifiant de l'entrée) ; sans lui, le premier jardin est utilisé.
* La carte des tâches accepte `garden:` ; le point d'accès PDF accepte `garden_id`.
* Les commandes websocket acceptent `garden_id` (l'identifiant de l'entrée).
* Assist répond au sujet du premier jardin.

## 10. Hortulus Web (site web facultatif)

Hortulus Web est une version site web d'Hortulus qui exécute le même moteur Python dans le navigateur
(Pyodide). Il est livré séparément et ne fait pas partie de cette intégration ; rien dans Home
Assistant n'en dépend. Ce que le dépôt lui-même en montre :

* Le panneau accepte des réglages supplémentaires d'une page hôte : une liste d'onglets autorisés
  (`tabs`), un indicateur `viewer` (lecture seule) et un indicateur `web`. Home Assistant n'en
  transmet aucun.
* Un onglet **Jardin** (un aperçu en lecture seule du plan : cliquez sur une zone, une planche, une
  culture ou un élément pour ses détails, choisissez l'année) et une liste d'onglets restreinte
  permettent au site web de montrer un jardin partagé aux visiteurs, seulement les parties choisies
  par son propriétaire. Une vue partagée dont la liste d'onglets n'autorise rien ne montre aucune
  partie du jardin.
* Les recettes de cuisine peuvent être marquées **Partagé** (visibles par quiconque peut voir le
  jardin) et envoyées par e-mail plutôt que vers un téléphone.
* Le site web exécute les gestionnaires websocket, les opérations et le stockage de l'intégration sur
  ses propres équivalents des modules de Home Assistant, de sorte que les fichiers de plan décrits à la
  [section 5](#5-format-dimportation-et-dexportation) peuvent être échangés entre les deux.
* **Historique du climat sur le site web.** Le site web tient le même historique du climat pour
  chaque jardin, sans enregistreur local : il le remplit avec la météo observée d'**Open-Meteo**
  pour l'emplacement du jardin et, quand le jardin est relié à un Home Assistant, avec
  l'**enregistreur** de ce Home Assistant via le jeton du jardin. Les mêmes règles s'appliquent
  (mesures propres d'abord, conservation de deux saisons / 400 jours, puis chiffres mensuels).
