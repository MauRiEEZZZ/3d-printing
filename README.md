# 3d-printing

Persoonlijke verzameling scripts, notities en kalibratie-experimenten voor 3D-printen.
Voornamelijk gericht op een **Bambu Lab P2S** met Bambu Studio.

## Projecten

| Map | Wat |
|---|---|
| [`ironing-cooldown/`](ironing-cooldown/) | Post-processing script dat een koelpauze vóór elke ironing-pass in Bambu Studio G-code injecteert, plus de bijbehorende troubleshooting-handoff. |

## ironing-cooldown

De ironing-kalibratietest print kleine vlakjes van 20×20 mm en irone daar direct achteraan.
Een echte print van ~230 mm doorsnede gaf echter een totaal ander resultaat: het kleine
vlakje + meteen ironen is niet representatief voor een groot oppervlak. Waarschijnlijke
oorzaak: op een groot vlak is de toplaag bij het begin van de ironing-pass al deels
afgekoeld, terwijl op een swatch alles nog warm is — de starttemperatuur verschilt dus met
de vlakgrootte.

Doel van het script: ironing **reproduceerbaar** maken door vóór elke pass een instelbare
`G4`-rustperiode (met retract, Z-hop en fans aan) in te lassen, zodat elk vlak bij nagenoeg
dezelfde starttemperatuur begint. Zo is wat je op een klein vlak afstelt representatief voor
een groot vlak.

- `ironing_dwell.py` — het post-processing script. Instellen in Bambu Studio onder
  *proces-preset → Others → Post-processing Scripts* (vervang `<username>` door je
  eigen home-map; het veld verwacht een absoluut pad):
  ```
  /usr/bin/python3 "/Users/<username>/scripts/ironing_dwell.py"
  ```
  Belangrijkste knoppen bovenin het script: `DWELLS` (seconden; meerdere waarden =
  cyclisch per ironing-blok), `Z_HOP`, `RETRACT`, `FAN_COOL`. Het script schrijft een
  header-comment met de gebruikte instellingen in de G-code (na `HEADER_BLOCK_END`) en
  markeert elk ingevoegd blok met `; >>> ironing_dwell.py cool-down ...`, zodat in de
  G-code zichtbaar is wat door het script is toegevoegd.
- `ironing-dwell-handoff.md` — volledige achtergrond, ontwerpkeuzes, geverifieerde feiten
  en volgende stappen.

### Status

Geverifieerd op Bambu Studio 02.07.01.62: de post-processing hook draait bij export, de
feature-marker `; FEATURE: Ironing` klopt, en de injectie werkt op een echte export. Zie
de handoff voor details.
