---
name: xauusd-structure
description: Read deterministic structure on gold before any proposal.
triggers:
  - structure
  - fvg
  - gold
permissions:
  - market.read
params:
  symbol: XAUUSD
---

Use the snapshot from the analysis tools. Cite swing, fair-value gap, and sweep marks that are actually present. Do not draw levels the detector did not return.
