# Reference data audit: ISO/IEC 42001 and the EU AI Act

*Drafted 24 October 2026. A first-pass audit for review, not legal advice, and not a
substitute for an expert's reading.*

The platform ships the structure of two frameworks as data
(`backend/app/core/framework_reference_data.py`, rules in
`backend/app/core/eu_ai_act_scope.py`). Every compliance number the product shows rests on
it, so this checks it against the standards.

## How this was done, and what it cannot tell you

- **ISO/IEC 42001:2023** is a paid standard. This audit compared clause and control
  *numbers and titles* against what the author knows of the published structure. It did not
  have the full text open, so it cannot judge the wording of the one-line descriptions
  against the standard's.
- **EU AI Act (Regulation (EU) 2024/1689)** article numbers and titles were compared with
  the author's knowledge of the Regulation; application dates were checked against public
  law-firm summaries (linked at the end), which disagree in places.
- The author is an AI model and could be wrong on any point. **Everything below should be
  checked by someone who knows the Act and the standard before it is relied on.** Items
  that most need that are marked ⚑.

## Summary

| # | Finding | Severity |
|---|---|---|
| E1 | The EU AI Act list leaves out articles that apply to ordinary organizations: **Art. 4** (AI literacy), **Art. 5** (prohibited practices), **Art. 50** (transparency) | High |
| E2 | It also leaves out the **provider** obligations in Art. 43, 47, 48 and 49 (conformity assessment, declaration of conformity, CE marking, registration). A code comment says these are obligations on authorities and certification bodies; that is wrong for those four | High |
| E3 | Art. 86 (a person's right to an explanation of a decision made with a high-risk system) is not covered, and it is an obligation on deployers | Medium |
| E4 | Art. 25's description omits one of its three triggers | Medium |
| E5 | Art. 7 is a power of the Commission, not an obligation of an organization, so it can never be "covered" and inflates the uncovered count | Medium |
| E6 | Applicability dates are not recorded, and they have moved (see below) | Medium |
| I1 | A few ISO descriptions sit close to the standard's own wording | Medium ⚑ |
| I2 | No notice that the standard's text is not included | Medium |
| I3 | `DESIGN.md` §12 omitted Annex A.4 from its mapping table (the controls themselves are present) | Low |
| C1 | Stale comments in the data file (counts and scope rationale) | Low |

Everything else checked matched. The ISO clause structure (24 clauses) and **all 38**
Annex A controls have the right numbers and titles, and the 22 articles from Art. 6 to 27,
plus Art. 72 and 73, have the right numbers and titles.

## Part 1: ISO/IEC 42001 main clauses (24)

Clauses 4.1 to 4.4, 5.1 to 5.3, 6.1 to 6.3, 7.1 to 7.5, 8.1 to 8.4, 9.1 to 9.3, 10.1 and
10.2 are all present with the standard's titles.

- The standard splits some clauses further (6.1.2 to 6.1.4, 9.2.1/9.2.2, 9.3.1 to 9.3.3).
  Treating them as one control each is a sensible simplification, and 8.2 to 8.4 carry the
  risk and impact assessment items.
- **I1 ⚑.** Clause 5.1 ("Top management shall demonstrate leadership and commitment...")
  and 9.3 ("Top management shall review the AI management system at planned intervals...")
  read close to the standard's wording, which follows the common ISO management-system
  boilerplate. Short generic phrases like these are routinely quoted, but the safe course is
  to reword every description that uses the standard's "shall" sentence in plain, original
  language.
- **I2.** Add a plain notice to the README and the in-app handbook: *this platform does not
  contain the text of ISO/IEC 42001; clause and control numbers and short titles are
  referenced to help you organise your records; buy the standard.*

## Part 2: Annex A controls (38)

All of A.2 (3), A.3 (2), A.4 (5), A.5 (4), A.6 (9), A.7 (5), A.8 (4), A.9 (3) and A.10 (3)
are present, with the standard's titles. The one-line descriptions are paraphrases in the
"shall be defined..." style; reviewing them for closeness to the standard falls under I1.

- **I3.** The design document's mapping table (§12) listed no feature for A.4 (resources for
  AI systems), though the controls exist. The AI system inventory and data inventory are the
  natural places to tag; the table now says so.

## Part 3: EU AI Act articles tracked (24)

Present and correctly titled: **Art. 6 to 27** (Chapter III, Sections 1 to 3), **Art. 72**
and **Art. 73**. Descriptions checked: the 10-year retention in Art. 18, the six-month log
minimum in Art. 19, and the 15/10/2-day serious-incident deadlines in Art. 73 are right.

### Descriptions to fix

- **E4. Art. 25** names two triggers (putting your name on a system, a substantial
  modification). The Regulation has a third: **changing the intended purpose of a system not
  classed as high-risk so that it becomes high-risk**. That third case matters to
  organizations that repurpose a general tool, so it is the one most worth stating.
- **E5. Art. 7** lets the Commission amend Annex III. It places no duty on an organization,
  so nothing can be tagged to it as evidence. Either remove it or mark it informational and
  exclude it from coverage.
- Art. 72's full title is "Post-market monitoring by providers and post-market monitoring
  plan for high-risk AI systems"; the shortened title is fine but loses the *plan*.

### Missing articles

| Article | What it requires | Who | Why include it |
|---|---|---|---|
| **4** | Ensure a sufficient level of **AI literacy** among staff using AI | Providers and deployers of *any* AI system | Applies since 2 Feb 2025. The competence feature already supports it; there is no control to tag it to |
| **5** | Do not use **prohibited practices** (for example manipulative techniques, social scoring, some biometric uses) | Everyone | Applies since 2 Feb 2025 and is the most basic check an organization can record |
| **50** | **Transparency**: tell people they are dealing with an AI, label synthetic content, disclose emotion recognition and deepfakes | Providers and deployers of certain systems (not only high-risk) | Very relevant to deployers using chatbots or generative AI. Not tied to high-risk status |
| **43** | **Conformity assessment** before placing a high-risk system on the market | Providers | A core provider duty |
| **47** | EU **declaration of conformity** | Providers | As above |
| **48** | **CE marking** | Providers | As above |
| **49** | **Registration** in the EU database (Art. 49(3) for certain public-sector deployers) | Providers; some deployers | As above |
| **86** | **Right to explanation** of an individual decision made with an Annex III system | Deployers | An obligation that people can enforce |
| 53, 55 | Obligations of providers of **general-purpose AI models** (technical documentation, copyright policy, training-content summary; systemic-risk duties) | GPAI model providers | Optional, only if you expect model providers as users |

- **E2 ⚑.** The data file's comment says Chapter III's Sections 4 and 5 (Art. 28 to 49) are
  "obligations on regulators and certification bodies". That is accurate for Section 4
  (notifying authorities) and for parts of Section 5, but **Art. 43, 47, 48 and 49 are
  duties of providers**, so the exclusion is wrong for them. (The comment also still says
  Art. 6 to 27 plus 72 and omits 73, which is included.)
- Art. 40 to 42 and 44 to 46 (standards, certificates, notified-body information) are mostly
  about authorities and certification bodies and are reasonably left out.

### Applicability rules (`eu_ai_act_scope.py`)

Checked each rule against the article it governs:

- Art. 6 and 7: apply to everyone in scope. ✓ (but see E5)
- Art. 8 to 22: providers of high-risk systems. ✓ Art. 22 (authorised representatives)
  applies to providers established outside the EU; the authorised representative's own role
  is not modelled.
- Art. 23 importers, 24 distributors, 25 importers/distributors/deployers, 26 and 27
  deployers, 72 and 73 providers: ✓. The note that deployers report serious incidents under
  Art. 26(5) is correct.
- **New articles will need rules.** Art. 4 and 5 apply to every organization in scope, not
  only to high-risk work. Art. 50 depends on the *type* of system (interacts with people,
  generates content), not on high-risk status, so it needs a different test from the
  current "has high-risk systems" flag.

### E6. Dates

The platform does not record when each article applies, and the dates have moved:

- Art. 4 and 5 have applied since **2 February 2025**.
- Reports say the **AI Omnibus** (Regulation (EU) 2026/1744, published in the Official
  Journal around 24 July 2026) moved the high-risk obligations to **2 December 2027** for
  Annex III systems and **2 August 2028** for those embedded in regulated products, while
  Art. 50 transparency and general-purpose model duties were not deferred. Sources disagree
  on some dates, so ⚑ **verify against the Official Journal**.
- Showing an application date next to each article would let users see what is already
  binding.

## Proposed changes (not yet applied)

None of these has been made; the seeded rows are the product's data and should change only
after review. Because they are seeded by migrations, a fix needs a **data migration** that
updates rows by code (keeping row ids, so existing tags survive) and inserts new ones.

1. **Add** Art. 4, 5, 43, 47, 48, 49, 50, 86 with applicability rules (E1 to E3). Art. 53 and
   55 optionally.
2. **Correct** Art. 25's description, and decide on Art. 7 (E4, E5).
3. **Add an application date** to each EU article and show it (E6).
4. **Reword** descriptions that sit close to the standard's text, and add the notice (I1, I2).
5. After 1 to 4, **re-check** the dashboard counts, the compliance view and the AI-assistant
   drafts, which read these rows.

## Questions for a reviewer

- Is the list of articles right for an organization that mostly *deploys* AI? For one that
  *provides* it?
- Is it right to omit Art. 53 and 55 and Annex-level items such as Annex IV (technical
  documentation contents)?
- Is the treatment of Art. 27 (fundamental rights impact assessment) accurate about *which*
  deployers must do it?
- Are the one-line ISO descriptions original enough to ship under Apache 2.0?
- Do the application dates above match the Official Journal text of the Omnibus?

## Sources

- [AI Omnibus: deferral of high-risk obligations (DLA Piper)](https://knowledge.dlapiper.com/dlapiperknowledge/globalemploymentlatestdevelopments/2026/The-Digital-AI-Omnibus-Proposed-deferral-of-high-risk-AI-obligations-under-the-AI-Act)
- [EU AI Omnibus formally adopted (Addleshaw Goddard)](https://www.addleshawgoddard.com/en/insights/insights-briefings/2026/technology/eu-ai-act-ai-omnibus-formally-adopted/)
- [Digital Omnibus on AI enters into force (National Law Review)](https://natlawreview.com/article/eu-digital-omnibus-ai-enters-force)
- [Upcoming EU AI Act obligations: mandatory training and prohibited practices (Latham & Watkins)](https://www.lw.com/en/insights/2025/01/upcoming-eu-ai-act-obligations-mandatory-training-and-prohibited-practices)
- The Regulation itself: Regulation (EU) 2024/1689 on EUR-Lex (the authoritative text).
