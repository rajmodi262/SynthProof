"""Empirical adversarial evaluation suite.

Implemented:
  - DistanceMIABaseline  (attacks/distance_mia.py)     weak nearest-neighbour MIA
  - ExactMatchRiskEvaluator (attacks/exact_match_risk.py) exact-match singling-out

NOT implemented (previously claimed in the README and this docstring):
  - LiRA (Carlini et al. 2022) with shadow models
  - DOMIAS density-ratio MIA
  - Attribute inference / reconstruction

See brutal_project_audit.md, Tier 2 item 17.
"""
