"""Noticing that a record changed, wherever in the app it changed.

Records are edited from a dozen services and will be edited from more. If
keeping the search index current meant remembering to call something after
each write, it would be correct on the day it was written and wrong within a
month -- and the failure would be silent, because a stale index looks
exactly like a fresh one until someone searches for the thing that changed.

So this listens to the session instead. Anything that flushes a change to an
indexed record queues that record for reindexing, in the same transaction as
the change itself. A future service cannot forget, because there is nothing
for it to remember.

Only the queue row is written here. The rendering and embedding happen later
(see ``document_index_service.drain``), because a sheet import writes
hundreds of rows in one transaction and none of them should wait on an
embedding model.
"""

from sqlalchemy import event, insert, select
from sqlalchemy.orm import Session

from app.models.data_inventory_record import DataInventoryRecord
from app.models.document_chunk import SourceType
from app.models.impact_assessment import ImpactAssessment
from app.models.impact_factor_assessment import ImpactFactorAssessment
from app.models.index_queue import IndexQueueEntry
from app.models.policy import Policy
from app.models.procedure import Procedure
from app.models.sheet import Sheet, SheetRow

# Which sheet a row belongs to decides what kind of record it is.
_SOURCE_FOR_SHEET = {
    "AISystemInventory": SourceType.AI_SYSTEM,
    "DataInventory": SourceType.DATA_INVENTORY,
    "RiskAssessment": SourceType.RISK_ITEM,
}


def _sheet_kinds(session: Session, sheet_ids: set[int]) -> dict[int, str]:
    """Which kind of record each sheet holds, in one query.

    Looked up in a batch because a sheet import flushes hundreds of rows at
    once, and asking per row would put hundreds of queries inside a single
    flush to learn the same two or three answers.
    """
    if not sheet_ids:
        return {}
    rows = session.execute(
        select(Sheet.id, Sheet.entity_type).where(Sheet.id.in_(sheet_ids))
    ).all()
    return {sheet_id: str(entity_type) for sheet_id, entity_type in rows}


def _source_of(
    instance: object, sheet_kinds: dict[int, str]
) -> tuple[str, int] | None:
    """The record whose index this object's change invalidates.

    Not always the object itself: a factor score belongs to its impact
    assessment, and a data inventory approval belongs to its row, because
    those are the records a person searches for and cites.
    """
    if isinstance(instance, Policy):
        return (SourceType.POLICY, instance.id)
    if isinstance(instance, Procedure):
        return (SourceType.PROCEDURE, instance.id)
    if isinstance(instance, ImpactAssessment):
        return (SourceType.IMPACT_ASSESSMENT, instance.id)
    if isinstance(instance, ImpactFactorAssessment):
        return (SourceType.IMPACT_ASSESSMENT, instance.impact_assessment_id)
    if isinstance(instance, DataInventoryRecord):
        return (SourceType.DATA_INVENTORY, instance.data_inventory_row_id)
    if isinstance(instance, SheetRow):
        source_type = _SOURCE_FOR_SHEET.get(sheet_kinds.get(instance.sheet_id, ""))
        return (source_type, instance.id) if source_type else None
    return None


@event.listens_for(Session, "after_flush")
def _queue_changed_records(session: Session, _flush_context) -> None:  # noqa: ANN001
    """Queue every indexed record touched by this flush.

    Runs inside the flush, so the queue rows commit or roll back with the
    change that caused them. Core inserts rather than ORM objects: this is
    past the point where new ORM objects would be picked up.
    """
    changed = (*session.new, *session.dirty, *session.deleted)
    sheet_kinds = _sheet_kinds(
        session, {i.sheet_id for i in changed if isinstance(i, SheetRow) and i.sheet_id}
    )

    touched: set[tuple[str, int]] = set()
    for instance in changed:
        source = _source_of(instance, sheet_kinds)
        if source is not None and source[1] is not None:
            touched.add(source)
    if not touched:
        return

    for source_type, source_id in sorted(touched):
        session.execute(
            # OR IGNORE against the uniqueness of (source_type, source_id):
            # a record edited ten times before the queue drains is reindexed
            # once, from its final state.
            insert(IndexQueueEntry).prefix_with("OR IGNORE"),
            {"source_type": str(source_type), "source_id": source_id},
        )
