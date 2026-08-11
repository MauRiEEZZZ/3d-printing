# Handoff: koelpauze vóór ironing op Bambu Lab P2S

> Dit document is een sessie-overdracht. Lees het in en ga verder waar het bij
> **Volgende stappen** ophoudt. Alles wat hieronder als "onverifieerd" staat is
> nog niet op echte hardware of in de echte UI getest.
>
> **Update 2026-08-11:** de opzet is grotendeels geverifieerd (script draait, hook
> werkt, feature-marker klopt). Zie **Geverifieerd op 2026-08-11** hieronder.

## Setup

| | |
|---|---|
| Printer | Bambu Lab P2S |
| Extra | AMS 2 Pro + filament buffer |
| Printer-firmware | 01.02.00 |
| Slicer | **Bambu Studio 02.07.01.62** (bevestigd) |
| Host | macOS, `/usr/bin/python3` = 3.9.6 |
| Script-pad | `~/scripts/ironing_dwell.py` (chmod +x) |

## Geverifieerd op 2026-08-11

Uit de `.3mf` (`~/Downloads/IroningTest-Swatchesv2(4).3mf`) en een echte G-code-export
(`~/Downloads/IroningTestv2_PETG_1h15m.gcode`) bevestigd:

- **Bambu Studio 02.07.01.62.** Bepaalt de UI-labels in stap 2.
- **De post-processing hook werkt.** De export bevatte bij het slicen al 8 geïnjecteerde
  `cool-down`-blokken — BS draait het script dus daadwerkelijk bij export. **Niet ook nog
  handmatig over de export draaien: dat injecteert dubbel.**
- **Feature-marker klopt:** de export gebruikt letterlijk `; FEATURE: Ironing`. `RE_FEAT`
  is correct.
- **`unique label id:` bestaat** en levert per ironing-pass een objectnummer voor de log.
- **Z-marker was fout.** BS 2.7 gebruikt `; Z_HEIGHT: 0.2`, niet `; Z:`. Zonder fix bleef
  de hoogte 0.0 (injectie werkte wel, alleen de log/comment klopte niet). `RE_Z` matcht nu
  beide vormen. Puur cosmetisch.
- De `.3mf`-matrix is **echt 5×5**: 25 swatches (`stl_1..25`), flow ∈ {10,20,30,40,50}%,
  speed ∈ {10,20,30,40,50} mm/s. De flow-10%- en speed-30-kolommen zitten als "default"
  (geen per-object override). Plus 2 losse objecten (o.a. een uitbijter 38%/150) → 27 totaal.
- **Materiaal wisselt per test.** De `.3mf` is PLA (slot 1 = Bambu PLA Wood, rest Generic
  PLA), 0.16mm-profiel. De laatste export is PETG met 8 swatches, 0.2mm. Let dus op welke
  plaat/materiaal je print — het zijn niet dezelfde test.

## Wat er al is

Een ironing-kalibratietest met **25 swatches** — een 5×5 matrix waarin ironing-**flow**
loopt van 10% t/m 50% en ironing-**speed** van 10 t/m 50 mm/s (bevestigd, zie boven).

## Het probleem

De ironing-kalibratietest gebruikt kleine vlakjes van **20×20 mm**: de toplaag printen en
er direct achteraan de ironing-pass. Lang aangenomen dat dit de waarheid gaf.

Maar een echte print van **~230 mm doorsnede** gaf een totaal ander ironing-resultaat dan de
swatch-test voorspelde. Daarmee is duidelijk: een 20×20-vlakje + meteen ironen geeft een
**verkeerd beeld** van wat er op een veel groter ironing-oppervlak gebeurt. De flow/speed die
op een swatch het mooiste resultaat geeft, houdt op een groot vlak geen stand.

## Waarom waarschijnlijk: de starttemperatuur verschilt

Op een klein vlak is de toplaag nog overal warm als de ironing-pass begint. Op een groot vlak
begint het ironen tientallen seconden na het eerste top-infill-spoor — de starttemperatuur
loopt dan sterk uiteen over het oppervlak, en verschilt bovendien per printformaat. Ironing
is gevoelig voor die starttemperatuur, dus verschuift het optimale flow/speed-punt mee met de
grootte van het vlak.

*Concurrerende verklaring (drukverval):* ironing extrudeert bij 10–50% flow extreem weinig.
Op een korte swatch teert de pass nog op de restdruk in de nozzle van het top-infill; op een
lang pad zakt die druk in en irone je aan het eind droog. Visueel bijna identiek aan "te koud".
In het achterhoofd houden, maar de starttemperatuur is de eerste verdachte.

## Doel van dit script: stabiliseren, niet alleen meten

De bedoeling is ironing **reproduceerbaar** maken, onafhankelijk van de vlakgrootte. Door vóór
elke ironing-pass een **rustperiode** (`G4`-dwell, met de fans aan) in te lassen, start elk
vlak bij (nagenoeg) dezelfde temperatuur. Dan is wat je op een klein vlak afstelt representatief
voor een groot vlak. Route naar hetzelfde doel langs de andere kant: via een gelijke
ironing-snelheid overal een gelijke warmte-inbreng krijgen.

Het dubbelt als **discriminator**: reproduceert een koelpauze op een kleine swatch het probleem
van het grote vlak → dan is temperatuur de dominante variabele. Verandert er niets → richting
flow zoeken (ironing-flow omhoog, ironing-speed omlaag).

## Waarom een post-processing script en niet een Bambu Studio-instelling

Ironing gebeurt in **dezelfde laag**, direct na het top-surface-infill. Geen enkele
Bambu Studio-hook zit op dat punt:

- **Layer-change / custom G-code via de layer-slider** vuurt aan het *begin* van de
  laag — de toplaag is dan nog niet gedeponeerd. Wel bruikbaar om de fans op vol te
  zetten voor de hele toplaag (de 80%-oplossing, nul frictie), maar dat koelt ook het
  top-infill tijdens het printen. Opslag: in het 3MF (`custom_gcode_per_layer`), los
  van het filament-preset.
- **Cooling-instellingen** (layer time, min speed) zitten in het *filament*-preset en
  vertragen de extrusie in plaats van een echte pauze toe te voegen. Daarmee verander
  je flowdynamiek en temperatuur tegelijk — precies wat geïsoleerd moet worden. Afblijven.
- **Post-processing script** kan wél tussen top-infill en ironing injecteren. Staat in
  het **process**-preset, reist mee in het 3MF, en laat het filament-preset volledig vrij.

## Het G-code blok dat geïnjecteerd wordt

Leunt op Bambu Studio's defaults: relatieve extrusie (M83) en absolute XYZ.

```gcode
; >>> ironing cool-down
M400                  ; wacht tot alle moves klaar zijn
M83
G1 E-0.6 F2100        ; kleine retract tegen oozen
G91
G1 Z1.0 F1200         ; 1 mm omhoog, nozzle niet op het vlak laten koken
G90
M106 P1 S255          ; part cooling fan
M106 P2 S255          ; aux fan
G4 S20                ; de koelpauze
M106 P1 S<origineel>
M106 P2 S<origineel>
G91
G1 Z-1.0 F1200
G90
G1 E0.6 F2100         ; unretract, druk terug opbouwen
; <<< ironing cool-down
```

Ontwerpkeuzes die niet optioneel zijn:

- **Z-hop + retract**: 20 s stilstaan met een hete nozzle op een verse toplaag geeft
  een glansvlek en een blob.
- **XY niet herstellen**: de eerstvolgende slicer-move is een absolute travel naar het
  ironing-startpunt, dus positie komt automatisch goed.
- **Fans terugzetten op de oorspronkelijke waarde**: het script houdt de laatst geziene
  `M106 P1/P2` bij, want de slicer zet die pas bij de volgende laag opnieuw.

Optionele extra knop (sterk effect, vaak onderschat): lagere nozzle-temperatuur tijdens
de ironing-pass. `M104 S<lager>` vóór de `G4`, `M109 S<lager>` erna — de dwell dient dan
meteen als afkoeltijd van de hotend.

## Het script

Bedoeld pad: `~/scripts/ironing_dwell.py`

```python
#!/usr/bin/env python3
"""Injecteert een koelpauze vóór elke ironing-pass in Bambu Studio G-code."""
import re, sys

DWELLS   = [20]      # sec. Meerdere waarden = per ironing-blok cyclisch (test-matrix!)
Z_HOP    = 1.0       # mm
RETRACT  = 0.6       # mm filament
FAN_COOL = 255       # part fan tijdens de pauze (0-255)
MIN_Z    = 0.0       # alleen injecteren boven deze hoogte

RE_FEAT  = re.compile(r'^;\s*FEATURE:\s*Ironing', re.I)
RE_FAN   = re.compile(r'^M106(?:\s+P(\d))?\s+S([\d.]+)', re.I)
RE_Z     = re.compile(r'^;\s*(?:Z_HEIGHT|Z):\s*([\d.]+)')  # BS 2.7 = "; Z_HEIGHT: 0.2"
RE_OBJ   = re.compile(r'unique label id:\s*(\d+)')

path = sys.argv[-1]
with open(path) as f:
    src = f.readlines()

out, fans, z, obj, n = [], {'1': '0', '2': '0'}, 0.0, '?', 0
for line in src:
    if (m := RE_Z.match(line)):   z = float(m.group(1))
    if (m := RE_FAN.match(line)): fans[m.group(1) or '1'] = m.group(2)
    if (m := RE_OBJ.search(line)): obj = m.group(1)

    if RE_FEAT.match(line) and z >= MIN_Z:
        d = DWELLS[n % len(DWELLS)]
        n += 1
        print(f"  ironing #{n}: object {obj} @ Z{z} -> dwell {d}s", file=sys.stderr)
        if d > 0:
            out += [f"; >>> cool-down {d}s (ironing #{n}, object {obj}, Z{z})\n",
                    "M400\n", "M83\n", f"G1 E-{RETRACT} F2100\n",
                    "G91\n", f"G1 Z{Z_HOP} F1200\n", "G90\n",
                    f"M106 P1 S{FAN_COOL}\n", "M106 P2 S255\n",
                    f"G4 S{d}\n",
                    f"M106 P1 S{fans['1']}\n", f"M106 P2 S{fans['2']}\n",
                    "G91\n", f"G1 Z-{Z_HOP} F1200\n", "G90\n",
                    f"G1 E{RETRACT} F2100\n", "; <<< cool-down\n"]
    out.append(line)

with open(path, 'w') as f:
    f.writelines(out)
print(f"{n} ironing-passes gevonden, {path}", file=sys.stderr)
```

Werking: het script wordt door Bambu Studio aangeroepen met het pad van het G-code
bestand als **laatste argument** (vandaar `sys.argv[-1]`) en bewerkt dat bestand
**in-place**. Exit code moet 0 zijn.

## Bambu Studio: post-processing script instellen

**1. Script op een vaste plek** (niet in een temp-map):

```bash
mkdir -p ~/scripts && chmod +x ~/scripts/ironing_dwell.py
```

Check welke Python beschikbaar is:

```bash
which -a python3 && python3 -V
```

`/usr/bin/python3` bestaat op macOS alleen met Xcode Command Line Tools; met
Homebrew-python is het `/opt/homebrew/bin/python3`.

**2. Het veld vinden** (verstopt achter het parameter-niveau):

- Rechter zijbalk, bovenaan de process-parameters: zet de schakelaar van **Simple**
  naar **Advanced** (of **All**). Op Simple bestaat de pagina niet.
- Tandwiel/edit-icoon naast de process-preset dropdown → volledig instellingenvenster.
- Links in de tabbladenlijst: **Others** → sectie **Post-processing Scripts**.
- Niet te vinden? Er zit een zoekveld in dat venster; zoek op "post".
- *Labels kunnen per versie afwijken (in sommige versies heet de pagina "Output
  options"). Het veld heet altijd iets met "Post-processing". Onverifieerd voor deze
  Bambu Studio-versie.*

**3. Invullen** — één script per regel, interpreter eerst, pad tussen quotes. Zelf geen
bestandsnaam toevoegen:

```
/usr/bin/python3 "/Users/<username>/scripts/ironing_dwell.py"
```

**4. Preset opslaan — de stap die mensen overslaan.** Je hebt een systeem-preset
gewijzigd (asterisk / "(modified)" achter de naam). Dat is vluchtig: bij van preset
wisselen of herstarten is het weg. Diskette-icoon → opslaan als eigen preset, bijv.
`0.20mm Standard – ironing test`. Daarna reist het mee in het 3MF, los van het
filament-preset.

**5. Verifiëren.** Slice, dan **Export G-code file** (niet Print/Send):

```bash
grep -c "cool-down" ~/Downloads/plate_1.gcode
```

`> 0` = werkt. `0` = het script liep niet, of de feature-marker heet anders:

```bash
grep -m5 "FEATURE:" ~/Downloads/plate_1.gcode
```

## Struikelpunten

- **Feature-marker.** Het hele script hangt aan de letterlijke string `; FEATURE: Ironing`.
  **Geverifieerd op 2026-08-11:** BS 2.7 gebruikt precies die string, `RE_FEAT` klopt.
- **Niet dubbel injecteren.** BS draait het script al bij export (bevestigd). Draai het
  daarna niet ook nog handmatig over dezelfde file — dan krijg je twee dwell-blokken per
  pass. Herken je aan dubbele `>>> cool-down`-headers met hetzelfde `ironing #`-nummer.
- **Geen script-output zichtbaar.** Bambu Studio slikt stdout/stderr. Het echte script
  schrijft daarom naar `~/ironing_dwell.log` (functie `log()` bovenin) met de
  `ironing #n -> object -> dwell Ys` mapping. Deze logfile-versie draait al; de listing
  hierboven is de kale variant.
- **Crash = generieke exportfout** die niets over de oorzaak zegt. Test daarom los op
  een kopie van een geëxporteerde G-code:
  ```bash
  python3 ~/scripts/ironing_dwell.py ~/Downloads/plate_1_kopie.gcode
  ```
- **Post-processing loopt bij "Export G-code file"** (bevestigd op 2026-08-11: de export
  bevatte de injecties). Of het ook meegaat bij direct naar de printer sturen is nog
  **onverifieerd** — zoek in de verzonden file naar `cool-down`. Zit het er niet in:
  exporteer de G-code en print van SD.
- **Spaties in paden** breken het zonder quotes.
- **25 swatches × 20 s ≈ 8 minuten extra**: elke swatch heeft zijn eigen ironing-blok en
  krijgt dus zijn eigen dwell.
- **`M73` resterende-tijd klopt niet meer.** Onschuldig.

## Volgende stappen

1. ~~Feature-marker valideren op een echte export.~~ **Klaar** — `; FEATURE: Ironing` bevestigd.
2. ~~Script wegschrijven, chmod, los testen.~~ **Klaar** — `~/scripts/ironing_dwell.py` draait,
   getest op synthetische én echte export.
3. ~~Post-processing script instellen in Bambu Studio.~~ **Klaar** — hook draait aantoonbaar bij
   export. *Nog te doen:* controleren of het als eigen process-preset is opgeslagen (anders bij
   preset-wissel/herstart weg).
4. **De eigenlijke test (bewaard voor later):** flow en speed vastzetten op de winnaar uit de
   5×5, dan **vijf
   patches van 20×20 mm** printen met `DWELLS = [0, 5, 15, 30, 60]`. Elk ironing-blok
   krijgt een andere pauze; het script logt welk object welke dwell kreeg zodat de mapping
   bekend is. Volgorde van de ironing-blokken = slice-volgorde, dus controleren via de
   geïnjecteerde comments in de G-code.
5. Loopt de kwaliteit monotoon mee met de dwell → temperatuur is de variabele, en je weet
   meteen hoeveel koeltijd nodig is. Blijft het vlak → richting flow zoeken
   (ironing-flow omhoog, ironing-speed omlaag).

## Beantwoorde vragen (2026-08-11)

- **5×5?** Ja — flow 10–50%, speed 10–50 mm/s, 25 swatches (+2 losse objecten).
- **Bambu Studio-versie?** 02.07.01.62.
- **Filament?** `.3mf` = PLA (slot 1 Bambu PLA Wood, rest Generic PLA), 0.16mm. Laatste
  export = PETG, 0.2mm. Bij PETG wil je de part-fan waarschijnlijk lager dan 255 (PETG
  hecht slechter met veel koeling); de restore-waarde in de export stond op ~30% (S76.5).
- **3MF beschikbaar?** Ja — `~/Downloads/IroningTest-Swatchesv2(4).3mf` (+ oudere kopieën).
- **Gaat de injectie ook mee bij direct naar de printer sturen?** Ja. Het script draait aan
  het eind van élke slice op Bambu Studio's interne temp-G-code (`.../bamboo_model/.../.gcode`)
  — precies het bestand dat vervolgens naar de printer gaat óf geëxporteerd wordt. Dus zowel
  "Print" als "Export G-code" krijgen de dwell. Bevestigd op 2026-08-11 in het slice-temp.
- **Live script-pad.** Bambu Studio wijst nu naar de repo-kopie
  (`~/Projects/3d-printing/ironing-cooldown/ironing_dwell.py`). De kopie in `~/scripts/` is
  daarmee overbodig; pas op voor divergentie als je er één bewerkt.

## Nog open

- Is het post-processing script als **eigen process-preset** opgeslagen? Zo niet, dan is het
  vluchtig (zie stap 3).
- Voor de PETG-plaat: is part-fan 255 tijdens de dwell niet te veel (randen/strings)?
