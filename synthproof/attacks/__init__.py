"""Empirical adversarial evaluation suite.

Run on every release (`frontier.experiment.run_cell`):
  - DistanceMIABaseline     (attacks/distance_mia.py)       nearest-neighbour MIA baseline
  - DOMIAS                  (attacks/domias.py)             density-ratio MIA
  - ExactMatchRiskEvaluator (attacks/exact_match_risk.py)   singling out
  - LinkabilityEvaluator    (attacks/linkability.py)        linkability
  - AttributeInferenceAttack (attacks/attribute_inference.py) inference vs a conditional baseline

Offline audit of a mechanism configuration (too costly per release):
  - LiRAAttack              (attacks/lira.py)               Carlini et al. (2022) with shadow
                                                            releases; scripts/run_lira.py

This docstring once listed LiRA, DOMIAS and attribute inference as implemented when none were
(brutal_project_audit.md, Tier 2 item 17); every name above now resolves to running code.
"""
