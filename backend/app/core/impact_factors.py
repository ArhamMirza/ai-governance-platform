"""The eight impact dimensions ISO/IEC 42005 uses to categorize an AI
system's effects on individuals, groups, and society. Single source of
truth for the "Identified Impacts" sheet's impact_factor select options."""

IMPACT_FACTORS: list[str] = [
    "Accountability",
    "Explainability",
    "Transparency",
    "Fairness",
    "Environmental Impact",
    "Reliability",
    "Privacy",
    "Safety",
]
