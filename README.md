# 3d-printing

Persoonlijke verzameling scripts, notities en kalibratie-experimenten voor 3D-printen.
Voornamelijk gericht op een **Bambu Lab P2S** met Bambu Studio.

## Projecten

| Map | Wat |
|---|---|
| [`ironing-cooldown/`](ironing-cooldown/) | Post-processing script dat koelpauzes rond elke ironing-pass in Bambu Studio G-code injecteert (stabiliseren óf het afkoel-verloop binnen een swatch tonen), plus de bijbehorende troubleshooting-handoff. |

## ironing-cooldown

De ironing-kalibratietest print kleine vlakjes en irone daar direct achteraan. Een echte print
van ~220 mm doorsnede gaf echter een totaal ander resultaat: het kleine vlakje + meteen ironen
is niet representatief voor een groot oppervlak. Waarschijnlijke oorzaak is **thermisch via
blootstellingstijd** — bij trage ironing (bijv. 10 mm/s) duurt de pass zó lang dat de toplaag
onderweg sterk afkoelt en op een koud substraat gestreken wordt. Bijkomend inzicht: de swatch
beloont juist een lage snelheid (kost op een vlakje geen afkoeling, geeft mooie glans), terwijl
diezelfde lage snelheid op een groot vlak de afkoeling *veroorzaakt* — de test stuurt qua
snelheid dus de verkeerde kant op.

Doel van het script: ironing **reproduceerbaar** maken door vóór elke pass een instelbare
`G4`-rustperiode (met retract, Z-hop en fans aan) in te lassen, zodat elk vlak bij nagenoeg
dezelfde starttemperatuur begint. Een tweede modus hakt elke pass in stukken en laat vóór elk
stuk oplopend meer dwell vallen, zodat je het afkoel-verloop van een groot vlak binnen één
swatch ziet.

- `ironing_dwell.py` — het post-processing script. Instellen in Bambu Studio onder
  *proces-preset → Others → Post-processing Scripts* (vervang `<username>` door je
  eigen home-map; het veld verwacht een absoluut pad):
  ```
  /usr/bin/python3 "/Users/<username>/Projects/3d-printing/ironing-cooldown/ironing_dwell.py"
  ```
  Knoppen bovenin het script:
  - `SEGMENTS` — stukken per ironing-pass; `1` = één dwell vóór de pass (stabiliseren),
    `>1` = pass opbreken en per stuk oplopend koelen (afkoel-verloop binnen één swatch).
  - `SEG_DWELLS` — dwell (s) vóór elk segment; koeling is cumulatief, dus segment k ondergaat
    `som(SEG_DWELLS[:k+1])`.
  - `DWELLS` — gebruikt als `SEGMENTS == 1` (per pass, cyclisch).
  - `Z_HOP`, `RETRACT`, `FAN_COOL`, `MIN_Z` — mechaniek van de pauze.

  Het script schrijft een header-comment met de gebruikte instellingen in de G-code (na
  `HEADER_BLOCK_END`) en markeert elk ingevoegd blok met `; >>> ironing_dwell.py ...`, zodat in
  de G-code zichtbaar is wat door het script is toegevoegd.
- `ironing-dwell-handoff.md` — volledige achtergrond, ontwerpkeuzes, geverifieerde feiten
  en volgende stappen.

### Status

Geverifieerd op Bambu Studio 02.07.01.62: de post-processing hook draait bij élke slice (dus
zowel "Export G-code" als direct "Print"), de feature-marker `; FEATURE: Ironing` klopt, en de
injectie werkt op een echte slice. Segment-modus getest op een 9-pass plaat. Zie de handoff
voor de volledige achtergrond en volgende stappen.
