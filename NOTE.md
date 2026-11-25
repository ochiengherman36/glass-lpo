# Note: Glass Drawing to LPO (SDA-FP-TRIAL-2026-02)

**Accuracy** (Claude Sonnet 5.5, scored against ground truth written before scoring; details in `test_drawings/EVALUATION.md`)

| Drawing | Fields right | Wrong and not flagged | Flagged for a human |
|---|---|---|---|
| Simple | 12/12 | 0 | none |
| Realistic | 47/47 | 0 | none |
| Hard | 20/20 | 0 | qty, thickness, glass type (not written, correctly flagged) |

An earlier, messier set of photos scored 76/79 with **0 wrong values unflagged**: the 3 misses were unclear
handwriting marked CHECK. One prompt fix cut the hard drawing's check list from 13 items to 8.

**Assumptions**
- Millimetres unless stated; "Ø25", "Q25" or "O25" by a circle is a 25 mm hole.
- Notes like "ALL PANELS H=2100, QTY 1 EACH" apply to every panel; one height drawn beside a row of panels applies to each.
- Missing quantity is assumed 1 and flagged; missing thickness or glass type is CHECK; missing edge work or hole positions is not flagged.
- Hole positions are measured from the panel's bottom-left corner. Panels 50–3,300 mm; standard thicknesses 4–19 mm.
- Before scoring, undimensioned hole positions in the ground truth were set to null. The final hard drawing is cleaner than
  "messy, angled, poor light"; results on the original messy photo are in the git history.

**Questions for a site visit**
- Can we have 20–50 real WhatsApp drawings with the LPOs actually cut from them?
- Which corner are hole positions measured from, and how are notches, offcuts and "TYP" usually written?
- What is the ERP import format, LPO numbering and product code for each glass type, thickness and edge finish?
- Who checks flagged items today, and how fast must a quote go out?
- Typical sheet sizes, tolerances and minimum hole-to-edge distances?

**Path to production**
1. Collect a few hundred real drawings with their final LPOs as ground truth; run `scripts/evaluate.py` on them.
2. Tune the prompt and rules, and compare models on cost against wrong-but-unflagged values.
3. Add a review screen where sales admin confirms CHECK cells; save every correction as new ground truth.
4. Export in the client's ERP format, add pricing, take photos straight from WhatsApp, and add login, storage and monitoring.

**Cost and time:** about KES 4–8 and 30 seconds per drawing. Time spent: **3.5 hours**.