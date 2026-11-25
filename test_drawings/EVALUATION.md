# Accuracy against ground truth

**All drawings:** 76/79 fields right (96%), 73 without a flag; 3 flagged but right; 3 flagged and wrong/missing; **0 wrong and NOT flagged**

- Dimensions: 20/22 right (91%), 1 false CHECK, 2 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 17/17 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 39/40 right (98%), 2 false CHECK, 1 flagged and wrong/missing, 0 wrong and not flagged

A false CHECK is a value the system read correctly but still asked a person to confirm.

## hard (03-hard)

19/20 fields right (95%), 16 without a flag; 3 flagged but right; 1 flagged and wrong/missing; **0 wrong and NOT flagged**

- Dimensions: 5/6 right (83%), 1 false CHECK, 1 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 4/4 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 10/10 right (100%), 2 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged

Model `claude-sonnet-5-5`, 8516 input / 2452 output tokens. LPO `LPO-20261125-145335`.

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| P1 | width_mm | 900 | - | yes | flagged, wrong or missing |
| P1 | qty | 1 | 1 | yes | checked, right value |
| P2 | width_mm | 600 | 600 | yes | checked, right value |
| P2 | qty | 1 | 1 | yes | checked, right value |

Expected flags (ground truth):
- thickness_mm is not written on the drawing - system must mark CHECK, not guess
- glass_type is not stated - system must mark CHECK, not guess
- P2 width 600 is a hand correction over a crossed-out 650 - low confidence is acceptable if flagged

System flags:
- P1: width unclear (raw: '?00 (first digit could be 5 or 9)')
- P1: quantity not written, assumed 1
- P1: thickness not written on drawing
- P1: glass type not written on drawing
- P2: width unclear (raw: '600 written, with a crossed-out number (looks like 650) written below it')
- P2: quantity not written, assumed 1
- P2: thickness not written on drawing
- P2: glass type not written on drawing

## realistic (02-realistic)

46/47 fields right (98%), 46 without a flag; 0 flagged but right; 1 flagged and wrong/missing; **0 wrong and NOT flagged**

- Dimensions: 11/12 right (92%), 0 false CHECK, 1 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 10/10 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 25/25 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged

Model `claude-sonnet-5-5`, 8516 input / 4148 output tokens. LPO `LPO-20261125-145326`.

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| P3 | width_mm | 400 | - | yes | flagged, wrong or missing |

Expected flags (ground truth):
- none

System flags:
- Unreadable on drawing: Text in brackets after 'Ø25 TYP' reads like '(GND.)' and its meaning is unclear
- P3: width unclear (raw: '4?00 – first digit looks like a 4 written over or struck through another digit (possibly 5); the value is overwritten and corrected, so the intended number is unclear')

## simple (01-simple)

11/12 fields right (92%), 11 without a flag; 0 flagged but right; 1 flagged and wrong/missing; **0 wrong and NOT flagged**

- Dimensions: 4/4 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 3/3 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 4/5 right (80%), 0 false CHECK, 1 flagged and wrong/missing, 0 wrong and not flagged

Model `claude-sonnet-5-5`, 8516 input / 1772 output tokens. LPO `LPO-20261125-145317`.

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| P1 | thickness_mm | 6 | - | yes | flagged, wrong or missing |

Expected flags (ground truth):
- none

System flags:
- P1: thickness unclear (raw: '6?MM (title reads '6?MM'; second character unclear, could be 6.5 or 66)')
