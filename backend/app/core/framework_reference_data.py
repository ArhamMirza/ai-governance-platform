"""Framework control reference data.

Single source of truth for the ISO 42001 / EU AI Act rows that ship with the
product. Consumed by the alembic migration that seeds the framework_controls
table (real deployments) and by tests/conftest.py, which builds its schema
with Base.metadata.create_all and so needs the same rows inserted directly.

A representative subset of clauses/articles orgs commonly tag work against,
not the full text of either standard.
"""

ISO_42001_CONTROLS: list[tuple[str, str, str]] = [
    ("4.1", "Understanding the organization and its context",
     "Determine external and internal issues relevant to the AI management system."),
    ("5.2", "AI policy",
     "Establish an AI policy appropriate to the purpose of the organization."),
    ("6.1", "Actions to address risks and opportunities",
     "Plan actions to address risks and opportunities in the AI management system."),
    ("6.2", "AI risk assessment",
     "Define and apply an AI risk assessment process."),
    ("8.2", "AI risk assessment (operational)",
     "Perform AI risk assessments at planned intervals."),
    ("8.3", "AI risk treatment",
     "Implement the AI risk treatment plan and retain documented evidence."),
    ("8.4", "AI system impact assessment",
     "Assess the impacts an AI system can have on individuals or groups of individuals, "
     "or both, and society."),
    ("9.1", "Monitoring, measurement, analysis and evaluation",
     "Evaluate the performance and effectiveness of the AI management system."),
    ("10.2", "Nonconformity and corrective action",
     "React to nonconformities and take action to control and correct them."),
]

EU_AI_ACT_CONTROLS: list[tuple[str, str, str]] = [
    ("Art.9", "Risk management system",
     "Establish, implement, document and maintain a risk management system for "
     "high-risk AI systems."),
    ("Art.10", "Data and data governance",
     "Training, validation and testing data sets shall be subject to appropriate "
     "data governance practices."),
    ("Art.11", "Technical documentation",
     "Technical documentation shall be drawn up before a high-risk AI system is "
     "placed on the market."),
    ("Art.13", "Transparency and provision of information to deployers",
     "High-risk AI systems shall be designed to ensure their operation is "
     "sufficiently transparent."),
    ("Art.14", "Human oversight",
     "High-risk AI systems shall be designed to be effectively overseen by "
     "natural persons."),
    ("Art.15", "Accuracy, robustness and cybersecurity",
     "High-risk AI systems shall be designed to achieve an appropriate level of "
     "accuracy, robustness and cybersecurity."),
    ("Art.17", "Quality management system",
     "Providers of high-risk AI systems shall put a quality management system in place."),
    ("Art.61", "Post-market monitoring by providers",
     "Providers shall establish a post-market monitoring system proportionate to "
     "the risks of the AI system."),
]


def as_rows() -> list[dict[str, str]]:
    return [
        {"framework": "iso_42001", "code": code, "title": title, "description": description}
        for code, title, description in ISO_42001_CONTROLS
    ] + [
        {"framework": "eu_ai_act", "code": code, "title": title, "description": description}
        for code, title, description in EU_AI_ACT_CONTROLS
    ]
