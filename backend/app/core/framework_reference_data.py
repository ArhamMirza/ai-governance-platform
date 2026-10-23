"""Framework control reference data.

Single source of truth for the ISO 42001 / EU AI Act rows that ship with the
product. Consumed by the alembic migration that seeds the framework_controls
table (real deployments) and by tests/conftest.py, which builds its schema
with Base.metadata.create_all and so needs the same rows inserted directly.

ISO_42001_CLAUSES covers the full main-body clause structure (4-10).
ISO_42001_ANNEX_A_CONTROLS covers all 38 Annex A controls -- these are the
rows a Statement of Applicability is built over. EU_AI_ACT_CONTROLS covers
Chapter III (Articles 6-27: classification of high-risk systems, the
requirements they must meet, and the obligations of providers, importers,
distributors and deployers) plus Articles 72 (post-market monitoring) and 73
(serious incident reporting) -- the substantive, organization-facing
obligations a governance program tags its own records against.

It leaves out Chapter III's Sections 4-5 (Articles 28-49). That is right for
the notifying-authority and notified-body articles, but NOT for Articles 43,
47, 48 and 49 (conformity assessment, declaration of conformity, CE marking,
registration), which are duties of providers, nor for Articles 4, 5 and 50,
which fall outside Chapter III. See docs/reference-data-audit.md.
"""

ISO_42001_CLAUSES: list[tuple[str, str, str]] = [
    ("4.1", "Understanding the organization and its context",
     "Determine external and internal issues relevant to the AI management system."),
    ("4.2", "Understanding the needs and expectations of interested parties",
     "Determine the interested parties relevant to the AI management system and their "
     "requirements."),
    ("4.3", "Determining the scope of the AI management system",
     "Determine the boundaries and applicability of the AI management system to establish "
     "its scope."),
    ("4.4", "AI management system",
     "Establish, implement, maintain and continually improve an AI management system."),
    ("5.1", "Leadership and commitment",
     "Top management shall demonstrate leadership and commitment to the AI management system."),
    ("5.2", "AI policy",
     "Establish an AI policy appropriate to the purpose of the organization."),
    ("5.3", "Roles, responsibilities and authorities",
     "Top management shall assign and communicate responsibilities and authorities for "
     "relevant roles."),
    ("6.1", "Actions to address risks and opportunities",
     "Plan actions to address risks and opportunities in the AI management system."),
    ("6.2", "AI objectives and planning to achieve them",
     "Establish AI objectives at relevant functions and levels and plan how to achieve them."),
    ("6.3", "Planning of changes",
     "Determine the need for changes to the AI management system and carry them out in a "
     "planned manner."),
    ("7.1", "Resources",
     "Determine and provide the resources needed for the AI management system."),
    ("7.2", "Competence",
     "Determine the necessary competence of persons doing work under the organization's "
     "control that affects AI system performance."),
    ("7.3", "Awareness",
     "Ensure persons doing work under the organization's control are aware of the AI policy "
     "and their contribution to the AI management system."),
    ("7.4", "Communication",
     "Determine internal and external communications relevant to the AI management system."),
    ("7.5", "Documented information",
     "Maintain documented information required by the AI management system and this "
     "document."),
    ("8.1", "Operational planning and control",
     "Plan, implement and control the processes needed to meet requirements and implement "
     "actions determined in clause 6."),
    ("8.2", "AI risk assessment",
     "Perform AI risk assessments at planned intervals or when significant changes occur."),
    ("8.3", "AI risk treatment",
     "Implement the AI risk treatment plan and retain documented evidence."),
    ("8.4", "AI system impact assessment",
     "Assess the impacts an AI system can have on individuals or groups of individuals, "
     "or both, and society."),
    ("9.1", "Monitoring, measurement, analysis and evaluation",
     "Evaluate the performance and effectiveness of the AI management system."),
    ("9.2", "Internal audit",
     "Conduct internal audits at planned intervals to check conformance of the AI "
     "management system."),
    ("9.3", "Management review",
     "Top management shall review the AI management system at planned intervals to ensure "
     "its continuing suitability."),
    ("10.1", "Continual improvement",
     "Continually improve the suitability, adequacy and effectiveness of the AI management "
     "system."),
    ("10.2", "Nonconformity and corrective action",
     "React to nonconformities and take action to control and correct them."),
]

ISO_42001_ANNEX_A_CONTROLS: list[tuple[str, str, str]] = [
    ("A.2.2", "AI policy",
     "Policies for the development, provision or use of AI systems shall be defined and "
     "approved by management."),
    ("A.2.3", "Alignment with other organizational policies",
     "The AI policy shall be aligned with other relevant organizational policies."),
    ("A.2.4", "Review of the AI policy",
     "The AI policy shall be reviewed at planned intervals or when significant changes occur."),
    ("A.3.2", "AI roles and responsibilities",
     "Roles and responsibilities relevant to AI risk management shall be defined and "
     "allocated according to organizational needs."),
    ("A.3.3", "Reporting of concerns",
     "A process shall be established for reporting concerns about the organization's role "
     "with respect to an AI system throughout its life cycle."),
    ("A.4.2", "Resource documentation",
     "Resources necessary for the AI system's life cycle stages shall be documented."),
    ("A.4.3", "Data resources",
     "Documentation of data resources used in developing and operating AI systems shall be "
     "maintained."),
    ("A.4.4", "Tooling resources",
     "Documentation of tooling resources used in developing and operating AI systems shall "
     "be maintained."),
    ("A.4.5", "System and computing resources",
     "Documentation of system and computing resources used in developing and operating AI "
     "systems shall be maintained."),
    ("A.4.6", "Human resources",
     "Documentation of the competencies and capabilities of personnel involved in the AI "
     "system's life cycle shall be maintained."),
    ("A.5.2", "AI system impact assessment process",
     "A process for assessing the impacts of an AI system over its life cycle shall be "
     "defined."),
    ("A.5.3", "Documentation of AI system impact assessments",
     "Documented information from AI system impact assessments shall be retained."),
    ("A.5.4", "Assessing AI system impact on individuals or groups of individuals",
     "Impacts of the AI system on individuals or groups of individuals shall be assessed."),
    ("A.5.5", "Assessing societal impacts of AI systems",
     "Impacts of the AI system on society shall be assessed."),
    ("A.6.1.2", "Objectives for responsible development of AI system",
     "Objectives for the responsible development of AI systems shall be defined."),
    ("A.6.1.3", "Processes for responsible design and development of AI systems",
     "Processes for the responsible design and development of AI systems shall be defined "
     "and applied."),
    ("A.6.2.2", "AI system requirements and specification",
     "Requirements and specifications for the AI system shall be determined and documented."),
    ("A.6.2.3", "Documentation of AI system design and development",
     "Documentation of the AI system's design and development shall be maintained."),
    ("A.6.2.4", "AI system verification and validation",
     "Verification and validation measures for the AI system shall be defined and applied."),
    ("A.6.2.5", "AI system deployment",
     "A process for the controlled deployment of AI systems shall be defined."),
    ("A.6.2.6", "AI system operation and monitoring",
     "Processes for operating and monitoring the AI system shall be defined and applied."),
    ("A.6.2.7", "AI system technical documentation",
     "Technical documentation describing the AI system's characteristics shall be maintained."),
    ("A.6.2.8", "AI system recording of event logs",
     "Event logs enabling the AI system's operation to be reconstructed shall be recorded and "
     "retained."),
    ("A.7.2", "Data for development and enhancement of AI system",
     "Requirements for data used in developing and enhancing the AI system shall be defined."),
    ("A.7.3", "Acquisition of data",
     "Data acquisition for the AI system shall be documented, including its origin."),
    ("A.7.4", "Quality of data for AI systems",
     "Requirements for the quality of data used by the AI system shall be defined and applied."),
    ("A.7.5", "Data provenance",
     "Documentation of the provenance of data used by the AI system shall be maintained."),
    ("A.7.6", "Data preparation",
     "Data preparation activities, including labelling and cleaning, shall be documented."),
    ("A.8.2", "System documentation and information for users",
     "Documentation and information necessary for users of the AI system shall be provided."),
    ("A.8.3", "External reporting",
     "A process for external reporting of information related to the AI system shall be "
     "defined."),
    ("A.8.4", "Communication of incidents",
     "A process for communicating incidents related to the AI system to relevant interested "
     "parties shall be defined."),
    ("A.8.5", "Information for interested parties",
     "Information about the AI system shall be made available to relevant interested "
     "parties."),
    ("A.9.2", "Processes for responsible use of AI systems",
     "Processes for the responsible use of AI systems shall be defined and applied."),
    ("A.9.3", "Objectives for responsible use of AI system",
     "Objectives for the responsible use of AI systems shall be defined."),
    ("A.9.4", "Intended use of the AI system",
     "The intended use of the AI system shall be documented and communicated."),
    ("A.10.2", "Allocation of responsibilities",
     "Responsibilities between the organization and third parties involved in the AI "
     "system's life cycle shall be allocated and documented."),
    ("A.10.3", "Suppliers",
     "Requirements for suppliers involved in the AI system's life cycle shall be defined."),
    ("A.10.4", "Customers",
     "Relevant information about the AI system shall be provided to customers."),
]

EU_AI_ACT_CONTROLS: list[tuple[str, str, str]] = [
    ("Art.6", "Classification rules for high-risk AI systems",
     "An AI system is high-risk if it is a safety component of a product requiring "
     "third-party conformity assessment under EU law, or if it falls within a use "
     "case listed in Annex III and is not exempted."),
    ("Art.7", "Amendments to Annex III",
     "The European Commission may add, modify or remove high-risk use cases in Annex "
     "III based on the risk of harm to health, safety or fundamental rights they pose."),
    ("Art.8", "Compliance with the requirements",
     "A high-risk AI system shall meet the requirements of this Section, taking into "
     "account its intended purpose and the generally acknowledged state of the art."),
    ("Art.9", "Risk management system",
     "Establish, implement, document and maintain a risk management system for "
     "high-risk AI systems."),
    ("Art.10", "Data and data governance",
     "Training, validation and testing data sets shall be subject to appropriate "
     "data governance practices."),
    ("Art.11", "Technical documentation",
     "Technical documentation shall be drawn up before a high-risk AI system is "
     "placed on the market."),
    ("Art.12", "Record-keeping",
     "A high-risk AI system shall technically allow for the automatic recording of "
     "events (logs) over its lifetime, to enable an appropriate level of traceability."),
    ("Art.13", "Transparency and provision of information to deployers",
     "High-risk AI systems shall be designed to ensure their operation is "
     "sufficiently transparent."),
    ("Art.14", "Human oversight",
     "High-risk AI systems shall be designed to be effectively overseen by "
     "natural persons."),
    ("Art.15", "Accuracy, robustness and cybersecurity",
     "High-risk AI systems shall be designed to achieve an appropriate level of "
     "accuracy, robustness and cybersecurity."),
    ("Art.16", "Obligations of providers of high-risk AI systems",
     "Providers shall ensure their high-risk AI system complies with the requirements "
     "of this Section, and shall have a quality management system, keep documentation, "
     "undergo conformity assessment and affix the CE marking."),
    ("Art.17", "Quality management system",
     "Providers of high-risk AI systems shall put a quality management system in place."),
    ("Art.18", "Documentation keeping",
     "Providers shall keep technical documentation, quality management system records "
     "and conformity assessment documentation for ten years after the AI system is "
     "placed on the market."),
    ("Art.19", "Automatically generated logs",
     "Providers shall keep the logs automatically generated by the high-risk AI system "
     "for a period appropriate to its intended purpose, at least six months unless "
     "other law requires longer."),
    ("Art.20", "Corrective actions and duty of information",
     "A provider that becomes aware a high-risk AI system is non-compliant shall "
     "immediately take corrective action -- or withdraw, disable or recall it -- and "
     "inform distributors, deployers, importers and the relevant authorities."),
    ("Art.21", "Cooperation with competent authorities",
     "Providers shall, on a reasoned request, give a competent authority all the "
     "information and documentation needed to demonstrate the AI system's conformity."),
    ("Art.22", "Authorised representatives of providers of high-risk AI systems",
     "A provider established outside the EU shall appoint an authorised representative "
     "in the Union to carry out compliance tasks on its behalf."),
    ("Art.23", "Obligations of importers",
     "An importer shall verify that a high-risk AI system's conformity assessment and "
     "documentation are in order before placing it on the market, and shall cooperate "
     "with authorities."),
    ("Art.24", "Obligations of distributors",
     "A distributor shall verify that a high-risk AI system bears the required CE "
     "marking and documentation before making it available, and shall report any "
     "non-compliance."),
    ("Art.25", "Responsibilities along the AI value chain",
     "A distributor, importer, deployer or other third party is considered a provider, "
     "and takes on a provider's obligations, if it puts its own name on a high-risk AI "
     "system or makes a substantial modification to it."),
    ("Art.26", "Obligations of deployers of high-risk AI systems",
     "A deployer shall use a high-risk AI system according to its instructions, assign "
     "competent human oversight, monitor its operation, and report any serious incident."),
    ("Art.27", "Fundamental rights impact assessment for high-risk AI systems",
     "Certain deployers shall assess a high-risk AI system's impact on fundamental "
     "rights before putting it into use, and notify the market surveillance authority "
     "of the outcome."),
    ("Art.72", "Post-market monitoring by providers",
     "Providers shall establish a post-market monitoring system proportionate to "
     "the risks of the AI system, and use it to evaluate the system's continuing "
     "compliance."),
    ("Art.73", "Reporting of serious incidents",
     "Providers of high-risk AI systems shall report any serious incident to the market "
     "surveillance authority within 15 days of becoming aware of it -- within 10 days of "
     "a death, and within 2 days of a widespread infringement or serious and "
     "irreversible disruption of critical infrastructure."),
]


def as_rows() -> list[dict[str, str]]:
    return [
        {
            "framework": "iso_42001",
            "code": code,
            "title": title,
            "description": description,
            "category": "clause",
        }
        for code, title, description in ISO_42001_CLAUSES
    ] + [
        {
            "framework": "iso_42001",
            "code": code,
            "title": title,
            "description": description,
            "category": "annex_a_control",
        }
        for code, title, description in ISO_42001_ANNEX_A_CONTROLS
    ] + [
        {
            "framework": "eu_ai_act",
            "code": code,
            "title": title,
            "description": description,
            "category": "clause",
        }
        for code, title, description in EU_AI_ACT_CONTROLS
    ]
