"""Stand-in for AFI's request back office. Replace with real calls if AFI exposes an API."""

from itertools import count

from afi_agent.models import Dossier, RequestDraft
from afi_agent.store import KnowledgeStore


class AfiziNotFound(Exception):
    pass


class AfiziConflict(Exception):
    pass


class AfiziMock:
    def __init__(self, store: KnowledgeStore) -> None:
        self._store = store
        self._drafts: dict[str, RequestDraft] = {}
        self._dossiers: dict[str, Dossier] = {}
        self._draft_ids = count(1)
        self._tracking_ids = count(1)
        self._ticket_ids = count(1)

    def create_draft(
        self,
        *,
        lot_id: str,
        applicant_name: str,
        company_name: str | None,
        activity: str,
        phone: str | None,
    ) -> RequestDraft:
        self._require_available(lot_id)
        draft = RequestDraft(
            id=f"DRAFT-{next(self._draft_ids):04d}",
            lot_id=lot_id,
            applicant_name=applicant_name,
            company_name=company_name,
            activity=activity,
            phone=phone,
            status="awaiting_confirmation",
        )
        self._drafts[draft.id] = draft
        return draft

    def get_draft(self, draft_id: str) -> RequestDraft | None:
        return self._drafts.get(draft_id)

    def confirm(self, draft_id: str) -> Dossier:
        """Submit a draft. Only the user-facing confirm endpoint calls this, never the agent."""
        draft = self._drafts.get(draft_id)
        if draft is None:
            raise AfiziNotFound(f"No draft with id {draft_id}")
        if draft.status == "submitted":
            raise AfiziConflict(f"Draft {draft_id} was already submitted")
        self._require_available(draft.lot_id)

        tracking_number = f"DEMO-{next(self._tracking_ids):04d}"
        dossier = Dossier(
            tracking_number=tracking_number,
            lot_id=draft.lot_id,
            applicant_name=draft.applicant_name,
            status="received",
            history=["Demande reçue (démonstration)"],
        )
        self._dossiers[tracking_number] = dossier
        self._drafts[draft_id] = draft.model_copy(
            update={"status": "submitted", "tracking_number": tracking_number}
        )
        self._store.reserve_lot(draft.lot_id)
        return dossier

    def get_dossier(self, tracking_number: str) -> Dossier | None:
        return self._dossiers.get(tracking_number.strip().upper())

    def escalate(self) -> str:
        return f"TICKET-{next(self._ticket_ids):04d}"

    def _require_available(self, lot_id: str) -> None:
        lot = self._store.get_lot(lot_id)
        if lot is None:
            raise AfiziNotFound(f"No lot with id {lot_id}")
        if lot.status != "available":
            raise AfiziConflict(f"Lot {lot_id} is {lot.status}, not available")
