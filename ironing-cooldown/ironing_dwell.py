#!/usr/bin/env python3
"""Injecteert een koelpauze voor elke ironing-pass in Bambu Studio G-code.

Bambu Studio roept dit script aan met het pad van het G-code bestand als
LAATSTE argument (sys.argv[-1]) en verwacht in-place bewerking + exit 0.

Instellen in Bambu Studio (proces-preset -> Others -> Post-processing Scripts):
  /usr/bin/python3 "/Users/<username>/scripts/ironing_dwell.py"
"""
import os
import re
import sys

DWELLS   = [20]      # sec. Meerdere waarden = per ironing-blok cyclisch (test-matrix!)
Z_HOP    = 1.0       # mm
RETRACT  = 0.6       # mm filament
FAN_COOL = 255       # part fan tijdens de pauze (0-255)
MIN_Z    = 0.0       # alleen injecteren boven deze hoogte
LOGFILE  = os.path.expanduser("~/ironing_dwell.log")
SCRIPT   = "ironing_dwell.py"

RE_FEAT  = re.compile(r'^;\s*FEATURE:\s*Ironing', re.I)
RE_FAN   = re.compile(r'^M106(?:\s+P(\d))?\s+S([\d.]+)', re.I)
RE_Z     = re.compile(r'^;\s*(?:Z_HEIGHT|Z):\s*([\d.]+)')  # BS 2.7 = "; Z_HEIGHT: 0.2"
RE_OBJ   = re.compile(r'unique label id:\s*(\d+)')


def log(msg):
    with open(LOGFILE, "a") as f:
        f.write(msg + "\n")
    print(msg, file=sys.stderr)


path = sys.argv[-1]
with open(path) as f:
    src = f.readlines()

out, fans, z, obj, n, injected = [], {'1': '0', '2': '0'}, 0.0, '?', 0, 0
log(f"--- run: {path} ---")
for line in src:
    if (m := RE_Z.match(line)):    z = float(m.group(1))
    if (m := RE_FAN.match(line)):  fans[m.group(1) or '1'] = m.group(2)
    if (m := RE_OBJ.search(line)): obj = m.group(1)

    if RE_FEAT.match(line) and z >= MIN_Z:
        d = DWELLS[n % len(DWELLS)]
        n += 1
        log(f"  ironing #{n}: object {obj} @ Z{z} -> dwell {d}s")
        if d > 0:
            injected += 1
            out += [f"; >>> {SCRIPT} cool-down {d}s (ironing #{n}, object {obj}, Z{z})\n",
                    "M400\n", "M83\n", f"G1 E-{RETRACT} F2100\n",
                    "G91\n", f"G1 Z{Z_HOP} F1200\n", "G90\n",
                    f"M106 P1 S{FAN_COOL}\n", "M106 P2 S255\n",
                    f"G4 S{d}\n",
                    f"M106 P1 S{fans['1']}\n", f"M106 P2 S{fans['2']}\n",
                    "G91\n", f"G1 Z-{Z_HOP} F1200\n", "G90\n",
                    f"G1 E{RETRACT} F2100\n", f"; <<< {SCRIPT} cool-down\n"]
    out.append(line)

# Header-comment met de script-instellingen. NA '; HEADER_BLOCK_END' invoegen, want
# de P2S leest het header-blok voor print-info; dat blok moet bovenaan blijven staan.
settings = (f"DWELLS={DWELLS}s | Z_HOP={Z_HOP}mm | RETRACT={RETRACT}mm | "
            f"FAN_COOL={FAN_COOL} | MIN_Z={MIN_Z}mm")
banner = ["; ------------------------------------------------------------\n",
          f"; {SCRIPT} (post-processing): koelpauze voor elke ironing-pass\n",
          "; De ';>>> ... cool-down' blokken hieronder zijn door dit script ingevoegd.\n",
          f"; settings: {settings}\n",
          f"; resultaat: {n} ironing-pass(es), {injected} cool-down-blok(ken) ingevoegd\n",
          "; ------------------------------------------------------------\n"]
insert_at = 0
for i, line in enumerate(out):
    if line.startswith("; HEADER_BLOCK_END"):
        insert_at = i + 1
        break
out[insert_at:insert_at] = banner

with open(path, 'w') as f:
    f.writelines(out)
log(f"{n} ironing-passes gevonden ({injected} ingevoegd), {path}")
