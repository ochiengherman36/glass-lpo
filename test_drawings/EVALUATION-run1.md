# Accuracy against ground truth

**All drawings:** 76/79 fields right (96%), 72 without a flag; 4 flagged but right; 3 flagged and wrong/missing; **0 wrong and NOT flagged**

## hard (03-hard)

18/20 fields right (90%), 15 without a flag; 3 flagged but right; 2 flagged and wrong/missing; **0 wrong and NOT flagged**

Model `claude-sonnet-5-5`, 8378 input / 2940 output tokens. LPO `LPO-20261125-144632`.

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| P1 | width_mm | 900 | - | yes | flagged, wrong or missing |
| P1 | qty | 1 | 1 | yes | checked, right value |
| P2 | width_mm | 600 | 600 | yes | checked, right value |
| P2 | height_mm | 1000 | - | yes | flagged, wrong or missing |
| P2 | qty | 1 | 1 | yes | checked, right value |

Expected flags (ground truth):
- thickness_mm is not written on the drawing - system must mark CHECK, not guess
- glass_type is not stated - system must mark CHECK, not guess
- P2 width 600 is a hand correction over a crossed-out 650 - low confidence is acceptable if flagged

System flags:
- Unreadable on drawing: P1 width: first digit is ambiguous, 5 or 9 (looks like 'S00')
- Unreadable on drawing: Crossed-out value below P2 width of 600 (cannot be read with certainty)
- Unreadable on drawing: Hole position dimensions for all three holes are not written
- Unreadable on drawing: Quantity, thickness, glass type and edge work are not written anywhere
- P1: width unclear (raw: '?00 (first digit could be 5 or 9; looks like 'S00')')
- P1: quantity not written, assumed 1
- P1: thickness not written on drawing
- P1: glass type not written on drawing
- P2: width unclear (raw: '600 written, with a crossed-out value underneath (looks like 650 or 656, struck through)')
- P2: height not written on drawing
- P2: quantity not written, assumed 1
- P2: thickness not written on drawing
- P2: glass type not written on drawing

## realistic (02-realistic)

47/47 fields right (100%), 46 without a flag; 1 flagged but right; 0 flagged and wrong/missing; **0 wrong and NOT flagged**

Model `claude-sonnet-5-5`, 8378 input / 4451 output tokens. LPO `LPO-20261125-144556`.

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| P3 | width_mm | 400 | 400 | yes | checked, right value |

Expected flags (ground truth):
- none

System flags:
- Unreadable on drawing: P3 width: first digit overwritten or corrected (looks like 500 changed to 400)
- Unreadable on drawing: Abbreviation in brackets after 'Q25 TYP' is hard to read (looks like 'GND.', possibly 'GEN.')
- Unreadable on drawing: No hole position dimensions are written for any of the 6 holes
- Unreadable on drawing: Total hole count is not stated
- P3: width unclear (raw: ''4' appears written over another digit, then '00' (looks like 500 corrected to 400)')

## simple (01-simple)

11/12 fields right (92%), 11 without a flag; 0 flagged but right; 1 flagged and wrong/missing; **0 wrong and NOT flagged**

Model `claude-sonnet-5-5`, 8378 input / 2024 output tokens. LPO `LPO-20261125-144449`.

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| P1 | thickness_mm | 6 | - | yes | flagged, wrong or missing |

Expected flags (ground truth):
- none

System flags:
- Unreadable on drawing: Glass thickness in the title line: written like '66MM' or '6.5MM', second character ambiguous
- P1: thickness unclear (raw: '6?MM (written like '66MM' or '6.5MM'; second character is ambiguous)')
