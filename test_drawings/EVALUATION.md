# Accuracy against ground truth

**All drawings:** 79/79 fields right (100%), 77 without a flag; 2 flagged but right; 0 flagged and wrong/missing; **0 wrong and NOT flagged**

- Dimensions: 22/22 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 17/17 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 40/40 right (100%), 2 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged

A false CHECK is a value the system read correctly but still asked a person to confirm.

## hard (03-hard)

20/20 fields right (100%), 18 without a flag; 2 flagged but right; 0 flagged and wrong/missing; **0 wrong and NOT flagged**

- Dimensions: 6/6 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 4/4 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 10/10 right (100%), 2 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged

Model `claude-sonnet-5-5`, 7524 input / 1657 output tokens. LPO `LPO-20261125-155711`. Panels matched by panel ID.

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| P1 | qty | 1 | 1 | yes | checked, right value |
| P2 | qty | 1 | 1 | yes | checked, right value |

Expected flags (ground truth):
- qty is not written on the drawing - system may assume 1 but must flag it
- thickness_mm is not written on the drawing - system must mark CHECK, not guess
- glass_type is not written on the drawing - system must mark CHECK, not guess

System flags:
- P1: quantity not written, assumed 1
- P1: thickness not written on drawing
- P1: glass type not written on drawing
- P2: quantity not written, assumed 1
- P2: thickness not written on drawing
- P2: glass type not written on drawing

## realistic (02-realistic)

47/47 fields right (100%), 47 without a flag; 0 flagged but right; 0 flagged and wrong/missing; **0 wrong and NOT flagged**

- Dimensions: 12/12 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 10/10 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 25/25 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged

Model `claude-sonnet-5-5`, 7547 input / 4335 output tokens. LPO `LPO-20261125-155703`. Panels matched by panel ID.

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| - | - | - | - | - | every field correct |

Expected flags (ground truth):
- none

System flags:
- none

## simple (01-simple)

12/12 fields right (100%), 12 without a flag; 0 flagged but right; 0 flagged and wrong/missing; **0 wrong and NOT flagged**

- Dimensions: 4/4 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Holes: 3/3 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged
- Other fields: 5/5 right (100%), 0 false CHECK, 0 flagged and wrong/missing, 0 wrong and not flagged

Model `claude-sonnet-5-5`, 7396 input / 1385 output tokens. LPO `LPO-20261125-155654`. Panels matched by panel ID.

| Panel | Field | Expected | Got | Flagged | Outcome |
|---|---|---|---|---|---|
| - | - | - | - | - | every field correct |

Expected flags (ground truth):
- none

System flags:
- none
