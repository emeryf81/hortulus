# Sensoren auswählen und kaufen

Hortulus funktioniert ohne einen einzigen Sensor: Es verlässt sich dann auf die Vorhersage und eine Wasserbilanz. Einige gut gewählte Sensoren machen die Empfehlungen aber deutlich genauer - vor allem Bodenfeuchte und die Gewächshaustemperatur. Dieses Kapitel hilft beim Auswählen, Kaufen und Verbinden.

## Was lohnt sich am meisten?

| Priorität | Sensor | Warum | In Hortulus verbinden |
|---|---|---|---|
| 1 | **Lufttemperatur im Gewächshaus** (am besten mit Luftfeuchtigkeit) | Lüften, Schattieren, Frost, Krankheitsrisiko | Zone › Sensoren › Lufttemperatur / Luftfeuchtigkeit |
| 2 | **Bodenfeuchte pro Beet** | nach Messung statt nach Gefühl gießen | Beet › Sensoren › Bodenfeuchte |
| 3 | **Bodentemperatur** | Aussaatzeitpunkt, Wachstum (Gradtage) | Beet › Sensoren › Bodentemperatur |
| 4 | **Regenmesser** oder Wetterstation | wirklich gemessener Regen, Wasser sparen | Einstellungen › Regen |
| 5 | **Außentemperatur** auf Pflanzenhöhe (etwa 50 cm) | genauere Frostwarnungen | Einstellungen › Außentemperatur |
| Extra | Blattnässe, Licht (Lux/PAR), EC / NPK | Pilzrisiko, Lichtsumme, Düngung | Zone / Beet › erweitert |
| Aktor | Ventil, Pumpe, Fensteröffner, Schattierung | automatisches Gießen und Lüften | Beet › Bewässerung, Zone › Lüftung / Schattierung |

## Die Typen und ihre Vor- und Nachteile

### Zigbee (über Zigbee2MQTT oder ZHA)
Günstig, Batterien halten 1-2 Jahre, zuverlässiges Mesh-Netz. Sie brauchen einen Zigbee-Stick (z. B. SONOFF ZBDongle, Home Assistant Connect ZBT-1). **Tipp:** Ein Gerät mit Netzstrom (smarte Steckdose) im Schuppen oder Gewächshaus dient als Repeater und vergrößert die Reichweite.
- Bodenfeuchtesensoren der Familie „Tuya Zigbee soil moisture“ messen Feuchte und Temperatur; wählen Sie einen **kapazitiven** Typ (keine korrodierenden Stifte).
- Temperatur-/Feuchtesensoren (Aqara, SONOFF SNZB-02, Tuya) - für das Gewächshaus einen mit Display oder externem Fühler wählen und **im Schatten** anbringen (sonst messen Sie Sonnenschein, nicht Luft).

### Ecowitt (433/868 MHz mit Gateway)
Bei Gärtnern sehr beliebt: der Bodenfeuchtesensor **WH51** (AA-Batterie, etwa ein Jahr, große Reichweite), ein Bodentemperaturfühler (WN34), Blattnässe (WN35), Regenmesser und komplette Wetterstationen. Das Gateway GW1100/GW2000 verbindet sich lokal über die **Ecowitt-Integration** von Home Assistant. Große Reichweite bis ans andere Ende des Gartens.

### Bluetooth (BLE)
Der bekannte Pflanzensensor **Mi Flora / Flower Care** misst Feuchte, Temperatur, Licht und Leitfähigkeit. Günstig, aber mit kurzer Reichweite: Sie brauchen einen **ESPHome-Bluetooth-Proxy** (ein ESP32 für wenige Euro) in der Nähe.

### WLAN und ESPHome (selbst bauen)
Ein ESP32 mit kapazitiven Bodenfeuchtesensoren (v1.2), einem DS18B20-Bodenthermometer oder einem BME280/SHT31 für die Luft. Günstig und flexibel, aber WLAN im Garten braucht Strom (Netz oder ein kleines Solarmodul + Deep Sleep). Beispiele finden Sie auf der ESPHome-Website. Bodenfeuchte immer kalibrieren: in trockenem und in klatschnassem Boden messen und diese Werte als 0 % und 100 % verwenden.

### Ventile, Pumpen und Fensteröffner
- **Ventile:** Zigbee- oder WLAN-Bewässerungscomputer (Tuya/Sonoff/LinkTap), das Gardena smart system (eigene Integration) oder ein 12/24-V-Magnetventil an einem Relais (Shelly, ESPHome).
- **Pumpe:** eine smarte Steckdose oder ein Relais (Shelly) - richten Sie in Hortulus die Pumpenverriegelung ein (die Pumpe läuft nur, solange ein Ventil offen ist).
- **Gewächshaus:** Fensteröffner mit Wachszylinder brauchen keinen Strom; zur Steuerung aus Home Assistant einen Linearantrieb an einem Relais oder einen smarten Ventilator verwenden.

## Tipps, um gute Sensoren zu finden

1. **Zuerst prüfen, ob Home Assistant ihn unterstützt:** die Liste der Integrationen auf der Home-Assistant-Website, die Gerätedatenbank von Zigbee2MQTT („supported devices“) und die ESPHome-Geräteliste. Was dort steht, funktioniert meist sofort.
2. **Suchbegriffe:** „Zigbee Bodenfeuchtesensor“, „kapazitiver Bodenfeuchtesensor“, „Ecowitt WH51“, „Zigbee Temperatur Feuchtigkeit Sensor außen“, „Zigbee Wasserventil“, „LinkTap“.
3. **Wasserdicht:** auf die IP-Schutzart achten - draußen IP65 oder besser, IP67 für Fühler im Boden. Die Elektronik vor direkter Sonne schützen.
4. **Batterie:** AA oder AAA lässt sich leichter ersetzen als Knopfzellen; Lithiumzellen halten bei Frost länger.
5. **Reichweite:** vor dem Kauf testen, ob Zigbee/WLAN bis ans Ende des Gartens reicht; 433/868 MHz (Ecowitt) und LoRa reichen viel weiter.
6. **Lokal:** Geräte bevorzugen, die lokal arbeiten (Zigbee, Ecowitt, ESPHome) - keine Cloud, kein Abo, sie funktionieren weiter, auch wenn der Hersteller aufhört.
7. **Wo kaufen:** spezialisierte Smart-Home-Webshops, die großen Online-Marktplätze (günstiger, aber langsamere Lieferung), Baumärkte und Gartencenter (meist Gardena). Lesen Sie Erfahrungsberichte im Home-Assistant-Forum und auf Reddit (r/homeassistant).
8. **Klein anfangen:** ein Gewächshausthermometer und ein Bodenfeuchtesensor im Hauptbeet. Erweitern Sie, sobald Sie sehen, wie Sie sie nutzen.

## Platzierung und Pflege

- **Bodenfeuchte:** im Wurzelraum (10-15 cm tief), zwischen den Pflanzen, nicht direkt neben einem Tropfer. Ein Sensor pro Beet mit gleicher Kultur und gleichem Boden genügt.
- **Gewächshausthermometer:** auf Pflanzenhöhe, im Schatten (hinter einem Topf oder in einem Strahlungsschutz), nicht am Glas.
- **Außentemperatur:** in 50 cm Höhe in einem Strahlungsschutz (ein umgedrehter weißer Blumentopf tut es) - so messen Sie den Frost, den Ihre Pflanzen spüren.
- **Regenmesser:** frei von Bäumen und Dächern, waagerecht.
- Bodenfühler vor dem Umgraben oder Fräsen herausziehen, und vor dem Winter, wenn sie nicht frostfest sind. Batterien im Frühjahr wechseln.

## Mit Hortulus verbinden

Öffnen Sie die **Einstellungen** (Außensensoren) oder wählen Sie im **Planer** eine Zone oder ein Beet und wählen Sie den Sensor im Feld aus. Hortulus zeigt den Wert sofort an, markiert Sensoren, die zu lange still waren, als „veraltet“ und greift dann auf die Wasserbilanz und die Vorhersage zurück.
