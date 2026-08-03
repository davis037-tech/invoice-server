import uuid
from ..extensions import db


class DemoInvoiceLog(db.Model):
    """
    One row per demo (no-signup) invoice generated. Used purely to rate
    limit abuse of the public demo endpoint — the real "only once" limit
    is enforced client-side via localStorage, this is just a backstop so
    a script can't hammer the endpoint and rack up PDF-generation cost.
    """
    __tablename__ = "demo_invoice_logs"

    id          = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ip_address  = db.Column(db.String, nullable=True)
    created_at  = db.Column(db.DateTime, server_default=db.func.now())
