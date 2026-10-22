# Gießen

Zu wenig Wasser bremst das Wachstum und lässt Früchte platzen oder bitter werden; zu viel erstickt die Wurzeln und fördert Krankheiten. So rechnet Hortulus es aus.

## Verdunstung: ET0 und Kc

Die **Referenzverdunstung (ET0)** gibt an, wie viel Wasser ein kurzer, gut bewässerter Rasen pro Tag verdunstet. Hortulus berechnet ET0 mit der **FAO-56-Penman-Monteith**-Gleichung aus Temperatur, Luftfeuchtigkeit, Wind und Bewölkung der Vorhersage. Fehlen diese Werte, weicht es auf die einfachere **Hargreaves**-Gleichung aus (nur Temperatur).

Eine Kultur verbraucht ET0 × **Kc** (Kulturkoeffizient). Kc ändert sich mit dem Wachstumsstadium:

| Stadium | Anteil der Saison | Kc (Beispiel Tomate) |
|---|---|---|
| Anfang | 15 % | 0,6 |
| Entwicklung | 25 % | steigend auf 1,15 |
| Hauptwachstum | 40 % | 1,15 |
| Spätphase | 20 % | fallend auf 0,8 |

Im Gewächshaus ist die Verdunstung etwa 30 % geringer (weniger Wind und Strahlung), Regen zählt dort aber nicht.

## Wasserbilanz pro Beet

Ohne Feuchtesensor führt Hortulus für jedes Beet einen **Eimer**: Der Wurzelraum hält eine bestimmte Wassermenge (abhängig von Boden und Wurzeltiefe). Jeden Tag wird die Verdunstung der Kultur abgezogen, 80 % des Regens und die gesamte Bewässerung kommen hinzu. Ist die Hälfte des verfügbaren Wassers verbraucht, ist es Zeit zu gießen - zurück bis zur Feldkapazität.

Mit einem **Bodenfeuchtesensor** verwendet Hortulus den Messwert und einen Zielbereich je Bodenart.

## Praktische Regeln

- **Selten und durchdringend** gießen (10-20 Liter pro m²) statt täglich ein wenig: Das fördert tiefe Wurzeln.
- **Morgens** am Fuß der Pflanze gießen, nicht über die Blätter (weniger Pilzkrankheiten).
- **Mulch** halbiert die Verdunstung aus dem Boden.
- Kritische Momente: Keimung, Auspflanzen, Blüte und Fruchtansatz (Tomate, Bohnen), Knollenbildung (Kartoffel).
- Regenwasser ist für säureliebende Pflanzen besser als Leitungswasser - und kostenlos.

## Automatische Bewässerung

Mit Ventilen (Schalter- oder Ventil-Entitäten) kann Hortulus selbst gießen. Sicherheitsregeln:

- **Frostsperre**: Ventile im Freien bleiben geschlossen, wenn innerhalb von 12 Stunden Frost vorhergesagt ist oder es jetzt zu kalt ist - eingefrorene Tropfleitungen platzen.
- **Regenpause**, wenn in den nächsten 24 Stunden mehr als die eingestellte Regenmenge vorhergesagt ist.
- **Maximale Laufzeit** pro Ventil.
- **Pumpenverriegelung**: Die Pumpe läuft nur, solange ein Ventil offen ist, und stoppt zuerst.
