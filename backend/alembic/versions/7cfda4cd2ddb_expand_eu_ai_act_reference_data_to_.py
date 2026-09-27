"""expand eu ai act reference data to chapter III

Revision ID: 7cfda4cd2ddb
Revises: d47ed6a7e667
Create Date: 2026-09-27 13:23:48.861133

Grows EU_AI_ACT_CONTROLS from 8 representative articles to the full
substantive obligations of Chapter III (Articles 6-27: classification,
requirements, and provider/importer/distributor/deployer obligations) plus
Article 72 (post-market monitoring) -- see app.core.framework_reference_data
for what's deliberately still excluded (Sections 4-5, notified-body and
conformity-assessment infrastructure).

Also corrects a mislabeled row from the original partial seed (migration
9b2f0633a014): post-market monitoring is Article 72 in the final
Regulation (EU) 2024/1689, not Article 61 as first seeded. Matched and
renamed by its old code rather than re-inserted, so any existing tag
pointing at that control's id keeps pointing at it.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.framework_reference_data import EU_AI_ACT_CONTROLS

# revision identifiers, used by Alembic.
revision: str = '7cfda4cd2ddb'
down_revision: str | Sequence[str] | None = 'd47ed6a7e667'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Codes already present from the original partial EU AI Act seed
# (migration 9b2f0633a014) -- these get their title/description brought up
# to the canonical text rather than re-inserted.
_EXISTING_CODES = {"Art.9", "Art.10", "Art.11", "Art.13", "Art.14", "Art.15", "Art.17"}

_OLD_POST_MARKET_MONITORING_CODE = "Art.61"
_OLD_POST_MARKET_MONITORING_TITLE = "Post-market monitoring by providers"
_OLD_POST_MARKET_MONITORING_DESCRIPTION = (
    "Providers shall establish a post-market monitoring system proportionate to "
    "the risks of the AI system."
)


def _framework_controls_table() -> sa.Table:
    return sa.table(
        'framework_controls',
        sa.column('framework', sa.String),
        sa.column('code', sa.String),
        sa.column('title', sa.String),
        sa.column('description', sa.Text),
        sa.column('category', sa.String),
    )


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    framework_controls_table = _framework_controls_table()

    # Article 72 was first seeded under the wrong article number -- rename in
    # place so the row (and anything already tagged to it) is preserved.
    conn.execute(
        framework_controls_table.update()
        .where(framework_controls_table.c.framework == "eu_ai_act")
        .where(framework_controls_table.c.code == _OLD_POST_MARKET_MONITORING_CODE)
        .values(code="Art.72")
    )

    for code, title, description in EU_AI_ACT_CONTROLS:
        if code in _EXISTING_CODES or code == "Art.72":
            conn.execute(
                framework_controls_table.update()
                .where(framework_controls_table.c.framework == "eu_ai_act")
                .where(framework_controls_table.c.code == code)
                .values(title=title, description=description, category="clause")
            )

    new_rows = [
        {
            "framework": "eu_ai_act",
            "code": code,
            "title": title,
            "description": description,
            "category": "clause",
        }
        for code, title, description in EU_AI_ACT_CONTROLS
        if code not in _EXISTING_CODES and code != "Art.72"
    ]
    if new_rows:
        op.bulk_insert(framework_controls_table, new_rows)


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    framework_controls_table = _framework_controls_table()

    new_codes = [
        code
        for code, _, _ in EU_AI_ACT_CONTROLS
        if code not in _EXISTING_CODES and code != "Art.72"
    ]
    conn.execute(
        sa.delete(framework_controls_table)
        .where(framework_controls_table.c.framework == "eu_ai_act")
        .where(framework_controls_table.c.code.in_(new_codes))
    )

    conn.execute(
        framework_controls_table.update()
        .where(framework_controls_table.c.framework == "eu_ai_act")
        .where(framework_controls_table.c.code == "Art.72")
        .values(
            code=_OLD_POST_MARKET_MONITORING_CODE,
            title=_OLD_POST_MARKET_MONITORING_TITLE,
            description=_OLD_POST_MARKET_MONITORING_DESCRIPTION,
        )
    )
