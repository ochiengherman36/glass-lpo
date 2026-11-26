# Accuracy against ground truth

**All drawings:** 73/88 fields right (83%), 66 without a flag; 7 flagged but right; 6 flagged and wrong/missing; **9 wrong and NOT flagged**

- Dimensions: 23/28 right (82%), 1 false CHECK, 3 flagged and wrong/missing, 2 wrong and not flagged
- Holes: 14/16 right (88%), 0 false CHECK, 2 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 36/44 right (82%), 6 false CHECK, 1 flagged and wrong/missing, 7 wrong and not flagged

A false CHECK is a value the system read correctly but still asked a person to confirm.

## client-images-16 (04-doors-and-sliding-window)

31/31 fields right (100%), 30 without a flag; 1 flagged but right; 0 flagged and wrong/missing; **0 wrong and NOT flagged**

- Dimensions: 10/10 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 6/6 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 15/15 right (100%), 1 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged

Model `claude-sonnet-5-5`, 7174 input / 2288 output tokens. LPO `LPO-20261126-231323`. Panels matched by item, then order within the item (no matching IDs).

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| window-1 | qty | 1 | 1 | yes | checked, right value |

Expected flags (ground truth):
- mixed units on one sheet (m and cm) - system must convert both to mm correctly
- individual door widths are not dimensioned - system must not split 2950 by 2 and present it as written
- door heights are not dimensioned - 2.4 m is the outer frame height, system must not use it as the door height
- window thickness and glass type not stated - CHECK
- door glass type not stated (only '12mm, 2 doors') - CHECK
- window qty not written - assumed 1, flag

System flags:
- P1: width not written on drawing
- P1: height not written on drawing
- P1: glass type not written on drawing
- P2: width not written on drawing
- P2: height not written on drawing
- P2: glass type not written on drawing
- P3: quantity not written, assumed 1
- P3: thickness not written on drawing
- P3: glass type not written on drawing

## client-images-17 (05-window-and-door-feet)

19/23 fields right (83%), 19 without a flag; 0 flagged but right; 2 flagged and wrong/missing; **2 wrong and NOT flagged**

- Dimensions: 5/8 right (62%), 0 false CHECK, 1 flagged and wrong/missing, 2 wrong and not flagged
- Holes: 4/4 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 10/11 right (91%), 0 false CHECK, 1 flagged and wrong/missing, 0 wrong and not flagged

Model `claude-sonnet-5-5`, 6481 input / 2682 output tokens. LPO `LPO-20261126-231329`. Panels matched by item, then order within the item (no matching IDs).

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| windows | overall_width_mm | - | 1219 | no | WRONG, NOT FLAGGED |
| doors | overall_height_mm | 2134 | - | yes | flagged, wrong or missing |
| window | width_mm | - | 610 | no | WRONG, NOT FLAGGED |
| P2 | panel | absent | extra panel | yes | flagged, wrong or missing |

Expected flags (ground truth):
- all dimensions in feet - system must convert (1 ft = 304.8 mm) and should show the original values
- window width conflicting: top says 4 ft, bottom says 2 ft / 4 ft / 2 ft - CHECK, do not add up
- door height digit unclear ('7 feet') - CHECK
- door glass size not written - only the upper half is glass, lower half is aluminium; system must not use the door size as the glass size
- no thickness or glass type anywhere - CHECK on both items
- word above each item is crossed out - only the circled quantities count

System flags:
- Doors overall height unclear (raw: '?feet (first digit unclear, possibly 5 or 6)')
- P1: thickness not written on drawing
- P1: glass type not written on drawing
- P2: thickness not written on drawing
- P2: glass type not written on drawing
- P3: width not written on drawing
- P3: height not written on drawing
- P3: thickness not written on drawing
- P3: glass type not written on drawing

## client-images-18 (06-oak-double-door)

15/20 fields right (75%), 11 without a flag; 4 flagged but right; 1 flagged and wrong/missing; **4 wrong and NOT flagged**

- Dimensions: 5/6 right (83%), 0 false CHECK, 1 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 4/4 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 6/10 right (60%), 4 false CHECK, 0 flagged and wrong/missing, 4 wrong and not flagged

Model `claude-sonnet-5-5`, 6537 input / 2069 output tokens. LPO `LPO-20261126-231336`. Panels matched by order (no matching IDs).

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| double door | overall_width_mm | 1187 | - | yes | flagged, wrong or missing |
| door-left | qty | 1 | 1 | yes | checked, right value |
| door-left | thickness_mm | 14 | 14 | yes | checked, right value |
| door-left | glass_type | double glazed unit | 14mm unit | no | WRONG, NOT FLAGGED |
| door-left | edge_work | bevel | - | no | WRONG, NOT FLAGGED |
| door-right | qty | 1 | 1 | yes | checked, right value |
| door-right | thickness_mm | 14 | 14 | yes | checked, right value |
| door-right | glass_type | double glazed unit | 14mm unit | no | WRONG, NOT FLAGGED |
| door-right | edge_work | bevel | - | no | WRONG, NOT FLAGGED |

Expected flags (ground truth):
- this is a timber door drawing, not a glass cutting list - the only glass data is '14MM UNIT' x2
- no glass width/height is written - system must mark sizes CHECK, never derive them from the frame drawing
- 1187 O/A and 2050 O/A are overall door frame sizes, not glass sizes - must not be used as glass dimensions
- 14 mm is not a standard thickness - CHECK
- many small annotations (90, 90x70, 170, 700, beads, hinges) are joinery details, not glass data

System flags:
- Overall width unclear (raw: 'bottom: 1187 O/A; top: '1?||?0|' with '12' below, unreadable and may disagree with the bottom figure')
- Unreadable on drawing: Top overall width dimension, reads like '1?||?0|' with '12' below
- Unreadable on drawing: Small number under 'DRIP' at the bottom of the side section, reads like '14?'
- P1: width not written on drawing
- P1: height not written on drawing
- P1: quantity not written, assumed 1
- P1: thickness 14 mm is not a standard glass thickness (4, 5, 6, 8, 10, 12, 15, 19)
- P2: width not written on drawing
- P2: height not written on drawing
- P2: quantity not written, assumed 1
- P2: thickness 14 mm is not a standard glass thickness (4, 5, 6, 8, 10, 12, 15, 19)

## client-sd42teinfr7f1 (07-imperial-partition)

8/14 fields right (57%), 6 without a flag; 2 flagged but right; 3 flagged and wrong/missing; **3 wrong and NOT flagged**

- Dimensions: 3/4 right (75%), 1 false CHECK, 1 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 0/2 right (0%), 0 false CHECK, 2 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 5/8 right (62%), 1 false CHECK, 0 flagged and wrong/missing, 3 wrong and not flagged

Model `claude-sonnet-5-5`, 9883 input / 1795 output tokens. LPO `LPO-20261126-231342`. Panels matched by order (no matching IDs).

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| partition screen | overall_width_mm | 2740 | 2740 | yes | checked, right value |
| panel-1 | width_mm | - | 2740 | yes | flagged, wrong or missing |
| panel-1 | qty | 1 | 1 | yes | checked, right value |
| panel-1 | hole_count | 0 | 3 | yes | flagged, wrong or missing |
| panel-1 | hole_diameters | - | [None, None, None] | yes | flagged, wrong or missing |
| panel-2 | panel | present | missing | no | WRONG, NOT FLAGGED |
| panel-3 | panel | present | missing | no | WRONG, NOT FLAGGED |
| top-rail | panel | present | missing | no | WRONG, NOT FLAGGED |

Expected flags (ground truth):
- width in inches with fraction (107 7/8 in = 2740 mm) - system must convert and keep the original
- both heights missing the whole number ('?? 1/4' left, '?? 3/8' right) - CHECK
- individual panel widths not dimensioned - CHECK, do not split 107 7/8 by 3
- hole diameters and positions not written - count only (3), everything else CHECK
- top strip covers panels 2-3 only; may be a rail or clamps, circles may be clamp or hinge points - confirm
- no glass type or quantity stated

System flags:
- Overall width unclear (raw: '107 7/8; unit not written, inches assumed from the fraction')
- Overall height unclear (raw: 'only fractions written beside the vertical edges: '1/4' on the left, '3/8' on the right; no whole number')
- Unreadable on drawing: Small marks between the holes along the top, possibly dimensions, cannot be read
- P1: width unclear (raw: '107 7/8; unit not written, inches assumed from the fraction')
- P1: height unclear (raw: 'only fractions written beside the vertical edges: '1/4' on the left, '3/8' on the right; no whole number')
- P1: quantity not written, assumed 1
- P1: thickness not written on drawing
- P1: glass type not written on drawing
- P1: hole 1 diameter not written on drawing
- P1: hole 2 diameter not written on drawing
- P1: hole 3 diameter not written on drawing
