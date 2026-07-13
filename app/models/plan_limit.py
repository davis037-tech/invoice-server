from ..extensions import db


class PlanLimit(db.Model):
    """
    Admin-editable default weekly invoice quota per plan tier. A tenant's
    actual limit is this value unless Tenant.invoice_limit_override is
    set, which always wins for that one tenant.

    Seeded on startup (see db_bootstrap.py) with sensible defaults if the
    table is empty, so the app works before an admin ever touches this.
    """
    __tablename__ = "plan_limits"

    plan          = db.Column(db.String, primary_key=True)  # "FREE" / "PRO" / "TEAM"
    weekly_limit  = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {"plan": self.plan, "weekly_limit": self.weekly_limit}
