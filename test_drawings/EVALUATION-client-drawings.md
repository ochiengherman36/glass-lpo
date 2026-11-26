# Accuracy against ground truth

**All drawings:** 102/113 fields right (90%), 92 without a flag; 10 flagged but right; 7 flagged and wrong/missing; **4 wrong and NOT flagged**

- Dimensions: 31/34 right (91%), 1 false CHECK, 1 flagged and wrong/missing, 2 wrong and not flagged
- Holes: 20/22 right (91%), 0 false CHECK, 2 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 51/57 right (89%), 9 false CHECK, 4 flagged and wrong/missing, 2 wrong and not flagged

A false CHECK is a value the system read correctly but still asked a person to confirm.

## client-images-16 (04-doors-and-sliding-window)

29/31 fields right (94%), 28 without a flag; 1 flagged but right; 2 flagged and wrong/missing; **0 wrong and NOT flagged**

- Dimensions: 10/10 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 6/6 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 13/15 right (87%), 1 false CHECK, 2 flagged and wrong/missing, 0 wrong and not flagged

Model `claude-sonnet-5-5`, 7556 input / 2346 output tokens. LPO `LPO-20261126-235017`. Panels matched by item, then order within the item (no matching IDs).

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| door-1 | qty | 1 | - | yes | flagged, wrong or missing |
| door-2 | qty | 1 | - | yes | flagged, wrong or missing |
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
- P1: quantity unclear (raw: '2 doors')
- P1: glass type not written on drawing
- P2: width not written on drawing
- P2: height not written on drawing
- P2: quantity unclear (raw: '2 doors')
- P2: glass type not written on drawing
- P3: quantity not written, assumed 1
- P3: thickness not written on drawing
- P3: glass type not written on drawing

## client-images-17 (05-window-and-door-feet)

19/23 fields right (83%), 19 without a flag; 0 flagged but right; 2 flagged and wrong/missing; **2 wrong and NOT flagged**

- Dimensions: 5/8 right (62%), 0 false CHECK, 1 flagged and wrong/missing, 2 wrong and not flagged
- Holes: 4/4 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 10/11 right (91%), 0 false CHECK, 1 flagged and wrong/missing, 0 wrong and not flagged

Model `claude-sonnet-5-5`, 7977 input / 2717 output tokens. LPO `LPO-20261126-235044`. Panels matched by item, then order within the item (no matching IDs).

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
- Doors overall height unclear (raw: '?feet (first character looks like 7 or 4)')
- Unreadable on drawing: Heading words above each drawing (above the window and above the door) are scribbled or struck out and cannot be read
- P1: thickness not written on drawing
- P1: glass type not written on drawing
- P2: thickness not written on drawing
- P2: glass type not written on drawing
- P3: width not written on drawing
- P3: height not written on drawing
- P3: thickness not written on drawing
- P3: glass type not written on drawing

## client-images-18 (06-oak-double-door)

18/20 fields right (90%), 14 without a flag; 4 flagged but right; 0 flagged and wrong/missing; **2 wrong and NOT flagged**

- Dimensions: 6/6 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 4/4 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 8/10 right (80%), 4 false CHECK, 0 flagged and wrong/missing, 2 wrong and not flagged

Model `claude-sonnet-5-5`, 8009 input / 1829 output tokens. LPO `LPO-20261126-235113`. Panels matched by order (no matching IDs).

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| door-left | qty | 1 | 1 | yes | checked, right value |
| door-left | thickness_mm | 14 | 14 | yes | checked, right value |
| door-left | glass_type | double glazed unit | 14mm Unit | no | WRONG, NOT FLAGGED |
| door-right | qty | 1 | 1 | yes | checked, right value |
| door-right | thickness_mm | 14 | 14 | yes | checked, right value |
| door-right | glass_type | double glazed unit | 14mm Unit | no | WRONG, NOT FLAGGED |

Expected flags (ground truth):
- this is a timber door drawing, not a glass cutting list - the only glass data is '14MM UNIT' x2
- no glass width/height is written - system must mark sizes CHECK, never derive them from the frame drawing
- 1187 O/A and 2050 O/A are overall door frame sizes, not glass sizes - must not be used as glass dimensions
- 14 mm is not a standard thickness - CHECK
- many small annotations (90, 90x70, 170, 700, beads, hinges) are joinery details, not glass data

System flags:
- Unreadable on drawing: Dimension at the top of the door elevation, something like '1701701' with '12' below it
- Unreadable on drawing: Small number below the side section, near 'DRIP'
- P1: width not written on drawing
- P1: height not written on drawing
- P1: quantity not written, assumed 1
- P1: thickness 14 mm is not a standard glass thickness (4, 5, 6, 8, 10, 12, 15, 19)
- P2: width not written on drawing
- P2: height not written on drawing
- P2: quantity not written, assumed 1
- P2: thickness 14 mm is not a standard glass thickness (4, 5, 6, 8, 10, 12, 15, 19)

## client-sd42teinfr7f1 (07-imperial-partition)

36/39 fields right (92%), 31 without a flag; 5 flagged but right; 3 flagged and wrong/missing; **0 wrong and NOT flagged**

- Dimensions: 10/10 right (100%), 1 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 6/8 right (75%), 0 false CHECK, 2 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 20/21 right (95%), 4 false CHECK, 1 flagged and wrong/missing, 0 wrong and not flagged

Model `claude-sonnet-5-5`, 10063 input / 3329 output tokens. LPO `LPO-20261126-235141`. Panels matched by order (no matching IDs).

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| partition screen | overall_width_mm | 2740 | 2740 | yes | checked, right value |
| panel-1 | qty | 1 | 1 | yes | checked, right value |
| panel-2 | qty | 1 | 1 | yes | checked, right value |
| panel-3 | qty | 1 | 1 | yes | checked, right value |
| top-rail | qty | 1 | 1 | yes | checked, right value |
| top-rail | hole_count | 3 | 1 | yes | flagged, wrong or missing |
| top-rail | hole_diameters | [None, None, None] | [None] | yes | flagged, wrong or missing |
| P5 | panel | absent | extra panel | yes | flagged, wrong or missing |

Expected flags (ground truth):
- width in inches with fraction (107 7/8 in = 2740 mm) - system must convert and keep the original
- both heights missing the whole number ('?? 1/4' left, '?? 3/8' right) - CHECK
- individual panel widths not dimensioned - CHECK, do not split 107 7/8 by 3
- hole diameters and positions not written - count only (3), everything else CHECK
- top strip covers panels 2-3 only; may be a rail or clamps, circles may be clamp or hinge points - confirm
- no glass type or quantity stated

System flags:
- Overall width unclear (raw: '107 7/8 (no unit written); unit not written, inches assumed from the fraction')
- Overall height unclear (raw: 'only fractions written beside the height: '1/4' on left side, '3/8' on right side, no whole number or unit')
- P1: width not written on drawing
- P1: height not written on drawing
- P1: quantity not written, assumed 1
- P1: thickness not written on drawing
- P1: glass type not written on drawing
- P2: width not written on drawing
- P2: height not written on drawing
- P2: quantity not written, assumed 1
- P2: thickness not written on drawing
- P2: glass type not written on drawing
- P3: width not written on drawing
- P3: height not written on drawing
- P3: quantity not written, assumed 1
- P3: thickness not written on drawing
- P3: glass type not written on drawing
- P4: width not written on drawing
- P4: height not written on drawing
- P4: quantity not written, assumed 1
- P4: thickness not written on drawing
- P4: glass type not written on drawing
- P4: hole 1 diameter not written on drawing
- P5: width not written on drawing
- P5: height not written on drawing
- P5: quantity not written, assumed 1
- P5: thickness not written on drawing
- P5: glass type not written on drawing
- P5: hole 1 diameter not written on drawing
- P5: hole 2 diameter not written on drawing
