#!/usr/bin/env python3
"""Injecteert koelpauzes (G4-dwell) rond ironing-passes in Bambu Studio G-code.

Twee modi:
- SEGMENTS == 1: één dwell vóór elke ironing-pass (stabiliseren / discriminator).
- SEGMENTS  > 1: elke ironing-pass in N stukken hakken en vóór elk stuk oplopend
  meer dwell inlassen, zodat je bínnen één swatch het afkoel-verloop over het
  oppervlak ziet. Let op: een pauze koelt het hele *nog-niet-gestreken* deel, dus
  de koeling is cumulatief -- segment k ondergaat som(SEG_DWELLS[:k+1]) seconden.

Bambu Studio roept dit script aan met het pad van het G-code bestand als LAATSTE
argument (sys.argv[-1]) en verwacht in-place bewerking + exit 0.

Instellen (proces-preset -> Others -> Post-processing Scripts):
  /usr/bin/python3 "/Users/<username>/scripts/ironing_dwell.py"
"""
import os
import re
import sys

# --- modus & dwell ---
SEGMENTS   = 5                   # stukken per ironing-pass; 1 = uit (dwell alleen vóór de pass)
SEG_DWELLS = [0, 5, 10, 15, 20]  # dwell (s) vóór segment 1..N (cumulatief, zie docstring)
DWELLS     = [20]                # gebruikt als SEGMENTS == 1 (per pass, cyclisch)

# --- mechaniek ---
Z_HOP    = 1.0       # mm, nozzle optillen tijdens de pauze
RETRACT  = 0.6       # mm filament tegen oozen (geeft een naadje bij segment-splits)
FAN_COOL = 255       # part fan tijdens de pauze (0-255)
MIN_Z    = 0.0       # alleen injecteren boven deze hoogte
LOGFILE  = os.path.expanduser("~/ironing_dwell.log")
SCRIPT   = "ironing_dwell.py"

RE_FEAT  = re.compile(r'^;\s*FEATURE:\s*Ironing', re.I)
RE_END   = re.compile(r'^;\s*(?:FEATURE:|CHANGE_LAYER|stop printing object)', re.I)
RE_MOVE  = re.compile(r'^G1 .*\bE-?[\d.]', re.I)           # ironing-extrusiemove (heeft E)
RE_FAN   = re.compile(r'^M106(?:\s+P(\d))?\s+S([\d.]+)', re.I)
RE_Z     = re.compile(r'^;\s*(?:Z_HEIGHT|Z):\s*([\d.]+)')  # BS 2.7 = "; Z_HEIGHT: 0.2"
RE_OBJ   = re.compile(r'unique label id:\s*(\d+)')


def log(msg):
    with open(LOGFILE, "a") as f:
        f.write(msg + "\n")
    print(msg, file=sys.stderr)


def dwell_block(d, tag, fans):
    """G-code voor één koelpauze van d seconden; leeg als d <= 0."""
    if d <= 0:
        return []
    return [f"; >>> {SCRIPT} {tag} dwell {d}s\n",
            "M400\n", "M83\n", f"G1 E-{RETRACT} F2100\n",
            "G91\n", f"G1 Z{Z_HOP} F1200\n", "G90\n",
            f"M106 P1 S{FAN_COOL}\n", "M106 P2 S255\n",
            f"G4 S{d}\n",
            f"M106 P1 S{fans['1']}\n", f"M106 P2 S{fans['2']}\n",
            "G91\n", f"G1 Z-{Z_HOP} F1200\n", "G90\n",
            f"G1 E{RETRACT} F2100\n", f"; <<< {SCRIPT} {tag}\n"]


def seg_dwell(s):
    return SEG_DWELLS[s] if s < len(SEG_DWELLS) else SEG_DWELLS[-1]


path = sys.argv[-1]
with open(path) as f:
    src = f.readlines()

out, fans, z, obj = [], {'1': '0', '2': '0'}, 0.0, '?'
n = injected = 0
log(f"--- run: {path} (SEGMENTS={SEGMENTS}) ---")

i = 0
while i < len(src):
    line = src[i]
    if (m := RE_Z.match(line)):    z = float(m.group(1))
    if (m := RE_FAN.match(line)):  fans[m.group(1) or '1'] = m.group(2)
    if (m := RE_OBJ.search(line)): obj = m.group(1)

    if RE_FEAT.match(line) and z >= MIN_Z:
        n += 1
        fsnap = dict(fans)
        out.append(line)                       # de FEATURE-marker zelf
        i += 1
        body = []
        while i < len(src) and not RE_END.match(src[i]):
            body.append(src[i]); i += 1
        moves = [k for k, l in enumerate(body) if RE_MOVE.match(l)]

        if SEGMENTS > 1 and len(moves) >= SEGMENTS:
            # eerste move-regel van elk segment -> daarvóór de dwell inlassen
            bounds = {moves[(s * len(moves)) // SEGMENTS]: s for s in range(SEGMENTS)}
            for k, l in enumerate(body):
                if k in bounds:
                    s = bounds[k]
                    d = seg_dwell(s)
                    tag = f"seg {s+1}/{SEGMENTS} (ironing #{n}, obj {obj}, Z{z})"
                    blk = dwell_block(d, tag, fsnap)
                    if blk:
                        injected += 1
                    log(f"  ironing #{n} seg {s+1}/{SEGMENTS} -> dwell {d}s")
                    out += blk
                out.append(l)
        else:
            d = DWELLS[(n - 1) % len(DWELLS)]
            tag = f"cool-down (ironing #{n}, obj {obj}, Z{z})"
            blk = dwell_block(d, tag, fsnap)
            if blk:
                injected += 1
            log(f"  ironing #{n} -> dwell {d}s")
            out += blk + body
        continue

    out.append(line); i += 1

# Header-comment met instellingen, NA '; HEADER_BLOCK_END' invoegen: de P2S leest het
# header-blok voor print-info, dus dat blok moet bovenaan blijven staan.
mode = (f"SEGMENTS={SEGMENTS}, SEG_DWELLS={SEG_DWELLS}s" if SEGMENTS > 1
        else f"DWELLS={DWELLS}s")
settings = f"{mode} | Z_HOP={Z_HOP}mm | RETRACT={RETRACT}mm | FAN_COOL={FAN_COOL} | MIN_Z={MIN_Z}mm"
banner = ["; ------------------------------------------------------------\n",
          f"; {SCRIPT} (post-processing): koelpauze(s) rond elke ironing-pass\n",
          "; De ';>>> ... ' blokken hieronder zijn door dit script ingevoegd.\n",
          f"; settings: {settings}\n",
          f"; resultaat: {n} ironing-pass(es), {injected} dwell(s) ingevoegd\n",
          "; ------------------------------------------------------------\n"]
at = 0
for k, l in enumerate(out):
    if l.startswith("; HEADER_BLOCK_END"):
        at = k + 1
        break
out[at:at] = banner

with open(path, 'w') as f:
    f.writelines(out)
log(f"{n} ironing-passes, {injected} dwell(s), {path}")
