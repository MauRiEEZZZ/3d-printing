# 3d-printing

Persoonlijke verzameling scripts, notities en kalibratie-experimenten voor 3D-printen.
Voornamelijk gericht op een **Bambu Lab P2S** met Bambu Studio.

## Projecten

| Map | Wat |
|---|---|
| [`ironing-cooldown/`](ironing-cooldown/) | Post-processing script dat een koelpauze vóór elke ironing-pass in Bambu Studio G-code injecteert, plus de bijbehorende troubleshooting-handoff. |

## ironing-cooldown

Onderzoek naar waarom ironing-instellingen die op een kleine swatch mooi zijn, op grote
vlakken (20×20 mm) niet standhouden. Hypothese: de toplaag is op een groot vlak al deels
afgekoeld voordat de ironing-pass begint. Het script injecteert een instelbare `G4`-dwell
(met retract, Z-hop en fans op vol) net vóór elke ironing-pass, zodat de invloed van
koeltijd geïsoleerd getest kan worden.

- `ironing_dwell.py` — het post-processing script. Instellen in Bambu Studio onder
  *proces-preset → Others → Post-processing Scripts* (vervang `<username>` door je
  eigen home-map; het veld verwacht een absoluut pad):
  ```
  /usr/bin/python3 "/Users/<username>/scripts/ironing_dwell.py"
  ```
  Belangrijkste knoppen bovenin het script: `DWELLS` (seconden; meerdere waarden =
  cyclisch per ironing-blok), `Z_HOP`, `RETRACT`, `FAN_COOL`.
- `ironing-dwell-handoff.md` — volledige achtergrond, ontwerpkeuzes, geverifieerde feiten
  en volgende stappen.

### Status

Geverifieerd op Bambu Studio 02.07.01.62: de post-processing hook draait bij export, de
feature-marker `; FEATURE: Ironing` klopt, en de injectie werkt op een echte export. Zie
de handoff voor details.
